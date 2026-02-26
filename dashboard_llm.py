import streamlit as st
import requests
import pandas as pd
from io import BytesIO
import json
import time

FASTAPI_URL = "http://localhost:8000"

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="LoanSense AI",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# CUSTOM CSS — Dark luxury fintech aesthetic
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=Sora:wght@300;400;500;600&display=swap');

:root {
    --bg:        #080c14;
    --surface:   #0e1624;
    --card:      #111927;
    --border:    #1e2d45;
    --accent:    #00c6ff;
    --accent2:   #7b61ff;
    --gold:      #f5c842;
    --green:     #00e5a0;
    --red:       #ff4f6d;
    --text:      #e8edf5;
    --muted:     #6b7fa3;
    --font-head: 'DM Serif Display', serif;
    --font-body: 'Sora', sans-serif;
    --font-mono: 'DM Mono', monospace;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--font-body) !important;
}

[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}

[data-testid="stSidebar"] * { color: var(--text) !important; }

h1, h2, h3 {
    font-family: var(--font-head) !important;
    color: var(--text) !important;
}

/* Cards */
.ls-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 20px;
    position: relative;
    overflow: hidden;
}
.ls-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
}

/* Metric cards */
.metric-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 24px;
}
.metric-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 20px;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s ease, border-color 0.2s ease;
}
.metric-card:hover {
    transform: translateY(-2px);
    border-color: var(--accent);
}
.metric-card .metric-icon {
    font-size: 28px;
    margin-bottom: 8px;
}
.metric-card .metric-value {
    font-family: var(--font-mono);
    font-size: 28px;
    font-weight: 500;
    color: var(--accent);
    line-height: 1;
    margin-bottom: 6px;
}
.metric-card .metric-label {
    font-size: 12px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

/* Pipeline steps */
.pipeline {
    display: flex;
    align-items: center;
    gap: 0;
    margin: 20px 0;
    padding: 20px 24px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
}
.step {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
    position: relative;
}
.step-circle {
    width: 44px; height: 44px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
    border: 2px solid var(--border);
    background: var(--surface);
    position: relative;
    z-index: 2;
    transition: all 0.3s;
}
.step.active .step-circle {
    border-color: var(--accent);
    background: rgba(0,198,255,0.12);
    box-shadow: 0 0 20px rgba(0,198,255,0.3);
}
.step.done .step-circle {
    border-color: var(--green);
    background: rgba(0,229,160,0.12);
}
.step-label {
    font-size: 11px;
    color: var(--muted);
    margin-top: 8px;
    text-align: center;
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.step.active .step-label { color: var(--accent); }
.step.done .step-label { color: var(--green); }
.step-connector {
    flex: 1;
    height: 2px;
    background: var(--border);
    position: relative;
    top: -12px;
}
.step-connector.done { background: linear-gradient(90deg, var(--green), var(--accent)); }

/* Quality bar */
.quality-bar-wrap {
    background: var(--surface);
    border-radius: 100px;
    height: 10px;
    overflow: hidden;
    margin: 8px 0 4px;
}
.quality-bar-fill {
    height: 100%;
    border-radius: 100px;
    background: linear-gradient(90deg, var(--accent2), var(--accent), var(--green));
    transition: width 0.8s cubic-bezier(0.4,0,0.2,1);
}

/* Field score rows */
.field-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
}
.field-name {
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--muted);
    width: 160px;
    flex-shrink: 0;
}
.field-bar-wrap {
    flex: 1;
    background: var(--surface);
    border-radius: 100px;
    height: 6px;
    overflow: hidden;
}
.field-bar-fill {
    height: 100%;
    border-radius: 100px;
}
.field-score {
    font-family: var(--font-mono);
    font-size: 12px;
    width: 44px;
    text-align: right;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #00c6ff22, #7b61ff22) !important;
    border: 1px solid var(--accent) !important;
    color: var(--accent) !important;
    border-radius: 10px !important;
    font-family: var(--font-body) !important;
    font-weight: 500 !important;
    letter-spacing: 0.04em !important;
    transition: all 0.2s ease !important;
    padding: 12px 24px !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #00c6ff44, #7b61ff44) !important;
    box-shadow: 0 0 24px rgba(0,198,255,0.25) !important;
    transform: translateY(-1px) !important;
}

