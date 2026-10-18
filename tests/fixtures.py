"""Synthetic fixtures for Volvo Car Financial Services tests.

Contains 100% mock data with zero real PII or network dependencies.
"""

from typing import Any, Dict


def get_synthetic_raw_data() -> Dict[str, Any]:
    """Return synthetic Volvo raw captured data dictionary."""
    return {
        "captured_at": "2026-10-18T00:00:00",
        "account_details": {
            "languagePreference": "en",
            "vinNumber": "YV4ED3GB1N2000000",
            "eiid": "0051Q0000000000000",
            "accountNumber": "030010000000000000",
            "isRetail": True,
            "contractStartDate": "4/4/2022 12:00:00 AM",
            "contractEndDate": "4/19/2028 12:00:00 AM",
            "contractTerm": 72,
            "vehicleYear": 2022,
            "vehicleMake": "VOLVO",
            "vehicleModel": "C40 RECHAR",
            "personaLegalStatus": "",
            "personaLifecycle": "RS",
            "personaLoyalty": "FT",
            "personaAudience": "",
            "personaClosedAccount": "",
            "personaState": "NC",
            "personaCollection": "",
        },
        "dashboard_info": {
            "paymentAmount": 1014.55,
            "nextDraftDate": "October 19, 2026",
            "currentPrincipalBalance": 20000.00,
            "term": 72,
            "paymentsMade": 53,
            "totalPayments": 72,
        },
        "payoff_data": {
            "payoffAmount": 20050.00,
            "goodUntil": "October 27, 2026",
        },
        "statements": [
            {
                "guid": "mock-guid-02",
                "year": 2022,
                "statement_date": "6/20/2022",
                "payments_made": 2,
                "payments_remaining": 70,
                "payoff_amount": 62920.77,
                "payment_date": "6/19/2022",
                "payment_amount": 1014.55,
                "principal_amount": 678.32,
                "interest_amount": 336.23,
                "due_date": "6/19/2022",
                "pdf_url": "https://www.volvocarfinancialservices.com/mock-pdf-02",
            },
            {
                "guid": "mock-guid-03",
                "year": 2022,
                "statement_date": "7/19/2022",
                "payments_made": 3,
                "payments_remaining": 69,
                "payoff_amount": 62060.23,
                "payment_date": "7/19/2022",
                "payment_amount": 1014.55,
                "principal_amount": 854.40,
                "interest_amount": 160.15,
                "due_date": "7/19/2022",
                "pdf_url": "https://www.volvocarfinancialservices.com/mock-pdf-03",
            },
            {
                "guid": "mock-guid-04",
                "year": 2022,
                "statement_date": "8/19/2022",
                "payments_made": 4,
                "payments_remaining": 68,
                "payoff_amount": 61208.13,
                "payment_date": "8/19/2022",
                "payment_amount": 1014.55,
                "principal_amount": 851.31,
                "interest_amount": 163.24,
                "due_date": "8/19/2022",
                "pdf_url": "https://www.volvocarfinancialservices.com/mock-pdf-04",
            },
            {
                "guid": "mock-guid-53",
                "year": 2026,
                "statement_date": "9/21/2026",
                "payments_made": 53,
                "payments_remaining": 19,
                "payoff_amount": 16487.86,
                "payment_date": "9/19/2026",
                "payment_amount": 1014.55,
                "principal_amount": 968.63,
                "interest_amount": 45.92,
                "due_date": "9/19/2026",
                "pdf_url": "https://www.volvocarfinancialservices.com/mock-pdf-53",
            },
        ],
    }
