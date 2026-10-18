"""Tests for Volvo Car Financial Services data parsing."""

import unittest
from tests.fixtures import get_synthetic_raw_data
from volvo_to_monarch.parser import (
    calculate_derived_apr,
    normalize_date,
    parse_volvo_data,
)


class TestVolvoParser(unittest.TestCase):
    """Test suite for parsing Volvo raw JSON into structured models."""

    def setUp(self):
        self.raw_data = get_synthetic_raw_data()

    def test_normalize_date(self):
        self.assertEqual(normalize_date("4/4/2022 12:00:00 AM"), "2022-04-04")
        self.assertEqual(normalize_date("06/20/2022"), "2022-06-20")
        self.assertEqual(normalize_date("2026-10-19"), "2026-10-19")
        self.assertIsNone(normalize_date(None))
        self.assertEqual(normalize_date(""), None)

    def test_calculate_derived_apr(self):
        statements = self.raw_data["statements"]
        apr = calculate_derived_apr(statements)
        self.assertGreater(apr, 2.5)
        self.assertLess(apr, 4.0)

    def test_parse_volvo_data_with_backfill(self):
        parsed = parse_volvo_data(self.raw_data, backfill_payment_one=True)
        meta = parsed.metadata

        self.assertEqual(meta.institution, "Volvo Car Financial Services")
        self.assertEqual(meta.account_number, "030010000000000000")
        self.assertEqual(meta.account_number_masked, "...0000")
        self.assertEqual(meta.vin, "YV4ED3GB1N2000000")
        self.assertEqual(meta.contract_start_date, "2022-04-04")
        self.assertEqual(meta.maturity_date, "2028-04-19")
        self.assertEqual(meta.contract_term, 72)
        self.assertEqual(meta.monthly_payment, 1014.55)
        self.assertEqual(meta.current_principal_balance, 20000.00)
        self.assertEqual(meta.current_payoff_amount, 20050.00)
        self.assertEqual(meta.payments_made, 53)
        self.assertEqual(meta.payments_remaining, 19)

        # Verify Payment 1 was backfilled
        self.assertEqual(len(parsed.transactions), 5)  # 4 synthetic + 1 backfilled
        p1 = parsed.transactions[0]
        self.assertEqual(p1.payment_number, 1)
        self.assertEqual(p1.date, "2022-05-19")
        self.assertEqual(p1.total_amount, 1014.55)
        self.assertGreater(p1.principal_amount, 700.0)
        self.assertGreater(p1.interest_amount, 200.0)

        # Verify origination balance checkpoint
        self.assertIn("2022-04-04", parsed.balance_checkpoints)
        self.assertGreater(parsed.balance_checkpoints["2022-04-04"], 60000.0)

    def test_parse_volvo_data_without_backfill(self):
        parsed = parse_volvo_data(self.raw_data, backfill_payment_one=False)
        self.assertEqual(len(parsed.transactions), 4)
        self.assertEqual(parsed.transactions[0].payment_number, 2)

    def test_custom_vehicle_name_override(self):
        parsed = parse_volvo_data(
            self.raw_data,
            vehicle_name_override="2022 Volvo XC40 Ultimate",
        )
        self.assertEqual(parsed.metadata.vehicle_name, "2022 Volvo XC40 Ultimate")


if __name__ == "__main__":
    unittest.main()