/* Upload zone */
[data-testid="stFileUploader"] {
    border: 2px dashed var(--border) !important;
    border-radius: 14px !important;
    background: var(--card) !important;
    padding: 8px !important;
    transition: border-color 0.2s !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--accent) !important;
}

/* Dataframes */
[data-testid="stDataFrame"] {
    border-radius: 12px !important;
    overflow: hidden !important;
}

/* Alerts */
.stSuccess, .stError, .stWarning, .stInfo {
    border-radius: 10px !important;
    font-family: var(--font-body) !important;
}

/* Section headers */
.section-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 28px 0 16px;
}
.section-header h3 {
    margin: 0;
    font-size: 20px;
}
.section-badge {
    background: rgba(0,198,255,0.12);
    border: 1px solid rgba(0,198,255,0.3);
    color: var(--accent);
    font-family: var(--font-mono);
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 100px;
    letter-spacing: 0.08em;
}

/* Mapping table */
.map-row {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 10px 16px;
    border-radius: 8px;
    margin-bottom: 6px;
    background: var(--surface);
    border: 1px solid var(--border);
    font-family: var(--font-mono);
    font-size: 13px;
    transition: border-color 0.2s;
}
.map-row:hover { border-color: var(--accent); }
.map-excel { color: var(--gold); flex: 1; }
.map-arrow { color: var(--muted); font-size: 16px; }
.map-db { color: var(--green); flex: 1; }

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    background: var(--card) !important;
    border-radius: 12px !important;
    padding: 4px !important;
    gap: 4px !important;
    border: 1px solid var(--border) !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    font-family: var(--font-body) !important;
    color: var(--muted) !important;
    font-size: 13px !important;
}
.stTabs [aria-selected="true"] {
    background: rgba(0,198,255,0.15) !important;
    color: var(--accent) !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--surface); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--muted); }

/* Spinner */
.stSpinner { color: var(--accent) !important; }

/* Hero */
.hero {
    text-align: center;
    padding: 40px 0 24px;
}
.hero-title {
    font-family: var(--font-head);
    font-size: 48px;
    background: linear-gradient(135deg, #00c6ff, #7b61ff, #00e5a0);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 8px;
    line-height: 1.1;
}
.hero-sub {
    color: var(--muted);
    font-size: 15px;
    letter-spacing: 0.04em;
    font-family: var(--font-mono);
}

/* API status dot */
.api-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;
}
.api-dot.on { background: var(--green); box-shadow: 0 0 8px var(--green); }
.api-dot.off { background: var(--red); }

