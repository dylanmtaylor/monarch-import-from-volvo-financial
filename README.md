# Monarch Import from Volvo Car Financial Services

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Monarch Money](https://img.shields.io/badge/Monarch%20Money-Compatible-blueviolet.svg)](https://www.monarchmoney.com/)

An automated command-line utility to extract and convert **Volvo Car Financial Services** auto loan payment history and continuous daily balance history into CSV files specifically formatted for import into **[Monarch Money](https://www.monarchmoney.com/)**.

Volvo Car Financial Services (VCFS) does not provide a direct one-click CSV export button for account history and splits statements across multiple year tabs. This tool connects directly to your active authenticated browser session via Chrome DevTools Protocol (CDP) to extract your complete multi-year payment history, statement closing checkpoints, and contract details, formatting everything for Monarch Money.

---

## 🌟 Key Features

- 🚀 **Automated Chrome Capture**: Connects via Chrome DevTools Protocol (CDP) to your authenticated browser session to extract loan terms, contract details, and multi-year payment records across all statement years.
- 💳 **Detailed Monarch Transactions**: Produces `volvo_monarch_transactions.csv` formatted with merchant, categories (`Auto Loan`), original statements, and detailed notes with principal, interest, remaining UPB, and payoff quote breakdowns.
- 📉 **Continuous Daily Balance History**: Generates `volvo_monarch_balance_history.csv` forward-filling daily unpaid principal balances from loan origination through the current date so net worth and liability charts render smoothly with no gaps.
- 📐 **Origination & Payment 1 Reconstruction**: Automatically reconstructs Payment 1 and the contract origination balance checkpoint from contractual loan terms and statement interest calculations when portal digital statements start at Payment 2.
- ⚖️ **Monarch Liability Conventions**: Formats balances and payments as negative numbers in compliance with Monarch Money's official requirements for liability accounts, preventing net worth inversion bugs.
- 🔒 **Zero Data Leakage**: All raw JSON and output CSV files are automatically excluded by `.gitignore`. Test fixtures use strictly synthetic mock data.

---

## 🛠️ How It Works

```
┌──────────────────────────────────────────────┐
│       Chrome Browser (Authenticated)         │
│     Volvo Car Financial Services Portal      │
└──────────────────────┬───────────────────────┘
                       │ Chrome DevTools Protocol (CDP)
                       ▼
┌──────────────────────────────────────────────┐
│           volvo-to-monarch all               │
│   (Captures Ledger, Statements & Payoffs)    │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│         output/volvo_raw_data.json           │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│           volvo-to-monarch convert           │
│   (Parses Statements & Reconstructs Balances)│
└──────────────────────┬───────────────────────┘
                       │
        ┌──────────────┴──────────────────────────┐
        ▼                                         ▼
┌───────────────────────────────┐   ┌───────────────────────────────┐
│ volvo_monarch_                │   │ volvo_monarch_                │
│ balance_history.csv           │   │ transactions.csv              │
│ (Daily continuous snapshots)  │   │ (Principal, Interest, Notes)  │
└───────────────────────────────┘   └───────────────────────────────┘
```

---

## 💻 Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/dylanmtaylor/monarch-import-from-volvo-financial.git
cd monarch-import-from-volvo-financial
pip install -e .
```

---

## 🚀 Usage

### Option 1: Automated Capture & Convert (Recommended)

1. Launch Google Chrome with remote debugging enabled on port `9222`:
   ```bash
   # Standard Linux / macOS / Windows Chrome:
   google-chrome --remote-debugging-port=9222 &

   # Flatpak Chrome (Linux):
   flatpak run com.google.Chrome --remote-debugging-port=9222 &
   ```
2. In the opened Chrome browser window, navigate to the Volvo portal and log in:
   [https://www.volvocarfinancialservices.com/vehicle-dashboard](https://www.volvocarfinancialservices.com/vehicle-dashboard)
3. Once logged in to your dashboard, run:
   ```bash
   volvo-to-monarch all
   ```

The tool will connect to Chrome, discover your vehicle dashboard, iterate through all statement years, extract itemized principal and interest breakdowns, save `output/volvo_raw_data.json`, and output your Monarch CSV files in `./output/`.

---

### Option 2: Step-by-Step Capture & Convert

If you prefer to capture raw JSON first and convert separately:

```bash
# Step 1: Capture raw JSON from Chrome
volvo-to-monarch capture -f output/volvo_raw_data.json

# Step 2: Convert existing raw JSON to Monarch CSVs
volvo-to-monarch convert output/volvo_raw_data.json -o ./output
```

---

## ⚙️ CLI Reference

```
usage: volvo-to-monarch [-h] [-v] [-o OUTPUT_DIR] [-a ACCOUNT_NAME]
                        [-m MERCHANT] [-c CATEGORY] [--positive-balance]
                        [--positive-payment] [--no-backfill]
                        [--start-date START_DATE] [--end-date END_DATE]
                        {all,capture,convert} ...
```

### Subcommands

| Subcommand | Description |
|:---|:---|
| `all` | Connects via CDP, captures live data, and exports Monarch CSVs (default). |
| `capture` | Connects via CDP and saves raw data to JSON. |
| `convert` | Converts an existing raw JSON export into Monarch CSVs. |

### Options

| Flag | Default | Description |
|:---|:---|:---|
| `-o`, `-d`, `--output-dir` | `./output` | Destination directory for output CSVs. |
| `-a`, `--account-name` | `2022 Volvo XC40 Ultimate` | Monarch account name to tag on transactions. |
| `-m`, `--merchant` | `Volvo Car Financial Services` | Merchant label for transactions. |
| `-c`, `--category` | `Auto Loan` | Monarch transaction category. |
| `--port` | `9222` | Chrome remote debugging port. |
| `--tab-id` | `144F05811656A4935A05B8CD0FA1904B` | Target Chrome tab ID (autodetected if omitted). |
| `--positive-balance` | `False` | Output balances as positive numbers (default is negative per Monarch standard). |
| `--positive-payment` | `False` | Output payment amounts as positive numbers (default is negative per Monarch standard). |
| `--no-backfill` | `False` | Disable automatic backfill of Payment 1. |
| `--start-date` | `None` | Filter output records starting from `YYYY-MM-DD`. |
| `--end-date` | `None` | Filter output records ending at `YYYY-MM-DD`. |

---

## 📥 Importing into Monarch Money

1. Log in to [Monarch Money](https://app.monarchmoney.com/).
2. Navigate to **Accounts** → **Add Account** → **Manual Account** → **Vehicle / Auto Loan**.
3. Set the account name to `2022 Volvo XC40 Ultimate` (or your preferred vehicle name).
4. Click into the new account:
   - **Upload Balances**: Select `output/volvo_monarch_balance_history.csv` to backfill your full continuous daily balance history from origination to present.
   - **Upload Transactions**: Select `output/volvo_monarch_transactions.csv` to import all historical monthly payments with complete principal and interest breakdowns.

---

## 🧪 Running Tests

The test suite runs with 100% synthetic fixtures, requiring zero network calls or credentials:

```bash
python3 -m unittest discover tests -v
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
