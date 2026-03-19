"""
Nepal Climate Policy Intelligence Portal
Requires: pip install streamlit anthropic PyPDF2 plotly pandas
"""

import streamlit as st
import os
import io
import json
import re
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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

st.set_page_config(
    page_title="Nepal Climate Policy Intelligence Portal",
    page_icon="🏔",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@400;500;600&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  h1, h2, h3 { font-family: 'Lora', serif !important; }
  .main { background: #faf7f2; }
  .block-container { padding: 1rem 2rem 2rem; max-width: 1400px; }

  /* Hide sidebar entirely */
  section[data-testid="stSidebar"] { display: none !important; }
  [data-testid="collapsedControl"]  { display: none !important; }

  /* Metric cards */
  [data-testid="metric-container"] {
    background: #ffffff;
    border: 0.5px solid rgba(26,26,24,0.12);
    border-radius: 10px;
    padding: 1rem;
    border-left: 3px solid #2d6a45;
  }

  /* Tabs — grey pill strip, forest green active */
  .stTabs [data-baseweb="tab-list"] {
    gap: 2px;
    background: #e8e6e0;
    border-radius: 12px;
    padding: 5px;
    margin-bottom: 24px;
  }
  .stTabs [data-baseweb="tab"] {
    border-radius: 9px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 500;
    color: #5a5a56;
    background: transparent;
    border: none;
    transition: background 0.15s, color 0.15s;
  }
  .stTabs [data-baseweb="tab"]:hover {
    background: rgba(255,255,255,0.6);
    color: #1a1a18;
  }
  .stTabs [aria-selected="true"] {
    background: white !important;
    color: #1a4a2e !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.10);
  }
  .stTabs [data-baseweb="tab-highlight"] { display: none; }
  .stTabs [data-baseweb="tab-border"]    { display: none; }

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

  .badge {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 11px; font-weight: 500; margin: 2px;
  }
  .badge-green  { background: #2d6a4518; color: #2d6a45; border: 0.5px solid #2d6a4540; }
  .badge-blue   { background: #2e72b018; color: #1e4f7a; border: 0.5px solid #2e72b040; }
  .badge-earth  { background: #c47c4018; color: #7a4a1e; border: 0.5px solid #c47c4040; }
  .badge-red    { background: #c9403018; color: #c94030; border: 0.5px solid #c9403040; }
  .badge-warn   { background: #c47c4018; color: #c47c40; border: 0.5px solid #c47c4040; }

  .section-label {
    font-size: 11px; color: #8a8a84; text-transform: uppercase;
    letter-spacing: 0.07em; margin-bottom: 8px; font-weight: 500;
  }

  #MainMenu { visibility: hidden; }
  footer    { visibility: hidden; }
  header    { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Document catalogue ─────────────────────────────────────────────────────
DOCUMENTS = [
    {"id":"ld-framework-2021","title":"National Framework on Climate Change Induced Loss and Damage","short_title":"L&D Framework 2021","year":2021,"level":"Federal","sector":["Disaster Risk","Climate Change"],"ministry":"Ministry of Forests and Environment","language":"English","keywords":["loss and damage","GLOF","floods","landslides","displacement","insurance","adaptation"],"filename":"Loss_and_Damage_Framework_Nepal_2021_1__1_.pdf","summary":"Defines Nepal's national framework for assessing and responding to climate-induced loss and damage, covering economic and non-economic losses, assessment methodology, and recommendations for institutionalizing L&D processes.","themes":["Adaptation","Finance","Governance"],"status":"Approved","highlights":["Climate-induced disasters cause ~65% of all disaster deaths in Nepal","Average annual economic loss: ~0.08% of GDP","2017 Tarai floods alone caused 2.08% GDP loss (NPR 60,716.6M)","Nepal has experienced at least 24 GLOF events historically","Proposes 10-step L&D assessment methodology"]},
    {"id":"wash-policy-2026","title":"Climate Resilient WASH in Nepal: Policy Alignment, Local Practices and Service Provider Readiness","short_title":"Climate-Resilient WASH 2026","year":2026,"level":"Federal","sector":["Water","Health","Climate Change"],"ministry":"Multiple Ministries","language":"English","keywords":["WASH","water sanitation hygiene","climate resilience","service providers","local government"],"filename":"GSAC_2026_P1_40_ClimateResilient_WASH_in_Nepal.pdf","summary":"Examines policy alignment and local preparedness for climate-resilient water, sanitation and hygiene systems across Nepal's federal structure.","themes":["Adaptation","Governance","Gender & Inclusion"],"status":"Active","highlights":["Covers all 3 tiers of Nepal's federal structure","Assesses service provider readiness for climate impacts","Reviews alignment between WASH and climate policies"]},
    {"id":"climate-policy-2019","title":"National Climate Change Policy 2019 (2076 BS)","short_title":"Climate Change Policy 2019","year":2019,"level":"Federal","sector":["Climate Change","Energy","Agriculture","Water"],"ministry":"Ministry of Forests and Environment","language":"Nepali","keywords":["mitigation","adaptation","carbon neutrality","renewable energy","NDC"],"filename":"Approved_climate_change_policy_2076.pdf","summary":"Nepal's overarching climate change policy establishing targets for mitigation and adaptation across all sectors, forming the basis for subsequent NDC and NAP formulation.","themes":["Mitigation","Adaptation","Governance","Finance"],"status":"Approved","highlights":["Sets Nepal's net-zero target by 2050","Basis for Nepal's 2nd NDC (2020-2030)","Covers 8 major sectors including energy, forests, agriculture","Calls for dedicated climate finance mechanisms"]},
    {"id":"health-wash-climate","title":"Nepal Climate Change, Health and WASH Nexus","short_title":"Climate-Health-WASH Nexus","year":2022,"level":"Federal","sector":["Health","Water","Climate Change"],"ministry":"Ministry of Health and Population","language":"English","keywords":["health impacts","water-borne diseases","climate vulnerability","WASH","epidemics"],"filename":"nepalclimatechangehealthwash_1.pdf","summary":"Analyzes the intersection of climate change with public health and WASH outcomes in Nepal, providing evidence for integrated policy responses.","themes":["Adaptation","Gender & Inclusion"],"status":"Active","highlights":["Epidemics cause 52.8% of climate-induced deaths","Links between extreme rainfall and disease outbreaks","Evidence base for integrated health-WASH-climate policy"]},
    {"id":"nep-env-1993","title":"Environment Protection Act / Nepal Environment Policy","short_title":"Environment Policy (Foundational)","year":1993,"level":"Federal","sector":["Environment","Agriculture","Water"],"ministry":"Ministry of Forests and Environment","language":"English/Nepali","keywords":["environment protection","biodiversity","land use","conservation"],"filename":"nep199367.pdf","summary":"Foundational environmental legislation establishing Nepal's regulatory framework for environmental protection, conservation and sustainable use of natural resources.","themes":["Governance","Mitigation"],"status":"Foundational","highlights":["Foundational legal framework for all environmental law","Establishes environmental impact assessment requirements","Conservation of biodiversity and forest resources"]},
    {"id":"climate-finance-2024","title":"Climate Finance and Loss & Damage: Global and Nepal Perspectives","short_title":"Climate Finance L&D 2024","year":2024,"level":"Federal","sector":["Finance","Climate Change","Disaster Risk"],"ministry":"National Planning Commission","language":"English","keywords":["climate finance","loss and damage fund","COP28","adaptation finance","LDC"],"filename":"wp2024040.pdf","summary":"Reviews global climate finance architecture with focus on the newly established Loss and Damage Fund and implications for Nepal's access to climate resources.","themes":["Finance","Governance","Adaptation"],"status":"Active","highlights":["Analysis of COP28 Loss & Damage Fund outcomes","Nepal's eligibility and access pathways","Identifies gaps between climate needs and finance flows"]},
]

PROVINCES = [
    {"id":1,"name":"Koshi","risk":"High","risk_score":4,"docs":8,"hazards":["GLOF","Landslides","Floods"]},
    {"id":2,"name":"Madhesh","risk":"High","risk_score":4,"docs":5,"hazards":["Floods","Heat waves","Drought"]},
    {"id":3,"name":"Bagmati","risk":"Moderate","risk_score":3,"docs":12,"hazards":["Urban flooding","Landslides","Water stress"]},
    {"id":4,"name":"Gandaki","risk":"High","risk_score":4,"docs":7,"hazards":["GLOF","Landslides","Drought"]},
    {"id":5,"name":"Lumbini","risk":"Moderate","risk_score":3,"docs":6,"hazards":["Flooding","Drought","Heatwaves"]},
    {"id":6,"name":"Karnali","risk":"Very High","risk_score":5,"docs":4,"hazards":["Drought","Food insecurity","Cold waves"]},
    {"id":7,"name":"Sudurpashchim","risk":"Very High","risk_score":5,"docs":5,"hazards":["Drought","Floods","Landslides"]},
]

POLICY_GAPS = [
    {"gap":"Local Level Adaptation Plans","status":"Missing","severity":"high","note":"No Palika-specific adaptation policies in database"},
    {"gap":"Provincial Climate Budgets","status":"Missing","severity":"high","note":"Province-level climate finance frameworks absent"},
    {"gap":"Gender-responsive Climate Policy","status":"Partial","severity":"medium","note":"References in WASH framework; no standalone policy"},
    {"gap":"Indigenous Knowledge Integration","status":"Partial","severity":"medium","note":"Mentioned in L&D Framework; not operationalized"},
    {"gap":"Biodiversity-Climate Nexus","status":"Gap","severity":"low","note":"No dedicated biodiversity-climate policy in database"},
    {"gap":"Urban Climate Resilience","status":"Missing","severity":"medium","note":"Rapid urbanization not addressed in current documents"},
]

# ── Persistent document store ──────────────────────────────────────────────
# Uses st.cache_resource so the store survives reruns & code-only redeploys.
# JSON is also written to /tmp/nepal_docs.json as a secondary persistence layer.
PERSIST_FILE = "/tmp/nepal_policy_docs.json"

@st.cache_resource
def _get_doc_store():
    """In-memory store shared across all reruns in the same server process.
    Initialised from the JSON file if it exists (survives code-only redeploys)."""
    if os.path.exists(PERSIST_FILE):
        try:
            with open(PERSIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_doc_store(docs):
    """Write the current doc list to the JSON file for persistence."""
    try:
        with open(PERSIST_FILE, "w", encoding="utf-8") as f:
            json.dump(docs, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # /tmp write failure is non-fatal

# ── Session state ──────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role":"assistant","content":"नमस्ते! I am Nepal's Climate Policy Intelligence Assistant.\n\nI have knowledge of 6 climate policy documents covering Loss & Damage, WASH, Climate Change Policy 2019, Health-Climate Nexus, Environment Law, and Climate Finance.\n\nAsk me anything about:\n• Policy gaps and overlaps\n• Sector-specific provisions\n• Province-level recommendations\n• UNFCCC alignment\n• Finance mechanisms\n\nYou can ask in English or नेपाली!"}]
if "uploaded_docs" not in st.session_state:
    # Load from the persistent cache resource on first run
    st.session_state.uploaded_docs = list(_get_doc_store())
if "selected_doc"      not in st.session_state: st.session_state.selected_doc      = None
if "lang"              not in st.session_state: st.session_state.lang              = "EN"
if "upload_form_key"   not in st.session_state: st.session_state.upload_form_key   = 0
if "last_upload_title" not in st.session_state: st.session_state.last_upload_title = ""

# ── Count helpers — computed ONCE at top, before sidebar/header ────────────
_n_uploaded = len(st.session_state.uploaded_docs)
_n_total    = len(DOCUMENTS) + _n_uploaded

# ── Utility functions ──────────────────────────────────────────────────────
def extract_pdf_text(file_bytes, max_chars=8000):
    if not PDF_SUPPORT:
        return "[PyPDF2 not installed]"
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
            if len(text) > max_chars: break
        return text[:max_chars]
    except Exception as e:
        return f"[Could not extract: {e}]"

def extract_url_text(url: str, max_chars: int = 8000) -> tuple[str, str]:
    """Fetch a URL and extract readable text. Returns (text, error_msg)."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        }
        resp = requests.get(url.strip(), headers=headers, timeout=15)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")

        # PDF served via URL
        if "pdf" in content_type or url.lower().endswith(".pdf"):
            return extract_pdf_text(resp.content, max_chars), ""

        # HTML — strip tags for plain text
        html = resp.text
        # Remove script/style blocks
        html = re.sub(r"<(script|style)[^>]*>.*?</(script|style)>", " ", html, flags=re.S|re.I)
        # Remove all tags
        text = re.sub(r"<[^>]+>", " ", html)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars], ""
    except requests.exceptions.Timeout:
        return "", "Request timed out. The URL may be slow or unavailable."
    except requests.exceptions.ConnectionError:
        return "", "Could not connect to the URL. Check that it is publicly accessible."
    except requests.exceptions.HTTPError as e:
        return "", f"HTTP error {e.response.status_code}: The page returned an error."
    except Exception as e:
        return "", f"Could not fetch URL: {e}"

def badge_html(text, cls="badge-green"):
    return f'<span class="badge {cls}">{text}</span>'

def status_color(s):
    return {"Approved":"badge-green","Active":"badge-blue","Foundational":"badge-earth","Missing":"badge-red","Partial":"badge-warn"}.get(s,"badge-green")

def risk_color(r):
    return {"Very High":"#c94030","High":"#c47c40","Moderate":"#2d7a4f","Low":"#2e72b0"}.get(r,"#8a8a84")

# ── Language toggle (no sidebar — use session state directly) ──────────────
if "lang" not in st.session_state:
    st.session_state.lang = "EN"

# ── Header banner ──────────────────────────────────────────────────────────
title_text    = "Nepal Climate Policy Intelligence Portal" if st.session_state.lang=="EN" else "नेपाल जलवायु नीति बौद्धिक पोर्टल"
subtitle_text = "Centralized access to federal, provincial & local climate policies" if st.session_state.lang=="EN" else "संघीय, प्रादेशिक र स्थानीय जलवायु नीतिहरूमा केन्द्रीकृत पहुँच"

# Plain string concatenation — avoids f-string vs CSS rgba() brace conflict
st.markdown(
    '<div style="background:linear-gradient(135deg,#1a4a2e 0%,#2d6a45 60%,#1e4f7a 100%);'
    'border-radius:14px;padding:24px 28px;margin-bottom:24px;display:flex;align-items:center;gap:20px;">'
    '<div style="font-size:52px;">🏔</div>'
    '<div>'
    '<h1 style="color:white;font-size:22px;margin:0;font-family:Lora,serif;font-weight:700;">' + title_text + '</h1>'
    '<div style="color:rgba(255,255,255,0.7);font-size:13px;margin-top:4px;">' + subtitle_text + '</div>'
    '<div style="display:flex;gap:8px;margin-top:10px;">'
    # '<span style="background:rgba(255,255,255,0.15);color:white;padding:3px 10px;border-radius:20px;font-size:10px;font-weight:600;">&#9679; LIVE</span>'
    '<span style="background:rgba(255,255,255,0.1);color:rgba(255,255,255,0.8);padding:3px 10px;border-radius:20px;font-size:10px;">' + str(_n_total) + ' documents indexed</span>'
    '<span style="background:rgba(255,255,255,0.1);color:rgba(255,255,255,0.8);padding:3px 10px;border-radius:20px;font-size:10px;">AI-powered search</span>'
    '</div></div></div>',
    unsafe_allow_html=True,
)

# ── Stats row ──────────────────────────────────────────────────────────────
_all_sectors = set(s for d in DOCUMENTS + [d for d in st.session_state.uploaded_docs if d.get("approved", True)] for s in d.get("sector",[]))

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Documents", _n_total,
              delta=f"+{_n_uploaded} uploaded" if _n_uploaded > 0 else None,
              help="Pre-loaded + user-uploaded documents")
with col2:
    st.metric("Sectors Covered", len(_all_sectors), help="Unique sectors across all documents")
with col3:
    st.metric("Federal Policies", "6", help="National-level policies")
with col4:
    st.metric("Year Span", "1993-2026", help="Temporal coverage")

st.markdown("<br>", unsafe_allow_html=True)

# ── Horizontal navigation tabs ─────────────────────────────────────────────
tab_explorer, tab_analytics, tab_provinces, tab_resources, tab_upload, tab_ai = st.tabs([
    "📋 Policy Explorer",
    "📊 Analytics",
    "🗺 Provinces",
    "📚 Resources",
    "📤 Upload Policy",
    "🤖 AI Assistant",
])

# ── Resources catalogue ────────────────────────────────────────────────────
RESOURCES = [
    {"category":"Uploaded & Indexed","id":"r01","title":"National Framework on Climate Change Induced Loss and Damage","year":2021,"type":"Policy Framework","author":"Ministry of Forests and Environment (MoFE)","language":"English","url":"https://mofe.gov.np","description":"Defines Nepal's L&D assessment methodology covering economic and non-economic losses, GLOF risks, insurance mechanisms, and displacement. 10-step assessment methodology proposed.","tags":["L&D","GLOF","Adaptation","Floods"],"source":"uploaded"},
    {"category":"Uploaded & Indexed","id":"r02","title":"Climate Resilient WASH in Nepal","year":2026,"type":"Research Report","author":"GSAC / Multiple Ministries","language":"English","url":"https://mofe.gov.np","description":"Examines policy alignment and local preparedness for climate-resilient WASH across Nepal's federal structure.","tags":["WASH","Water","Local Government","Resilience"],"source":"uploaded"},
    {"category":"Uploaded & Indexed","id":"r03","title":"National Climate Change Policy 2019 (2076 BS)","year":2019,"type":"National Policy","author":"Ministry of Forests and Environment (MoFE)","language":"Nepali","url":"https://mofe.gov.np","description":"Nepal's overarching climate change policy forming the basis for Nepal's NDC and NAP.","tags":["Mitigation","Adaptation","NDC","Governance"],"source":"uploaded"},
    {"category":"Uploaded & Indexed","id":"r04","title":"Nepal Climate Change, Health and WASH Nexus","year":2022,"type":"Research Report","author":"Ministry of Health and Population","language":"English","url":"https://climate.mohp.gov.np","description":"Analyzes the intersection of climate change with public health and WASH outcomes.","tags":["Health","WASH","Epidemics","Vulnerability"],"source":"uploaded"},
    {"category":"Uploaded & Indexed","id":"r05","title":"Environment Protection Act / Nepal Environment Policy","year":1993,"type":"Legislation","author":"Government of Nepal","language":"English/Nepali","url":"https://mofe.gov.np","description":"Foundational environmental legislation establishing Nepal's regulatory framework.","tags":["Environment","Biodiversity","Conservation","Law"],"source":"uploaded"},
    {"category":"Uploaded & Indexed","id":"r06","title":"Climate Finance and Loss & Damage: Global and Nepal Perspectives","year":2024,"type":"Working Paper","author":"National Planning Commission","language":"English","url":"https://npc.gov.np","description":"Reviews global climate finance architecture focusing on the COP28 Loss and Damage Fund.","tags":["Climate Finance","L&D Fund","COP28","LDC"],"source":"uploaded"},
    {"category":"National Policies & Strategies","id":"r07","title":"Nepal's Third Nationally Determined Contribution (NDC 3.0)","year":2025,"type":"UNFCCC Submission","author":"Ministry of Forests and Environment (MoFE)","language":"English","url":"https://unfccc.int/sites/default/files/2025-05/Nepal%20NDC3.pdf","description":"Nepal's NDC submitted May 2025. Targets 17.12% GHG reduction by 2030; total cost USD 73.74 billion.","tags":["NDC","Mitigation","Net-zero 2045","UNFCCC"],"source":"internet"},
    {"category":"National Policies & Strategies","id":"r08","title":"National Adaptation Plan (NAP) 2021-2050","year":2021,"type":"National Plan","author":"Ministry of Forests and Environment (MoFE)","language":"English","url":"https://unfccc.int/sites/default/files/resource/NAP_Nepal_2021.pdf","description":"30-year adaptation roadmap covering 9 sectors with total cost USD 47.4 billion.","tags":["Adaptation","NAP","GCF","Long-term"],"source":"internet"},
    {"category":"National Policies & Strategies","id":"r09","title":"Long-term Strategy for Net-Zero Emissions (LTS) 2021","year":2021,"type":"Long-term Strategy","author":"Government of Nepal","language":"English","url":"https://unfccc.int/sites/default/files/resource/NepalLTLEDS.pdf","description":"Nepal's pathway to carbon neutrality by 2045 including hydropower export scenarios.","tags":["Net-zero","Mitigation","Energy","Long-term"],"source":"internet"},
    {"category":"National Policies & Strategies","id":"r10","title":"Disaster Risk Reduction National Strategic Plan 2018-2030","year":2018,"type":"Strategic Plan","author":"Ministry of Home Affairs (MoHA)","language":"English","url":"https://ndrrma.gov.np","description":"Sendai-aligned DRR strategy including lowering 7 glacial lakes and multi-hazard EWS by 2030.","tags":["DRR","Sendai Framework","Hazards","EWS"],"source":"internet"},
    {"category":"National Policies & Strategies","id":"r11","title":"16th National Periodic Plan 2024/25-2028/29","year":2024,"type":"Development Plan","author":"National Planning Commission (NPC)","language":"English/Nepali","url":"https://npc.gov.np","description":"Nepal's Five-Year Plan emphasizing climate-development interlinkage and DRR integration.","tags":["Development","Planning","Gender","DRR"],"source":"internet"},
    {"category":"National Policies & Strategies","id":"r12","title":"National Climate Change Health Adaptation Plan (HNAP) 2023-2030","year":2023,"type":"Sectoral Plan","author":"Ministry of Health and Population","language":"English","url":"https://www.atachcommunity.com/fileadmin/uploads/atach/Documents/Country_documents/Nepal_HNAP_English_2024_FINAL.pdf","description":"Health adaptation plan targeting 1,400 climate-smart facilities by 2030.","tags":["Health","Adaptation","WASH","Surveillance"],"source":"internet"},
    {"category":"Data Portals & Tools","id":"r13","title":"BIPAD Portal — National Disaster Information Management System","year":2020,"type":"Data Portal","author":"NDRRMA, Government of Nepal","language":"English/Nepali","url":"https://bipadportal.gov.np","description":"Integrated disaster data platform with hazards, risk, incidents, early warning, and recovery at Palika level.","tags":["Data","Disasters","Early Warning","NDRRMA"],"source":"internet"},
    {"category":"Data Portals & Tools","id":"r14","title":"Department of Hydrology and Meteorology (DHM) — Climate Data","year":2024,"type":"Data Portal","author":"DHM, Government of Nepal","language":"English/Nepali","url":"http://dhm.gov.np","description":"Hydro-meteorological data: 337 precipitation stations, 154 hydrometric stations, climate projections.","tags":["Hydrology","Meteorology","Climate Data","Floods"],"source":"internet"},
    {"category":"Data Portals & Tools","id":"r15","title":"Climate Change Laws of the World — Nepal Profile","year":2024,"type":"Database","author":"Grantham Research Institute, LSE","language":"English","url":"https://climate-laws.org/geographies/nepal","description":"Real-time database of Nepal's climate laws and policies.","tags":["Laws","Policy Database","Legislation","Tracking"],"source":"internet"},
    {"category":"Data Portals & Tools","id":"r16","title":"Nepal — Climate Action Tracker Assessment","year":2024,"type":"Assessment Tool","author":"Climate Action Tracker (CAT)","language":"English","url":"https://climateactiontracker.org/countries/nepal/","description":"Independent NDC assessment. Nepal rated 1.5-degree compatible but emissions up 41.5% since 2010.","tags":["NDC Rating","Tracking","Emissions","1.5 degrees"],"source":"internet"},
    {"category":"Data Portals & Tools","id":"r17","title":"Climate Change Statistics and Indicators of Nepal","year":2022,"type":"Statistical Report","author":"Central Bureau of Statistics (CBS)","language":"English","url":"https://unstats.un.org/unsd/envstats/compendia/Nepal_ClimateChangeRelatedIndicatorsofNepal_2022.pdf","description":"First national climate statistics covering emissions, disasters, exposure, and adaptive capacity.","tags":["Statistics","Indicators","CBS","Transparency"],"source":"internet"},
    {"category":"International Frameworks","id":"r18","title":"UNFCCC Warsaw International Mechanism (WIM) for Loss and Damage","year":2013,"type":"International Mechanism","author":"UNFCCC","language":"English","url":"https://unfccc.int/process-and-meetings/bodies/constituted-bodies/warsaw-international-mechanism-for-loss-and-damage-wim","description":"Primary UNFCCC L&D mechanism. Nepal advocates L&D as a standalone third pillar of negotiations.","tags":["L&D","WIM","UNFCCC","COP","Finance"],"source":"internet"},
    {"category":"International Frameworks","id":"r19","title":"Paris Agreement — NDC Registry","year":2015,"type":"International Agreement","author":"UNFCCC","language":"English","url":"https://unfccc.int/NDCREG","description":"Nepal's NDC 3.0 (May 2025) publicly accessible in the UNFCCC NDC registry.","tags":["Paris Agreement","NDC","L&D","UNFCCC"],"source":"internet"},
    {"category":"International Frameworks","id":"r20","title":"Sendai Framework for Disaster Risk Reduction 2015-2030","year":2015,"type":"International Framework","author":"UNDRR","language":"English","url":"https://www.undrr.org/publication/sendai-framework-disaster-risk-reduction-2015-2030","description":"Global DRR framework. Nepal's DRR Strategic Plan 2018-2030 is fully aligned to Sendai targets.","tags":["Sendai","DRR","UNDRR","Hazards"],"source":"internet"},
    {"category":"International Frameworks","id":"r21","title":"Hindu Kush Himalaya Assessment Report (ICIMOD)","year":2019,"type":"Scientific Assessment","author":"ICIMOD","language":"English","url":"https://www.icimod.org/hkhassessment/","description":"1.5-degree warming causes 1.8-2.2-degree warming in HKH due to elevation-dependent warming.","tags":["HKH","ICIMOD","Science","Glaciers"],"source":"internet"},
    {"category":"Climate Finance Resources","id":"r22","title":"Green Climate Fund (GCF) — Nepal Country Portfolio","year":2024,"type":"Finance Portal","author":"Green Climate Fund (GCF)","language":"English","url":"https://www.greenclimate.fund/countries/NPL","description":"GCF projects: Gandaki Basin Resilience (USD 27.4M), Churia Region (USD 39.3M).","tags":["GCF","Finance","Adaptation","Projects"],"source":"internet"},
    {"category":"Climate Finance Resources","id":"r23","title":"World Bank Country Climate and Development Report — Nepal","year":2023,"type":"Country Report","author":"World Bank","language":"English","url":"https://www.worldbank.org/en/country/nepal/brief/key-highlights-country-climate-and-development-report-for-nepal","description":"Pathways for Nepal to develop while transitioning to a green, resilient economy.","tags":["World Bank","Finance","Development","Investment"],"source":"internet"},
    {"category":"Climate Finance Resources","id":"r24","title":"UNDP Climate Promise — Nepal NDC Support","year":2025,"type":"Programme","author":"UNDP","language":"English","url":"https://climatepromise.undp.org/what-we-do/where-we-work/nepal","description":"NDC 3.0 includes USD 18-20 billion for adaptation 2025-2035 and L&D losses of USD 345 million.","tags":["UNDP","NDC Support","Adaptation Finance","L&D"],"source":"internet"},
    {"category":"Research & Reports","id":"r25","title":"IOM Policy Brief: Climate, Migration and Environment in Nepal (2025)","year":2025,"type":"Policy Brief","author":"International Organization for Migration (IOM)","language":"English","url":"https://nepal.iom.int/sites/g/files/tmzbdl1116/files/documents/2025-04/mecc-policy-brief-english-version.pdf","description":"Latest analysis on climate-induced migration and gender-responsive approaches.","tags":["Migration","Displacement","Gender","IOM"],"source":"internet"},
    {"category":"Research & Reports","id":"r26","title":"IPCC Sixth Assessment Report (AR6)","year":2022,"type":"Scientific Report","author":"IPCC","language":"English","url":"https://www.ipcc.ch/assessment-report/ar6/","description":"Confirms accelerating glacier retreat in HKH and adaptation limits referenced in Nepal's L&D Framework.","tags":["IPCC","Science","Glaciers","Adaptation Limits"],"source":"internet"},
    {"category":"Research & Reports","id":"r27","title":"NDC Partnership — Nepal Country Profile","year":2025,"type":"Programme Dashboard","author":"NDC Partnership","language":"English","url":"https://ndcpartnership.org/country/npl","description":"Nepal submitted NDC 3.0 May 2025 targeting 26.8% emission cut by 2035 needing USD 73.7 billion.","tags":["NDC","Tracking","Finance","Implementation"],"source":"internet"},
]
RESOURCE_CATEGORIES = ["All"] + sorted(set(r["category"] for r in RESOURCES))
RESOURCE_TYPES      = ["All"] + sorted(set(r["type"]     for r in RESOURCES))
RESOURCE_SOURCES    = ["All","Uploaded & Indexed","Internet / External"]

# ── call_ai ────────────────────────────────────────────────────────────────
def call_ai(system_prompt, messages):
    groq_key = st.secrets.get("GROQ_API_KEY","") or os.environ.get("GROQ_API_KEY","")
    ant_key  = st.secrets.get("ANTHROPIC_API_KEY","") or os.environ.get("ANTHROPIC_API_KEY","")
    if groq_key:
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":"Bearer "+groq_key,"Content-Type":"application/json"},
                json={"model":"llama-3.3-70b-versatile",
                      "messages":[{"role":"system","content":system_prompt}]+messages,
                      "max_tokens":1000,"temperature":0.4}, timeout=30)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e: return "Groq error: "+str(e)
    if ant_key:
        try:
            if ANTHROPIC_SDK:
                c = anthropic.Anthropic(api_key=ant_key)
                res = c.messages.create(model="claude-sonnet-4-20250514",max_tokens=1000,system=system_prompt,messages=messages)
                return res.content[0].text
            r = requests.post("https://api.anthropic.com/v1/messages",
                headers={"x-api-key":ant_key,"anthropic-version":"2023-06-01","content-type":"application/json"},
                json={"model":"claude-sonnet-4-20250514","max_tokens":1000,"system":system_prompt,"messages":messages},timeout=30)
            r.raise_for_status()
            return r.json()["content"][0]["text"]
        except Exception as e: return "Anthropic error: "+str(e)
    return "No AI key set. Add GROQ_API_KEY (free at console.groq.com) or ANTHROPIC_API_KEY to Streamlit Secrets."

with tab_explorer:
    all_docs = DOCUMENTS + [d for d in st.session_state.uploaded_docs if d.get("approved", True)]
    col_s,col_sec,col_lev,col_th = st.columns([3,1.5,1.5,1.5])
    with col_s:
        search_q = st.text_input("",placeholder="Search policies, keywords, ministries...",label_visibility="collapsed")
    with col_sec:
        sectors = ["All"]+sorted(set(s for d in all_docs for s in d.get("sector",[])))
        filter_sector = st.selectbox("Sector",sectors,label_visibility="visible")
    with col_lev:
        filter_level = st.selectbox("Level",["All","Federal","Provincial","Local"],label_visibility="visible")
    with col_th:
        all_themes = ["All"]+sorted(set(t for d in all_docs for t in d.get("themes",[])))
        filter_theme = st.selectbox("Theme",all_themes,label_visibility="visible")

    def doc_matches(d):
        q = search_q.lower()
        if q and not any(q in str(v).lower() for v in [d["title"],d.get("summary",""),d.get("ministry",""),*d.get("keywords",[])]):
            return False
        if filter_sector!="All" and filter_sector not in d.get("sector",[]): return False
        if filter_level!="All" and d.get("level")!=filter_level: return False
        if filter_theme!="All" and filter_theme not in d.get("themes",[]): return False
        return True

    filtered = [d for d in all_docs if doc_matches(d)]
    st.markdown(f'<div class="section-label">{len(filtered)} of {len(all_docs)} documents</div>',unsafe_allow_html=True)

    for doc in filtered:
        with st.expander(f"📄  {doc['short_title']}  ·  {doc['year']}  ·  {doc['level']}",expanded=False):
            c1,c2 = st.columns([3,1])
            with c1:
                st.markdown(f"**{doc['title']}**")
                st.markdown(f'<div style="background:#f5f0e8;border-left:3px solid #4a9966;padding:10px 14px;border-radius:0 8px 8px 0;font-size:13px;color:#4a4a46;line-height:1.7;margin:8px 0;">{doc["summary"]}</div>',unsafe_allow_html=True)
                if doc.get("highlights"):
                    st.markdown('<div class="section-label" style="margin-top:12px;">Key highlights</div>',unsafe_allow_html=True)
                    for h in doc["highlights"]: st.markdown(f"• {h}")
            with c2:
                st.markdown(f'<div class="section-label">Ministry</div><div style="font-size:12px;color:#1a1a18;margin-bottom:12px;">{doc["ministry"]}</div>',unsafe_allow_html=True)
                st.markdown(badge_html(doc["status"],status_color(doc["status"]))+badge_html(doc["language"],"badge-blue")+badge_html(str(doc["year"]),"badge-earth"),unsafe_allow_html=True)
                st.markdown('<br><div class="section-label">Sectors</div>',unsafe_allow_html=True)
                st.markdown(" ".join(badge_html(s,"badge-green") for s in doc.get("sector",[])),unsafe_allow_html=True)
                st.markdown('<br><div class="section-label">Themes</div>',unsafe_allow_html=True)
                st.markdown(" ".join(badge_html(t,"badge-blue") for t in doc.get("themes",[])),unsafe_allow_html=True)

    if not filtered: st.info("No policies match your filters.")

with tab_ai:
    col_chat,col_side = st.columns([2.5,1])
    with col_chat:
        st.markdown("### 🤖 Nepal Climate Policy AI")
        for msg in st.session_state.chat_history:
            css = "user-msg" if msg["role"]=="user" else "bot-msg"
            icon = "👤" if msg["role"]=="user" else "🏔"
            st.markdown(f'<div class="{css}">{icon} {msg["content"]}</div>',unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
        if len(st.session_state.chat_history)<3:
            st.markdown('<div class="section-label">Suggested questions:</div>',unsafe_allow_html=True)
            suggs = ["What are Nepal's main climate risks?","How does the L&D Framework define economic vs non-economic loss?","Which policies address GLOF risks?","What climate finance mechanisms exist?","What are key policy gaps?","जलवायु परिवर्तनले नेपालमा कस्तो प्रभाव पारेको छ?"]
            cols2 = st.columns(2)
            for i,q in enumerate(suggs):
                with cols2[i%2]:
                    if st.button(q,key=f"sugg_{i}",use_container_width=True):
                        st.session_state._pending_question = q
        with st.form("chat_form",clear_on_submit=True):
            ci,cb = st.columns([5,1])
            with ci:
                ph = "Ask about any climate policy..." if st.session_state.lang=="EN" else "जलवायु नीतिको बारेमा सोध्नुहोस्..."
                user_input = st.text_input("",placeholder=ph,label_visibility="collapsed")
            with cb: submitted = st.form_submit_button("Send",use_container_width=True)
        if hasattr(st.session_state,"_pending_question"):
            user_input = st.session_state._pending_question; submitted = True
            del st.session_state._pending_question
        if submitted and user_input.strip():
            st.session_state.chat_history.append({"role":"user","content":user_input})
            doc_ctx = "\n".join(f"{i+1}. {d['title']} ({d['year']}): {d['summary']}" for i,d in enumerate(DOCUMENTS+[d for d in st.session_state.uploaded_docs if d.get("approved", True)]))
            up_ctx  = "".join(f"\n\nExtracted from {u['title']}:\n{u['extracted_text'][:3000]}" for u in [d for d in st.session_state.uploaded_docs if d.get("approved", True)] if u.get("extracted_text"))
            sysprompt = (
                "You are Nepal Climate Policy Intelligence Assistant.\n\n"
                f"Policy documents:\n{doc_ctx}{up_ctx}\n\n"
                "Key facts: Nepal is LDC, climate disasters cause 65% of deaths, 2017 Tarai floods=2.08% GDP loss, "
                "NDC 2020 targets net-zero 2050, 7 provinces, Karnali+Sudurpashchim Very High risk, 21 dangerous glacial lakes.\n\n"
                "Answer concisely, cite policies, respond in same language as question, max 400 words."
            )
            msgs = [{"role":m["role"],"content":m["content"]} for m in st.session_state.chat_history]
            with st.spinner("Analyzing policies..."):
                reply = call_ai(sysprompt,msgs)
            st.session_state.chat_history.append({"role":"assistant","content":reply})
            st.rerun()
        if st.button("Clear chat",type="secondary"):
            st.session_state.chat_history = st.session_state.chat_history[:1]; st.rerun()

    with col_side:
        st.markdown("### Knowledge base")
        for doc in DOCUMENTS:
            st.markdown(f'<div style="display:flex;gap:8px;margin-bottom:8px;"><div style="width:6px;height:6px;border-radius:50%;background:#2d6a45;margin-top:5px;flex-shrink:0;"></div><div><div style="font-size:12px;font-weight:600;color:#1a1a18;">{doc["short_title"]}</div><div style="font-size:10px;color:#8a8a84;">{doc["year"]} · {doc["language"]}</div></div></div>',unsafe_allow_html=True)
        if st.session_state.uploaded_docs:
            for ud in st.session_state.uploaded_docs: st.markdown(f"✅ {ud['short_title']}")
        st.info("Upload more documents in the Upload Policy tab.")
        gk = st.secrets.get("GROQ_API_KEY","") or os.environ.get("GROQ_API_KEY","")
        ak = st.secrets.get("ANTHROPIC_API_KEY","") or os.environ.get("ANTHROPIC_API_KEY","")
        if gk: st.success("AI: Groq (free) · llama-3.3-70b")
        elif ak: st.info("AI: Anthropic Claude")
        else: st.warning("Add GROQ_API_KEY to Secrets for free AI")

with tab_analytics:
    st.markdown("### 📊 Policy Analytics Dashboard")
    all_docs = DOCUMENTS + [d for d in st.session_state.uploaded_docs if d.get("approved", True)]
    c1,c2 = st.columns(2)
    with c1:
        tc = {}
        for d in all_docs:
            for t in d.get("themes",[]): tc[t]=tc.get(t,0)+1
        dft = pd.DataFrame(list(tc.items()),columns=["Theme","Count"]).sort_values("Count",ascending=True)
        fig1 = go.Figure(go.Bar(x=dft["Count"],y=dft["Theme"],orientation="h",
            marker_color=["#8a5aa0","#c47c40","#7a4a1e","#2e72b0","#2d6a45"][:len(dft)],
            text=dft["Count"],textposition="outside",textfont=dict(size=12,color="#1a1a18"),cliponaxis=False))
        fig1.update_layout(title=dict(text="Policy themes distribution",font=dict(size=13),x=0),
            paper_bgcolor="white",plot_bgcolor="white",height=300,
            margin=dict(l=10,r=50,t=45,b=10),
            xaxis=dict(showgrid=False,zeroline=False,visible=False,range=[0,dft["Count"].max()*1.35]),
            yaxis=dict(tickfont=dict(size=12),automargin=True),
            font=dict(family="Inter, sans-serif"),bargap=0.35)
        st.plotly_chart(fig1,use_container_width=True)
    with c2:
        sc = {}
        for d in all_docs:
            for s in d.get("sector",[]): sc[s]=sc.get(s,0)+1
        dfs = pd.DataFrame(list(sc.items()),columns=["Sector","Count"]).sort_values("Count",ascending=False)
        scols = ["#2d6a45","#2e72b0","#7a4a1e","#c47c40","#8a5aa0","#1e6a6a","#b56a00","#c94030"][:len(dfs)]
        fig2 = go.Figure(go.Pie(labels=dfs["Sector"],values=dfs["Count"],hole=0.52,
            marker=dict(colors=scols,line=dict(color="white",width=2)),
            textinfo="percent",textposition="inside",textfont=dict(size=11,color="white"),
            insidetextorientation="radial",
            hovertemplate="<b>%{label}</b><br>%{value} docs (%{percent})<extra></extra>"))
        fig2.update_layout(title=dict(text="Sector coverage",font=dict(size=13),x=0),
            paper_bgcolor="white",height=300,margin=dict(l=0,r=0,t=45,b=10),
            font=dict(family="Inter, sans-serif",size=11),showlegend=True,
            legend=dict(orientation="v",x=1.02,y=0.95,xanchor="left",font=dict(size=10),bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig2,use_container_width=True)

    c3,c4 = st.columns(2)
    with c3:
        sdocs = sorted(all_docs,key=lambda d:d["year"])
        scmap = {"Approved":"#2d6a45","Active":"#2e72b0","Foundational":"#7a4a1e","Draft":"#c47c40"}
        yrmin,yrmax=1990,2030
        def xp(yr): return (yr-yrmin)/(yrmax-yrmin)*100
        LW,NL=20,5; ltip=[-999]*NL; dlanes=[]
        for d in sdocs:
            x=xp(d["year"]); ch=0
            for li in range(NL):
                if x-ltip[li]>=LW: ch=li; break
            else: ch=min(range(NL),key=lambda i:ltip[i])
            ltip[ch]=x; dlanes.append(ch)
        ly=[0,0.30,-0.30,0.58,-0.58]; SY=-0.10
        fig3=go.Figure()
        fig3.add_shape(type="line",x0=0,x1=100,y0=SY,y1=SY,line=dict(color="#d0cec8",width=2))
        for yr in [1993,2000,2005,2010,2015,2019,2021,2024,2026]:
            xv=xp(yr)
            if 0<=xv<=100:
                fig3.add_shape(type="line",x0=xv,x1=xv,y0=SY-0.04,y1=SY+0.04,line=dict(color="#c0beb8",width=1))
                fig3.add_annotation(x=xv,y=SY-0.13,text=str(yr),showarrow=False,font=dict(size=8,color="#8a8a84"),yanchor="top",xanchor="center")
        for i,d in enumerate(sdocs):
            x=xp(d["year"]); lane=dlanes[i]; yoff=ly[lane]
            col=scmap.get(d["status"],"#8a8a84")
            lbl=d["short_title"][:30]+"..." if len(d["short_title"])>30 else d["short_title"]
            fig3.add_trace(go.Scatter(x=[x],y=[SY],mode="markers",
                marker=dict(size=10,color=col,line=dict(color="white",width=2)),
                hovertemplate=f"<b>{d['short_title']}</b><br>{d['year']}<extra></extra>",showlegend=False))
            if abs(yoff)>0.01:
                sg=1 if yoff>0 else -1
                fig3.add_shape(type="line",x0=x,x1=x,y0=SY+sg*0.05,y1=SY+yoff-sg*0.09,line=dict(color=col,width=1,dash="dot"))
            fig3.add_annotation(x=x,y=SY+yoff,text=f"<b>{d['year']}</b>  {lbl}",showarrow=False,
                font=dict(size=9,color="#1a1a18"),bgcolor="white",bordercolor=col,
                borderwidth=1.2,borderpad=4,xanchor="center",yanchor="middle",opacity=1.0)
        nu=max(dlanes)+1; ysp=ly[min(nu-1,NL-1)]
        fig3.update_layout(title=dict(text="Policy chronology",font=dict(size=13),x=0),
            paper_bgcolor="white",plot_bgcolor="white",height=340,margin=dict(l=10,r=10,t=45,b=10),
            xaxis=dict(range=[-2,102],visible=False,showgrid=False,zeroline=False),
            yaxis=dict(range=[SY-abs(ysp)-0.35,SY+abs(ysp)+0.45],visible=False,showgrid=False,zeroline=False),
            font=dict(family="Inter, sans-serif"),showlegend=False)
        st.plotly_chart(fig3,use_container_width=True)
        seen={}
        for d in sdocs: seen[d["status"]]=scmap.get(d["status"],"#8a8a84")
        st.markdown(" ".join(f'<span style="display:inline-flex;align-items:center;gap:5px;margin-right:14px;font-size:11px;color:#4a4a46;"><span style="width:10px;height:10px;border-radius:50%;background:{c};display:inline-block;"></span>{s}</span>' for s,c in seen.items()),unsafe_allow_html=True)
    with c4:
        lc={}
        for d in all_docs: lc[d.get("language","Unknown")]=lc.get(d.get("language","Unknown"),0)+1
        dfl=pd.DataFrame(list(lc.items()),columns=["Language","Count"])
        lcmap={"English":"#2e72b0","Nepali":"#c47c40","English/Nepali":"#2d6a45","Unknown":"#8a8a84"}
        fig4=go.Figure(go.Bar(x=dfl["Language"],y=dfl["Count"],
            marker_color=[lcmap.get(l,"#8a8a84") for l in dfl["Language"]],
            text=dfl["Count"],textposition="outside",textfont=dict(size=13,color="#1a1a18"),cliponaxis=False,width=0.45))
        fig4.update_layout(title=dict(text="Language distribution",font=dict(size=13),x=0),
            paper_bgcolor="white",plot_bgcolor="white",height=300,margin=dict(l=10,r=20,t=45,b=10),
            yaxis=dict(showgrid=False,visible=False,range=[0,dfl["Count"].max()*1.4]),
            xaxis=dict(tickfont=dict(size=11),automargin=True),
            font=dict(family="Inter, sans-serif"),showlegend=False)
        st.plotly_chart(fig4,use_container_width=True)

    st.markdown("### Province climate risk profile")
    dfp=pd.DataFrame(PROVINCES)
    rcmap={"Very High":"#c94030","High":"#c47c40","Moderate":"#2d7a4f"}
    fig5=go.Figure(go.Bar(x=dfp["name"],y=dfp["risk_score"],
        marker_color=[rcmap.get(r,"#8a8a84") for r in dfp["risk"]],
        text=dfp["risk"],textposition="outside",textfont=dict(size=11,color="#1a1a18"),cliponaxis=False,width=0.55,
        hovertemplate="<b>%{x}</b><br>Risk: %{text}<extra></extra>"))
    fig5.update_layout(title=dict(text="Provincial climate risk levels",font=dict(size=13),x=0),
        paper_bgcolor="white",plot_bgcolor="white",height=300,margin=dict(l=10,r=20,t=45,b=10),
        yaxis=dict(visible=False,range=[0,dfp["risk_score"].max()*1.5]),
        xaxis=dict(tickfont=dict(size=11),automargin=True),
        font=dict(family="Inter, sans-serif"),showlegend=False)
    st.plotly_chart(fig5,use_container_width=True)
    st.markdown(" ".join(f'<span style="display:inline-flex;align-items:center;gap:4px;margin-right:16px;font-size:11px;color:#4a4a46;"><span style="width:10px;height:10px;border-radius:2px;background:{c};display:inline-block;"></span>{r}</span>' for r,c in rcmap.items()),unsafe_allow_html=True)

    st.markdown("<br>",unsafe_allow_html=True)
    st.markdown("### Policy gap analysis")
    for g in POLICY_GAPS:
        sc={"high":"#c94030","medium":"#c47c40","low":"#8a8a84"}[g["severity"]]
        st.markdown(f'<div style="background:white;border:0.5px solid rgba(26,26,24,0.1);border-left:3px solid {sc};border-radius:8px;padding:12px 16px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;"><div><div style="font-size:13px;font-weight:600;color:#1a1a18;">{g["gap"]}</div><div style="font-size:11px;color:#4a4a46;margin-top:3px;">{g["note"]}</div></div><span class="badge {status_color(g["status"])}">{g["status"]}</span></div>',unsafe_allow_html=True)

with tab_provinces:
    st.markdown("### 🗺 Provincial Climate Policy Coverage")
    cm,cd=st.columns([1.5,2])
    with cm:
        st.markdown('<div class="section-label">Select a province</div>',unsafe_allow_html=True)
        for p in PROVINCES:
            if st.button(f"Province {p['id']} — {p['name']}",key=f"prov_{p['id']}",use_container_width=True,help=f"Risk: {p['risk']}"):
                st.session_state.selected_province=p
        st.markdown('<div style="margin-top:16px;padding:12px;background:#1a4a2e0a;border-radius:8px;font-size:11px;color:#4a4a46;line-height:1.7;border:0.5px solid #2d6a4530;">📌 Province data is indicative. More documents will populate province-specific views.</div>',unsafe_allow_html=True)
    with cd:
        prov=st.session_state.get("selected_province",PROVINCES[0])
        rc=risk_color(prov["risk"])
        st.markdown(f'<div style="background:white;border-radius:12px;border:0.5px solid rgba(26,26,24,0.12);padding:20px 22px;margin-bottom:14px;"><div style="display:flex;justify-content:space-between;align-items:flex-start;"><div><h3 style="font-size:20px;font-weight:700;color:#1a1a18;margin:0;font-family:Lora,serif;">{prov["name"]} Province</h3><div style="font-size:12px;color:#4a4a46;margin-top:4px;">Province {prov["id"]} · Federal Republic of Nepal</div></div><span class="badge" style="background:{rc}18;color:{rc};border:0.5px solid {rc}40;font-size:12px;padding:4px 12px;">{prov["risk"]} Risk</span></div></div>',unsafe_allow_html=True)
        m1,m2,m3=st.columns(3)
        with m1: st.metric("Policy Documents",prov["docs"])
        with m2: st.metric("Climate Risk",prov["risk"])
        with m3: st.metric("Pending Upload","100+")
        st.markdown('<div class="section-label" style="margin-top:16px;">Key climate hazards</div>',unsafe_allow_html=True)
        for h in prov["hazards"]:
            st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:6px 10px;background:#faf7f2;border-radius:6px;margin-bottom:6px;"><div style="width:6px;height:6px;border-radius:50%;background:{rc};flex-shrink:0;"></div><span style="font-size:12px;color:#1a1a18;">{h}</span></div>',unsafe_allow_html=True)
        prov_recs={"Koshi":["Strengthen GLOF early warning systems","Trans-boundary water treaty with China","Agricultural insurance for hill farmers"],"Madhesh":["Flood embankment maintenance policy","Heat action plan for urban areas","Drought-resistant crop promotion"],"Bagmati":["Urban stormwater management policy","Kathmandu Valley air quality plan","Green building codes"],"Gandaki":["Glacial lake monitoring programme","Tourism climate resilience plan","Landslide risk mapping"],"Lumbini":["Flood early warning for Rapti basin","Irrigation efficiency programme","Wetland conservation policy"],"Karnali":["Food security emergency protocol","Spring revival programme","Nomadic herder adaptation support"],"Sudurpashchim":["Drought monitoring and response plan","Forest fire management policy","Drinking water resilience programme"]}
        st.markdown('<div class="section-label" style="margin-top:16px;">Recommended policy priorities</div>',unsafe_allow_html=True)
        for r in prov_recs.get(prov["name"],[]):
            st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:6px 10px;background:white;border:0.5px solid rgba(26,26,24,0.1);border-radius:6px;margin-bottom:6px;"><span style="color:#2d6a45;">→</span><span style="font-size:12px;color:#1a1a18;">{r}</span></div>',unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)
    dfpp=pd.DataFrame(PROVINCES)
    figp=px.bar(dfpp,x="name",y="docs",color="risk",color_discrete_map={"Very High":"#c94030","High":"#c47c40","Moderate":"#2d7a4f"},title="Policy document coverage by province",labels={"name":"Province","docs":"Documents","risk":"Risk Level"},text="docs")
    figp.update_traces(textposition="outside")
    figp.update_layout(paper_bgcolor="white",plot_bgcolor="white",height=300,margin=dict(l=0,r=0,t=40,b=0),yaxis=dict(showgrid=True,gridcolor="rgba(0,0,0,0.05)"),font=dict(family="Inter, sans-serif"),title_font_size=13,legend=dict(font=dict(size=10),orientation="h",y=-0.15))
    st.plotly_chart(figp,use_container_width=True)

with tab_resources:
    st.markdown("### 📚 Resources Library")
    st.markdown("Comprehensive library — **uploaded & indexed** in this portal and **externally sourced** from UNFCCC, World Bank, UNDP, ICIMOD, and Government of Nepal portals.")
    cr,crc,crt,crs=st.columns([3,1.8,1.8,1.5])
    with cr: res_search=st.text_input("",placeholder="Search title, author, tags...",key="res_search",label_visibility="collapsed")
    with crc: res_cat=st.selectbox("Category",RESOURCE_CATEGORIES,key="res_cat")
    with crt: res_type=st.selectbox("Type",RESOURCE_TYPES,key="res_type")
    with crs: res_src=st.selectbox("Source",RESOURCE_SOURCES,key="res_src")
    def res_matches(r):
        q=res_search.lower()
        if q and not any(q in str(v).lower() for v in [r["title"],r["description"],r["author"]]+r["tags"]): return False
        if res_cat!="All" and r["category"]!=res_cat: return False
        if res_type!="All" and r["type"]!=res_type: return False
        if res_src=="Uploaded & Indexed" and r["source"]!="uploaded": return False
        if res_src=="Internet / External" and r["source"]!="internet": return False
        return True
    fr=[r for r in RESOURCES if res_matches(r)]
    un=len([r for r in RESOURCES if r["source"]=="uploaded"])
    inn=len([r for r in RESOURCES if r["source"]=="internet"])
    st.markdown(f'<div class="section-label">{len(fr)} of {len(RESOURCES)} resources · <span style="color:#2d6a45;font-weight:600;">📁 {un} uploaded</span> · <span style="color:#1e4f7a;font-weight:600;">🌐 {inn} from internet</span></div>',unsafe_allow_html=True)
    from collections import defaultdict
    grpd=defaultdict(list)
    for r in fr: grpd[r["category"]].append(r)
    cmeta={"Uploaded & Indexed":("📁","#2d6a45"),"National Policies & Strategies":("🏛","#1e4f7a"),"Data Portals & Tools":("📊","#7a4a1e"),"International Frameworks":("🌐","#5a2d7a"),"Climate Finance Resources":("💰","#b56a00"),"Research & Reports":("🔬","#1e6a6a")}
    for cat,crs_list in grpd.items():
        icon,color=cmeta.get(cat,("📄","#2d6a45"))
        st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin:22px 0 8px;"><span style="font-size:18px;">{icon}</span><span style="font-size:15px;font-weight:700;color:{color};">{cat}</span><span style="font-size:11px;color:#8a8a84;background:#f5f0e8;padding:2px 8px;border-radius:10px;">{len(crs_list)}</span></div>',unsafe_allow_html=True)
        for r in crs_list:
            sb='<span style="background:#2d6a4518;color:#2d6a45;font-size:10px;padding:2px 7px;border-radius:3px;">📁 Uploaded</span>' if r["source"]=="uploaded" else '<span style="background:#1e4f7a18;color:#1e4f7a;font-size:10px;padding:2px 7px;border-radius:3px;">🌐 Internet</span>'
            th=" ".join(f'<span style="font-size:10px;background:#f5f0e8;color:#4a4a46;padding:2px 6px;border-radius:3px;display:inline-block;margin:1px;">{t}</span>' for t in r["tags"])
            with st.expander(f"  {r['title']}  ·  {r['year']}",expanded=False):
                dd,dm=st.columns([3,1])
                with dd:
                    st.markdown(f'<div style="background:#faf7f2;border-left:3px solid {color};padding:10px 14px;border-radius:0 8px 8px 0;font-size:13px;color:#4a4a46;line-height:1.7;margin-bottom:10px;">{r["description"]}</div>',unsafe_allow_html=True)
                    st.markdown(f'<div style="margin-bottom:8px;">{th}</div>',unsafe_allow_html=True)
                    if r.get("url","").startswith("http"):
                        st.markdown(f'<a href="{r["url"]}" target="_blank" style="font-size:12px;color:{color};text-decoration:none;border:0.5px solid {color}40;padding:5px 14px;border-radius:6px;display:inline-block;">🔗 Open resource →</a>',unsafe_allow_html=True)
                with dm:
                    st.markdown(f'<div style="background:#f5f0e8;border-radius:8px;padding:12px 14px;"><div style="font-size:10px;color:#8a8a84;text-transform:uppercase;margin-bottom:3px;">Type</div><div style="font-size:11px;color:#1a1a18;font-weight:500;margin-bottom:8px;">{r["type"]}</div><div style="font-size:10px;color:#8a8a84;text-transform:uppercase;margin-bottom:3px;">Author</div><div style="font-size:11px;color:#1a1a18;margin-bottom:8px;line-height:1.4;">{r["author"]}</div><div style="font-size:10px;color:#8a8a84;text-transform:uppercase;margin-bottom:3px;">Language</div><div style="font-size:11px;color:#1a1a18;margin-bottom:8px;">{r["language"]}</div><div>{sb}</div></div>',unsafe_allow_html=True)
    if not fr: st.info("No resources match your filters.")
    st.markdown("<br>",unsafe_allow_html=True)
    with st.expander("➕  Suggest a resource to add"):
        with st.form("suggest_resource"):
            st_=st.text_input("Title *"); su=st.text_input("URL *")
            sc1,sc2=st.columns(2)
            with sc1: sy=st.number_input("Year",1990,2030,2024)
            with sc2: scat=st.selectbox("Category",RESOURCE_CATEGORIES[1:])
            sd=st.text_area("Description",height=80)
            if st.form_submit_button("Submit suggestion",type="primary"):
                if st_ and su: st.success(f"'{st_}' noted. Thank you!")
                else: st.error("Please fill in title and URL.")

with tab_upload:
    st.markdown("### 📤 Add Policy to Database")
    st.markdown("Upload a PDF/text file **or** paste a website URL — the system extracts the content automatically and remembers it across sessions.")

    if st.session_state.last_upload_title:
        st.success(f"✅ **'{st.session_state.last_upload_title}'** added and saved permanently!")
        st.balloons()
        st.session_state.last_upload_title = ""

    cf, ci = st.columns([2, 1])
    with cf:
        # ── Source type selector ──────────────────────────────────────────
        src_type = st.radio(
            "Content source",
            ["📄 Upload file (PDF / TXT)", "🌐 Paste a website URL"],
            horizontal=True,
            label_visibility="visible",
        )
        st.markdown("<br>", unsafe_allow_html=True)

        fk = f"upload_form_{st.session_state.upload_form_key}"
        with st.form(fk, clear_on_submit=False):
            st.markdown("**Document details**")
            dt  = st.text_input("Full title *", placeholder="e.g. Karnali Province Climate Change Adaptation Plan 2023")
            y1, l1, s1 = st.columns(3)
            with y1: dy = st.number_input("Year *", min_value=1990, max_value=2030, value=2023)
            with l1: dl = st.selectbox("Level *", ["Federal","Provincial","Local"])
            with s1: ds = st.selectbox("Status", ["Active","Approved","Draft","Foundational"])
            dm   = st.text_input("Ministry / Author", placeholder="e.g. Ministry of Forests and Environment")
            dsec = st.multiselect("Sectors", ["Climate Change","Water","Agriculture","Energy","Disaster Risk","Health","Environment","Finance","Forests","Urban"])
            dth  = st.multiselect("Themes", ["Adaptation","Mitigation","Governance","Finance","Gender & Inclusion","Biodiversity"])
            dlan = st.selectbox("Language", ["English","Nepali","English/Nepali"])
            dsum = st.text_area("Summary", placeholder="Brief description of the policy document…", height=90)
            dkw  = st.text_input("Keywords (comma-separated)", placeholder="e.g. GLOF, adaptation, water, floods")

            st.markdown("---")
            # Dynamic source inputs
            if "URL" in src_type:
                durl = st.text_input(
                    "Website / document URL *",
                    placeholder="https://mofe.gov.np/policy/adaptation-plan-2024",
                    help="The system will fetch and extract text from this URL automatically.",
                )
                dfile = None
            else:
                dfile = st.file_uploader("Upload document (PDF / TXT)", type=["pdf","txt"])
                durl  = ""

            sub = st.form_submit_button("➕ Add to database", type="primary", use_container_width=True)

        if sub:
            if not dt.strip() or not dsec:
                st.error("⚠️ Please fill in at least the **title** and at least one **sector**.")
            elif "URL" in src_type and not durl.strip():
                st.error("⚠️ Please paste a URL to fetch content from.")
            else:
                extracted = ""
                source_label = "manual entry"

                if "URL" in src_type and durl.strip():
                    with st.spinner(f"Fetching content from {durl.strip()[:60]}…"):
                        extracted, err = extract_url_text(durl.strip())
                    if err:
                        st.error(f"⚠️ Could not fetch URL: {err}")
                        st.stop()
                    source_label = durl.strip()
                    st.info(f"✓ Extracted {len(extracted):,} characters from URL.")
                elif dfile:
                    fb = dfile.read()
                    extracted = (
                        extract_pdf_text(fb)
                        if dfile.type == "application/pdf"
                        else fb.decode("utf-8", errors="replace")[:8000]
                    )
                    source_label = dfile.name

                nd = {
                    "id":             f"user-{len(st.session_state.uploaded_docs)+1}",
                    "title":          dt.strip(),
                    "short_title":    dt.strip()[:50] + ("…" if len(dt.strip()) > 50 else ""),
                    "year":           int(dy),
                    "level":          dl,
                    "sector":         dsec,
                    "ministry":       dm.strip() or "Not specified",
                    "language":       dlan,
                    "keywords":       [k.strip() for k in dkw.split(",") if k.strip()],
                    "filename":       source_label,
                    "summary":        dsum.strip() or "No summary provided.",
                    "themes":         dth,
                    "status":         ds,
                    "highlights":     [],
                    "extracted_text": extracted,
                    "source_type":    "url" if "URL" in src_type else "file",
                }
                st.session_state.uploaded_docs.append(nd)
                # Persist to cache_resource + JSON file
                _get_doc_store().clear()
                _get_doc_store().extend(st.session_state.uploaded_docs)
                save_doc_store(st.session_state.uploaded_docs)
                st.session_state.last_upload_title = nd["title"]
                st.session_state.upload_form_key  += 1
                st.rerun()

    with ci:
        st.markdown("#### Current database")
        st.metric("Pre-loaded documents", len(DOCUMENTS))
        st.metric("User-uploaded documents", len(st.session_state.uploaded_docs))
        st.metric("Total", len(DOCUMENTS) + len(st.session_state.uploaded_docs))

        st.markdown(
            '<div style="background:#1a4a2e0a;border-radius:10px;border:0.5px solid #2d6a4530;padding:14px 16px;margin-top:12px;">' +
            '<div style="font-size:12px;font-weight:600;color:#1a4a2e;margin-bottom:8px;">📌 How it works</div>' +
            '<div style="font-size:11px;color:#4a4a46;line-height:1.9;">' +
            '✓ Upload PDF / TXT <strong>or</strong> paste a URL<br>' +
            '✓ Content extracted automatically<br>' +
            '✓ <strong>Remembered across sessions</strong><br>' +
            '✓ AI Assistant gets immediate access<br>' +
            '✓ Appears in Explorer & Analytics</div></div>',
            unsafe_allow_html=True,
        )

        if st.session_state.uploaded_docs:
            st.markdown("#### Saved documents")
            for ud in st.session_state.uploaded_docs:
                icon = "🌐" if ud.get("source_type") == "url" else "📄"
                # Per-document approve / reject controls (visible to dev only — see below)
                _approved = ud.get("approved", True)  # default approved
                status_dot = (
                    '<span style="width:7px;height:7px;border-radius:50%;background:#2d7a4f;'
                    'display:inline-block;flex-shrink:0;margin-top:3px;" title="Approved"></span>'
                    if _approved else
                    '<span style="width:7px;height:7px;border-radius:50%;background:#c47c40;'
                    'display:inline-block;flex-shrink:0;margin-top:3px;" title="Pending review"></span>'
                )
                st.markdown(
                    f'<div style="display:flex;gap:8px;margin-bottom:8px;align-items:flex-start;">' +
                    status_dot +
                    f'<span style="font-size:13px;">{icon}</span>' +
                    f'<div><div style="font-size:12px;font-weight:500;color:#1a1a18;">{ud["short_title"]}</div>' +
                    f'<div style="font-size:10px;color:#8a8a84;">{ud["year"]} · {ud["level"]} · {ud.get("source_type","file").upper()}</div></div></div>',
                    unsafe_allow_html=True,
                )

        # ── Developer admin panel ─────────────────────────────────────────
        # Hidden behind a password — not visible to regular users.
        # Set ADMIN_PASSWORD in Streamlit Cloud Secrets to enable.
        _admin_pwd = (
            st.secrets.get("ADMIN_PASSWORD", None)
            or os.environ.get("ADMIN_PASSWORD", None)
        )
        if _admin_pwd:
            with st.expander("🔧 Developer admin panel", expanded=False):
                entered = st.text_input(
                    "Admin password", type="password",
                    key="admin_pwd_input",
                    label_visibility="visible",
                )
                if entered == _admin_pwd:
                    st.success("✅ Admin access granted")

                    if st.session_state.uploaded_docs:
                        st.markdown("**Review & manage uploaded documents:**")
                        to_remove = []
                        for idx, ud in enumerate(st.session_state.uploaded_docs):
                            icon = "🌐" if ud.get("source_type") == "url" else "📄"
                            ca, cb, cc = st.columns([4, 1, 1])
                            with ca:
                                approved = ud.get("approved", True)
                                st.markdown(
                                    f'{"✅" if approved else "⏳"} **{ud["short_title"]}** ' +
                                    f'`{ud["year"]}` · {ud["level"]} · {icon}',
                                )
                            with cb:
                                lbl = "Revoke" if approved else "Approve"
                                if st.button(lbl, key=f"toggle_{idx}", use_container_width=True):
                                    st.session_state.uploaded_docs[idx]["approved"] = not approved
                                    _get_doc_store().clear()
                                    _get_doc_store().extend(st.session_state.uploaded_docs)
                                    save_doc_store(st.session_state.uploaded_docs)
                                    st.rerun()
                            with cc:
                                if st.button("Delete", key=f"del_{idx}", type="secondary", use_container_width=True):
                                    st.session_state.uploaded_docs.pop(idx)
                                    _get_doc_store().clear()
                                    _get_doc_store().extend(st.session_state.uploaded_docs)
                                    save_doc_store(st.session_state.uploaded_docs)
                                    st.rerun()

                        st.markdown("---")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("🗑 Delete ALL documents", type="secondary", use_container_width=True):
                                st.session_state.uploaded_docs = []
                                _get_doc_store().clear()
                                save_doc_store([])
                                st.rerun()
                        with c2:
                            st.download_button(
                                "⬇ Export as JSON",
                                data=json.dumps(
                                    [
                                        {k: v for k, v in d.items() if k != "extracted_text"}
                                        for d in st.session_state.uploaded_docs
                                    ],
                                    ensure_ascii=False, indent=2
                                ),
                                file_name="nepal_policy_uploads.json",
                                mime="application/json",
                                use_container_width=True,
                            )
                    else:
                        st.info("No user-uploaded documents in the database.")
                elif entered:
                    st.error("Incorrect password.")

# ── Footer ─────────────────────────────────────────────────────────────────
st.markdown("<br><br>",unsafe_allow_html=True)
st.markdown('<div style="border-top:0.5px solid rgba(26,26,24,0.12);padding:16px 0;display:flex;justify-content:space-between;align-items:center;"><div style="font-size:11px;color:#8a8a84;">🏔 Nepal Climate Policy Intelligence Portal · Built with Streamlit + Claude AI + Groq AI</div><div style="font-size:11px;color:#8a8a84;">Data: Ministry of Forests and Environment · NDRRMA · NPC · Government of Nepal</div></div>',unsafe_allow_html=True)
