"""Chrome DevTools Protocol (CDP) connection and data capture for Volvo Car Financial Services."""

from __future__ import annotations

import json
import re
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import websocket


DEFAULT_CDP_PORT = 9222
TARGET_TAB_ID = "144F05811656A4935A05B8CD0FA1904B"
VOLVO_HOST = "www.volvocarfinancialservices.com"


class CDPError(Exception):
    """Raised when CDP connection or data capture fails."""
    pass


def find_volvo_tab(port: int = DEFAULT_CDP_PORT, target_tab_id: Optional[str] = None) -> Dict[str, Any]:
    """Find the Volvo Car Financial Services tab via Chrome DevTools Protocol."""
    try:
        url = f"http://127.0.0.1:{port}/json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            tabs = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise CDPError(
            f"Could not connect to Chrome debugging port {port}: {e}. "
            f"Ensure Chrome is running with --remote-debugging-port={port}"
        )

    # 1. Match specific target tab id if provided
    desired_id = target_tab_id or TARGET_TAB_ID
    if desired_id:
        for tab in tabs:
            if tab.get("id") == desired_id:
                return tab

    # 2. Match active dashboard or vehicle settings tab
    for tab in tabs:
        tab_url = tab.get("url", "")
        if VOLVO_HOST in tab_url and tab.get("type") == "page":
            if "vehicle-dashboard" in tab_url or "statement-details" in tab_url:
                return tab

    # 3. Fallback to any volvo tab
    for tab in tabs:
        tab_url = tab.get("url", "")
        if VOLVO_HOST in tab_url and tab.get("type") == "page":
            return tab

    raise CDPError(
        f"No open Volvo Car Financial Services tab found on port {port}. "
        f"Please log in to https://{VOLVO_HOST} in Chrome."
    )


