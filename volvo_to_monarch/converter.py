"""Converters from Volvo Car Financial Services transactions into Monarch Money CSV data."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from volvo_to_monarch.parser import VolvoTransaction


def convert_to_monarch_transactions(
    transactions: List[VolvoTransaction],
    account_name: str = "2022 Volvo XC40 Ultimate",
    merchant: str = "Volvo Car Financial Services",
    category: str = "Auto Loan",
    positive_payment: bool = False,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Convert Volvo transactions into Monarch Money transactions schema.

    Monarch Money Schema:
    Date,Merchant,Category,Account,Original Statement,Notes,Amount

    Monarch Liability Account Conventions:
    - Payments that pay down the auto loan balance are negative numbers (e.g. -1014.55),
      unless positive_payment=True is explicitly set.
    """
    rows: List[Dict[str, Any]] = []

    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

    for tx in transactions:
        tx_dt = datetime.strptime(tx.date, "%Y-%m-%d").date()
        if start_dt and tx_dt < start_dt:
            continue
        if end_dt and tx_dt > end_dt:
            continue

        amt = abs(tx.total_amount)
        signed_amount = amt if positive_payment else -amt

        orig_statement = f"Volvo Car Financial Services Ach payment - Payment {tx.payment_number}/72"

        notes_parts = [f"Payment #{tx.payment_number} of 72"]
        if tx.principal_amount > 0:
            notes_parts.append(f"Principal: ${tx.principal_amount:,.2f}")
        if tx.interest_amount > 0:
            notes_parts.append(f"Interest: ${tx.interest_amount:,.2f}")
        if tx.remaining_principal_balance > 0:
            notes_parts.append(f"Remaining UPB: ${tx.remaining_principal_balance:,.2f}")
        if tx.payoff_amount and tx.payoff_amount > 0:
            notes_parts.append(f"Payoff Quote: ${tx.payoff_amount:,.2f}")
        if tx.due_date and tx.due_date != tx.date:
            notes_parts.append(f"Due: {tx.due_date}")

        notes = " | ".join(notes_parts)

        rows.append({
            "Date": tx.date,
            "Merchant": merchant,
            "Category": category,
            "Account": account_name,
            "Original Statement": orig_statement,
            "Notes": notes,
            "Amount": f"{signed_amount:.2f}",
        })

    return rows


def convert_to_monarch_balance_history(
    checkpoints: Dict[str, float],
    initial_balance: Optional[float] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    positive_balance: bool = False,
) -> List[Dict[str, str]]:
    """Generate continuous daily balance history from Volvo loan balance checkpoints.

    Monarch Money Schema:
    Date,Balance

    Monarch Liability Account Conventions:
    - Liability balances (auto loans / debt) must be negative numbers (e.g. -15000.00)
    - for Monarch to properly calculate Net Worth, unless positive_balance=True.
    - Forward-fills daily so continuous net worth charts render smoothly without gaps.
    """
    if not checkpoints and initial_balance is None:
        return []

    sorted_dates = sorted(checkpoints.keys())
    if not sorted_dates and initial_balance is None:
        return []

    first_recorded_date = sorted_dates[0] if sorted_dates else start_date
    actual_start = start_date or first_recorded_date
    actual_end = end_date or datetime.today().strftime("%Y-%m-%d")

    start_dt = datetime.strptime(actual_start, "%Y-%m-%d").date()
    end_dt = datetime.strptime(actual_end, "%Y-%m-%d").date()

    if end_dt < start_dt:
        start_dt, end_dt = end_dt, start_dt

    if initial_balance is not None:
        current_bal = initial_balance
    elif sorted_dates:
        current_bal = checkpoints[sorted_dates[0]]
    else:
        current_bal = 0.0

    rows: List[Dict[str, str]] = []
    curr_dt = start_dt

    while curr_dt <= end_dt:
        curr_str = curr_dt.strftime("%Y-%m-%d")
        if curr_str in checkpoints:
            current_bal = checkpoints[curr_str]

        val = abs(current_bal) if positive_balance else -abs(current_bal)
        rows.append({
            "Date": curr_str,
            "Balance": f"{val:.2f}",
        })
        curr_dt += timedelta(days=1)

    return rows
