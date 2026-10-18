"""Tests for Chrome DevTools Protocol (CDP) connection and discovery logic."""

import io
import json
import unittest
from unittest.mock import MagicMock, patch
from volvo_to_monarch.cdp import (
    CDPError,
    VolvoCDPClient,
    find_volvo_tab,
)


class TestVolvoCDP(unittest.TestCase):
    """Test suite for CDP tab discovery and client interaction."""

    def test_find_volvo_tab_success(self):
        mock_tabs = [
            {"id": "tab1", "type": "page", "url": "https://google.com"},
            {"id": "144F05811656A4935A05B8CD0FA1904B", "type": "page", "url": "https://www.volvocarfinancialservices.com/vehicle-dashboard"},
        ]
        with patch("urllib.request.urlopen") as mock_url:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_tabs).encode("utf-8")
            mock_url.return_value.__enter__.return_value = mock_resp

            tab = find_volvo_tab(port=9222, target_tab_id="144F05811656A4935A05B8CD0FA1904B")
            self.assertEqual(tab["id"], "144F05811656A4935A05B8CD0FA1904B")

    def test_find_volvo_tab_not_found(self):
        mock_tabs = [
            {"id": "tab1", "type": "page", "url": "https://google.com"},
        ]
        with patch("urllib.request.urlopen") as mock_url:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_tabs).encode("utf-8")
            mock_url.return_value.__enter__.return_value = mock_resp

            with self.assertRaises(CDPError):
                find_volvo_tab(port=9222, target_tab_id="nonexistent-id")

    def test_find_volvo_tab_connection_error(self):
        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            with self.assertRaises(CDPError) as ctx:
                find_volvo_tab(port=9222)
            self.assertIn("Could not connect to Chrome debugging port", str(ctx.exception))

    def test_cdp_client_evaluate(self):
        client = VolvoCDPClient("ws://localhost:9222/mock")
        mock_ws = MagicMock()
        mock_ws.recv.return_value = json.dumps({
            "id": 1,
            "result": {
                "result": {
                    "value": "Vehicle Dashboard"
                }
            }
        })
        client.ws = mock_ws

        val = client.evaluate("document.title")
        self.assertEqual(val, "Vehicle Dashboard")
        mock_ws.send.assert_called_once()

    def test_cdp_client_get_cookies(self):
        client = VolvoCDPClient("ws://localhost:9222/mock")
        mock_ws = MagicMock()
        mock_ws.recv.return_value = json.dumps({
            "id": 1,
            "result": {
                "cookies": [
                    {"name": "sessionId", "value": "xyz123"},
                    {"name": "token", "value": "abc456"},
                ]
            }
        })
        client.ws = mock_ws

        cookies = client.get_cookies()
        self.assertIn("sessionId=xyz123", cookies)
        self.assertIn("token=abc456", cookies)


if __name__ == "__main__":
    unittest.main()
