"""Command-line interface for Volvo Car Financial Services to Monarch Money converter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional
from volvo_to_monarch import __version__
from volvo_to_monarch.cdp import TARGET_TAB_ID, capture_volvo_data
from volvo_to_monarch.exporter import export_monarch_files
from volvo_to_monarch.parser import parse_volvo_data


def find_default_input_file() -> Optional[Path]:
    """Look for standard Volvo raw JSON filenames in cwd or output directory."""
    candidates = [
        Path("volvo_raw_data.json"),
        Path("output/volvo_raw_data.json"),
        Path("volvo_raw_statements.json"),
        Path("output/volvo_raw_statements.json"),
        Path.home() / "volvo_raw_data.json",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None


def run_pipeline(
    input_file: Path,
    output_dir: Path,
    account_name: Optional[str] = None,
    merchant: str = "Volvo Car Financial Services",
    category: str = "Auto Loan",
    positive_balance: bool = False,
    positive_payment: bool = False,
    backfill_payment_one: bool = True,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> int:
    """Execute the parsing and conversion pipeline."""
    print("=" * 64)
    print(" Volvo Car Financial Services to Monarch Money Converter")
    print("=" * 64)
    print(f"Input file:        {input_file.resolve()}")
    print(f"Output directory:  {output_dir.resolve()}")
    print(f"Account name:      {account_name or '2022 Volvo XC40 Ultimate'}")
    print(f"Merchant name:     {merchant}")
    print(f"Liability sign:    {'Positive (+)' if positive_balance else 'Negative (-) [Monarch Standard]'}")
    print(f"Payment sign:      {'Positive (+)' if positive_payment else 'Negative (-) [Monarch Standard]'}")
    print("-" * 64)

    try:
        parsed_data = parse_volvo_data(
            raw_data_or_file=input_file,
            backfill_payment_one=backfill_payment_one,
            vehicle_name_override=account_name,
        )
    except Exception as e:
        print(f"❌ Error parsing input JSON: {e}", file=sys.stderr)
        return 1

    meta = parsed_data.metadata
    print(f"📋 Institution:     {meta.institution}")
    print(f"🚗 Vehicle:         {meta.vehicle_name} ({meta.vehicle_model})")
    print(f"🔒 Account Number:  {meta.account_number_masked} (VIN: {meta.vin})")
    print(f"📅 Contract Period: {meta.contract_start_date} to {meta.maturity_date} ({meta.contract_term} months)")
    print(f"💵 Monthly Payment: ${meta.monthly_payment:,.2f}")
    print(f"📈 Interest Rate:   {meta.interest_rate_percent:.3f}% APR")
    print(f"💰 Principal UPB:   ${meta.current_principal_balance:,.2f} (Payoff: ${meta.current_payoff_amount:,.2f})")
    print(f"🧾 Payments Status: {meta.payments_made} made, {meta.payments_remaining} remaining")
    print(f"💳 Transactions:    {len(parsed_data.transactions)} ledger entries loaded")

    try:
        summary = export_monarch_files(
            parsed_data=parsed_data,
            output_dir=output_dir,
            account_name=account_name,
            merchant=merchant,
            category=category,
            positive_balance=positive_balance,
            positive_payment=positive_payment,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as e:
        print(f"❌ Error exporting files: {e}", file=sys.stderr)
        return 1

    print("-" * 64)
    print("🎉 Export complete! Generated Monarch Money files:")
    print(f"  1. Transactions:     {summary['transactions_file']}")
    print(f"     -> {summary['transactions_count']} transactions")
    print(f"  2. Balance History:  {summary['balance_history_file']}")
    print(f"     -> {summary['balance_snapshots_count']} continuous daily snapshots")
    if summary["date_range"]:
        print(f"     -> Date Range:     {summary['date_range'][0]} to {summary['date_range'][1]}")
    print(f"     -> Latest Balance: ${float(summary['latest_balance']):,.2f}")
    print("=" * 64)
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    """Main CLI entrypoint for volvo-to-monarch."""
    parser = argparse.ArgumentParser(
        description="Extract Volvo Car Financial Services auto loan history and continuous daily balances for Monarch Money.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command")

    # 'all' subcommand (capture from CDP + convert)
    all_parser = subparsers.add_parser(
        "all",
        help="Capture live data from Chrome via CDP and export Monarch CSVs (default).",
    )
    all_parser.add_argument(
        "--port",
        type=int,
        default=9222,
        help="Chrome remote debugging port (default: 9222)",
    )
    all_parser.add_argument(
        "--tab-id",
        default=TARGET_TAB_ID,
        help=f"Chrome tab ID for Volvo portal (default: {TARGET_TAB_ID})",
    )
    all_parser.add_argument(
        "-f", "--raw-file",
        default="output/volvo_raw_data.json",
        help="Path to save captured raw JSON data (default: output/volvo_raw_data.json)",
    )

    # 'capture' subcommand (only capture from CDP)
    capture_parser = subparsers.add_parser(
        "capture",
        help="Capture live data from Chrome via CDP and save raw JSON.",
    )
    capture_parser.add_argument(
        "-f", "--output-file",
        default="output/volvo_raw_data.json",
        help="Destination path for captured JSON file (default: output/volvo_raw_data.json)",
    )
    capture_parser.add_argument(
        "--port",
        type=int,
        default=9222,
        help="Chrome remote debugging port (default: 9222)",
    )
    capture_parser.add_argument(
        "--tab-id",
        default=TARGET_TAB_ID,
        help=f"Chrome tab ID for Volvo portal (default: {TARGET_TAB_ID})",
    )
    capture_parser.add_argument(
        "--convert",
        action="store_true",
        default=False,
        help="Also convert captured JSON to Monarch CSV files",
    )

    # 'convert' subcommand (convert existing JSON)
    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert an existing Volvo raw JSON file to Monarch CSV format.",
    )
    convert_parser.add_argument(
        "input_file",
        nargs="?",
        default=None,
        help="Path to Volvo raw JSON file (defaults to standard names in current dir or output)",
    )

    # Add shared arguments to all parsers
    for p in [parser, all_parser, capture_parser, convert_parser]:
        p.add_argument(
            "-o", "-d", "--output-dir",
            default="./output",
            help="Directory to save generated Monarch CSV files (default: ./output)",
        )
        p.add_argument(
            "-a", "--account-name",
            default="2022 Volvo XC40 Ultimate",
            help="Monarch account name (default: '2022 Volvo XC40 Ultimate')",
        )
        p.add_argument(
            "-m", "--merchant",
            default="Volvo Car Financial Services",
            help="Merchant label for transactions (default: 'Volvo Car Financial Services')",
        )
        p.add_argument(
            "-c", "--category",
            default="Auto Loan",
            help="Monarch transaction category (default: 'Auto Loan')",
        )
        p.add_argument(
            "--positive-balance",
            action="store_true",
            help="Output liability balances as positive (default is negative per Monarch standard)",
        )
        p.add_argument(
            "--positive-payment",
            action="store_true",
            help="Output payment transactions as positive (default is negative per Monarch standard)",
        )
        p.add_argument(
            "--no-backfill",
            action="store_true",
            help="Do not backfill reconstructed Payment 1 (2022-05-19)",
        )
        p.add_argument(
            "--start-date",
            default=None,
            help="Optional start date filter (YYYY-MM-DD)",
        )
        p.add_argument(
            "--end-date",
            default=None,
            help="Optional end date filter (YYYY-MM-DD)",
        )

    clean_argv = list(argv) if argv is not None else sys.argv[1:]
    if not clean_argv:
        clean_argv = ["all"]
    elif clean_argv[0] not in ["all", "capture", "convert", "-h", "--help", "-v", "--version"]:
        if clean_argv[0].endswith(".json"):
            clean_argv = ["convert"] + clean_argv
        else:
            clean_argv = ["all"] + clean_argv

    args = parser.parse_args(clean_argv)
    out_dir = Path(args.output_dir)

    # Handle 'all' command
    if args.command == "all":
        raw_file = Path(getattr(args, "raw_file", "output/volvo_raw_data.json"))
        port = getattr(args, "port", 9222)
        tab_id = getattr(args, "tab_id", TARGET_TAB_ID)
        try:
            capture_volvo_data(port=port, target_tab_id=tab_id, output_file=raw_file, verbose=True)
        except Exception as e:
            print(f"❌ Browser capture failed: {e}", file=sys.stderr)
            # If raw file exists from prior capture, fallback to it
            if raw_file.exists():
                print(f"⚠️ Falling back to existing cached file: {raw_file}")
            else:
                return 1

        return run_pipeline(
            input_file=raw_file,
            output_dir=out_dir,
            account_name=args.account_name,
            merchant=args.merchant,
            category=args.category,
            positive_balance=args.positive_balance,
            positive_payment=args.positive_payment,
            backfill_payment_one=not args.no_backfill,
            start_date=args.start_date,
            end_date=args.end_date,
        )

    # Handle 'capture' command
    if args.command == "capture":
        out_json = Path(getattr(args, "output_file", "output/volvo_raw_data.json"))
        port = getattr(args, "port", 9222)
        tab_id = getattr(args, "tab_id", TARGET_TAB_ID)
        try:
            capture_volvo_data(port=port, target_tab_id=tab_id, output_file=out_json, verbose=True)
        except Exception as e:
            print(f"❌ Browser capture failed: {e}", file=sys.stderr)
            return 1

        if not getattr(args, "convert", False):
            return 0

        return run_pipeline(
            input_file=out_json,
            output_dir=out_dir,
            account_name=args.account_name,
            merchant=args.merchant,
            category=args.category,
            positive_balance=args.positive_balance,
            positive_payment=args.positive_payment,
            backfill_payment_one=not args.no_backfill,
            start_date=args.start_date,
            end_date=args.end_date,
        )

    # Handle 'convert' command
    input_str = getattr(args, "input_file", None)
    if input_str:
        input_path = Path(input_str)
        if not input_path.exists():
            print(f"❌ Input file not found: {input_path}", file=sys.stderr)
            return 1
    else:
        default_path = find_default_input_file()
        if default_path:
            input_path = default_path
        else:
            print("❌ No input file specified and no standard JSON file found.", file=sys.stderr)
            print("Run 'volvo-to-monarch all' or 'volvo-to-monarch capture' to capture from Chrome,", file=sys.stderr)
            print("or provide a path: 'volvo-to-monarch convert path/to/volvo_raw_data.json'", file=sys.stderr)
            return 1

    return run_pipeline(
        input_file=input_path,
        output_dir=out_dir,
        account_name=args.account_name,
        merchant=args.merchant,
        category=args.category,
        positive_balance=args.positive_balance,
        positive_payment=args.positive_payment,
        backfill_payment_one=not args.no_backfill,
        start_date=args.start_date,
        end_date=args.end_date,
    )


if __name__ == "__main__":
    sys.exit(main())
