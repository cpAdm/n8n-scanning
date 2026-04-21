import json
import urllib.request
from bisect import bisect_right
from dataclasses import dataclass
from functools import cached_property
from ipaddress import IPv4Address, IPv4Network, IPv6Network, collapse_addresses, ip_network
from typing import Any

DEFAULT_REPO_BASE_URL = "https://github.com/cpAdm/csp-ip-ranges/raw/refs/heads/main/data"

type CspEntry = dict[str, Any]
type CspEntries = list[CspEntry]


@dataclass(frozen=True)
class CspLookup:
    """Raw CSP networks split by IP version"""
    networks_by_csp_v4: dict[str, list[IPv4Network]]
    networks_by_csp_v6: dict[str, list[IPv6Network]]

    @property
    def all_csps(self) -> list[str]:
        return sorted(set(self.networks_by_csp_v4) | set(self.networks_by_csp_v6))

    @cached_property
    def collapsed_networks_by_csp_v4(self) -> dict[str, list[IPv4Network]]:
        return {csp: list(collapse_addresses(networks)) for csp, networks in self.networks_by_csp_v4.items()}

    @cached_property
    def collapsed_networks_by_csp_v6(self) -> dict[str, list[IPv6Network]]:
        return {csp: list(collapse_addresses(networks)) for csp, networks in self.networks_by_csp_v6.items()}

    @staticmethod
    def from_entries(entries: CspEntries) -> "CspLookup":
        networks_by_csp_v4: dict[str, list[IPv4Network]] = {}
        networks_by_csp_v6: dict[str, list[IPv6Network]] = {}

        for entry in entries:
            csp = entry["csp"]
            prefix = entry["ipPrefix"]
            parsed_network = ip_network(prefix, strict=False)
            if isinstance(parsed_network, IPv4Network):
                networks_by_csp_v4.setdefault(csp, []).append(parsed_network)
            elif isinstance(parsed_network, IPv6Network):
                networks_by_csp_v6.setdefault(csp, []).append(parsed_network)

        return CspLookup(networks_by_csp_v4, networks_by_csp_v6)

    @cached_property
    def _ranges_v4(self) -> list[tuple[int, int, str]]:
        return self._build_ranges(self.collapsed_networks_by_csp_v4)

    @cached_property
    def _ranges_v6(self) -> list[tuple[int, int, str]]:
        return self._build_ranges(self.collapsed_networks_by_csp_v6)

    @staticmethod
    def _build_ranges(networks_by_csp: dict[str, list[IPv4Network | IPv6Network]]) -> list[tuple[int, int, str]]:
        ranges: list[tuple[int, int, str]] = []

        for csp, networks in networks_by_csp.items():
            for net in networks:
                start = int(net.network_address)
                end = int(net.broadcast_address)
                ranges.append((start, end, csp))

        # Sort by start address
        ranges.sort(key=lambda x: x[0])

        # Sanity check: ensure no overlaps across CSPs
        for i in range(1, len(ranges)):
            prev_start, prev_end, prev_csp = ranges[i - 1]
            start, end, csp = ranges[i]
            if start <= prev_end:
                if csp != prev_csp:
                    raise ValueError(
                        f"Overlap detected: {prev_start}-{prev_end} ({prev_csp}) "
                        f"conflicts with {start}-{end} ({csp})"
                    )

        return ranges

    # A fast lookup method using binary search on the sorted IPv4 ranges
    def find_csp(self, ip: str) -> str:
        ip_int = int(IPv4Address(ip))
        i = bisect_right(self._ranges_v4, (ip_int, float("inf"), "")) - 1
        if i >= 0:
            start, end, csp = self._ranges_v4[i]
            if start <= ip_int <= end:
                return csp

        raise ValueError(f"IP {ip} did not match any CSP")


def load_json_from_url(url: str) -> Any:
    with urllib.request.urlopen(url) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def load_csp_entries_for_date(date: str) -> tuple[CspEntries, str]:
    source = f"{DEFAULT_REPO_BASE_URL}/{date}.json"
    parsed = load_json_from_url(source)
    prefixes = parsed["prefixes"]
    return prefixes, source
