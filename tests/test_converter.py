"""Tests for Monarch Money conversion logic."""

import unittest
from tests.fixtures import get_synthetic_raw_data
from volvo_to_monarch.converter import (
    convert_to_monarch_balance_history,
    convert_to_monarch_transactions,
)
from volvo_to_monarch.parser import parse_volvo_data


class TestVolvoConverter(unittest.TestCase):
    """Test suite for converting Volvo data to Monarch Money CSV schemas."""

    def setUp(self):
        self.raw_data = get_synthetic_raw_data()
        self.parsed = parse_volvo_data(self.raw_data, backfill_payment_one=True)

    def test_convert_to_monarch_transactions_standard(self):
        tx_rows = convert_to_monarch_transactions(
            transactions=self.parsed.transactions,
            account_name="2022 Volvo XC40 Ultimate",
            merchant="Volvo Car Financial Services",
            category="Auto Loan",
            positive_payment=False,
        )

        self.assertEqual(len(tx_rows), 5)
        first_row = tx_rows[0]

        # Verify columns
        expected_keys = {"Date", "Merchant", "Category", "Account", "Original Statement", "Notes", "Amount"}
        self.assertEqual(set(first_row.keys()), expected_keys)

        # Verify values
        self.assertEqual(first_row["Date"], "2022-05-19")
        self.assertEqual(first_row["Merchant"], "Volvo Car Financial Services")
        self.assertEqual(first_row["Category"], "Auto Loan")
        self.assertEqual(first_row["Account"], "2022 Volvo XC40 Ultimate")
        # Monarch liability convention: payments reducing debt are negative numbers
        self.assertEqual(first_row["Amount"], "-1014.55")
        self.assertIn("Payment #1 of 72", first_row["Notes"])
        self.assertIn("Principal:", first_row["Notes"])

    def test_convert_to_monarch_transactions_positive_payment(self):
        tx_rows = convert_to_monarch_transactions(
            transactions=self.parsed.transactions,
            positive_payment=True,
        )
        self.assertEqual(tx_rows[0]["Amount"], "1014.55")

    def test_convert_to_monarch_transactions_date_filtering(self):
        tx_rows = convert_to_monarch_transactions(
            transactions=self.parsed.transactions,
            start_date="2022-07-01",
            end_date="2022-08-31",
        )
        self.assertEqual(len(tx_rows), 2)
        dates = [r["Date"] for r in tx_rows]
        self.assertEqual(dates, ["2022-07-19", "2022-08-19"])

    def test_convert_to_monarch_balance_history_continuous(self):
        bal_rows = convert_to_monarch_balance_history(
            checkpoints=self.parsed.balance_checkpoints,
            initial_balance=self.parsed.metadata.original_loan_balance,
            start_date="2022-04-04",
            end_date="2022-04-10",
            positive_balance=False,
        )

        # 7 consecutive days: April 4 through April 10
        self.assertEqual(len(bal_rows), 7)
        self.assertEqual(bal_rows[0]["Date"], "2022-04-04")
        self.assertEqual(bal_rows[-1]["Date"], "2022-04-10")

        # Monarch liability convention: debt balances are negative
        first_val = float(bal_rows[0]["Balance"])
        self.assertLess(first_val, 0)
        self.assertAlmostEqual(first_val, -self.parsed.metadata.original_loan_balance, places=2)

    def test_convert_to_monarch_balance_history_positive(self):
        bal_rows = convert_to_monarch_balance_history(
            checkpoints=self.parsed.balance_checkpoints,
            initial_balance=self.parsed.metadata.original_loan_balance,
            start_date="2022-04-04",
            end_date="2022-04-05",
            positive_balance=True,
        )
        self.assertGreater(float(bal_rows[0]["Balance"]), 0)


if __name__ == "__main__":
    unittest.main()
