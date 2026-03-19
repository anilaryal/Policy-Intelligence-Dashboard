"""
Nepal Climate Policy Intelligence Portal
Run with: streamlit run app.py
Requires: pip install streamlit anthropic PyPDF2 plotly pandas
"""

import streamlit as st
import json
import os
import io
import time
import requests
from pathlib import Path
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Graceful imports (never crash on missing packages) ─────────────────────
try:
    import anthropic
    ANTHROPIC_SDK = True
except ImportError:
    ANTHROPIC_SDK = False

try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nepal Climate Policy Intelligence Portal",
    page_icon="🏔",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@400;500;600&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  h1, h2, h3 { font-family: 'Lora', serif !important; }

  .main { background: #faf7f2; }
  .block-container { padding: 1.5rem 2rem 2rem; max-width: 1300px; }

  /* Sidebar */
  section[data-testid="stSidebar"] {
    background: #1a4a2e !important;
    color: white;
  }
  section[data-testid="stSidebar"] * { color: white !important; }
  section[data-testid="stSidebar"] .stSelectbox > div > div {
    background: rgba(255,255,255,0.1) !important;
    border-color: rgba(255,255,255,0.2) !important;
    color: white !important;
  }

  /* Metric cards */
  [data-testid="metric-container"] {
    background: #ffffff;
    border: 0.5px solid rgba(26,26,24,0.12);
    border-radius: 10px;
    padding: 1rem;
    border-left: 3px solid #2d6a45;
  }

  /* Chat messages */
  .user-msg {
    background: #2d6a45; color: white; padding: 10px 14px;
    border-radius: 12px 12px 4px 12px; margin: 6px 0 6px 20%;
    font-size: 13px; line-height: 1.6;
  }
  .bot-msg {
    background: #f5f0e8; color: #1a1a18; padding: 10px 14px;
    border-radius: 12px 12px 12px 4px; margin: 6px 20% 6px 0;
    font-size: 13px; line-height: 1.6;
    border: 0.5px solid rgba(26,26,24,0.12);
  }

  /* Policy cards */
  .policy-card {
    background: white; border: 0.5px solid rgba(26,26,24,0.12);
    border-radius: 10px; padding: 14px 16px; margin-bottom: 10px;
    border-left: 3px solid #2d6a45; transition: all 0.15s;
  }
  .policy-card:hover { background: #faf7f2; border-color: #2d6a45; }

  /* Badges */
  .badge {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 11px; font-weight: 500; margin: 2px;
  }
  .badge-green  { background: #2d6a4518; color: #2d6a45; border: 0.5px solid #2d6a4540; }
  .badge-blue   { background: #2e72b018; color: #1e4f7a; border: 0.5px solid #2e72b040; }
  .badge-earth  { background: #c47c4018; color: #7a4a1e; border: 0.5px solid #c47c4040; }
  .badge-red    { background: #c9403018; color: #c94030; border: 0.5px solid #c9403040; }
  .badge-warn   { background: #c47c4018; color: #c47c40; border: 0.5px solid #c47c4040; }

  /* Gap cards */
  .gap-high   { border-left: 3px solid #c94030 !important; }
  .gap-medium { border-left: 3px solid #c47c40 !important; }
  .gap-low    { border-left: 3px solid #8a8a84 !important; }

  /* Section headers */
  .section-label {
    font-size: 11px; color: #8a8a84; text-transform: uppercase;
    letter-spacing: 0.07em; margin-bottom: 8px; font-weight: 500;
  }

  /* Province row */
  .province-row {
    display: flex; align-items: center; gap: 10px; padding: 8px 12px;
    border-radius: 8px; cursor: pointer; margin-bottom: 4px;
  }
  .province-row:hover { background: rgba(255,255,255,0.08); }

  /* Sticker / pill */
  .pill {
    background: #1a4a2e; color: white; padding: 3px 10px;
    border-radius: 20px; font-size: 11px; font-weight: 600;
    display: inline-block;
  }

  /* Hide Streamlit branding */
  #MainMenu { visibility: hidden; }
  footer { visibility: hidden; }
  header { visibility: hidden; }

  /* Scrollable chat */
  .chat-container { max-height: 480px; overflow-y: auto; padding-right: 4px; }

  /* Timeline dot */
  .timeline-dot {
    width: 10px; height: 10px; border-radius: 50%;
    background: #2d6a45; display: inline-block; margin-right: 8px;
  }
</style>
""", unsafe_allow_html=True)

# ── Document catalogue ─────────────────────────────────────────────────────
DOCUMENTS = [
    {
        "id": "ld-framework-2021",
        "title": "National Framework on Climate Change Induced Loss and Damage",
        "short_title": "L&D Framework 2021",
        "year": 2021,
        "level": "Federal",
        "sector": ["Disaster Risk", "Climate Change"],
        "ministry": "Ministry of Forests and Environment",
        "language": "English",
        "keywords": ["loss and damage", "GLOF", "floods", "landslides", "displacement", "insurance", "adaptation"],
        "filename": "Loss_and_Damage_Framework_Nepal_2021_1__1_.pdf",
        "summary": "Defines Nepal's national framework for assessing and responding to climate-induced loss and damage, covering economic and non-economic losses, assessment methodology, and recommendations for institutionalizing L&D processes.",
        "themes": ["Adaptation", "Finance", "Governance"],
        "status": "Approved",
        "highlights": [
            "Climate-induced disasters cause ~65% of all disaster deaths in Nepal",
            "Average annual economic loss: ~0.08% of GDP",
            "2017 Tarai floods alone caused 2.08% GDP loss (NPR 60,716.6M)",
            "Nepal has experienced at least 24 GLOF events historically",
            "Proposes 10-step L&D assessment methodology",
        ],
    },
    {
        "id": "wash-policy-2026",
        "title": "Climate Resilient WASH in Nepal: Policy Alignment, Local Practices and Service Provider Readiness",
        "short_title": "Climate-Resilient WASH 2026",
        "year": 2026,
        "level": "Federal",
        "sector": ["Water", "Health", "Climate Change"],
        "ministry": "Multiple Ministries",
        "language": "English",
        "keywords": ["WASH", "water sanitation hygiene", "climate resilience", "service providers", "local government"],
        "filename": "GSAC_2026_P1_40_ClimateResilient_WASH_in_Nepal.pdf",
        "summary": "Examines policy alignment and local preparedness for climate-resilient water, sanitation and hygiene systems across Nepal's federal structure.",
        "themes": ["Adaptation", "Governance", "Gender & Inclusion"],
        "status": "Active",
        "highlights": [
            "Covers all 3 tiers of Nepal's federal structure",
            "Assesses service provider readiness for climate impacts",
            "Reviews alignment between WASH and climate policies",
        ],
    },
    {
        "id": "climate-policy-2019",
        "title": "National Climate Change Policy 2019 (2076 BS)",
        "short_title": "Climate Change Policy 2019",
        "year": 2019,
        "level": "Federal",
        "sector": ["Climate Change", "Energy", "Agriculture", "Water"],
        "ministry": "Ministry of Forests and Environment",
        "language": "Nepali",
        "keywords": ["mitigation", "adaptation", "carbon neutrality", "renewable energy", "NDC"],
        "filename": "Approved_climate_change_policy_2076.pdf",
        "summary": "Nepal's overarching climate change policy establishing targets for mitigation and adaptation across all sectors, forming the basis for subsequent NDC and NAP formulation.",
        "themes": ["Mitigation", "Adaptation", "Governance", "Finance"],
        "status": "Approved",
        "highlights": [
            "Sets Nepal's net-zero target by 2050",
            "Basis for Nepal's 2nd NDC (2020–2030)",
            "Covers 8 major sectors including energy, forests, agriculture",
            "Calls for dedicated climate finance mechanisms",
        ],
    },
    {
        "id": "health-wash-climate",
        "title": "Nepal Climate Change, Health and WASH Nexus",
        "short_title": "Climate-Health-WASH Nexus",
        "year": 2022,
        "level": "Federal",
        "sector": ["Health", "Water", "Climate Change"],
        "ministry": "Ministry of Health and Population",
        "language": "English",
        "keywords": ["health impacts", "water-borne diseases", "climate vulnerability", "WASH", "epidemics"],
        "filename": "nepalclimatechangehealthwash_1.pdf",
        "summary": "Analyzes the intersection of climate change with public health and WASH outcomes in Nepal, providing evidence for integrated policy responses.",
        "themes": ["Adaptation", "Gender & Inclusion"],
        "status": "Active",
        "highlights": [
            "Epidemics cause 52.8% of climate-induced deaths",
            "Links between extreme rainfall and disease outbreaks",
            "Evidence base for integrated health-WASH-climate policy",
        ],
    },
    {
        "id": "nep-env-1993",
        "title": "Environment Protection Act / Nepal Environment Policy",
        "short_title": "Environment Policy (Foundational)",
        "year": 1993,
        "level": "Federal",
        "sector": ["Environment", "Agriculture", "Water"],
        "ministry": "Ministry of Forests and Environment",
        "language": "English/Nepali",
        "keywords": ["environment protection", "biodiversity", "land use", "conservation"],
        "filename": "nep199367.pdf",
        "summary": "Foundational environmental legislation establishing Nepal's regulatory framework for environmental protection, conservation and sustainable use of natural resources.",
        "themes": ["Governance", "Mitigation"],
        "status": "Foundational",
        "highlights": [
            "Foundational legal framework for all environmental law",
            "Establishes environmental impact assessment requirements",
            "Conservation of biodiversity and forest resources",
        ],
    },
    {
        "id": "climate-finance-2024",
        "title": "Climate Finance and Loss & Damage: Global and Nepal Perspectives",
        "short_title": "Climate Finance L&D 2024",
        "year": 2024,
        "level": "Federal",
        "sector": ["Finance", "Climate Change", "Disaster Risk"],
        "ministry": "National Planning Commission",
        "language": "English",
        "keywords": ["climate finance", "loss and damage fund", "COP28", "adaptation finance", "LDC"],
        "filename": "wp2024040.pdf",
        "summary": "Reviews global climate finance architecture with focus on the newly established Loss and Damage Fund and implications for Nepal's access to climate resources.",
        "themes": ["Finance", "Governance", "Adaptation"],
        "status": "Active",
        "highlights": [
            "Analysis of COP28 Loss & Damage Fund outcomes",
            "Nepal's eligibility and access pathways",
            "Identifies gaps between climate needs and finance flows",
        ],
    },
]

PROVINCES = [
    {"id": 1, "name": "Koshi",          "risk": "High",      "risk_score": 4, "docs": 8,  "hazards": ["GLOF", "Landslides", "Floods"]},
    {"id": 2, "name": "Madhesh",        "risk": "High",      "risk_score": 4, "docs": 5,  "hazards": ["Floods", "Heat waves", "Drought"]},
    {"id": 3, "name": "Bagmati",        "risk": "Moderate",  "risk_score": 3, "docs": 12, "hazards": ["Urban flooding", "Landslides", "Water stress"]},
    {"id": 4, "name": "Gandaki",        "risk": "High",      "risk_score": 4, "docs": 7,  "hazards": ["GLOF", "Landslides", "Drought"]},
    {"id": 5, "name": "Lumbini",        "risk": "Moderate",  "risk_score": 3, "docs": 6,  "hazards": ["Flooding", "Drought", "Heatwaves"]},
    {"id": 6, "name": "Karnali",        "risk": "Very High", "risk_score": 5, "docs": 4,  "hazards": ["Drought", "Food insecurity", "Cold waves"]},
    {"id": 7, "name": "Sudurpashchim",  "risk": "Very High", "risk_score": 5, "docs": 5,  "hazards": ["Drought", "Floods", "Landslides"]},
]

POLICY_GAPS = [
    {"gap": "Local Level Adaptation Plans",     "status": "Missing",  "severity": "high",   "note": "No Palika-specific adaptation policies in database"},
    {"gap": "Provincial Climate Budgets",       "status": "Missing",  "severity": "high",   "note": "Province-level climate finance frameworks absent"},
    {"gap": "Gender-responsive Climate Policy", "status": "Partial",  "severity": "medium", "note": "References in WASH framework; no standalone policy"},
    {"gap": "Indigenous Knowledge Integration", "status": "Partial",  "severity": "medium", "note": "Mentioned in L&D Framework; not operationalized"},
    {"gap": "Biodiversity-Climate Nexus",       "status": "Gap",      "severity": "low",    "note": "No dedicated biodiversity-climate policy in database"},
    {"gap": "Urban Climate Resilience",         "status": "Missing",  "severity": "medium", "note": "Rapid urbanization not addressed in current documents"},
]

# ── Session state initialisation ───────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {
            "role": "assistant",
            "content": "नमस्ते! I am Nepal's Climate Policy Intelligence Assistant.\n\nI have knowledge of 6 climate policy documents covering Loss & Damage, WASH, Climate Change Policy 2019, Health-Climate Nexus, Environment Law, and Climate Finance.\n\nAsk me anything about:\n• Policy gaps and overlaps\n• Sector-specific provisions\n• Province-level recommendations\n• UNFCCC alignment\n• Finance mechanisms\n\nYou can ask in English or नेपाली!"
        }
    ]
if "uploaded_docs" not in st.session_state:
    st.session_state.uploaded_docs = []
if "selected_doc" not in st.session_state:
    st.session_state.selected_doc = None
if "lang" not in st.session_state:
    st.session_state.lang = "EN"

# ── Helpers ────────────────────────────────────────────────────────────────
def extract_pdf_text(file_bytes: bytes, max_chars: int = 8000) -> str:
    """Extract text from PDF bytes."""
    if not PDF_SUPPORT:
        return "[PyPDF2 not installed — text extraction unavailable]"
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
            if len(text) > max_chars:
                break
        return text[:max_chars]
    except Exception as e:
        return f"[Could not extract text: {e}]"

def badge_html(text, color_class="badge-green"):
    return f'<span class="badge {color_class}">{text}</span>'

def status_color(status):
    return {"Approved": "badge-green", "Active": "badge-blue",
            "Foundational": "badge-earth", "Missing": "badge-red",
            "Partial": "badge-warn"}.get(status, "badge-green")

def risk_color(risk):
    return {"Very High": "#c94030", "High": "#c47c40",
            "Moderate": "#2d7a4f", "Low": "#2e72b0"}.get(risk, "#8a8a84")

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 8px 0 16px;">
      <div style="font-size: 40px; margin-bottom:8px;">🏔</div>
      <div style="font-size:15px; font-weight:700; font-family:'Lora',serif;">Nepal Climate Portal</div>
      <div style="font-size:10px; opacity:0.65; margin-top:4px; letter-spacing:0.04em;">POLICY INTELLIGENCE SYSTEM</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Navigation
    page = st.radio(
        "Navigate",
        ["📋 Policy Explorer", "🤖 AI Assistant", "📊 Analytics", "🗺 Provinces", "📤 Upload Policy"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Language toggle
    lang_choice = st.radio("Language / भाषा", ["English", "नेपाली"], horizontal=True,
                           label_visibility="visible")
    st.session_state.lang = "EN" if lang_choice == "English" else "NP"

    st.markdown("---")

    # Quick stats in sidebar
    st.markdown('<div style="font-size:11px;opacity:0.7;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;">Database status</div>', unsafe_allow_html=True)
    total = len(DOCUMENTS) + len(st.session_state.uploaded_docs)
    st.markdown(f"""
    <div style="font-size:12px;line-height:2;opacity:0.85;">
      📄 {total} documents indexed<br>
      🏛 6 Federal policies<br>
      🌐 {len([d for d in DOCUMENTS if d['language']=='English'])} in English<br>
      📝 1 in नेपाली<br>
      ⏳ 100+ expected
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Risk legend
    st.markdown('<div style="font-size:11px;opacity:0.7;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;">Climate risk legend</div>', unsafe_allow_html=True)
    for risk, color in [("Very High", "#c94030"), ("High", "#c47c40"), ("Moderate", "#2d7a4f")]:
        st.markdown(f'<div style="font-size:11px;display:flex;align-items:center;gap:6px;margin-bottom:4px;opacity:0.85;"><span style="width:8px;height:8px;border-radius:50%;background:{color};display:inline-block;"></span>{risk}</div>', unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────
title_text = "Nepal Climate Policy Intelligence Portal" if st.session_state.lang == "EN" else "नेपाल जलवायु नीति बौद्धिक पोर्टल"
subtitle_text = "Centralized access to federal, provincial & local climate policies" if st.session_state.lang == "EN" else "संघीय, प्रादेशिक र स्थानीय जलवायु नीतिहरूमा केन्द्रीकृत पहुँच"

st.markdown(f"""
<div style="background: linear-gradient(135deg, #1a4a2e 0%, #2d6a45 60%, #1e4f7a 100%);
     border-radius: 14px; padding: 24px 28px; margin-bottom: 24px;
     display:flex; align-items:center; gap:20px;">
  <div style="font-size:52px;">🏔</div>
  <div>
    <h1 style="color:white; font-size:22px; margin:0; font-family:'Lora',serif; font-weight:700;">{title_text}</h1>
    <div style="color:rgba(255,255,255,0.7); font-size:13px; margin-top:4px;">{subtitle_text}</div>
    <div style="display:flex; gap:8px; margin-top:10px;">
      <span style="background:rgba(255,255,255,0.15);color:white;padding:3px 10px;border-radius:20px;font-size:10px;font-weight:600;">● LIVE</span>
      <span style="background:rgba(255,255,255,0.1);color:rgba(255,255,255,0.8);padding:3px 10px;border-radius:20px;font-size:10px;">{len(DOCUMENTS)+len(st.session_state.uploaded_docs)} documents indexed</span>
      <span style="background:rgba(255,255,255,0.1);color:rgba(255,255,255,0.8);padding:3px 10px;border-radius:20px;font-size:10px;">AI-powered search</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Stats row ──────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Documents", len(DOCUMENTS) + len(st.session_state.uploaded_docs), help="Uploaded policy documents")
with col2:
    st.metric("Sectors Covered", "8", help="Cross-cutting sectors")
with col3:
    st.metric("Federal Policies", "6", help="National-level policies")
with col4:
    st.metric("Year Span", "1993–2026", help="Temporal coverage")

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# PAGE: POLICY EXPLORER
# ═══════════════════════════════════════════════════════════════════════════
if "Policy Explorer" in page:
    all_docs = DOCUMENTS + st.session_state.uploaded_docs

    # Filter bar
    col_s, col_sec, col_lev, col_th = st.columns([3, 1.5, 1.5, 1.5])
    with col_s:
        search_q = st.text_input("", placeholder="🔍  Search policies, keywords, ministries…", label_visibility="collapsed")
    with col_sec:
        sectors = ["All"] + sorted(set(s for d in all_docs for s in d.get("sector", [])))
        filter_sector = st.selectbox("Sector", sectors, label_visibility="visible")
    with col_lev:
        filter_level = st.selectbox("Level", ["All", "Federal", "Provincial", "Local"], label_visibility="visible")
    with col_th:
        all_themes = ["All"] + sorted(set(t for d in all_docs for t in d.get("themes", [])))
        filter_theme = st.selectbox("Theme", all_themes, label_visibility="visible")

    # Apply filters
    def doc_matches(d):
        q = search_q.lower()
        if q and not any(q in str(v).lower() for v in [d["title"], d.get("summary",""), d.get("ministry",""), *d.get("keywords",[])]):
            return False
        if filter_sector != "All" and filter_sector not in d.get("sector", []):
            return False
        if filter_level != "All" and d.get("level") != filter_level:
            return False
        if filter_theme != "All" and filter_theme not in d.get("themes", []):
            return False
        return True

    filtered = [d for d in all_docs if doc_matches(d)]
    st.markdown(f'<div class="section-label">{len(filtered)} of {len(all_docs)} documents · Click to expand</div>', unsafe_allow_html=True)

    # Document list
    for doc in filtered:
        with st.expander(f"📄  {doc['short_title']}  ·  {doc['year']}  ·  {doc['level']}", expanded=False):
            col_main, col_meta = st.columns([3, 1])

            with col_main:
                st.markdown(f"**{doc['title']}**")
                st.markdown(f'<div style="background:#f5f0e8;border-left:3px solid #4a9966;padding:10px 14px;border-radius:0 8px 8px 0;font-size:13px;color:#4a4a46;line-height:1.7;margin:8px 0;">{doc["summary"]}</div>', unsafe_allow_html=True)

                # Highlights
                if doc.get("highlights"):
                    st.markdown('<div class="section-label" style="margin-top:12px;">Key highlights</div>', unsafe_allow_html=True)
                    for h in doc["highlights"]:
                        st.markdown(f"• {h}")

            with col_meta:
                st.markdown(f'<div class="section-label">Ministry</div><div style="font-size:12px;color:#1a1a18;margin-bottom:12px;">{doc["ministry"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="section-label">Status</div>', unsafe_allow_html=True)
                st.markdown(badge_html(doc["status"], status_color(doc["status"])) +
                            badge_html(doc["language"], "badge-blue") +
                            badge_html(str(doc["year"]), "badge-earth"), unsafe_allow_html=True)
                st.markdown('<br><div class="section-label">Sectors</div>', unsafe_allow_html=True)
                st.markdown(" ".join(badge_html(s, "badge-green") for s in doc.get("sector", [])), unsafe_allow_html=True)
                st.markdown('<br><div class="section-label">Themes</div>', unsafe_allow_html=True)
                st.markdown(" ".join(badge_html(t, "badge-blue") for t in doc.get("themes", [])), unsafe_allow_html=True)
                st.markdown('<br><div class="section-label">Keywords</div>', unsafe_allow_html=True)
                kw_html = " ".join(f'<span style="font-size:11px;background:#f5f0e8;color:#4a4a46;padding:2px 7px;border-radius:4px;display:inline-block;margin:2px;">{k}</span>' for k in doc.get("keywords", []))
                st.markdown(kw_html, unsafe_allow_html=True)

    if not filtered:
        st.info("No policies match your filters. Try broadening your search.")

# ═══════════════════════════════════════════════════════════════════════════
# PAGE: AI ASSISTANT
# ═══════════════════════════════════════════════════════════════════════════
elif "AI Assistant" in page:
    col_chat, col_side = st.columns([2.5, 1])

    with col_chat:
        st.markdown("### 🤖 Nepal Climate Policy AI")

        # Chat history display
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(f'<div class="user-msg">👤 {msg["content"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="bot-msg">🏔 {msg["content"]}</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Suggested questions
        if len(st.session_state.chat_history) < 3:
            st.markdown('<div class="section-label">Suggested questions:</div>', unsafe_allow_html=True)
            suggestions = [
                "What are Nepal's main climate risks and vulnerable populations?",
                "How does the L&D Framework define economic vs non-economic loss?",
                "Which policies address GLOF risks in Nepal?",
                "What climate finance mechanisms are available to Nepal?",
                "What are the key policy gaps in Nepal's climate governance?",
                "जलवायु परिवर्तनले नेपालमा कस्तो प्रभाव पारेको छ?",
            ]
            cols = st.columns(2)
            for i, q in enumerate(suggestions):
                with cols[i % 2]:
                    if st.button(q, key=f"sugg_{i}", use_container_width=True):
                        st.session_state._pending_question = q

        # Input area
        with st.form("chat_form", clear_on_submit=True):
            col_inp, col_btn = st.columns([5, 1])
            with col_inp:
                placeholder = "Ask about any climate policy, sector, or province…" if st.session_state.lang == "EN" else "जलवायु नीति, क्षेत्र वा प्रदेशको बारेमा सोध्नुहोस्…"
                user_input = st.text_input("", placeholder=placeholder, label_visibility="collapsed")
            with col_btn:
                submitted = st.form_submit_button("Send →", use_container_width=True)

        # Handle pending suggestion
        if hasattr(st.session_state, "_pending_question"):
            user_input = st.session_state._pending_question
            submitted = True
            del st.session_state._pending_question

        if submitted and user_input.strip():
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            # Build system prompt with all doc summaries
            doc_context = "\n".join([
                f"{i+1}. {d['title']} ({d['year']}): {d['summary']}"
                for i, d in enumerate(DOCUMENTS + st.session_state.uploaded_docs)
            ])
            uploaded_context = ""
            for ud in st.session_state.uploaded_docs:
                if ud.get("extracted_text"):
                    uploaded_context += f"\n\nExtracted content from {ud['title']}:\n{ud['extracted_text'][:3000]}"

            system_prompt = f"""You are Nepal Climate Policy Intelligence Assistant — an expert on Nepal's climate policies, environmental law, disaster risk reduction, and UNFCCC negotiations.

You have access to these policy documents:
{doc_context}
{uploaded_context}

Key facts about Nepal's climate context:
- Nepal is an LDC and highly climate-vulnerable
- Climate-induced disasters cause ~65% of all disaster deaths
- Average annual economic loss: ~0.08% GDP from climate disasters
- 2017 Tarai floods caused 2.08% GDP loss (worst single event)
- Nepal submitted 2nd NDC in 2020 targeting net-zero by 2050
- 7 provinces: Koshi, Madhesh, Bagmati, Gandaki, Lumbini, Karnali, Sudurpashchim
- Karnali and Sudurpashchim face Very High climate risk
- Nepal has 21 potentially dangerous glacial lakes (PDGLs)

Instructions:
- Answer concisely and accurately, citing specific policies by name
- Point out gaps, overlaps, and policy opportunities
- Support both English and Nepali queries — respond in the same language as the question
- Keep responses under 400 words
- Use bullet points for clarity where appropriate
- When discussing provinces, reference their specific hazards and vulnerabilities"""

            messages = [{"role": m["role"], "content": m["content"]}
                        for m in st.session_state.chat_history]

            with st.spinner("Analyzing policies…"):
                try:
                    api_key = (
                        st.secrets.get("ANTHROPIC_API_KEY", None)
                        or os.environ.get("ANTHROPIC_API_KEY", None)
                    )
                    if not api_key:
                        raise ValueError("ANTHROPIC_API_KEY not found.")

                    if ANTHROPIC_SDK:
                        client = anthropic.Anthropic(api_key=api_key)
                        response = client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=1000,
                            system=system_prompt,
                            messages=messages,
                        )
                        reply = response.content[0].text
                    else:
                        resp = requests.post(
                            "https://api.anthropic.com/v1/messages",
                            headers={
                                "x-api-key": api_key,
                                "anthropic-version": "2023-06-01",
                                "content-type": "application/json",
                            },
                            json={
                                "model": "claude-sonnet-4-20250514",
                                "max_tokens": 1000,
                                "system": system_prompt,
                                "messages": messages,
                            },
                            timeout=30,
                        )
                        resp.raise_for_status()
                        reply = resp.json()["content"][0]["text"]

                except ValueError as e:
                    reply = (
                        "⚠️ **API key not configured.**\n\n"
                        "On Streamlit Cloud, add your key in **App Settings → Secrets**:\n"
                        "```\nANTHROPIC_API_KEY = \"sk-ant-...\"\n```\n"
                        "Locally, run: `export ANTHROPIC_API_KEY=sk-ant-...`"
                    )
                except Exception as e:
                    reply = f"⚠️ Could not reach AI service: {e}"

            st.session_state.chat_history.append({"role": "assistant", "content": reply})
            st.rerun()

        # Clear chat
        if st.button("🗑 Clear chat", type="secondary"):
            st.session_state.chat_history = st.session_state.chat_history[:1]
            st.rerun()

    with col_side:
        st.markdown("### 📚 Knowledge base")
        for doc in DOCUMENTS:
            st.markdown(f"""
            <div style="display:flex;gap:8px;margin-bottom:10px;align-items:flex-start;">
              <div style="width:6px;height:6px;border-radius:50%;background:#2d6a45;margin-top:5px;flex-shrink:0;"></div>
              <div>
                <div style="font-size:12px;font-weight:600;color:#1a1a18;line-height:1.3;">{doc['short_title']}</div>
                <div style="font-size:10px;color:#8a8a84;">{doc['year']} · {doc['language']}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        if st.session_state.uploaded_docs:
            st.markdown("**Uploaded documents:**")
            for ud in st.session_state.uploaded_docs:
                st.markdown(f"✅ {ud['short_title']}")

        st.info("💡 Upload more documents in the 'Upload Policy' tab to expand the AI's knowledge base.")

        st.markdown("### 🌐 Bilingual support")
        st.markdown("Ask in **English** or **नेपाली**. The assistant responds in the same language.")

# ═══════════════════════════════════════════════════════════════════════════
# PAGE: ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════
elif "Analytics" in page:
    st.markdown("### 📊 Policy Analytics Dashboard")

    all_docs = DOCUMENTS + st.session_state.uploaded_docs
    col1, col2 = st.columns(2)

    with col1:
        # Theme distribution
        theme_counts = {}
        for d in all_docs:
            for t in d.get("themes", []):
                theme_counts[t] = theme_counts.get(t, 0) + 1
        df_themes = pd.DataFrame(list(theme_counts.items()), columns=["Theme", "Count"]).sort_values("Count", ascending=True)
        fig = go.Figure(go.Bar(
            x=df_themes["Count"], y=df_themes["Theme"], orientation="h",
            marker_color=["#2d6a45", "#2e72b0", "#7a4a1e", "#c47c40", "#8a5aa0"][:len(df_themes)],
            text=df_themes["Count"], textposition="outside",
        ))
        fig.update_layout(
            title="Policy themes distribution", title_font_size=13,
            paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(l=0, r=30, t=40, b=0), height=280,
            xaxis=dict(showgrid=False, zeroline=False, visible=False),
            yaxis=dict(tickfont=dict(size=11)),
            font=dict(family="Inter, sans-serif"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Sector coverage
        sector_counts = {}
        for d in all_docs:
            for s in d.get("sector", []):
                sector_counts[s] = sector_counts.get(s, 0) + 1
        df_sec = pd.DataFrame(list(sector_counts.items()), columns=["Sector", "Count"]).sort_values("Count", ascending=False)
        colors = px.colors.qualitative.Set2
        fig2 = px.pie(df_sec, values="Count", names="Sector",
                      title="Sector coverage",
                      color_discrete_sequence=colors)
        fig2.update_traces(textposition="inside", textinfo="percent+label", textfont_size=11)
        fig2.update_layout(
            paper_bgcolor="white", height=280, margin=dict(l=0, r=0, t=40, b=0),
            font=dict(family="Inter, sans-serif", size=11),
            showlegend=False, title_font_size=13,
        )
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        # Timeline
        st.markdown('<div class="section-label">Policy timeline (1993–2026)</div>', unsafe_allow_html=True)
        sorted_docs = sorted(all_docs, key=lambda d: d["year"])
        df_time = pd.DataFrame([{"Year": d["year"], "Policy": d["short_title"], "Level": d["level"], "Status": d["status"]} for d in sorted_docs])

        fig3 = px.scatter(df_time, x="Year", y=[0]*len(df_time), text="Policy",
                          size=[15]*len(df_time), color="Status",
                          color_discrete_map={"Approved": "#2d6a45", "Active": "#2e72b0",
                                              "Foundational": "#7a4a1e"},
                          title="Policy chronology")
        fig3.update_traces(textposition="top center", textfont_size=9, mode="markers+text")
        fig3.update_layout(
            paper_bgcolor="white", plot_bgcolor="white", height=240,
            margin=dict(l=0, r=0, t=40, b=0), showlegend=True,
            yaxis=dict(visible=False), xaxis=dict(tickfont=dict(size=10)),
            font=dict(family="Inter, sans-serif"), title_font_size=13,
            legend=dict(font=dict(size=10), orientation="h", y=-0.1),
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        # Language distribution
        lang_counts = {}
        for d in all_docs:
            l = d.get("language", "Unknown")
            lang_counts[l] = lang_counts.get(l, 0) + 1
        df_lang = pd.DataFrame(list(lang_counts.items()), columns=["Language", "Count"])
        fig4 = px.bar(df_lang, x="Language", y="Count",
                      color="Language",
                      color_discrete_map={"English": "#2e72b0", "Nepali": "#c47c40", "English/Nepali": "#2d6a45"},
                      title="Language distribution", text="Count")
        fig4.update_traces(textposition="outside")
        fig4.update_layout(
            paper_bgcolor="white", plot_bgcolor="white", height=240,
            margin=dict(l=0, r=0, t=40, b=30), showlegend=False,
            yaxis=dict(showgrid=False, visible=False),
            xaxis=dict(tickfont=dict(size=11)),
            font=dict(family="Inter, sans-serif"), title_font_size=13,
        )
        st.plotly_chart(fig4, use_container_width=True)

    # Province risk map
    st.markdown("### Province climate risk profile")
    df_prov = pd.DataFrame(PROVINCES)
    df_prov["risk_color"] = df_prov["risk"].map(
        {"Very High": "#c94030", "High": "#c47c40", "Moderate": "#2d7a4f"})

    fig5 = go.Figure()
    for _, row in df_prov.iterrows():
        fig5.add_trace(go.Bar(
            name=row["name"], x=[row["name"]], y=[row["risk_score"]],
            marker_color=row["risk_color"], text=row["risk"],
            textposition="outside", width=0.5,
        ))
    fig5.update_layout(
        title="Provincial climate risk levels", barmode="group",
        paper_bgcolor="white", plot_bgcolor="white", height=280,
        margin=dict(l=0, r=0, t=40, b=0), showlegend=False,
        yaxis=dict(visible=False, range=[0, 7]),
        xaxis=dict(tickfont=dict(size=11)),
        font=dict(family="Inter, sans-serif"), title_font_size=13,
    )
    st.plotly_chart(fig5, use_container_width=True)

    # Policy gaps table
    st.markdown("### 🔍 Policy gap analysis")
    for g in POLICY_GAPS:
        sev_color = {"high": "#c94030", "medium": "#c47c40", "low": "#8a8a84"}[g["severity"]]
        st.markdown(f"""
        <div style="background:white;border:0.5px solid rgba(26,26,24,0.1);border-left:3px solid {sev_color};
             border-radius:8px;padding:12px 16px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;">
          <div>
            <div style="font-size:13px;font-weight:600;color:#1a1a18;">{g['gap']}</div>
            <div style="font-size:11px;color:#4a4a46;margin-top:3px;">{g['note']}</div>
          </div>
          <span class="badge {status_color(g['status'])}">{g['status']}</span>
        </div>
        """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# PAGE: PROVINCES
# ═══════════════════════════════════════════════════════════════════════════
elif "Provinces" in page:
    st.markdown("### 🗺 Provincial Climate Policy Coverage")

    col_map, col_detail = st.columns([1.5, 2])

    with col_map:
        st.markdown('<div class="section-label">Select a province</div>', unsafe_allow_html=True)
        selected_prov = None
        for p in PROVINCES:
            rc = risk_color(p["risk"])
            if st.button(
                f"{'⬡'} Province {p['id']} — {p['name']}",
                key=f"prov_{p['id']}",
                use_container_width=True,
                help=f"Risk: {p['risk']} · {p['docs']} documents"
            ):
                selected_prov = p
                st.session_state.selected_province = p

        st.markdown("""
        <div style="margin-top:16px;padding:12px 14px;background:#1a4a2e0a;border-radius:8px;font-size:11px;color:#4a4a46;line-height:1.7;border:0.5px solid #2d6a4530;">
        📌 <strong>Note:</strong> Province data is indicative. As 100+ documents are uploaded, this view will populate with province-specific adaptation plans, DRR strategies, and local climate budgets.
        </div>
        """, unsafe_allow_html=True)

    with col_detail:
        prov = st.session_state.get("selected_province", PROVINCES[0])
        rc = risk_color(prov["risk"])
        st.markdown(f"""
        <div style="background:white;border-radius:12px;border:0.5px solid rgba(26,26,24,0.12);padding:20px 22px;margin-bottom:14px;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div>
              <h3 style="font-size:20px;font-weight:700;color:#1a1a18;margin:0;font-family:'Lora',serif;">{prov['name']} Province</h3>
              <div style="font-size:12px;color:#4a4a46;margin-top:4px;">Province {prov['id']} · Federal Republic of Nepal</div>
            </div>
            <span class="badge" style="background:{rc}18;color:{rc};border:0.5px solid {rc}40;font-size:12px;padding:4px 12px;">{prov['risk']} Risk</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Metrics
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Policy Documents", prov["docs"], help="In current database")
        with m2:
            st.metric("Climate Risk", prov["risk"])
        with m3:
            st.metric("Pending Upload", "100+")

        # Hazards
        st.markdown('<div class="section-label" style="margin-top:16px;">Key climate hazards</div>', unsafe_allow_html=True)
        for h in prov["hazards"]:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:8px;padding:6px 10px;background:#faf7f2;border-radius:6px;margin-bottom:6px;">
              <div style="width:6px;height:6px;border-radius:50%;background:{rc};flex-shrink:0;"></div>
              <span style="font-size:12px;color:#1a1a18;">{h}</span>
            </div>
            """, unsafe_allow_html=True)

        # Province-specific policy recommendations
        prov_recs = {
            "Koshi":          ["Strengthen GLOF early warning systems", "Trans-boundary water treaty with China", "Agricultural insurance for hill farmers"],
            "Madhesh":        ["Flood embankment maintenance policy", "Heat action plan for urban areas", "Drought-resistant crop promotion"],
            "Bagmati":        ["Urban stormwater management policy", "Kathmandu Valley air quality plan", "Green building codes"],
            "Gandaki":        ["Glacial lake monitoring programme", "Tourism climate resilience plan", "Landslide risk mapping"],
            "Lumbini":        ["Flood early warning for Rapti basin", "Irrigation efficiency programme", "Wetland conservation policy"],
            "Karnali":        ["Food security emergency protocol", "Spring revival programme", "Nomadic herder adaptation support"],
            "Sudurpashchim":  ["Drought monitoring and response plan", "Forest fire management policy", "Drinking water resilience programme"],
        }
        st.markdown('<div class="section-label" style="margin-top:16px;">Recommended policy priorities</div>', unsafe_allow_html=True)
        for r in prov_recs.get(prov["name"], []):
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:8px;padding:6px 10px;background:white;border:0.5px solid rgba(26,26,24,0.1);border-radius:6px;margin-bottom:6px;">
              <span style="color:#2d6a45;font-size:12px;">→</span>
              <span style="font-size:12px;color:#1a1a18;">{r}</span>
            </div>
            """, unsafe_allow_html=True)

    # Province risk bar chart
    st.markdown("<br>", unsafe_allow_html=True)
    df_p = pd.DataFrame(PROVINCES)
    fig = px.bar(
        df_p, x="name", y="docs",
        color="risk",
        color_discrete_map={"Very High": "#c94030", "High": "#c47c40", "Moderate": "#2d7a4f"},
        title="Policy document coverage by province",
        labels={"name": "Province", "docs": "Documents", "risk": "Risk Level"},
        text="docs",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        paper_bgcolor="white", plot_bgcolor="white", height=300,
        margin=dict(l=0, r=0, t=40, b=0),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
        font=dict(family="Inter, sans-serif"), title_font_size=13,
        legend=dict(font=dict(size=10), orientation="h", y=-0.15),
    )
    st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════
# PAGE: UPLOAD POLICY
# ═══════════════════════════════════════════════════════════════════════════
elif "Upload Policy" in page:
    st.markdown("### 📤 Upload Policy Document")
    st.markdown("Add new policy documents to expand the database and AI knowledge base. Supports PDF, Word, and text files.")

    col_form, col_info = st.columns([2, 1])

    with col_form:
        with st.form("upload_form"):
            st.markdown("**Document details**")
            doc_title = st.text_input("Full title *", placeholder="e.g. Karnali Province Climate Change Adaptation Plan 2023")
            col_y, col_l, col_s = st.columns(3)
            with col_y:
                doc_year = st.number_input("Year *", min_value=1990, max_value=2030, value=2023)
            with col_l:
                doc_level = st.selectbox("Level *", ["Federal", "Provincial", "Local"])
            with col_s:
                doc_status = st.selectbox("Status", ["Active", "Approved", "Draft", "Foundational"])

            doc_ministry = st.text_input("Ministry / Author", placeholder="e.g. Ministry of Forests and Environment")
            doc_sectors = st.multiselect("Sectors", ["Climate Change", "Water", "Agriculture", "Energy", "Disaster Risk", "Health", "Environment", "Finance", "Forests", "Urban"])
            doc_themes = st.multiselect("Themes", ["Adaptation", "Mitigation", "Governance", "Finance", "Gender & Inclusion", "Biodiversity"])
            doc_language = st.selectbox("Language", ["English", "Nepali", "English/Nepali"])
            doc_summary = st.text_area("Summary", placeholder="Brief description of the policy document…", height=100)
            doc_keywords = st.text_input("Keywords (comma-separated)", placeholder="e.g. GLOF, adaptation, water, floods")
            uploaded_file = st.file_uploader("Upload document (PDF / TXT)", type=["pdf", "txt"])

            submitted = st.form_submit_button("➕ Add to database", type="primary", use_container_width=True)

        if submitted:
            if not doc_title or not doc_sectors:
                st.error("Please fill in at least the title and sectors.")
            else:
                extracted = ""
                if uploaded_file:
                    file_bytes = uploaded_file.read()
                    if uploaded_file.type == "application/pdf":
                        extracted = extract_pdf_text(file_bytes)
                    else:
                        extracted = file_bytes.decode("utf-8", errors="replace")[:8000]

                new_doc = {
                    "id": f"user-{len(st.session_state.uploaded_docs)+1}",
                    "title": doc_title,
                    "short_title": doc_title[:50] + ("…" if len(doc_title) > 50 else ""),
                    "year": int(doc_year),
                    "level": doc_level,
                    "sector": doc_sectors,
                    "ministry": doc_ministry or "Not specified",
                    "language": doc_language,
                    "keywords": [k.strip() for k in doc_keywords.split(",") if k.strip()],
                    "filename": uploaded_file.name if uploaded_file else "manual entry",
                    "summary": doc_summary or "No summary provided.",
                    "themes": doc_themes,
                    "status": doc_status,
                    "highlights": [],
                    "extracted_text": extracted,
                }
                st.session_state.uploaded_docs.append(new_doc)
                st.success(f"✅ '{doc_title}' added successfully! The AI Assistant now has access to this document.")
                st.balloons()

    with col_info:
        st.markdown("#### Current database")
        st.metric("Pre-loaded documents", len(DOCUMENTS))
        st.metric("User-uploaded documents", len(st.session_state.uploaded_docs))
        st.metric("Total", len(DOCUMENTS) + len(st.session_state.uploaded_docs))

        st.markdown("""
        <div style="background:#1a4a2e0a;border-radius:10px;border:0.5px solid #2d6a4530;padding:14px 16px;margin-top:12px;">
          <div style="font-size:12px;font-weight:600;color:#1a4a2e;margin-bottom:8px;">📌 Upload guidelines</div>
          <div style="font-size:11px;color:#4a4a46;line-height:1.8;">
            ✓ PDF or plain text files<br>
            ✓ Any language (EN/NP supported)<br>
            ✓ Federal, Provincial or Local level<br>
            ✓ Text extracted automatically from PDF<br>
            ✓ AI assistant updated immediately<br>
            ✓ Appears in Explorer & Analytics
          </div>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.uploaded_docs:
            st.markdown("#### Uploaded documents")
            for ud in st.session_state.uploaded_docs:
                st.markdown(f"""
                <div style="display:flex;gap:8px;margin-bottom:8px;align-items:flex-start;">
                  <span style="color:#2d6a45;">✓</span>
                  <div>
                    <div style="font-size:12px;font-weight:500;color:#1a1a18;">{ud['short_title']}</div>
                    <div style="font-size:10px;color:#8a8a84;">{ud['year']} · {ud['level']} · {ud['language']}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

# ── Footer ─────────────────────────────────────────────────────────────────
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style="border-top:0.5px solid rgba(26,26,24,0.12);padding:16px 0;display:flex;justify-content:space-between;align-items:center;">
  <div style="font-size:11px;color:#8a8a84;">
    🏔 Nepal Climate Policy Intelligence Portal · Government of Nepal · Built with Streamlit + Claude AI
  </div>
  <div style="font-size:11px;color:#8a8a84;">
    Data: Ministry of Forests and Environment · NDRRMA · NPC
  </div>
</div>
""", unsafe_allow_html=True)
