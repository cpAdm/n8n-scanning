import json
import urllib.request
from bisect import bisect_right
from dataclasses import dataclass
from functools import cached_property
from ipaddress import IPv4Address, IPv4Network, collapse_addresses, ip_network
from typing import Any

DEFAULT_REPO_BASE_URL = "https://github.com/cpAdm/csp-ip-ranges/raw/refs/heads/main/data"

type CspEntry = dict[str, Any]
type CspEntries = list[CspEntry]


@dataclass(frozen=True)
class CspLookup:
    """Raw IPv4 networks keyed by CSP name"""
    networks_by_csp: dict[str, list[IPv4Network]]

    @cached_property
    def collapsed_networks_by_csp(self) -> dict[str, list[IPv4Network]]:
        # Collapse overlapping and adjacent networks for each CSP once on first access
        return {csp: list(collapse_addresses(networks)) for csp, networks in self.networks_by_csp.items()}

    @staticmethod
    def from_entries(entries: CspEntries) -> "CspLookup":
        networks_by_csp: dict[str, list[IPv4Network]] = {}

        for entry in entries:
            csp = entry["csp"]
            prefix = entry["ipPrefix"]
            parsed_network = ip_network(prefix, strict=False)
            # We only scan IPv4 networks, so skip any IPv6 entries and any private ranges
            if isinstance(parsed_network, IPv4Network):
                networks_by_csp.setdefault(csp, []).append(parsed_network)

        return CspLookup(networks_by_csp)

    @cached_property
    def _ranges(self):
        ranges = []

        for csp, networks in self.collapsed_networks_by_csp.items():
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

    # A fast lookup method using binary search on the sorted ranges
    def find_csp(self, ip: str) -> str:
        ip_int = int(IPv4Address(ip))
        i = bisect_right(self._ranges, (ip_int, float("inf"), "")) - 1
        if i >= 0:
            start, end, csp = self._ranges[i]
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
