import json
import re
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal, NotRequired, TypedDict
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from service_types import ServiceAnalyserProto
from utils import MemoCache

# https://nvd.nist.gov/developers/products
NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_RESULTS_PER_PAGE = 2000

MatchConfidence = Literal["exact", "range", "broad", "none"]
MatchTier = Literal["exact", "range", "broad"]
SeverityLevel = Literal["critical", "high", "medium", "low"]
MATCH_TIERS: tuple[MatchTier, ...] = ("exact", "range", "broad")
SEVERITY_LEVELS: tuple[SeverityLevel, ...] = ("critical", "high", "medium", "low")
MATCH_CONFIDENCE_RANK: dict[MatchConfidence, int] = {
    "none": 0,
    "broad": 1,
    "range": 2,
    "exact": 3,
}

VERSION_NUMBER_RE = re.compile(r"\d+")


class NvdCpeMatch(TypedDict):
    vulnerable: bool
    criteria: str
    matchCriteriaId: str
    versionStartIncluding: NotRequired[str]
    versionStartExcluding: NotRequired[str]
    versionEndIncluding: NotRequired[str]
    versionEndExcluding: NotRequired[str]


class NvdNode(TypedDict):
    operator: str
    cpeMatch: list[NvdCpeMatch]
    negate: NotRequired[bool]


class NvdConfig(TypedDict):
    nodes: list[NvdNode]
    operator: NotRequired[str]
    negate: NotRequired[bool]


class NvdCvssData(TypedDict):
    baseScore: float
    attackVector: NotRequired[str]
    privilegesRequired: NotRequired[str]
    accessVector: NotRequired[str]
    authentication: NotRequired[str]


class NvdMetric(TypedDict):
    cvssData: NvdCvssData


class NvdMetrics(TypedDict):
    cvssMetricV40: NotRequired[list[NvdMetric]]
    cvssMetricV31: NotRequired[list[NvdMetric]]
    cvssMetricV30: NotRequired[list[NvdMetric]]
    cvssMetricV2: NotRequired[list[NvdMetric]]


class CveRecord(TypedDict):
    id: str
    configurations: NotRequired[list[NvdConfig]]
    metrics: NotRequired[NvdMetrics]


class NvdVulnerabilityItem(TypedDict):
    cve: CveRecord


# See: https://csrc.nist.gov/schema/nvd/api/2.0/cve_api_json_2.0.schema
class NvdApiResponse(TypedDict):
    resultsPerPage: int
    startIndex: int
    totalResults: int
    format: str
    version: str
    timestamp: str
    vulnerabilities: list[NvdVulnerabilityItem]


@dataclass(frozen=True)
class VulnerabilityResult:
    cve_ids_by_confidence: dict[MatchTier, list[str]]

    @property
    def cve_ids(self) -> list[str]:
        return sorted({cve_id for tier in MATCH_TIERS for cve_id in self.cve_ids_by_confidence.get(tier, [])})

    @property
    def confidence(self) -> MatchConfidence:
        for tier in MATCH_TIERS:
            if self.cve_ids_by_confidence.get(tier):
                return tier
        return "none"

    @property
    def cve_count(self) -> int:
        return len(self.cve_ids)


def _normalize_version(value: str) -> str:
    return value.lower().lstrip('v')


class CpeMatchClassifier:
    @staticmethod
    @lru_cache(maxsize=4096)
    def parse_version_numbers(value: str) -> tuple[int, ...]:
        return tuple(int(part) for part in VERSION_NUMBER_RE.findall(value))

    @classmethod
    def versions_equal(cls, left: str, right: str) -> bool:
        left_numbers = cls.parse_version_numbers(left)
        right_numbers = cls.parse_version_numbers(right)
        if left_numbers and right_numbers:
            return left_numbers == right_numbers
        return left.strip().lower() == right.strip().lower()

    @classmethod
    def is_version_in_range(cls, version: str, cpe_match: NvdCpeMatch) -> bool:
        current = cls.parse_version_numbers(version)
        if not current:
            return False

        if start_including := cpe_match.get("versionStartIncluding"):
            start_including_tuple = cls.parse_version_numbers(start_including)
            if start_including_tuple and current < start_including_tuple:
                return False

        if start_excluding := cpe_match.get("versionStartExcluding"):
            start_excluding_tuple = cls.parse_version_numbers(start_excluding)
            if start_excluding_tuple and current <= start_excluding_tuple:
                return False

        if end_including := cpe_match.get("versionEndIncluding"):
            end_including_tuple = cls.parse_version_numbers(end_including)
            if end_including_tuple and current > end_including_tuple:
                return False

        if end_excluding := cpe_match.get("versionEndExcluding"):
            end_excluding_tuple = cls.parse_version_numbers(end_excluding)
            if end_excluding_tuple and current >= end_excluding_tuple:
                return False

        return True

    @staticmethod
    def has_version_range(cpe_match: NvdCpeMatch) -> bool:
        return bool(
            cpe_match.get("versionStartIncluding")
            or cpe_match.get("versionStartExcluding")
            or cpe_match.get("versionEndIncluding")
            or cpe_match.get("versionEndExcluding")
        )

    @classmethod
    def classify(cls, version: str, cpe_match: NvdCpeMatch) -> MatchConfidence:
        cpe_parts = cpe_match["criteria"].lower().split(":")
        cpe_version = cpe_parts[5] if len(cpe_parts) > 5 else ""

        if cpe_version not in {"", "*", "-"} and cls.versions_equal(cpe_version, version):
            return "exact"

        has_range = cls.has_version_range(cpe_match)
        if has_range and cls.is_version_in_range(version, cpe_match):
            return "range"

        # Wildcard CPE with no bounds is broad/low-confidence coverage.
        if cpe_version in {"*", "-"} and not has_range:
            return "broad"

        return "none"


