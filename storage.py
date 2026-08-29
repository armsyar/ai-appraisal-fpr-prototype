"""
Storage backend for the AI Appraisal Drafting Assistant.

Writes each completed submission to one row in the Google Sheet.
Each field is stored in a fixed column defined by FIELDNAMES.
"""

import csv
import os

import streamlit as st

FIELDNAMES = [
    "case_id",
    "employee_name",
    "condition",
    "summary_text",
    "clarity",
    "specificity",
    "balance",
    "tone",
    "accuracy",
    "unsupported_claim_flag",
    "rubric_notes",
    "fairness",
    "trust",
    "usefulness",
    "transparency",
    "open_fairness",
    "open_trust",
]


def _sheets_configured() -> bool:
    try:
        return (
            "gcp_service_account" in st.secrets
            and "sheet_id" in st.secrets
        )
    except Exception:
        return False


@st.cache_resource(show_spinner=False)
def _get_worksheet():
    import gspread

    creds_dict = dict(st.secrets["gcp_service_account"])
    gc = gspread.service_account_from_dict(creds_dict)
    spreadsheet = gc.open_by_key(st.secrets["sheet_id"])
    worksheet = spreadsheet.sheet1

    existing_headers = worksheet.row_values(1)

    if not existing_headers:
        worksheet.update(
            range_name="A1:Q1",
            values=[FIELDNAMES],
            value_input_option="RAW",
        )
    elif existing_headers[:len(FIELDNAMES)] != FIELDNAMES:
        raise ValueError(
            "The Google Sheet header row does not match the required "
            "appraisal-response structure. Create a new blank worksheet "
            "or restore the expected headers before collecting data."
        )

    return worksheet


def save_response(ratings: dict) -> str:
    row = [ratings.get(field, "") for field in FIELDNAMES]

    if _sheets_configured():
        worksheet = _get_worksheet()
        worksheet.append_row(
            row,
            value_input_option="RAW",
            insert_data_option="INSERT_ROWS",
            table_range="A:Q",
        )
        return "Google Sheets"

    file_exists = os.path.exists("responses.csv")

    with open("responses.csv", "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)

        if not file_exists:
            writer.writeheader()

        writer.writerow({field: ratings.get(field, "") for field in FIELDNAMES})

    return "local responses.csv"
