"""Tests for the command-line interface."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tests.fixtures import get_synthetic_raw_data
from volvo_to_monarch.cli import main


class TestVolvoCLI(unittest.TestCase):
    """Test suite for CLI subcommands and parameter parsing."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.raw_file = Path(self.temp_dir.name) / "test_raw_data.json"
        with open(self.raw_file, "w", encoding="utf-8") as f:
            json.dump(get_synthetic_raw_data(), f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cli_convert_command(self):
        out_dir = Path(self.temp_dir.name) / "out"
        code = main([
            "convert",
            str(self.raw_file),
            "--output-dir", str(out_dir),
            "--account-name", "2022 Volvo XC40 Ultimate",
        ])
        self.assertEqual(code, 0)
        self.assertTrue((out_dir / "volvo_monarch_transactions.csv").exists())
        self.assertTrue((out_dir / "volvo_monarch_balance_history.csv").exists())

    def test_cli_capture_command_mocked(self):
        out_dir = Path(self.temp_dir.name) / "out"
        with patch("volvo_to_monarch.cli.capture_volvo_data") as mock_cap:
            mock_cap.return_value = get_synthetic_raw_data()
            code = main([
                "capture",
                "--output-file", str(self.raw_file),
                "--output-dir", str(out_dir),
            ])
            self.assertEqual(code, 0)
            mock_cap.assert_called_once()

    def test_cli_all_command_mocked(self):
        out_dir = Path(self.temp_dir.name) / "out"
        with patch("volvo_to_monarch.cli.capture_volvo_data") as mock_cap:
            mock_cap.return_value = get_synthetic_raw_data()
            code = main([
                "all",
                "--raw-file", str(self.raw_file),
                "--output-dir", str(out_dir),
            ])
            self.assertEqual(code, 0)
            mock_cap.assert_called_once()
            self.assertTrue((out_dir / "volvo_monarch_transactions.csv").exists())
            self.assertTrue((out_dir / "volvo_monarch_balance_history.csv").exists())


if __name__ == "__main__":
    unittest.main()
