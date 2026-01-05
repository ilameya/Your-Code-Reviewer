from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from ocr.core.reviewer import review_code

def inject_css():
    st.markdown(
        """
        <style>
        /* Overall background */
        .stApp {
            background: #F7F9FC;
        }

        /* Main container */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: #FFFFFF !important;
            border-right: 1px solid #E5E7EB;
        }

        /* Headings */
        h1, h2, h3 {
            color: #111827;
        }

        /* File uploader */
        section[data-testid="stFileUploaderDropzone"] {
            border: 2px dashed #CBD5E1;
            border-radius: 12px;
            background: #FFFFFF;
        }

        /* Buttons */
        .stButton > button {
            border-radius: 10px;
            padding: 0.55rem 1rem;
            border: 1px solid #CBD5E1;
            background: #EEF2FF;
            color: #1E3A8A;
            font-weight: 600;
        }
        .stButton > button:hover {
            background: #E0E7FF;
            border-color: #A5B4FC;
        }

        /* Dataframe */
        div[data-testid="stDataFrame"] {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #E5E7EB;
            background: #FFFFFF;
        }

        /* Expanders (cards) */
        details {
            border-radius: 12px !important;
            border: 1px solid #E5E7EB !important;
            background: #FFFFFF !important;
            padding: 0.4rem 0.8rem;
        }

        /* Score badge */
        .ycr-badge {
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            background: #F1F5F9;
            border: 1px solid #CBD5E1;
            color: #0F172A;
            font-size: 0.9rem;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def decode_bytes(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", errors="replace")


def is_probably_text(filename: str) -> bool:
    bad_ext = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".exe", ".dmg", ".bin"}
    return Path(filename).suffix.lower() not in bad_ext


def score_badge(score: int) -> str:
    if score >= 80:
        icon = "🟢"
        label = "Good"
    elif score >= 50:
        icon = "🟡"
        label = "Needs work"
    else:
        icon = "🔴"
        label = "Risky"
    return f'<span class="ycr-badge">{icon} <b>{score}/100</b> · {label}</span>'


st.set_page_config(page_title="YCR: Your Code Reviewer", layout="wide")
inject_css()

st.title("YCR: Your Code Reviewer")
st.caption("Upload code files. Get instant feedback. No patches. No magic. Just structured criticism.")

with st.sidebar:
    st.header("Settings")
    model = st.text_input("Ollama model", value="llama3.1:latest")
    base_url = st.text_input("Ollama base URL", value="http://localhost:11434")
    temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.2, step=0.05)

    st.divider()
    st.subheader("Filters")
    sev_filter = st.multiselect(
        "Severity",
        options=["low", "medium", "high", "critical"],
        default=["low", "medium", "high", "critical"],
    )
    search = st.text_input("Search in title/details", value="").strip()

    st.divider()
    st.markdown(
        "**Supported uploads:** .py, .c, .cpp, .h, .js, .ts, .java, .go, .rs, .cs, .php, .rb, .swift, .kt, .scala, .sh, etc."
    )

uploaded = st.file_uploader("Upload code file(s)", type=None, accept_multiple_files=True)

c_run, c_clear = st.columns([1, 1])
with c_run:
    run_review = st.button("Review now", use_container_width=True)
with c_clear:
    if st.button("Clear", use_container_width=True):
        st.session_state.pop("reports", None)
        st.rerun()

if not uploaded:
    st.info("Upload one or more code files to review.")
    st.stop()

if run_review:
    reports = []
    for uf in uploaded:
        fname = uf.name
        if not is_probably_text(fname):
            reports.append(
                {
                    "path": fname,
                    "language": "unknown",
                    "summary": "Skipped non-text/binary-ish file",
                    "score": 0,
                    "findings": [],
                }
            )
            continue

        code = decode_bytes(uf.getvalue())
        with st.spinner(f"Reviewing {fname}..."):
            try:
                report = review_code(
                    path=fname,
                    code=code,
                    model=model,
                    base_url=base_url,
                    temperature=temperature,
                )
                data = report.model_dump()
            except Exception as e:
                data = {
                    "path": fname,
                    "language": "unknown",
                    "summary": f"Review failed: {e}",
                    "score": 0,
                    "findings": [],
                }
        reports.append(data)

    st.session_state["reports"] = reports

reports = st.session_state.get("reports")
if not reports:
    st.warning("Click **Review now** to generate feedback.")
    st.stop()

for data in reports:
    fname = data["path"]
    findings = data.get("findings", [])

    if findings:
        df = pd.DataFrame(findings)

        if "severity" in df.columns:
            df = df[df["severity"].isin(sev_filter)]

        if search:
            q = search.lower()
            title = df["title"].astype(str).str.lower() if "title" in df.columns else ""
            details = df["details"].astype(str).str.lower() if "details" in df.columns else ""
            df = df[title.str.contains(q, na=False) | details.str.contains(q, na=False)]

        filtered_findings = df.to_dict(orient="records")
    else:
        filtered_findings = []

    header_left, header_right = st.columns([3, 2])
    with header_left:
        st.markdown(f"### 📄 {fname}")
        st.write(f"**Summary:** {data['summary']}")
    with header_right:
        st.markdown(score_badge(int(data["score"])), unsafe_allow_html=True)
        st.caption(f"Language: {data['language']}")

    with st.expander("Show findings", expanded=bool(filtered_findings)):
        if filtered_findings:
            df = pd.DataFrame(filtered_findings)
            preferred_cols = ["category", "severity", "line_start", "line_end", "title", "details", "suggestion"]
            cols = [c for c in preferred_cols if c in df.columns] + [c for c in df.columns if c not in preferred_cols]
            st.dataframe(df[cols], use_container_width=True, hide_index=True)
        else:
            st.success("No findings (after filters).")

    st.download_button(
        label="Download JSON report",
        data=json.dumps(data, indent=2).encode("utf-8"),
        file_name=f"{Path(fname).stem}_review.json",
        mime="application/json",
        use_container_width=True,
    )

    st.divider()