/* Error row highlight */
.error-badge {
    background: rgba(255,79,109,0.15);
    border: 1px solid rgba(255,79,109,0.3);
    color: var(--red);
    font-family: var(--font-mono);
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 6px;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def field_color(score):
    if score >= 80: return "#00e5a0"
    if score >= 50: return "#f5c842"
    return "#ff4f6d"

def render_quality_panel(quality: dict):
    if not quality:
        return
    overall = quality.get("overall", 0)
    fields  = quality.get("fields", {})

    color = field_color(overall)
    st.markdown(f"""
    <div class="ls-card">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
            <div>
                <div style="font-family:var(--font-head);font-size:22px">Data Quality Score</div>
                <div style="color:var(--muted);font-size:13px;margin-top:2px">Post-repair field validation</div>
            </div>
            <div style="font-family:var(--font-mono);font-size:48px;font-weight:500;color:{color}">{overall}%</div>
        </div>
        <div class="quality-bar-wrap">
            <div class="quality-bar-fill" style="width:{overall}%"></div>
        </div>
    """, unsafe_allow_html=True)

    for field, score in fields.items():
        c = field_color(score)
        st.markdown(f"""
        <div class="field-row">
            <div class="field-name">{field}</div>
            <div class="field-bar-wrap">
                <div class="field-bar-fill" style="width:{score}%;background:{c}"></div>
            </div>
            <div class="field-score" style="color:{c}">{score}%</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

def render_mapping(mapping: dict):
    if not mapping:
        st.info("No mapping data available.")
        return
    st.markdown("""
    <div class="ls-card">
    <div style="font-family:var(--font-head);font-size:20px;margin-bottom:16px">
        Field Mapping — LLM Column Detection
    </div>
    """, unsafe_allow_html=True)

    # Header
    st.markdown("""
    <div style="display:flex;gap:16px;padding:6px 16px;font-family:var(--font-mono);
                font-size:11px;color:var(--muted);letter-spacing:0.08em;text-transform:uppercase;">
        <div style="flex:1">Excel Column</div>
        <div style="width:32px"></div>
        <div style="flex:1">DB Field</div>
    </div>
    """, unsafe_allow_html=True)

    for excel_col, db_field in mapping.items():
        st.markdown(f"""
        <div class="map-row">
            <div class="map-excel">📋 {excel_col}</div>
            <div class="map-arrow">→</div>
            <div class="map-db">🗄 {db_field}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

def render_pipeline_status(step: int):
    """step: 0=idle, 1=mapping, 2=repairing, 3=done"""
    steps = [
        ("📤", "Upload"),
        ("🧠", "Mapping"),
        ("🔧", "Repair"),
        ("✅", "Done"),
    ]
    html = '<div class="pipeline">'
    for i, (icon, label) in enumerate(steps):
        cls = "done" if i < step else ("active" if i == step else "")
        html += f"""
        <div class="step {cls}">
            <div class="step-circle">{icon}</div>
            <div class="step-label">{label}</div>
        </div>
        """
        if i < len(steps) - 1:
            conn_cls = "done" if i < step - 1 else ""
            html += f'<div class="step-connector {conn_cls}"></div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

def download_excel(df: pd.DataFrame, label: str, filename: str):
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    st.download_button(
        label=label,
        data=buffer.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

def check_api():
    try:
        r = requests.get(f"{FASTAPI_URL}/", timeout=3)
        return r.status_code == 200
    except:
        return False

def get_stats():
    try:
        r = requests.get(f"{FASTAPI_URL}/stats/", timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 0 24px">
        <div style="font-family:'DM Serif Display',serif;font-size:26px;
                    background:linear-gradient(135deg,#00c6ff,#7b61ff);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    background-clip:text;">LoanSense</div>
        <div style="font-family:'DM Mono',monospace;font-size:11px;
                    color:#6b7fa3;letter-spacing:0.1em;text-transform:uppercase;
                    margin-top:2px;">AI Ingestion System</div>
    </div>
    """, unsafe_allow_html=True)

    # API Health
    api_ok = check_api()
    dot_cls = "on" if api_ok else "off"
    api_label = "FastAPI Online" if api_ok else "FastAPI Offline"
    st.markdown(f"""
    <div style="background:var(--card);border:1px solid var(--border);
                border-radius:10px;padding:12px 16px;margin-bottom:20px;
                font-size:13px;font-family:'DM Mono',monospace">
        <span class="api-dot {dot_cls}"></span>{api_label}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:12px;color:#6b7fa3;font-family:'DM Mono',monospace;
                text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">
        Pipeline
    </div>
    """, unsafe_allow_html=True)

    for item in ["① Upload Excel", "② LLM Field Mapping", "③ LLM Row Repair", "④ Rule Validation", "⑤ Save to DB"]:
        st.markdown(f"""
        <div style="padding:8px 12px;font-size:13px;color:#6b7fa3;
                    border-left:2px solid #1e2d45;margin-bottom:4px">
            {item}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:12px;color:#6b7fa3;font-family:'DM Mono',monospace;
                text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">
        APIs Used
    </div>
    <div style="font-size:12px;padding:8px 12px;background:var(--card);
                border-radius:8px;border:1px solid var(--border);
                font-family:'DM Mono',monospace;color:#6b7fa3;line-height:1.8">
        🧠 API 1 — Field Mapping<br>
        🔧 API 2 — Row Unjumbling
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# MAIN CONTENT
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-title">LoanSense AI</div>
    <div class="hero-sub">Dual-LLM • Field Mapping • Row Repair • Smart Ingestion</div>
</div>
""", unsafe_allow_html=True)

# ─── Session State ───
if "validated_rows" not in st.session_state:
    st.session_state.validated_rows = None
if "validated_quality" not in st.session_state:
    st.session_state.validated_quality = None
if "validated_mapping" not in st.session_state:
    st.session_state.validated_mapping = None

# ─── TABS ───
tab_ingest, tab_stats, tab_db = st.tabs(["⚡  Ingest", "📊  Analytics", "🗄  Database"])


# ══════════════════════════════════════════════
# TAB 1 — INGEST
# ══════════════════════════════════════════════
with tab_ingest:

    # Upload zone
    st.markdown("""
    <div class="section-header">
        <h3>Upload Excel</h3>
        <span class="section-badge">STEP 1</span>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Drop your Excel file here or click to browse",
        type=["xlsx"],
        label_visibility="collapsed"
    )

    if uploaded_file:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;padding:12px 16px;
                    background:rgba(0,229,160,0.08);border:1px solid rgba(0,229,160,0.25);
                    border-radius:10px;margin:12px 0;font-family:'DM Mono',monospace;font-size:13px">
            <span style="color:#00e5a0">✓</span>
            <span style="color:#e8edf5">{uploaded_file.name}</span>
            <span style="color:#6b7fa3;margin-left:auto">{uploaded_file.size / 1024:.1f} KB</span>
        </div>
        """, unsafe_allow_html=True)

        # Quick peek
        try:
            peek_df = pd.read_excel(uploaded_file, nrows=3)
            uploaded_file.seek(0)
            st.markdown(f"""
            <div style="font-family:'DM Mono',monospace;font-size:11px;color:#6b7fa3;
                        margin-bottom:6px;text-transform:uppercase;letter-spacing:0.06em">
                Preview — {len(peek_df.columns)} columns detected
            </div>
            """, unsafe_allow_html=True)
            st.dataframe(peek_df, use_container_width=True, height=130)
            uploaded_file.seek(0)
        except:
            pass

    # ── Action Buttons ──
    st.markdown("""
    <div class="section-header">
        <h3>Run Pipeline</h3>
        <span class="section-badge">STEP 2</span>
    </div>
    """, unsafe_allow_html=True)

    col_v, col_u = st.columns(2)

    # ── VALIDATE ──
    with col_v:
        if st.button("🔍  Validate & Preview", use_container_width=True):
            if not uploaded_file:
                st.error("Please upload an Excel file first.")
            elif not api_ok:
                st.error("FastAPI server is offline. Please start it first.")
            else:
                render_pipeline_status(1)
                with st.spinner("🧠 API 1: Detecting field mapping..."):
                    time.sleep(0.3)

                with st.spinner("🔧 API 2: Unjumbling rows with LLM..."):
                    files = {"file": ("file.xlsx", uploaded_file.getvalue(),
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                    res = requests.post(f"{FASTAPI_URL}/validate/", files=files, timeout=300)

                render_pipeline_status(3)

                if res.status_code == 200:
                    data = res.json()
                    st.success(f"✅ Validation complete — {data.get('total_rows', 0)} rows processed")

                    # Store in session state for direct upload
                    st.session_state.validated_rows    = data.get("preview", [])
                    st.session_state.validated_quality = data.get("quality", {})
                    st.session_state.validated_mapping = data.get("mapping", {})

                    # ── Metrics row ──
                    quality = data.get("quality", {})
                    overall = quality.get("overall", 0)
                    mapping = data.get("mapping", {})
                    errors  = data.get("errors", [])
                    total   = data.get("total_rows", 0)
                    conf    = round(len(mapping) / 10 * 100, 1) if mapping else 0

                    st.markdown(f"""
                    <div class="metric-grid">
                        <div class="metric-card">
                            <div class="metric-icon">📋</div>
                            <div class="metric-value">{total}</div>
                            <div class="metric-label">Total Rows</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-icon">🗺️</div>
                            <div class="metric-value" style="color:#f5c842">{conf}%</div>
                            <div class="metric-label">Map Confidence</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-icon">✨</div>
                            <div class="metric-value" style="color:#00e5a0">{overall}%</div>
                            <div class="metric-label">Data Quality</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-icon">⚠️</div>
                            <div class="metric-value" style="color:{'#ff4f6d' if errors else '#00e5a0'}">{len(errors)}</div>
                            <div class="metric-label">Repair Errors</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # ── Tabs for results ──
                    r1, r2, r3, r4 = st.tabs(["🗺 Field Mapping", "📊 Quality", "🔁 Before / After", "⚠️ Errors"])

                    with r1:
                        render_mapping(mapping)

                    with r2:
                        render_quality_panel(quality)

                    with r3:
                        orig_data    = data.get("original_preview", [])
                        cleaned_data = data.get("preview", [])
                        orig_df    = pd.DataFrame(orig_data)
                        cleaned_df = pd.DataFrame(cleaned_data)

                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("""
                            <div style="font-family:'DM Mono',monospace;font-size:12px;
                                        color:#f5c842;text-transform:uppercase;
                                        letter-spacing:0.06em;margin-bottom:8px">
                                📥 Original
                            </div>""", unsafe_allow_html=True)
                            st.dataframe(orig_df, use_container_width=True, height=380)

                        with c2:
                            st.markdown("""
                            <div style="font-family:'DM Mono',monospace;font-size:12px;
                                        color:#00e5a0;text-transform:uppercase;
                                        letter-spacing:0.06em;margin-bottom:8px">
                                ✨ Cleaned
                            </div>""", unsafe_allow_html=True)
                            st.dataframe(cleaned_df, use_container_width=True, height=380)

                        st.markdown("<br>", unsafe_allow_html=True)
                        download_excel(
                            cleaned_df,
                            "⬇️  Download Cleaned Excel",
                            "cleaned_loan_applicants.xlsx"
                        )

                    with r4:
                        if errors:
                            for err in errors:
                                st.markdown(f"""
                                <div style="display:flex;align-items:center;gap:12px;
                                            padding:10px 16px;background:rgba(255,79,109,0.08);
                                            border:1px solid rgba(255,79,109,0.2);
                                            border-radius:8px;margin-bottom:6px;
                                            font-family:'DM Mono',monospace;font-size:13px">
                                    <span class="error-badge">Row {err.get('row')}</span>
                                    <span style="color:#6b7fa3">{err.get('error','Unknown error')}</span>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.success("🎉 No repair errors — all rows processed cleanly!")
                else:
                    st.error("❌ Validation failed")
                    st.code(res.text)

    # ── UPLOAD TO DB ──
    with col_u:
        # Show whether validated data is ready
        if st.session_state.validated_rows:
            n = len(st.session_state.validated_rows)
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;padding:10px 14px;
                        background:rgba(0,229,160,0.08);border:1px solid rgba(0,229,160,0.2);
                        border-radius:10px;margin-bottom:10px;
                        font-family:'DM Mono',monospace;font-size:12px">
                <span style="color:#00e5a0">✓</span>
                <span style="color:#6b7fa3">{n} validated rows ready to upload</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="display:flex;align-items:center;gap:10px;padding:10px 14px;
                        background:rgba(107,127,163,0.08);border:1px solid rgba(107,127,163,0.2);
                        border-radius:10px;margin-bottom:10px;
                        font-family:'DM Mono',monospace;font-size:12px;color:#6b7fa3">
                ⚠ Run Validate first to prepare data
            </div>
            """, unsafe_allow_html=True)

        if st.button("🚀  Upload to Database", use_container_width=True):
            if not api_ok:
                st.error("FastAPI server is offline.")
            elif not st.session_state.validated_rows:
                st.warning("Please run **Validate & Preview** first — no validated data found.")
            else:
                with st.spinner("💾 Saving validated rows to DB..."):
                    res = requests.post(
                        f"{FASTAPI_URL}/upload-validated/",
                        json={
                            "rows":    st.session_state.validated_rows,
                            "quality": st.session_state.validated_quality or {}
                        },
                        timeout=60
                    )

                if res.status_code == 200:
                    data = res.json()
                    quality = data.get("quality", {})
                    overall = quality.get("overall", 0)

                    # Clear session after successful upload
                    st.session_state.validated_rows    = None
                    st.session_state.validated_quality = None
                    st.session_state.validated_mapping = None

                    st.markdown(f"""
                    <div class="ls-card" style="border-color:rgba(0,229,160,0.3)">
                        <div style="font-family:'DM Serif Display',serif;font-size:22px;
                                    color:#00e5a0;margin-bottom:16px">🎉 Upload Successful!</div>
                        <div class="metric-grid" style="grid-template-columns:repeat(3,1fr)">
                            <div class="metric-card">
                                <div class="metric-icon">🆕</div>
                                <div class="metric-value">{data.get('inserted',0)}</div>
                                <div class="metric-label">Inserted</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-icon">🔄</div>
                                <div class="metric-value" style="color:#7b61ff">{data.get('updated',0)}</div>
                                <div class="metric-label">Updated</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-icon">✨</div>
                                <div class="metric-value" style="color:#00e5a0">{overall}%</div>
                                <div class="metric-label">Quality</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if quality:
                        render_quality_panel(quality)
                else:
                    st.error("❌ Upload failed")
                    st.code(res.text)


# ══════════════════════════════════════════════
# TAB 2 — ANALYTICS
# ══════════════════════════════════════════════
with tab_stats:
    st.markdown("""
    <div class="section-header">
        <h3>Database Analytics</h3>
        <span class="section-badge">LIVE</span>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🔄  Refresh Stats", use_container_width=False):
        st.rerun()

    stats = get_stats()

    if stats and "error" not in stats:
        total_ap = stats.get("total_applicants", 0)
        avg_loan = stats.get("avg_loan_amount", 0)
        avg_inc  = stats.get("avg_monthly_income", 0)
        by_pur   = stats.get("by_purpose", [])
        by_emp   = stats.get("by_employment", [])

        st.markdown(f"""
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-icon">👥</div>
                <div class="metric-value">{total_ap:,}</div>
                <div class="metric-label">Total Applicants</div>
            </div>
            <div class="metric-card">
                <div class="metric-icon">💰</div>
                <div class="metric-value" style="color:#f5c842">₹{avg_loan/100000:.1f}L</div>
                <div class="metric-label">Avg Loan Amount</div>
            </div>
            <div class="metric-card">
                <div class="metric-icon">📈</div>
                <div class="metric-value" style="color:#00e5a0">₹{avg_inc/1000:.0f}K</div>
                <div class="metric-label">Avg Monthly Income</div>
            </div>
            <div class="metric-card">
                <div class="metric-icon">🎯</div>
                <div class="metric-value" style="color:#7b61ff">{len(by_pur)}</div>
                <div class="metric-label">Loan Categories</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_p, col_e = st.columns(2)

        with col_p:
            st.markdown("""
            <div class="ls-card">
                <div style="font-family:'DM Serif Display',serif;font-size:18px;margin-bottom:16px">
                    Loan Purpose Distribution
                </div>
            """, unsafe_allow_html=True)
            if by_pur:
                max_count = max(r["count"] for r in by_pur)
                for row in sorted(by_pur, key=lambda x: -x["count"]):
                    pct = round(row["count"] / max_count * 100, 1) if max_count else 0
                    st.markdown(f"""
                    <div class="field-row">
                        <div class="field-name">{row['purpose'] or 'Unknown'}</div>
                        <div class="field-bar-wrap">
                            <div class="field-bar-fill" style="width:{pct}%;background:#7b61ff"></div>
                        </div>
                        <div class="field-score" style="color:#7b61ff">{row['count']}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No data yet.")
            st.markdown("</div>", unsafe_allow_html=True)

        with col_e:
            st.markdown("""
            <div class="ls-card">
                <div style="font-family:'DM Serif Display',serif;font-size:18px;margin-bottom:16px">
                    Employment Type Distribution
                </div>
            """, unsafe_allow_html=True)
            if by_emp:
                max_count = max(r["count"] for r in by_emp)
                colors = ["#00c6ff", "#00e5a0", "#f5c842"]
                for i, row in enumerate(sorted(by_emp, key=lambda x: -x["count"])):
                    pct = round(row["count"] / max_count * 100, 1) if max_count else 0
                    c = colors[i % len(colors)]
                    st.markdown(f"""
                    <div class="field-row">
                        <div class="field-name">{row['type'] or 'Unknown'}</div>
                        <div class="field-bar-wrap">
                            <div class="field-bar-fill" style="width:{pct}%;background:{c}"></div>
                        </div>
                        <div class="field-score" style="color:{c}">{row['count']}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No data yet.")
            st.markdown("</div>", unsafe_allow_html=True)

    elif not api_ok:
        st.markdown("""
        <div class="ls-card" style="text-align:center;padding:48px">
            <div style="font-size:48px;margin-bottom:16px">🔌</div>
            <div style="font-family:'DM Serif Display',serif;font-size:22px;color:#6b7fa3">
                FastAPI server is offline
            </div>
            <div style="color:#6b7fa3;margin-top:8px;font-size:13px">
                Start the server to view live analytics
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="ls-card" style="text-align:center;padding:48px">
            <div style="font-size:48px;margin-bottom:16px">📭</div>
            <div style="font-family:'DM Serif Display',serif;font-size:22px;color:#6b7fa3">
                No data in database yet
            </div>
            <div style="color:#6b7fa3;margin-top:8px;font-size:13px">
                Upload your first Excel file to see analytics here
            </div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════
# TAB 3 — DATABASE VIEWER
# ══════════════════════════════════════════════
with tab_db:
    st.markdown("""
    <div class="section-header">
        <h3>Live Database Records</h3>
        <span class="section-badge">READ-ONLY</span>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🔄  Fetch Records", use_container_width=False):
        try:
            from sqlalchemy import create_engine, text
            from dotenv import load_dotenv
            import os
            load_dotenv()
            _url = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
            _eng = create_engine(_url)
            with _eng.connect() as conn:
                df = pd.read_sql("SELECT * FROM loan_applicants ORDER BY created_at DESC LIMIT 200", conn)

            st.markdown(f"""
            <div style="font-family:'DM Mono',monospace;font-size:12px;color:#6b7fa3;
                        margin-bottom:10px;text-transform:uppercase;letter-spacing:0.06em">
                Showing {len(df)} records (latest 200)
            </div>
            """, unsafe_allow_html=True)
            st.dataframe(df, use_container_width=True, height=480)

            # Download
            download_excel(df, "⬇️  Export All Records", "loan_applicants_db.xlsx")

        except Exception as e:
            st.error(f"Could not connect to DB: {e}")