class VolvoCDPClient:
    """Client for evaluating JS and capturing cookies and statements via CDP."""

    def __init__(self, ws_url: str, timeout: float = 20.0):
        self.ws_url = ws_url
        self.timeout = timeout
        self.ws: Optional[websocket.WebSocket] = None
        self._req_id = 0

    def connect(self) -> None:
        """Establish websocket connection."""
        self.ws = websocket.create_connection(self.ws_url, suppress_origin=True, timeout=self.timeout)

    def close(self) -> None:
        """Close websocket connection."""
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None

    def __enter__(self) -> VolvoCDPClient:
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def send_cmd(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a CDP command and wait for response matching its id."""
        if not self.ws:
            raise CDPError("WebSocket connection is not open.")
        self._req_id += 1
        current_id = self._req_id
        msg = {"id": current_id, "method": method}
        if params is not None:
            msg["params"] = params

        self.ws.send(json.dumps(msg))
        while True:
            raw = self.ws.recv()
            resp = json.loads(raw)
            if resp.get("id") == current_id:
                if "error" in resp:
                    raise CDPError(f"CDP command error ({method}): {resp['error']}")
                return resp.get("result", {})

    def evaluate(self, expression: str, await_promise: bool = True) -> Any:
        """Evaluate JavaScript in the page context."""
        result = self.send_cmd(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": await_promise,
            },
        )
        if "exceptionDetails" in result:
            err = result["exceptionDetails"]
            raise CDPError(f"JS evaluation error: {err.get('text', '')} {err.get('exception', {})}")
        return result.get("result", {}).get("value")

    def get_cookies(self, url: str = f"https://{VOLVO_HOST}") -> str:
        """Capture session cookies as a Cookie header string."""
        res = self.send_cmd("Network.getCookies", {"urls": [url]})
        cookies = res.get("cookies", [])
        return "; ".join(f"{c['name']}={c['value']}" for c in cookies)


def capture_volvo_data(
    port: int = DEFAULT_CDP_PORT,
    target_tab_id: Optional[str] = TARGET_TAB_ID,
    output_file: Optional[Union[str, Path]] = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Capture Volvo Financial Services loan metadata and statements.

    Args:
        port: Chrome remote debugging port.
        target_tab_id: Target Chrome tab ID.
        output_file: Optional path to save raw JSON.
        verbose: Whether to print progress to stdout.

    Returns:
        Structured dictionary of captured account details and statements.
    """
    if verbose:
        print(f"Connecting to Chrome on port {port}...")

    tab = find_volvo_tab(port=port, target_tab_id=target_tab_id)
    ws_url = tab.get("webSocketDebuggerUrl")
    if not ws_url:
        raise CDPError(f"Tab {tab.get('id')} has no webSocketDebuggerUrl available.")

    if verbose:
        print(f"Connected to tab: {tab.get('title')} ({tab.get('id')})")

    with VolvoCDPClient(ws_url, timeout=25.0) as client:
        # 1. Capture cookies for HTTP requests
        cookie_header = client.get_cookies()

        # 2. Extract account details and dashboard metadata
        account_details = client.evaluate("""
        (() => {
            return typeof accountDetails !== 'undefined' ? accountDetails : {};
        })()
        """) or {}

        # Check vehicle display title & dashboard numbers
        dashboard_info = client.evaluate("""
        (() => {
            const bodyText = document.body.innerText;
            const draftMatch = bodyText.match(/Will be drafted on\\s*([A-Za-z0-9, ]+)/i);
            const amtMatch = bodyText.match(/\\$\\s*([\\d,]+\\.\\d{2})\\s*Will be drafted/i);
            const balanceMatch = bodyText.match(/Current Principal Balance\\s*\\$([\\d,]+\\.\\d{2})/i);
            const termMatch = bodyText.match(/Term:\\s*(\\d+)/i);
            const paymentsMatch = bodyText.match(/Payments:\\s*(\\d+)\\s*of\\s*(\\d+)/i);
            
            return {
                paymentAmount: amtMatch ? parseFloat(amtMatch[1].replace(/,/g, '')) : null,
                nextDraftDate: draftMatch ? draftMatch[1].trim() : null,
                currentPrincipalBalance: balanceMatch ? parseFloat(balanceMatch[1].replace(/,/g, '')) : null,
                term: termMatch ? parseInt(termMatch[1], 10) : null,
                paymentsMade: paymentsMatch ? parseInt(paymentsMatch[1], 10) : null,
                totalPayments: paymentsMatch ? parseInt(paymentsMatch[2], 10) : null
            };
        })()
        """) or {}

        # 3. Payoff quote from retail-payoff-form
        payoff_data = client.evaluate("""
        (async () => {
            try {
                const res = await fetch('/vehicle-settings/retail-payoff-form');
                const text = await res.text();
                const mPayoff = text.match(/Payoff amount:\\s*<\\/span>\\s*<span[^>]*>\\$([\\d,]+\\.\\d{2})/i) || text.match(/Payoff amount:\\s*\\$([\\d,]+\\.\\d{2})/i);
                const mGoodUntil = text.match(/Good until:\\s*<\\/span>\\s*<span[^>]*>([^<]+)/i) || text.match(/Good until:\\s*([A-Za-z0-9, ]+)/i);
                return {
                    payoffAmount: mPayoff ? parseFloat(mPayoff[1].replace(/,/g, '')) : null,
                    goodUntil: mGoodUntil ? mGoodUntil[1].trim() : null
                };
            } catch (e) {
                return { error: e.toString() };
            }
        })()
        """) or {}

        # 4. Navigate to statement details page to access statements history if not already there
        curr_url = client.evaluate("window.location.href")
        if "statement-details-page" not in curr_url:
            if verbose:
                print("Navigating to statements & payment history...")
            client.evaluate("window.location.href = '/vehicle-settings/statement-details-page?viewmore=true'")
            time.sleep(2.0)

        # 5. Discover all statement links across all years
        years = ["2022", "2023", "2024", "2025", "2026"]
        all_meta: List[Dict[str, Any]] = []
        seen_guids: set[str] = set()

        if verbose:
            print("Discovering statements across years...")

        for y in years:
            client.evaluate(f"""
            (async () => {{
                const btn = Array.from(document.querySelectorAll('.payment-history__year-button')).find(b => b.value === '{y}');
                if (btn) {{
                    btn.click();
                    let waited = 0;
                    while (!btn.classList.contains('payment-history__year-button--active') && waited < 2000) {{
                        await new Promise(r => setTimeout(r, 100));
                        waited += 100;
                    }}
                    await new Promise(r => setTimeout(r, 400));
                    const vm = document.querySelector('.statements-history__view-more');
                    if (vm && vm.offsetParent !== null) vm.click();
                    await new Promise(r => setTimeout(r, 300));
                }}
            }})()
            """)

            items = client.evaluate("""
            (() => {
                const res = [];
                document.querySelectorAll('.statement-card__title-link').forEach(a => {
                    const guid = a.getAttribute('data-value');
                    if (guid) {
                        res.push({
                            title: a.innerText.trim(),
                            href: a.href,
                            guid: guid
                        });
                    }
                });
                return res;
            })()
            """) or []

            year_count = 0
            for item in items:
                if item["guid"] not in seen_guids:
                    seen_guids.add(item["guid"])
                    item["year"] = int(y)
                    all_meta.append(item)
                    year_count += 1

            if verbose:
                print(f"  Year {y}: {year_count} statements found")

        if verbose:
            print(f"Total unique statements discovered: {len(all_meta)}")

    # 6. Fetch statements using session cookies via urllib
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": cookie_header,
    }

    parsed_statements: List[Dict[str, Any]] = []
    if verbose:
        print("Fetching statement details...")

    for idx, meta in enumerate(all_meta):
        req = urllib.request.Request(meta["href"], headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=12) as r:
                html = r.read().decode("utf-8", errors="ignore")
        except Exception as e:
            if verbose:
                print(f"  Warning: failed to fetch statement {meta['guid']}: {e}")
            continue

        pm = re.search(r"Payments Made:\s*</div>\s*<div[^>]*>\s*(\d+)", html) or re.search(r"Payments Made:\s*(\d+)", html)
        pr = re.search(r"Payments Remaining:\s*</div>\s*<div[^>]*>\s*(\d+)", html) or re.search(r"Payments Remaining:\s*(\d+)", html)
        payoff = re.search(r"Payoff Amount:\s*</div>\s*<div[^>]*>\s*\$([\d,]+\.\d{2})", html) or re.search(r"Payoff Amount:\s*\$([\d,]+\.\d{2})", html)
        rec_date = re.search(r"Received on\s*</div>\s*<div[^>]*>\s*([0-9/]+)", html) or re.search(r"Received on\s*([0-9/]+)", html)
        rec_amt = re.search(r"Received Amount\s*</div>\s*<div[^>]*>\s*\$([\d,]+\.\d{2})", html) or re.search(r"Received Amount\s*\$([\d,]+\.\d{2})", html)
        princ = re.search(r"Principal\s*</div>\s*<div[^>]*>\s*\$([\d,]+\.\d{2})", html) or re.search(r"Principal\s*\$([\d,]+\.\d{2})", html)
        fin_chg = re.search(r"Finance Charge\s*</div>\s*<div[^>]*>\s*\$([\d,]+\.\d{2})", html) or re.search(r"Finance Charge\s*\$([\d,]+\.\d{2})", html)
        due_date = re.search(r"Due Date\s*</div>\s*<div[^>]*>\s*([0-9/]+)", html) or re.search(r"Due Date\s*([0-9/]+)", html)

        title_m = re.search(r"([0-9/]+)", meta["title"])
        stmt_date = title_m.group(1) if title_m else None

        pdf_m = re.search(r'href="([^"]*DownloadPdf[^"]*)"', html)
        pdf_url = pdf_m.group(1).replace("&amp;", "&") if pdf_m else None
        if pdf_url and pdf_url.startswith("/"):
            pdf_url = f"https://{VOLVO_HOST}" + pdf_url

        parsed_statements.append({
            "guid": meta["guid"],
            "year": meta["year"],
            "statement_date": stmt_date,
            "payments_made": int(pm.group(1)) if pm else None,
            "payments_remaining": int(pr.group(1)) if pr else None,
            "payoff_amount": float(payoff.group(1).replace(",", "")) if payoff else None,
            "payment_date": rec_date.group(1) if rec_date else None,
            "payment_amount": float(rec_amt.group(1).replace(",", "")) if rec_amt else None,
            "principal_amount": float(princ.group(1).replace(",", "")) if princ else None,
            "interest_amount": float(fin_chg.group(1).replace(",", "")) if fin_chg else None,
            "due_date": due_date.group(1) if due_date else None,
            "pdf_url": pdf_url,
        })

        if verbose and ((idx + 1) % 10 == 0 or idx == len(all_meta) - 1):
            print(f"  Fetched {idx + 1}/{len(all_meta)} statements")

    parsed_statements.sort(key=lambda x: x["payments_made"] or 0)

    # Compile result dictionary
    result_data = {
        "captured_at": datetime.now().isoformat(),
        "account_details": account_details,
        "dashboard_info": dashboard_info,
        "payoff_data": payoff_data,
        "statements": parsed_statements,
    }

    if output_file:
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=2)
        if verbose:
            print(f"Raw data saved to: {out_path.resolve()}")

    return result_data
