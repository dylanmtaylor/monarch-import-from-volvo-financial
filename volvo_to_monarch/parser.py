"""Parser for Volvo Car Financial Services raw captured loan and statement data."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """Normalize date string to ISO YYYY-MM-DD."""
    if not date_str:
        return None
    date_clean = date_str.strip().split()[0]
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_clean, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_clean


@dataclass
class VolvoLoanMetadata:
    """Metadata describing the Volvo auto loan contract."""
    institution: str = "Volvo Car Financial Services"
    account_number: str = "000000000000000000"
    account_number_masked: str = "...0000"
    vehicle_name: str = "2022 Volvo XC40 Ultimate"
    vehicle_model: str = "C40 RECHAR"
    vin: str = "YV400000000000000"
    contract_start_date: str = "2022-04-04"
    maturity_date: str = "2028-04-19"
    contract_term: int = 72
    monthly_payment: float = 0.0
    current_principal_balance: float = 0.0
    current_payoff_amount: float = 0.0
    interest_rate_percent: float = 0.0
    original_loan_balance: float = 0.0
    payments_made: int = 53
    payments_remaining: int = 19


@dataclass
class VolvoTransaction:
    """Single Volvo auto loan payment transaction."""
    payment_number: int
    date: str
    statement_date: Optional[str] = None
    due_date: Optional[str] = None
    total_amount: float = 1014.55
    principal_amount: float = 0.0
    interest_amount: float = 0.0
    remaining_principal_balance: float = 0.0
    payoff_amount: Optional[float] = None
    description: str = "Ach payment"
    status: str = "Posted"


@dataclass
class ParsedVolvoData:
    """Full parsed Volvo dataset ready for Monarch conversion."""
    metadata: VolvoLoanMetadata
    transactions: List[VolvoTransaction] = field(default_factory=list)
    balance_checkpoints: Dict[str, float] = field(default_factory=dict)


def calculate_derived_apr(statements: List[Dict[str, Any]]) -> float:
    """Calculate the simple interest APR from statement finance charges and balances.

    Formula: APR = (Finance Charge * 365) / (Principal Balance * Days in period)
    """
    valid_rates = []
    for i in range(1, len(statements)):
        prev = statements[i - 1]
        curr = statements[i]
        fin_chg = curr.get("interest_amount")
        bal = prev.get("payoff_amount")
        d_prev = normalize_date(prev.get("payment_date") or prev.get("statement_date"))
        d_curr = normalize_date(curr.get("payment_date") or curr.get("statement_date"))

        if fin_chg and bal and bal > 0 and d_prev and d_curr:
            try:
                dt_prev = datetime.strptime(d_prev, "%Y-%m-%d").date()
                dt_curr = datetime.strptime(d_curr, "%Y-%m-%d").date()
                days = (dt_curr - dt_prev).days
                if 25 <= days <= 35:
                    apr = (fin_chg * 365.0) / (bal * days) * 100.0
                    if 2.5 <= apr <= 4.5:
                        valid_rates.append(apr)
            except Exception:
                pass

    if valid_rates:
        return round(sum(valid_rates) / len(valid_rates), 3)
    return 3.097


def parse_volvo_data(
    raw_data_or_file: Union[dict, str, Path],
    backfill_payment_one: bool = True,
    vehicle_name_override: Optional[str] = None,
) -> ParsedVolvoData:
    """Parse raw captured Volvo JSON or file into structured ParsedVolvoData.

    Args:
        raw_data_or_file: Dict of raw JSON or path to JSON file.
        backfill_payment_one: Whether to backfill reconstructed Payment 1 (2022-05-19)
            if the portal only lists digital statements starting from Payment 2.
        vehicle_name_override: Optional custom vehicle name for Monarch display.

    Returns:
        ParsedVolvoData instance with validated metadata, ledger, and balance checkpoints.
    """
    if isinstance(raw_data_or_file, (str, Path)):
        with open(raw_data_or_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
    else:
        raw = raw_data_or_file

    acct_details = raw.get("account_details", {})
    dash_info = raw.get("dashboard_info", {})
    payoff_data = raw.get("payoff_data", {})
    raw_statements = raw.get("statements", [])

    # Metadata extraction
    acct_num = acct_details.get("accountNumber") or "000000000000000000"
    acct_masked = f"...{acct_num[-4:]}" if len(acct_num) >= 4 else acct_num
    vin = acct_details.get("vinNumber") or "YV400000000000000"
    model = acct_details.get("vehicleModel") or "C40 RECHAR"
    vname = vehicle_name_override or "2022 Volvo XC40 Ultimate"

    start_date = normalize_date(acct_details.get("contractStartDate")) or "2022-04-04"
    end_date = normalize_date(acct_details.get("contractEndDate")) or "2028-04-19"
    term = acct_details.get("contractTerm") or dash_info.get("term") or 72

    mo_payment = float(dash_info.get("paymentAmount") or 0.0)
    curr_principal = float(dash_info.get("currentPrincipalBalance") or 0.0)
    payoff_amount = float(payoff_data.get("payoffAmount") or 0.0)
    payments_made = int(dash_info.get("paymentsMade") or 0)
    payments_remaining = term - payments_made

    # Deduplicate statements by payments_made or statement_date
    deduped: Dict[int, Dict[str, Any]] = {}
    for s in raw_statements:
        pm = s.get("payments_made")
        if pm is not None:
            if pm not in deduped:
                deduped[pm] = s
        else:
            # Fallback key by statement date
            key = hash(s.get("statement_date"))
            if key not in deduped:
                deduped[key] = s

    sorted_raw = sorted(deduped.values(), key=lambda x: x.get("payments_made") or 0)
    derived_apr = calculate_derived_apr(sorted_raw)

    # Convert to VolvoTransaction objects
    transactions: List[VolvoTransaction] = []
    balance_checkpoints: Dict[str, float] = {}

    for s in sorted_raw:
        pm_num = s.get("payments_made")
        p_date = normalize_date(s.get("payment_date")) or normalize_date(s.get("statement_date"))
        s_date = normalize_date(s.get("statement_date"))
        due_d = normalize_date(s.get("due_date"))

        tot_amt = s.get("payment_amount") or mo_payment
        pr_amt = s.get("principal_amount") or 0.0
        int_amt = s.get("interest_amount") or 0.0
        po_amt = s.get("payoff_amount")

        # Running principal balance from payoff amount
        rem_balance = po_amt if po_amt is not None else 0.0

        tx = VolvoTransaction(
            payment_number=pm_num if pm_num is not None else len(transactions) + 1,
            date=p_date or s_date or "2022-01-01",
            statement_date=s_date,
            due_date=due_d,
            total_amount=tot_amt,
            principal_amount=pr_amt,
            interest_amount=int_amt,
            remaining_principal_balance=rem_balance,
            payoff_amount=po_amt,
            description="Ach payment",
            status="Posted",
        )
        transactions.append(tx)
        if p_date and rem_balance > 0:
            balance_checkpoints[p_date] = rem_balance

    # Handle Payment 1 reconstruction if needed
    has_p1 = any(t.payment_number == 1 for t in transactions)
    orig_loan_bal = 0.0

    if not has_p1 and backfill_payment_one and transactions:
        p2 = next((t for t in transactions if t.payment_number == 2), transactions[0])
        bal_before_p2 = p2.remaining_principal_balance + p2.principal_amount

        # Standard simple interest for 45 days (2022-04-04 to 2022-05-19)
        # Interest = orig_bal * (apr / 365) * 45
        # orig_bal - (1014.55 - Interest) = bal_before_p2
        rate_decimal = derived_apr / 100.0
        days_orig_to_p1 = 45.0
        factor = 1.0 + (rate_decimal * days_orig_to_p1 / 365.0)
        orig_loan_bal = round((bal_before_p2 + mo_payment) / factor, 2)
        int_p1 = round(orig_loan_bal * rate_decimal * days_orig_to_p1 / 365.0, 2)
        princ_p1 = round(mo_payment - int_p1, 2)

        tx_p1 = VolvoTransaction(
            payment_number=1,
            date="2022-05-19",
            statement_date="2022-05-19",
            due_date="2022-05-19",
            total_amount=mo_payment,
            principal_amount=princ_p1,
            interest_amount=int_p1,
            remaining_principal_balance=bal_before_p2,
            payoff_amount=bal_before_p2,
            description="Ach payment (Reconstructed)",
            status="Posted",
        )
        transactions.insert(0, tx_p1)
        balance_checkpoints["2022-05-19"] = bal_before_p2

    # Add origination checkpoint
    balance_checkpoints[start_date] = orig_loan_bal

    # Ensure latest checkpoint reflects current principal balance
    if transactions:
        latest_date = transactions[-1].date
        balance_checkpoints[latest_date] = transactions[-1].remaining_principal_balance

    metadata = VolvoLoanMetadata(
        institution="Volvo Car Financial Services",
        account_number=acct_num,
        account_number_masked=acct_masked,
        vehicle_name=vname,
        vehicle_model=model,
        vin=vin,
        contract_start_date=start_date,
        maturity_date=end_date,
        contract_term=term,
        monthly_payment=mo_payment,
        current_principal_balance=curr_principal,
        current_payoff_amount=payoff_amount,
        interest_rate_percent=derived_apr,
        original_loan_balance=orig_loan_bal,
        payments_made=payments_made,
        payments_remaining=payments_remaining,
    )

    return ParsedVolvoData(
        metadata=metadata,
        transactions=transactions,
        balance_checkpoints=balance_checkpoints,
    )
