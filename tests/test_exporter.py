"""Tests for CSV exporter module."""

import csv
import tempfile
import unittest
from pathlib import Path
from tests.fixtures import get_synthetic_raw_data
from volvo_to_monarch.exporter import export_monarch_files
from volvo_to_monarch.parser import parse_volvo_data


class TestVolvoExporter(unittest.TestCase):
    """Test suite for exporting Monarch CSV files."""

    def setUp(self):
        self.raw_data = get_synthetic_raw_data()
        self.parsed = parse_volvo_data(self.raw_data, backfill_payment_one=True)

    def test_export_monarch_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            summary = export_monarch_files(
                parsed_data=self.parsed,
                output_dir=temp_dir,
                account_name="2022 Volvo XC40 Ultimate",
                merchant="Volvo Car Financial Services",
                start_date="2022-04-04",
                end_date="2022-04-10",
            )

            tx_file = Path(summary["transactions_file"])
            bal_file = Path(summary["balance_history_file"])

            self.assertTrue(tx_file.exists())
            self.assertTrue(bal_file.exists())
            self.assertEqual(summary["balance_snapshots_count"], 7)

            # Inspect transactions CSV
            with open(tx_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                tx_rows = list(reader)
                self.assertEqual(reader.fieldnames, [
                    "Date",
                    "Merchant",
                    "Category",
                    "Account",
                    "Original Statement",
                    "Notes",
                    "Amount",
                ])
                # Transactions outside 2022-04-04 to 2022-04-10 should be filtered
                self.assertEqual(len(tx_rows), 0)

            # Inspect balance history CSV
            with open(bal_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                bal_rows = list(reader)
                self.assertEqual(reader.fieldnames, ["Date", "Balance"])
                self.assertEqual(len(bal_rows), 7)
                self.assertEqual(bal_rows[0]["Date"], "2022-04-04")
                self.assertEqual(bal_rows[-1]["Date"], "2022-04-10")


if __name__ == "__main__":
    unittest.main()
