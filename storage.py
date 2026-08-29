"""
Storage backend for the AI Appraisal Drafting Assistant.

Writes each submitted response as a row in a Google Sheet using a Google
service account (server-to-server authentication) — participants never see
or need any Google credentials themselves. Falls back automatically to a
local responses.csv file if the Google Sheets secrets are not configured,
so the app still works unmodified for local testing on a laptop.

Required Streamlit secrets for the Google Sheets backend
(see .streamlit/secrets.toml.example for the exact format):

    [gcp_service_account]
    type = "service_account"
    project_id = "..."
    private_key_id = "..."
    private_key = "..."
    client_email = "..."
    client_id = "..."
    token_uri = "https://oauth2.googleapis.com/token"

    sheet_id = "1bkSg6dojxOrcz_wWFwXzdgIrlCcItUtO4j0O98lwVU0"
"""

import csv
import os

import streamlit as st

FIELDNAMES = [
    "case_id", "employee_name", "condition", "summary_text",
    "clarity", "specificity", "balance", "tone", "accuracy",
    "unsupported_claim_flag", "rubric_notes",
    "fairness", "trust", "usefulness", "transparency",
    "open_fairness", "open_trust",
]


def _sheets_configured() -> bool:
    try:
        return "gcp_service_account" in st.secrets and "sheet_id" in st.secrets
    except Exception:
        return False


@st.cache_resource(show_spinner=False)
def _get_worksheet():
    import gspread

    creds_dict = dict(st.secrets["gcp_service_account"])
    gc = gspread.service_account_from_dict(creds_dict)
    sh = gc.open_by_key(st.secrets["sheet_id"])
    ws = sh.sheet1
    if not ws.get_all_values():
        ws.append_row(FIELDNAMES, value_input_option="RAW")
    return ws


def save_response(ratings: dict) -> str:
    """
    Persist one response row to whichever backend is configured.
    Returns a short human-readable label of where it was saved, so the
    app can confirm this to the researcher/participant.
    """
    if _sheets_configured():
        ws = _get_worksheet()
        row = [ratings.get(k, "") for k in FIELDNAMES]
        ws.append_row(row, value_input_option="RAW")
        return "Google Sheets"

    file_exists = os.path.exists("responses.csv")
    with open("responses.csv", "a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: ratings.get(k, "") for k in FIELDNAMES})
    return "local responses.csv (Google Sheets secrets not configured yet)"
