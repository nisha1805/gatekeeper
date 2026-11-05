import copy
import html
import os

import httpx
import streamlit as st

from ui_logic import (
    ANNEX_AREAS,
    DEFAULTS,
    HIGH_RISK,
    PROHIBITED,
    ROLES,
    SAMPLES,
    TIER_STYLE,
    TRANSPARENCY,
    build_payload,
    sample_values,
)

API = os.environ.get("GATEKEEPER_API", "http://localhost:8000")

for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, copy.deepcopy(value))
st.session_state.setdefault("result", None)
st.session_state.setdefault("error", None)


def load_sample(label: str) -> None:
    for key, value in sample_values(label).items():
        st.session_state[key] = value
    st.session_state["result"] = None
    st.session_state["error"] = None


def classify() -> None:
    payload = build_payload(st.session_state)
    try:
        response = httpx.post(f"{API}/assessments", json=payload, timeout=10)
    except httpx.HTTPError:
        st.session_state["result"] = None
        st.session_state["error"] = (
            f"Cannot reach the API at {API}. Start it with "
            "'uvicorn api:app --port 8000' in app/compliance."
        )
        return
    if response.status_code == 201:
        st.session_state["result"] = response.json()
        st.session_state["error"] = None
    else:
        st.session_state["result"] = None
        st.session_state["error"] = (
            f"The API refused the request ({response.status_code}): {response.text[:300]}"
        )


def checkboxes(items) -> None:
    for field, label in items:
        st.checkbox(label, key=field)


def show_result(record: dict) -> None:
    assessment = record["assessment"]
    label, background, colour = TIER_STYLE.get(
        assessment["tier"], (assessment["tier"], "#F0F2F5", "#3B4656")
    )
    st.markdown(
        f'<span style="padding: 8px 14px; border-radius: 8px; font-weight: 700; '
        f'font-size: 18px; background: {background}; color: {colour}">'
        f"{html.escape(label)}</span>",
        unsafe_allow_html=True,
    )
    st.markdown("**Why**")
    for reason in assessment["reasons"]:
        st.markdown(f"- **{reason['article']}**: {reason['text']}")
    if assessment["transparency_duties"] and assessment["tier"] != "limited_risk":
        st.markdown("**Transparency duties that also apply**")
        for duty in assessment["transparency_duties"]:
            st.markdown(f"- **{duty['article']}**: {duty['text']}")
    with st.expander("Notes and limits"):
        for note in assessment["notes"]:
            st.markdown(f"- {note}")
    st.caption(
        f"Assessment {record['id']} · rules {assessment['rules_version']} · "
        f"{record['created_at']}"
    )
    st.info(assessment["disclaimer"])


st.title("Compliance copilot")
st.caption(
    "Answer a few questions about an AI system. Gatekeeper's written rules classify "
    "it under the EU AI Act and cite the articles they used."
)
st.warning("Decision support, not legal advice.")

left, right = st.columns([1, 1.3], gap="large")

with left:
    st.subheader("1. Describe the system")
    st.markdown("Start from a sample")
    columns = st.columns(len(SAMPLES))
    for column, label in zip(columns, SAMPLES):
        column.button(label, on_click=load_sample, args=(label,), use_container_width=True)

    st.text_input("System name", key="name", max_chars=200)
    st.selectbox(
        "Your role", options=list(ROLES), format_func=ROLES.get, key="role"
    )
    st.checkbox("Placed on the EU market, or its output is used in the EU", key="eu_nexus")

    with st.expander("Prohibited practices (Article 5)"):
        checkboxes(PROHIBITED)
    with st.expander("High-risk use (Article 6, Annex III)", expanded=True):
        st.multiselect(
            "Annex III areas this system is used in",
            options=list(ANNEX_AREAS),
            format_func=ANNEX_AREAS.get,
            key="annex3_areas",
        )
        checkboxes(HIGH_RISK)
    with st.expander("Transparency (Article 50)"):
        checkboxes(TRANSPARENCY)

    if st.button("Classify", type="primary", use_container_width=True):
        with st.spinner("Classifying..."):
            classify()

with right:
    st.subheader("2. Result")
    if st.session_state["error"]:
        st.error(st.session_state["error"])
    elif st.session_state["result"]:
        show_result(st.session_state["result"])
    else:
        st.markdown(
            "**No classification yet.** Pick a sample or answer the questions, then "
            "press Classify. The answer will cite the AI Act articles it used."
        )
    st.caption("Human review and the audit trail arrive in the next step.")