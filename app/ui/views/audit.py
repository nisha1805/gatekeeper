import json
import os

import httpx
import streamlit as st

from audit_logic import audit_rows, filter_rows, to_csv
from ui_logic import TIER_STYLE

API = os.environ.get("GATEKEEPER_API", "http://localhost:8000")

st.title("Audit trail")
st.caption("Every assessment the API has produced. Sample and synthetic data only.")
st.info(
    "In this version the list lives in the API's memory and disappears when the API "
    "restarts. A permanent, append-only log in Postgres comes with the next step."
)

try:
    response = httpx.get(f"{API}/assessments", timeout=10)
except httpx.HTTPError:
    st.error(
        f"Cannot reach the API at {API}. Start it with "
        "'uvicorn api:app --port 8000' in app/compliance."
    )
    st.stop()

if response.status_code != 200:
    st.error(f"The API answered {response.status_code}.")
    st.stop()

records = response.json()
rows = audit_rows(records)

filter_column, search_column, refresh_column = st.columns([1, 2, 0.6])
result_filter = filter_column.selectbox(
    "Result", ["All"] + [style[0] for style in TIER_STYLE.values()]
)
text_filter = search_column.text_input("Search", placeholder="System name or article")
refresh_column.write("")
refresh_column.button("Refresh")

shown = filter_rows(rows, result=result_filter, text=text_filter)
st.caption(f"{len(shown)} of {len(rows)} entries")

if shown:
    st.dataframe(shown, hide_index=True, use_container_width=True)
else:
    st.markdown("**No entries yet.** Classify a system on the copilot page.")

json_column, csv_column, _ = st.columns([1, 1, 3])
json_column.download_button(
    "Export JSON",
    data=json.dumps(records, indent=2),
    file_name="gatekeeper-audit.json",
    mime="application/json",
)
csv_column.download_button(
    "Export CSV",
    data=to_csv(shown),
    file_name="gatekeeper-audit.csv",
    mime="text/csv",
)
st.caption("Entries cannot be edited or deleted through this page.")