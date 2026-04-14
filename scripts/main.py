import argparse
from pathlib import Path

from tabulate import tabulate

from csp_loader import CspLookup, load_csp_entries_for_date
from hilbert_prefix_plots import save_combined_hilbert_prefix_plot
from plotting import ensure_output_dir
from services import SERVICE_ANALYSERS
from zgrab2_parser import iter_jsonl

OUTPUT_ROOT = Path("data") / "analysis"


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
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    entries, source = load_csp_entries_for_date(args.scan_date)
    csp_lookup = CspLookup.from_entries(entries)
    output_root = ensure_output_dir(args.output_root)
    implemented_services = {service.name for service in SERVICE_ANALYSERS}

    print(f"Loaded CSP entries from: {source}")
    print(f"Output root: {output_root.absolute()}\n")

    csp_rows = [(csp, len(networks), sum(net.num_addresses for net in networks)) for csp, networks in
                csp_lookup.networks_by_csp.items()]
    print(tabulate(csp_rows, headers=["CSP", "Number of prefixes", "Total IPv4 addresses"], intfmt=","))

    hilbert_output = output_root / "all-csps-hilbert-order.png"
    ensure_output_dir(hilbert_output.parent)
    print(f"\nRendering combined CSP Hilbert plot -> {hilbert_output.relative_to(output_root)}")
    save_combined_hilbert_prefix_plot(csp_lookup.networks_by_csp, hilbert_output)

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
                service.analyse(input_file, csp_lookup, output_root)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