def _pick_stronger_confidence(left: MatchConfidence, right: MatchConfidence) -> MatchConfidence:
    return left if MATCH_CONFIDENCE_RANK[left] >= MATCH_CONFIDENCE_RANK[right] else right


def _match_single_cve(cve: CveRecord, version: str, cpe_prefixes: tuple[str, ...]) -> MatchConfidence:
    best_match: MatchConfidence = "none"

    for config in cve.get("configurations", []):
        for node in config["nodes"]:
            for cpe_match in node["cpeMatch"]:
                if not cpe_match.get("vulnerable"):
                    continue

                if not cpe_match["criteria"].lower().startswith(cpe_prefixes):
                    continue

                match_type = CpeMatchClassifier.classify(version, cpe_match)
                best_match = _pick_stronger_confidence(best_match, match_type)

                if best_match == "exact":
                    return best_match

    return best_match


def _severity_from_base_score(base_score: float) -> SeverityLevel:
    if base_score >= 9.0:
        return "critical"
    if base_score >= 7.0:
        return "high"
    if base_score >= 4.0:
        return "medium"
    return "low"


def _extract_cve_severity(cve: CveRecord) -> SeverityLevel | None:
    metrics = cve.get("metrics")
    if not metrics:
        return None

    best_score: float | None = None
    for metric_entries in (
            metrics.get("cvssMetricV40", []),
            metrics.get("cvssMetricV31", []),
            metrics.get("cvssMetricV30", []),
            metrics.get("cvssMetricV2", []),
    ):
        for entry in metric_entries:
            score = float(entry["cvssData"]["baseScore"])
            if best_score is None or score > best_score:
                best_score = score

    if best_score is None:
        return None

    return _severity_from_base_score(best_score)


def _is_network_no_privileges(cve: CveRecord) -> bool:
    metrics = cve.get("metrics")
    if not metrics:
        return False

    for metric_entries in (
            metrics.get("cvssMetricV40", []),
            metrics.get("cvssMetricV31", []),
            metrics.get("cvssMetricV30", []),
            metrics.get("cvssMetricV2", []),
    ):
        for entry in metric_entries:
            cvss_data = entry["cvssData"]
            attack_vector = str(cvss_data.get("attackVector", cvss_data.get("accessVector", ""))).upper()
            if attack_vector != "NETWORK":
                continue

            privileges = str(cvss_data.get("privilegesRequired", cvss_data.get("authentication", ""))).upper()
            if privileges == "NONE":
                return True

    return False


