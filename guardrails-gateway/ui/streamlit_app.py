

import os

import requests
import streamlit as st

# Inside Docker, the UI container reaches the API container by its
# service name ("api"), not localhost. Outside Docker (running locally),
# localhost works. This env var lets the same code work in both cases.
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="SentraGuard Lite", layout="centered")
st.title("SentraGuard Lite — Guardrails Gateway")
st.caption("Enter a prompt and (optionally) retrieved context docs, then analyze.")

prompt = st.text_area("Prompt", height=100, placeholder="Type a prompt to check...")

st.subheader("Context documents (optional, up to 3)")
context_docs = []
for i in range(3):
    doc_text = st.text_area(f"Doc {i + 1}", key=f"doc_{i}", height=60)
    if doc_text.strip():
        context_docs.append({"id": f"doc-{i + 1}", "text": doc_text})

if st.button("Analyze", type="primary"):
    if not prompt.strip():
        st.warning("Please enter a prompt first.")
    else:
        payload = {"prompt": prompt, "context_docs": context_docs, "metadata": {}}
        try:
            response = requests.post(f"{API_BASE_URL}/analyze", json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()

            st.subheader("Decision")
            col1, col2 = st.columns(2)
            col1.metric("Decision", result["decision"].upper())
            col2.metric("Risk score", result["risk_score"])
            st.write("**Tags:**", ", ".join(result["risk_tags"]) or "none")

            st.subheader("Sanitized output")
            st.write("**Sanitized prompt:**")
            st.code(result["sanitized_prompt"])
            if result["sanitized_context_docs"]:
                st.write("**Sanitized context docs:**")
                for doc in result["sanitized_context_docs"]:
                    st.code(f"[{doc['id']}] {doc['text']}")

            with st.expander("Raw JSON response"):
                st.json(result)

        except requests.exceptions.RequestException as e:
            st.error(f"Could not reach API at {API_BASE_URL}: {e}")
