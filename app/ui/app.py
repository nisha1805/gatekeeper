import streamlit as st

st.set_page_config(page_title="Gatekeeper", layout="wide")

navigation = st.navigation(
    [
        st.Page("views/copilot.py", title="Compliance copilot"),
        st.Page("views/audit.py", title="Audit trail"),
    ]
)
navigation.run()