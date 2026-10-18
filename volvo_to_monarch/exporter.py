"""CSV Exporter for Volvo Car Financial Services to Monarch Money formatted files."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Optional, Union
from volvo_to_monarch.converter import (
    convert_to_monarch_balance_history,
    convert_to_monarch_transactions,
)
from volvo_to_monarch.parser import ParsedVolvoData


def export_monarch_files(
    parsed_data: ParsedVolvoData,
    output_dir: Union[str, Path] = "./output",
    account_name: Optional[str] = None,
    merchant: str = "Volvo Car Financial Services",
    category: str = "Auto Loan",
    positive_balance: bool = False,
    positive_payment: bool = False,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Export parsed Volvo auto loan data to Monarch Money CSV files.

    Generates:
    1. volvo_monarch_transactions.csv
    2. volvo_monarch_balance_history.csv

    Returns:
        Summary dictionary with output file paths, record counts, and date ranges.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    acct_name = account_name or parsed_data.metadata.vehicle_name

    # 1. Transactions CSV
    tx_rows = convert_to_monarch_transactions(
        transactions=parsed_data.transactions,
        account_name=acct_name,
        merchant=merchant,
        category=category,
        positive_payment=positive_payment,
        start_date=start_date,
        end_date=end_date,
    )

    tx_file = out_dir / "volvo_monarch_transactions.csv"
    with open(tx_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "Date",
                "Merchant",
                "Category",
                "Account",
                "Original Statement",
                "Notes",
                "Amount",
            ],
        )
        writer.writeheader()
        writer.writerows(tx_rows)

    # 2. Balance History CSV
    initial_bal = parsed_data.metadata.original_loan_balance
    bal_start = start_date or parsed_data.metadata.contract_start_date

    bal_rows = convert_to_monarch_balance_history(
        checkpoints=parsed_data.balance_checkpoints,
        initial_balance=initial_bal,
        start_date=bal_start,
        end_date=end_date,
        positive_balance=positive_balance,
    )

    bal_file = out_dir / "volvo_monarch_balance_history.csv"
    with open(bal_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Date", "Balance"])
        writer.writeheader()
        writer.writerows(bal_rows)

    date_range = None
    if bal_rows:
        date_range = (bal_rows[0]["Date"], bal_rows[-1]["Date"])

    latest_bal = bal_rows[-1]["Balance"] if bal_rows else "0.00"

    return {
        "transactions_file": str(tx_file.resolve()),
        "transactions_count": len(tx_rows),
        "balance_history_file": str(bal_file.resolve()),
        "balance_snapshots_count": len(bal_rows),
        "date_range": date_range,
        "latest_balance": latest_bal,
    }