class NvdVulnerabilityLookup:
    def __init__(self, nvd_api_key: str | None = None):
        self.nvd_api_key = nvd_api_key.strip() if nvd_api_key else None
        self._lookup_result_cache: MemoCache[str, VulnerabilityResult] = MemoCache()
        self._service_cves_cache: MemoCache[str, list[CveRecord]] = MemoCache()
        self._merged_service_cves_cache: MemoCache[str, list[CveRecord]] = MemoCache()
        self._severity_counts_cache: MemoCache[tuple[str, tuple[str, ...]], dict[SeverityLevel, int]] = MemoCache()
        self._network_no_priv_cache: MemoCache[tuple[str, tuple[str, ...]], list[str]] = MemoCache()

    @staticmethod
    def _version_cache_key(service_name: str, version: str) -> str:
        return f"{service_name}|{version}"

    @staticmethod
    def _service_cache_key(query_mode: str, query_value: str) -> str:
        return f"{query_mode}|{query_value.lower()}"

    def lookup(self, service: ServiceAnalyserProto, version: str) -> VulnerabilityResult:
        normalized_version = _normalize_version(version)
        if not normalized_version:
            return VulnerabilityResult(cve_ids_by_confidence=self._empty_match_map())

        return self._lookup_result_cache.get_or_compute(
            key=self._version_cache_key(service.name, normalized_version),
            factory=lambda: self._match_against_service_cves(service, normalized_version),
        )

    @staticmethod
    def _empty_match_map() -> dict[MatchTier, list[str]]:
        return {tier: [] for tier in MATCH_TIERS}

    def severity_counts_for_cves(self, service: ServiceAnalyserProto, cve_ids: list[str]) -> dict[SeverityLevel, int]:
        unique_ids = tuple(sorted(set(cve_ids)))
        if not unique_ids:
            return {level: 0 for level in SEVERITY_LEVELS}

        memo_key = (service.name, unique_ids)

        def _compute_counts() -> dict[SeverityLevel, int]:
            counts = {level: 0 for level in SEVERITY_LEVELS}
            cves_by_id = {cve["id"]: cve for cve in self._fetch_service_cves(service)}
            for cve_id in unique_ids:
                cve = cves_by_id.get(cve_id)
                if not cve:
                    continue

                if severity := _extract_cve_severity(cve):
                    counts[severity] += 1
            return counts

        return dict(self._severity_counts_cache.get_or_compute(memo_key, _compute_counts))

    def network_no_privilege_cve_ids_for_cves(self, service: ServiceAnalyserProto, cve_ids: list[str]) -> list[str]:
        unique_ids = tuple(sorted(set(cve_ids)))
        if not unique_ids:
            return []

        memo_key = (service.name, unique_ids)

        def _compute_matches() -> list[str]:
            cves_by_id = {cve["id"]: cve for cve in self._fetch_service_cves(service)}
            matches: list[str] = []
            for cve_id in unique_ids:
                cve = cves_by_id.get(cve_id)
                if cve and _is_network_no_privileges(cve):
                    matches.append(cve_id)
            return matches

        return list(self._network_no_priv_cache.get_or_compute(memo_key, _compute_matches))

    def _match_against_service_cves(self, service: ServiceAnalyserProto, version: str) -> VulnerabilityResult:
        cpe_prefixes = service.nvd_cpe_prefixes
        cves = self._fetch_service_cves(service)
        if not cves:
            return VulnerabilityResult(cve_ids_by_confidence=self._empty_match_map())

        matches_by_tier = self._empty_match_map()

        for cve in cves:
            cve_id = str(cve.get("id", "")).strip()
            if not cve_id:
                continue

            match_type = _match_single_cve(cve, version, cpe_prefixes)
            if match_type != "none":
                matches_by_tier[match_type].append(cve_id)

        for tier in MATCH_TIERS:
            matches_by_tier[tier] = sorted(set(matches_by_tier[tier]))

        return VulnerabilityResult(cve_ids_by_confidence=matches_by_tier)

    def _fetch_cves_for_query(self, cache_key: str, query_params: dict[str, Any]) -> list[CveRecord]:
        def _fetch_all() -> list[CveRecord]:
            start_index = 0
            total_results = None
            all_cves: list[CveRecord] = []

            # Results are paginated, so we need to loop until we've fetched all results.
            while total_results is None or start_index < total_results:
                headers = {"User-Agent": "scanning-container-vuln-lookup/1.0"}
                if self.nvd_api_key:
                    headers["apiKey"] = self.nvd_api_key

                print(f"Fetching CVEs with query params: {query_params}, start index: {start_index}")
                request = Request(
                    f"{NVD_API_URL}?{urlencode({
                        **query_params,
                        "resultsPerPage": NVD_RESULTS_PER_PAGE,
                        "startIndex": start_index,
                    })}",
                    headers=headers,
                )

                with urlopen(request) as response:
                    payload: NvdApiResponse = json.loads(response.read().decode("utf-8"))

                if not self.nvd_api_key:
                    # Keep within the public no-key rate limit budget.
                    # https://nvd.nist.gov/developers/start-here#divRateLimits
                    time.sleep(5)

                if total_results is None:
                    total_results = int(payload["totalResults"])

                page_items = payload["vulnerabilities"]
                if not page_items:
                    break

                for item in page_items:
                    cve = item.get("cve")
                    if not cve:
                        continue
                    all_cves.append(
                        {
                            "id": cve["id"],
                            "configurations": cve.get("configurations", []),
                            "metrics": cve.get("metrics", {}),
                        }
                    )

                start_index += len(page_items)

            return all_cves

        return list(self._service_cves_cache.get_or_compute(cache_key, _fetch_all))

    def _fetch_service_cves(self, service: ServiceAnalyserProto) -> list[CveRecord]:
        service_key = f"{service.name}|{','.join(sorted(set(service.nvd_cpe_prefixes)))}"

        def _merge_service_cves() -> list[CveRecord]:
            merged: dict[str, CveRecord] = {}
            for cpe_prefix in sorted(set(service.nvd_cpe_prefixes)):
                cpe_name = f"{cpe_prefix.rstrip(':')}:*:*:*:*:*:*:*:*"
                cache_key = self._service_cache_key("virtual_match", cpe_name)
                cves = self._fetch_cves_for_query(cache_key, {"virtualMatchString": cpe_name})
                for cve in cves:
                    if cve_id := str(cve.get("id", "")).strip():
                        merged[cve_id] = cve
            return list(merged.values())

        return list(self._merged_service_cves_cache.get_or_compute(service_key, _merge_service_cves))
