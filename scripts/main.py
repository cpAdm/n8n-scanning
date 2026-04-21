import argparse
from ipaddress import IPv4Network, IPv6Network, collapse_addresses
from pathlib import Path

from tabulate import SEPARATING_LINE, tabulate

from csp_loader import CspLookup, load_csp_entries_for_date
from hilbert_prefix_plots import save_combined_hilbert_prefix_plot
from plotting import ensure_output_dir, format_compact_number
from services import SERVICE_ANALYSERS
from vuln_lookup import NvdVulnerabilityLookup
from zgrab2_parser import iter_jsonl

OUTPUT_ROOT = Path("data") / "analysis"
TOTAL_IPV4_ADDRESSES = IPv4Network("0.0.0.0/0").num_addresses
TOTAL_IPV6_ADDRESSES = IPv6Network("::/0").num_addresses


def parse_args():
    parser = argparse.ArgumentParser(description="Run service analysis on one or more ZGrab 2.0 JSONL outputs.")
    parser.add_argument(
        "--scan-date",
        help=f"Scan date used for CSP lookup",
        required=True
    )
    parser.add_argument(
        "--input",
        dest="input_files",
        type=Path,
        nargs="+",
        action="extend",
        help="One or more ZGrab 2.0 JSONL files to analyse",
        required=True
    )
    parser.add_argument(
        "--output-root",
        dest="output_root",
        type=Path,
        default=OUTPUT_ROOT,
        help=f"Directory where analysis outputs are written (default: {OUTPUT_ROOT})",
    )
    parser.add_argument(
        "--nvd-api-key",
        dest="nvd_api_key",
        help="Optional NVD API key. Request one at https://nvd.nist.gov/developers/request-an-api-key . If omitted, unauthenticated NVD requests are throttled to one every 5 seconds.",
    )
    return parser.parse_args()


def print_csp_distribution(csp_lookup: CspLookup):
    def csp_row(csp: str, v4_networks: list, v6_networks: list) -> tuple[str, str, str, str, str]:
        return (
            csp,
            format_compact_number(len(v4_networks)),
            format_compact_number(sum(net.num_addresses for net in v4_networks)),
            format_compact_number(len(v6_networks)),
            format_compact_number(sum(net.num_addresses for net in v6_networks)),
        )

    csp_networks = [
        (csp, csp_lookup.networks_by_csp_v4.get(csp, []), csp_lookup.networks_by_csp_v6.get(csp, []))
        for csp in csp_lookup.all_csps
    ]
    csp_rows = [csp_row(csp, v4_networks, v6_networks) for csp, v4_networks, v6_networks in csp_networks]
    csp_rows.append(SEPARATING_LINE)
    total_v4_networks = [net for _csp, networks, _v6 in csp_networks for net in networks]
    total_v6_networks = [net for _csp, _v4, networks in csp_networks for net in networks]
    csp_rows.append(csp_row("TOTAL", total_v4_networks, total_v6_networks))

    print(
        tabulate(
            csp_rows,
            headers=[
                "CSP",
                "Number of IPv4 prefixes",
                "Total IPv4 addresses",
                "Number of IPv6 prefixes",
                "Total IPv6 addresses",
            ],
        )
    )

    def format_percent(covered: int, total: int) -> str:
        return f"{(covered * 100) / total:.6f}%"

    all_v4_networks = [net for networks in csp_lookup.collapsed_networks_by_csp_v4.values() for net in networks]
    all_v6_networks = [net for networks in csp_lookup.collapsed_networks_by_csp_v6.values() for net in networks]
    total_v4_covered = sum(net.num_addresses for net in collapse_addresses(all_v4_networks))
    total_v6_covered = sum(net.num_addresses for net in collapse_addresses(all_v6_networks))

    print(
        f"Combined CSP IPv4 coverage: {format_compact_number(total_v4_covered)} / "
        f"{format_compact_number(TOTAL_IPV4_ADDRESSES)} ({format_percent(total_v4_covered, TOTAL_IPV4_ADDRESSES)})"
    )
    print(
        f"Combined CSP IPv6 coverage: {format_compact_number(total_v6_covered)} / "
        f"{format_compact_number(TOTAL_IPV6_ADDRESSES)} ({format_percent(total_v6_covered, TOTAL_IPV6_ADDRESSES)})"
    )

def main() -> int:
    args = parse_args()

    entries, source = load_csp_entries_for_date(args.scan_date)
    csp_lookup = CspLookup.from_entries(entries)
    output_root = ensure_output_dir(args.output_root)
    vuln_lookup = NvdVulnerabilityLookup(nvd_api_key=args.nvd_api_key)
    implemented_services = {service.name for service in SERVICE_ANALYSERS}

    print(f"Loaded CSP entries from: {source}")
    print(f"Output root: {output_root.absolute()}\n")

    print_csp_distribution(csp_lookup)

    hilbert_output = output_root / "all-csps-hilbert-order.png"
    ensure_output_dir(hilbert_output.parent)
    print(f"\nRendering combined CSP Hilbert plot -> {hilbert_output.relative_to(output_root)}")
    save_combined_hilbert_prefix_plot(csp_lookup.networks_by_csp_v4, hilbert_output)

    print(f'\nProcessing {len(args.input_files)} input files...')
    for input_file in args.input_files:
        detected_services = set(next(iter_jsonl(input_file)).get("data").keys())

        if unknown_services := sorted(detected_services - implemented_services):
            print(
                f"WARNING: Input '{input_file}' contains unsupported services: "
                f"{', '.join(unknown_services)}"
            )

        # Only run those analyses for services that are actually present in the input file
        for service in SERVICE_ANALYSERS:
            if service.name in detected_services:
                print(f"\n\nAnalysing '{service.display_name}' service on input: {input_file}")
                service.analyse(input_file, csp_lookup, output_root, vuln_lookup)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
