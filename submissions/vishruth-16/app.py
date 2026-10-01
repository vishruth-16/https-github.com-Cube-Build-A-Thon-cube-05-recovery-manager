import os
import json
import io
import csv
import uuid
import hashlib
from datetime import datetime, timedelta
import random

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dotenv import load_dotenv

# ══════════════════════════════════════════════════════════════════════════════
# 1. ENVIRONMENT & PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
env_api_key = os.getenv("GEMINI_API_KEY", "")

from agent.engine import RecoveryAuditEngine, RecoveryEvidenceRecord

st.set_page_config(
    page_title="Trident Recovery — AI Command Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# 2. DESIGN SYSTEM & CSS (Dark Mode SaaS)
# ══════════════════════════════════════════════════════════════════════════════
COLORS = {
    "bg":           "#0B0F17",
    "surface":      "#121824",
    "surface_subtle": "#162032",
    "border":       "#1F2937",
    "text":         "#F3F4F6",
    "muted":        "#9CA3AF",
    "blue":         "#3B82F6",
    "blue_dark":    "#2563EB",
    "orange":       "#F97316",
    "orange_dark":  "#EA580C",
    "green":        "#10B981",
    "green_dark":   "#059669",
    "red":          "#EF4444",
    "amber":        "#F59E0B",
    "purple":       "#8B5CF6",
}

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

  /* ── Global Surface & Background ─────────────────────────────────────── */
  html, body, [class*="css"], .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
      background-color: {COLORS['bg']} !important;
      color: {COLORS['text']} !important;
  }}
  .block-container {{
      padding-top: 1.2rem !important;
      padding-bottom: 2.5rem !important;
      max-width: 1460px !important;
  }}

  /* ── Streamlit Header & Sidebar Controls ────────────────────────────── */
  header[data-testid="stHeader"] {{
      background: transparent !important;
      visibility: visible !important;
      z-index: 99 !important;
  }}
  [data-testid="stToolbar"] {{
      visibility: hidden !important;
  }}
  /* Hide the native Streamlit collapse arrow on the sidebar edge */
  [data-testid="stSidebarCollapseButton"] {{
      display: none !important;
  }}

  /* ── Sidebar Styling ─────────────────────────────────────────────────── */
  [data-testid="stSidebar"] {{
      background-color: #0F172A !important;
      border-right: 1px solid #1E293B !important;
      min-width: 275px !important;
      max-width: 300px !important;
      transform: translateX(0) !important;
      visibility: visible !important;
  }}
  /* Force sidebar to stay expanded - override Streamlit's collapsed state */
  [data-testid="stSidebar"][aria-expanded="false"] {{
      transform: translateX(0) !important;
      margin-left: 0 !important;
      min-width: 275px !important;
  }}
  [data-testid="stSidebar"] .stButton > button {{
      width: 100% !important;
      text-align: left !important;
      background-color: transparent !important;
      border: 1px solid transparent !important;
      color: #94A3B8 !important;
      padding: 10px 14px !important;
      border-radius: 8px !important;
      font-size: 13.5px !important;
      font-weight: 500 !important;
      transition: all 0.15s ease !important;
      margin-bottom: 3px !important;
  }}
  [data-testid="stSidebar"] .stButton > button:hover {{
      background-color: rgba(59,130,246,0.1) !important;
      border-color: rgba(59,130,246,0.25) !important;
      color: #F8FAFC !important;
  }}
  [data-testid="stSidebar"] .stButton > button[kind="primary"] {{
      background: linear-gradient(135deg, #1E3A8A 0%, #1D4ED8 100%) !important;
      border: 1px solid #3B82F6 !important;
      color: #FFFFFF !important;
      font-weight: 600 !important;
      box-shadow: 0 2px 10px rgba(59, 130, 246, 0.3) !important;
  }}
  [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {{
      background: #2563EB !important;
      border-color: #60A5FA !important;
  }}


  /* ── KPI Metric Cards ─────────────────────────────────────────────────── */
  .kpi-row {{ display: flex; gap: 18px; margin-bottom: 24px; }}
  .kpi-card {{
      flex: 1;
      border-radius: 14px;
      padding: 20px 22px;
      display: flex; flex-direction: column;
      justify-content: space-between;
      min-height: 134px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
      position: relative; overflow: hidden;
  }}
  .kpi-card::before {{
      content: ''; position: absolute; top: 0; right: 0;
      width: 110px; height: 110px; border-radius: 50%;
      opacity: 0.08; transform: translate(30%, -30%);
  }}
  .kpi-blue   {{ background: linear-gradient(135deg, #1E3A5F 0%, #0F2744 100%); border: 1px solid rgba(59,130,246,0.25); }}
  .kpi-blue::before   {{ background: {COLORS['blue']}; }}
  .kpi-orange {{ background: linear-gradient(135deg, #3D2508 0%, #2A1A06 100%); border: 1px solid rgba(249,115,22,0.25); }}
  .kpi-orange::before {{ background: {COLORS['orange']}; }}
  .kpi-green  {{ background: linear-gradient(135deg, #0A2E1F 0%, #071F15 100%); border: 1px solid rgba(16,185,129,0.25); }}
  .kpi-green::before  {{ background: {COLORS['green']}; }}
  .kpi-dark   {{ background: {COLORS['surface']}; border: 1px solid {COLORS['border']}; }}
  .kpi-dark::before   {{ background: {COLORS['red']}; }}

  .kpi-icon {{ font-size: 18px; margin-bottom: 8px; }}
  .kpi-value {{ font-size: 28px; font-weight: 800; line-height: 1.1; margin-bottom: 2px; }}
  .kpi-label {{ font-size: 11px; color: {COLORS['muted']}; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
  .kpi-delta {{
      margin-top: 10px; font-size: 11px; font-weight: 600;
      padding: 3px 10px; border-radius: 10px; display: inline-block;
  }}
  .delta-up   {{ color: {COLORS['green']};  background: rgba(16,185,129,0.12); }}
  .delta-down {{ color: {COLORS['red']};    background: rgba(239,68,68,0.12); }}
  .delta-flat {{ color: {COLORS['amber']};  background: rgba(245,158,11,0.12); }}

  /* ── Panels & Cards ──────────────────────────────────────────────────── */
  .panel {{
      background-color: {COLORS['surface']};
      border-radius: 14px;
      border: 1px solid {COLORS['border']};
      padding: 22px 24px;
      margin-bottom: 22px;
  }}
  .panel-header {{
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 18px;
  }}
  .panel-title {{
      font-size: 15px; font-weight: 700; color: {COLORS['text']};
      text-transform: uppercase; letter-spacing: 0.5px;
      display: flex; align-items: center; gap: 8px;
  }}

  /* ── Badge Classes ───────────────────────────────────────────────────── */
  .badge {{
      display: inline-block; padding: 4px 10px; border-radius: 6px;
      font-size: 11px; font-weight: 700; letter-spacing: 0.3px;
  }}
  .badge-contradicted {{ background: rgba(16,185,129,0.15); color: {COLORS['green']}; border: 1px solid {COLORS['green']}; }}
  .badge-supports     {{ background: rgba(239,68,68,0.15); color: {COLORS['red']}; border: 1px solid {COLORS['red']}; }}
  .badge-silent       {{ background: rgba(245,158,11,0.15); color: {COLORS['amber']}; border: 1px solid {COLORS['amber']}; }}
  .badge-uncertain    {{ background: rgba(59,130,246,0.15); color: {COLORS['blue']}; border: 1px solid {COLORS['blue']}; }}
  .badge-duplicate    {{ background: rgba(139,92,246,0.15); color: {COLORS['purple']}; border: 1px solid {COLORS['purple']}; }}

  /* ── Callout Banner ──────────────────────────────────────────────────── */
  .problem-banner {{
      background: linear-gradient(135deg, rgba(30,58,95,0.4) 0%, rgba(18,24,36,0.8) 100%);
      border: 1px solid rgba(59,130,246,0.3);
      border-left: 5px solid {COLORS['blue']};
      border-radius: 12px;
      padding: 16px 20px;
      margin-bottom: 22px;
  }}
  .rule-banner {{
      background: rgba(245,158,11,0.08);
      border: 1px solid rgba(245,158,11,0.25);
      border-left: 5px solid {COLORS['amber']};
      border-radius: 10px;
      padding: 12px 16px;
      margin-bottom: 18px;
      font-size: 12.5px;
      color: #E5E7EB;
  }}

  /* ── Result Cards Grid ───────────────────────────────────────────────── */
  .result-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 18px; }}
  .result-card {{
      background-color: {COLORS['bg']}; border: 1px solid {COLORS['border']};
      border-radius: 10px; padding: 18px;
  }}
  .result-card-label {{ font-size: 11px; color: {COLORS['muted']}; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 6px; font-weight: 600; }}
  .result-card-value {{ font-size: 22px; font-weight: 800; line-height: 1.2; }}
  .result-card-sub   {{ font-size: 11px; color: {COLORS['muted']}; margin-top: 4px; }}

  /* ── Evidence Inspection Block ───────────────────────────────────────── */
  .evidence-block {{
      background-color: {COLORS['bg']}; border: 1px solid {COLORS['border']};
      border-radius: 10px; padding: 18px;
  }}
  .evidence-title {{ font-size: 13px; font-weight: 700; margin-bottom: 12px; }}
  .evidence-row {{ display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(31,41,55,0.4); font-size: 12.5px; }}
  .evidence-key {{ color: {COLORS['muted']}; }}
  .evidence-val {{ color: {COLORS['text']}; font-weight: 600; font-family: 'JetBrains Mono', monospace; }}

  /* ── Form Inputs ─────────────────────────────────────────────────────── */
  .stTextInput input, .stSelectbox > div > div, .stNumberInput > div > div > input {{
      background-color: {COLORS['bg']} !important;
      border: 1px solid {COLORS['border']} !important;
      border-radius: 8px !important;
      color: {COLORS['text']} !important;
      font-size: 13px !important;
  }}
  label {{ color: {COLORS['muted']} !important; font-size: 11px !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 0.5px !important; }}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 3. STATE INITIALIZATION & BUILDATHON REPOSITORY
# ══════════════════════════════════════════════════════════════════════════════
if "active_page" not in st.session_state:
    st.session_state.active_page = "Dashboard"
if "audit_result" not in st.session_state:
    st.session_state.audit_result = None
if "latest_audit" not in st.session_state:
    st.session_state.latest_audit = None
if "last_fee_amount" not in st.session_state:
    st.session_state.last_fee_amount = 0.0

# 1. Persistent Claims Ledger — Global Database for the Session
if 'claims_ledger' not in st.session_state:
    st.session_state.claims_ledger = pd.DataFrame(columns=['order_no', 'charge_type', 'amount', 'verdict', 'manager', 'timestamp'])

# Master Operational Evidence Database (Simulated data generated by other Managers)
OPERATIONAL_EVIDENCE_STORE = {
    # Scenario 1 Evidence
    "SHP-10291": {
        "shipment_id": "SHP-10291",
        "sku": "SKU-9281",
        "order_id": "ORD-44910",
        "source_manager": "Prep Manager",
        "record_id": "PRP-9281-OK",
        "packaging_check": "PASS",
        "fnsku_label_placement": "compliant",
        "captured": "Before shipment",
        "evidence_type": "3 inspection photographs + barcode laser scan",
        "photos_count": 3,
        "timestamp": "2024-03-05 09:14 UTC",
        "notes": "Unit verified polybagged, suffocation label verified, barcode scanned 100% compliant."
    },
    # Scenario 2 Evidence (Partial only)
    "SHP-10292": {
        "shipment_id": "SHP-10292",
        "sku": "SKU-7741",
        "order_id": "ORD-55012",
        "source_manager": "Receiving Manager",
        "record_id": "RCV-SCALE-PARTIAL",
        "packaging_check": "PASS",
        "fnsku_label_placement": "compliant",
        "captured": "Dock intake scale",
        "partial_evidence": True,
        "evidence_type": "Pallet gross weight record only (Unit tare weight missing)",
        "photos_count": 1,
        "timestamp": "2024-03-08 14:22 UTC",
        "notes": "Pallet weight captured as 450kg. Individual carton weigh-in was skipped due to scale maintenance."
    },
    # Scenario 4 Evidence (Shipment with multiple charges)
    "SHP-10294": {
        "shipment_id": "SHP-10294",
        "sku": "SKU-2094",
        "order_id": "ORD-88194",
        "source_manager": "Pack Manager",
        "record_id": "PCK-88194-CHK",
        "packaging_check": "FAIL",
        "fnsku_label_placement": "compliant",
        "captured": "Carton pack station",
        "evidence_type": "Automated carton conveyor scan & manual checklist",
        "photos_count": 2,
        "timestamp": "2024-03-11 11:05 UTC",
        "notes": "Barcode label placement verified COMPLIANT. However, polybag seal was noted DEFECTIVE/SKIPPED by operator."
    },
    # Scenario 5 Evidence (Receiving Manager Carrier Damage)
    "SHP-10295": {
        "shipment_id": "SHP-10295",
        "sku": "SKU-5502",
        "order_id": "ORD-99125",
        "source_manager": "Receiving Manager",
        "record_id": "RCV-BOL-5502",
        "packaging_check": "PASS",
        "fnsku_label_placement": "compliant",
        "captured": "Inbound intake dock",
        "evidence_type": "Bill of Lading Exception + 4 dock arrival photos",
        "photos_count": 4,
        "timestamp": "2024-03-12 08:30 UTC",
        "notes": "Carrier freight arrived with crushed outer pallet corners prior to FC intake. Driver signed BOL damage exception."
    },
    # Scenario 6 Evidence (Ambiguous)
    "SHP-10296": {
        "shipment_id": "SHP-10296",
        "sku": "SKU-6610",
        "order_id": "ORD-11029",
        "source_manager": "Prep Manager",
        "record_id": "PRP-AMBIG-6610",
        "packaging_check": "NOT_REQUIRED",
        "fnsku_label_placement": "not_required",
        "ambiguous": True,
        "captured": "Prep intake",
        "evidence_type": "Checklist marked exempt without aperture measurement",
        "photos_count": 0,
        "timestamp": "2024-03-14 16:00 UTC",
        "notes": "Operator logged 'bagging_exempt' based on vendor declaration; aperture width was not measured."
    },
}

# Pre-seeded official Buildathon Claims Ledger
if "claims_history" not in st.session_state:
    st.session_state.claims_history = [
        {"id": "#CLM-48291", "shipment": "SHP-10291", "sku": "SKU-9281", "type": "Packaging Defect", "amount": 38.00, "assessment": "CONTRADICTED", "decision": "CLAIM_APPROVED", "recoverable": 38.00, "status": "Approved", "evidence_source": "Prep Manager", "updated": "2h ago"},
        {"id": "#CLM-48292", "shipment": "SHP-10292", "sku": "SKU-7741", "type": "Weight Discrepancy", "amount": 45.00, "assessment": "SILENT", "decision": "NOT_SUPPORTED", "recoverable": 0.0, "status": "Denied", "evidence_source": "Receiving (Partial)", "updated": "4h ago"},
        {"id": "#CLM-48293", "shipment": "SHP-10293", "sku": "SKU-3319", "type": "Unplanned Prep Tape", "amount": 65.00, "assessment": "SILENT", "decision": "NOT_SUPPORTED", "recoverable": 0.0, "status": "Denied", "evidence_source": "None (Silent)", "updated": "6h ago"},
        {"id": "#CLM-48294A", "shipment": "SHP-10294", "sku": "SKU-2094", "type": "Inbound Defect Barcode", "amount": 25.00, "assessment": "CONTRADICTED", "decision": "CLAIM_APPROVED", "recoverable": 25.00, "status": "Approved", "evidence_source": "Pack Manager", "updated": "8h ago"},
        {"id": "#CLM-48294B", "shipment": "SHP-10294", "sku": "SKU-2094", "type": "Polybag Defect", "amount": 35.00, "assessment": "SUPPORTS", "decision": "NOT_SUPPORTED", "recoverable": 0.0, "status": "Denied", "evidence_source": "Pack Manager", "updated": "8h ago"},
        {"id": "#CLM-48295", "shipment": "SHP-10295", "sku": "SKU-5502", "type": "Carton Damaged FC", "amount": 120.00, "assessment": "CONTRADICTED", "decision": "CLAIM_APPROVED", "recoverable": 120.00, "status": "Approved", "evidence_source": "Receiving Manager", "updated": "1d ago"},
        {"id": "#CLM-48296", "shipment": "SHP-10296", "sku": "SKU-6610", "type": "Suffocation Warning", "amount": 55.00, "assessment": "UNCERTAIN", "decision": "NEEDS_MANUAL_REVIEW", "recoverable": 0.0, "status": "In Review", "evidence_source": "Prep (Ambiguous)", "updated": "1d ago"},
        {"id": "#CLM-48297", "shipment": "SHP-10291", "sku": "SKU-9281", "type": "Duplicate Packaging Fee", "amount": 38.00, "assessment": "DUPLICATE_CHARGE", "decision": "CLAIM_APPROVED", "recoverable": 38.00, "status": "Approved", "evidence_source": "Audit Ledger", "updated": "2d ago"},
    ]

# Default preloaded fee report records for Ingestion module
DEFAULT_FEE_REPORT = [
    {"charge_id": "48291", "shipment_id": "SHP-10291", "order_id": "ORD-44910", "sku": "SKU-9281", "charge_type": "packaging_defect", "reason": "Packaging defect", "amount": 38.00, "days_since_event": 21, "status": "Pending Audit"},
    {"charge_id": "48292", "shipment_id": "SHP-10292", "order_id": "ORD-55012", "sku": "SKU-7741", "charge_type": "weight_handling", "reason": "Weight handling discrepancy", "amount": 45.00, "days_since_event": 30, "status": "Pending Audit"},
    {"charge_id": "48293", "shipment_id": "SHP-10293", "order_id": "ORD-66190", "sku": "SKU-3319", "charge_type": "unplanned_prep", "reason": "Unplanned bubble wrap & tape", "amount": 65.00, "days_since_event": 14, "status": "Pending Audit"},
    {"charge_id": "48294A", "shipment_id": "SHP-10294", "order_id": "ORD-88194", "sku": "SKU-2094", "charge_type": "inbound_defect_barcode", "reason": "Barcode unscannable", "amount": 25.00, "days_since_event": 18, "status": "Pending Audit"},
    {"charge_id": "48294B", "shipment_id": "SHP-10294", "order_id": "ORD-88194", "sku": "SKU-2094", "charge_type": "missing_polybag", "reason": "Missing polybag / seal open", "amount": 35.00, "days_since_event": 18, "status": "Pending Audit"},
    {"charge_id": "48295", "shipment_id": "SHP-10295", "order_id": "ORD-99125", "sku": "SKU-5502", "charge_type": "item_damaged_in_warehouse", "reason": "Carton damaged at intake", "amount": 120.00, "days_since_event": 25, "status": "Pending Audit"},
    {"charge_id": "48296", "shipment_id": "SHP-10296", "order_id": "ORD-11029", "sku": "SKU-6610", "charge_type": "suffocation_warning", "reason": "Suffocation warning missing", "amount": 55.00, "days_since_event": 35, "status": "Pending Audit"},
    {"charge_id": "48297", "shipment_id": "SHP-10291", "order_id": "ORD-44910", "sku": "SKU-9281", "charge_type": "packaging_defect", "reason": "Packaging defect (Duplicate Cycle)", "amount": 38.00, "days_since_event": 42, "is_duplicate": True, "status": "Pending Audit"},
    {"charge_id": "48298", "shipment_id": "SHP-10298", "order_id": "ORD-77180", "sku": "SKU-8820", "charge_type": "lost_in_transit", "reason": "Inbound inventory adjustment", "amount": 75.00, "days_since_event": 10, "already_reimbursed": True, "reimbursement_id": "REMB-8820-SETTLED", "status": "Pending Audit"},
]

if "parsed_charges" not in st.session_state:
    st.session_state.parsed_charges = DEFAULT_FEE_REPORT

def compute_kpis():
    df = st.session_state.get('claims_ledger', pd.DataFrame(columns=['order_no', 'charge_type', 'amount', 'verdict', 'manager', 'timestamp']))
    if df.empty or 'verdict' not in df.columns or 'amount' not in df.columns:
        return {
            "open": 0,
            "in_review": 0,
            "recovered": 0.0,
            "flags": 0,
            "approved": 0,
            "denied": 0,
        }
    amounts = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
    verdicts = df['verdict'].astype(str)

    total_claims = len(df)
    # Sum amount where verdict == 'CONTRADICTED' (and duplicate charges if applicable)
    recovered_amount = float(amounts[verdicts == 'CONTRADICTED'].sum())
    # Count rows where verdict == 'SILENT'
    silent_flags = int((verdicts == 'SILENT').sum())
    in_review_count = int(verdicts.isin(['SILENT', 'UNCERTAIN']).sum())
    approved_count = int((verdicts == 'CONTRADICTED').sum())
    denied_count = int(verdicts.isin(['SUPPORTS', 'ALREADY_REIMBURSED']).sum())
    return {
        "open": total_claims,
        "in_review": in_review_count,
        "recovered": recovered_amount,
        "flags": silent_flags,
        "approved": approved_count,
        "denied": denied_count,
    }

# ══════════════════════════════════════════════════════════════════════════════
# 4. SIDEBAR NAVIGATION
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="padding: 10px 0 20px 0;">
        <div style="font-size: 24px; font-weight: 800; color: #3B82F6; letter-spacing: -0.5px; line-height: 1.1;">Trident<span style="color: #F97316;"> Recovery</span></div>
        <div style="font-size: 11px; color: #94A3B8; margin-top: 4px; font-weight: 600; letter-spacing: 0.8px;">AI RECOVERY MANAGER</div>
        <div style="font-size: 10px; color: #10B981; font-weight: 700; margin-top: 4px;">● AGENT ACTIVE</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Pipeline section label ──────────────────────────────────────────────
    st.markdown(f"<div style='font-size: 10px; color: {COLORS['muted']}; text-transform: uppercase; letter-spacing: 1px; padding: 4px 0 8px 6px; font-weight: 700;'>RECOVERY PIPELINE</div>", unsafe_allow_html=True)

    # Only the 5 steps that match the challenge brief pipeline:
    # 1. Dashboard  2. Ingest  3. AI Auditor  4. Evidence Hub  5. Claims Ledger
    sidebar_items = [
        ("📊", "Dashboard",       "Dashboard",            None),
        ("📥", "Ingest Reports",  "Ingest & Parse Reports", str(len(st.session_state.parsed_charges))),
        ("⚡", "AI Auditor",      "AI Recovery Auditor",  "Live"),
        ("📂", "Evidence Hub",    "Evidence Hub",         "5"),
        ("📋", "Claims Ledger",   "Claims Ledger",        str(len(st.session_state.claims_ledger))),
    ]

    for icon, label, page_key, badge in sidebar_items:
        is_active = st.session_state.active_page == page_key
        badge_text = f"  [{badge}]" if badge else ""
        btn_label = f"{icon}  {label}{badge_text}"
        if st.button(btn_label, key=f"side_nav_{page_key}", use_container_width=True, type="primary" if is_active else "secondary"):
            st.session_state.active_page = page_key
            st.rerun()


    # ── User footer ─────────────────────────────────────────────────────────
    st.markdown("""
    <div style="margin-top: 32px; padding: 12px; background: rgba(18,24,36,0.75); border: 1px solid #1E293B; border-radius: 10px; display: flex; align-items: center; gap: 10px;">
        <div style="width: 34px; height: 34px; border-radius: 50%; background: linear-gradient(135deg,#1E3A8A,#3B82F6); color: white; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px;">TR</div>
        <div>
            <div style="font-size: 12px; font-weight: 700; color: #F8FAFC;">Trident Specialist</div>
            <div style="font-size: 10px; color: #94A3B8;">Recovery Manager Agent</div>
        </div>
    </div>
    <div style="margin-top: 10px; font-size: 10px; color: #64748B; padding-left: 4px;">
        Cube Buildathon · Track 05
    </div>
    """, unsafe_allow_html=True)



# ══════════════════════════════════════════════════════════════════════════════
# 5. INITIALIZE ENGINE (HYBRID AUTH)
# ══════════════════════════════════════════════════════════════════════════════
api_key = env_api_key
if not api_key:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(f"<div class='panel-title'>🔑 Gemini API Key Authentication</div>", unsafe_allow_html=True)
    api_key = st.text_input("Enter Gemini API Key (or set in submissions/vishruth-16/.env)", type="password")
    st.markdown('</div>', unsafe_allow_html=True)
    if not api_key:
        st.stop()

engine = RecoveryAuditEngine(api_key=api_key)

# ══════════════════════════════════════════════════════════════════════════════
# 6. TOP HEADER BAR
# ══════════════════════════════════════════════════════════════════════════════
kpis = compute_kpis()

# Sidebar toggle button (CSS + HTML only — no <script> in st.markdown to avoid text leakage)
st.markdown("""
<style>
/* Permanent sidebar toggle button - always visible top-left */
#trident-sidebar-toggle {
    position: fixed;
    top: 12px;
    left: 12px;
    z-index: 2147483647;
    background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%);
    color: #fff;
    border: 2px solid #60A5FA;
    border-radius: 9px;
    padding: 8px 14px 8px 10px;
    font-size: 15px;
    font-family: Inter, sans-serif;
    font-weight: 700;
    cursor: pointer;
    box-shadow: 0 0 20px rgba(59,130,246,0.7), 0 2px 8px rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    gap: 7px;
    letter-spacing: 0.3px;
    transition: background 0.15s, box-shadow 0.15s;
    user-select: none;
}
#trident-sidebar-toggle:hover {
    background: #3B82F6;
    box-shadow: 0 0 28px rgba(59,130,246,0.9);
    border-color: #93C5FD;
}
#trident-sidebar-toggle .toggle-label {
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
    opacity: 0.92;
}
</style>
<button id="trident-sidebar-toggle" onclick="tridentToggleSidebar()" title="Toggle navigation sidebar">
  <span style="font-size:18px; line-height:1;">☰</span>
  <span class="toggle-label">MENU</span>
</button>
""", unsafe_allow_html=True)

# Inject sidebar JS via components.html so <script> executes properly
# without Streamlit leaking its text content onto the page
import streamlit.components.v1 as components
components.html("""
<script>
(function() {
    const EXPAND_SELECTORS = [
        '[data-testid="collapsedControl"]',
        '[data-testid="stSidebarCollapsedControl"]',
        '[data-testid="stSidebarCollapseButton"]',
        'button[aria-label="Expand sidebar"]',
        'button[aria-label="Open sidebar"]',
        'button[aria-label="open sidebar"]',
        'section[data-testid="stSidebar"] + div button',
    ];
    function findSidebarToggle() {
        for (const sel of EXPAND_SELECTORS) {
            try { const el = window.parent.document.querySelector(sel); if (el) return el; } catch(e) {}
        }
        return null;
    }
    function isSidebarOpen() {
        const sb = window.parent.document.querySelector('[data-testid="stSidebar"]');
        if (!sb) return false;
        return sb.getBoundingClientRect().width > 100;
    }
    window.parent.tridentToggleSidebar = function() {
        const toggle = findSidebarToggle();
        if (toggle) { toggle.click(); return; }
        const sb = window.parent.document.querySelector('[data-testid="stSidebar"]');
        if (sb) {
            const isOpen = isSidebarOpen();
            sb.style.transform = isOpen ? 'translateX(-100%)' : 'translateX(0)';
            sb.style.minWidth = isOpen ? '0' : '275px';
        }
    };
    let attempts = 0;
    const expandTimer = setInterval(function() {
        attempts++;
        if (!isSidebarOpen()) { const t = findSidebarToggle(); if (t) t.click(); }
        if (isSidebarOpen() || attempts > 20) clearInterval(expandTimer);
    }, 300);
})();
</script>
""", height=0, scrolling=False)



_, head_right = st.columns([2, 1])
with head_right:
    btn_cols = st.columns([1, 1, 1])
    with btn_cols[0]:
        time_filter = st.selectbox("Period", ["Last 30 Days", "Last 7 Days", "Last 90 Days", "All Time"], label_visibility="collapsed")
    with btn_cols[1]:
        df_export = st.session_state.claims_ledger.copy()
        csv_buf = io.StringIO()
        df_export.to_csv(csv_buf, index=False)
        st.download_button("📊 Export CSV", csv_buf.getvalue(), file_name=f"trident_recovery_audit_report_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)
    with btn_cols[2]:
        if st.button("➕ New Audit", use_container_width=True, type="primary"):
            st.session_state.active_page = "AI Recovery Auditor"
            st.rerun()


# Breadcrumb on subpages (back button removed per user request)
if st.session_state.active_page != "Dashboard":
    st.write("")
    st.markdown(f"<div style='font-size: 13.5px; font-weight: 600; color: {COLORS['muted']}; padding-top: 4px; padding-bottom: 6px;'>Dashboard  /  <span style='color: {COLORS['blue']}; font-weight: 700;'>{st.session_state.active_page}</span></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 7. PAGE ROUTING
# ══════════════════════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────────────────────────────
# MODULE 1: DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────
if st.session_state.active_page == "Dashboard":

    # Problem Statement & Buildathon Mission Banner
    st.markdown("""
    <div class="problem-banner">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <div style="font-size: 14px; font-weight: 800; color: #60A5FA; letter-spacing: 0.5px; text-transform: uppercase;">
                    🎯 Problem Solved: Late Amazon FBA Fee Reconciliation
                </div>
                <div style="font-size: 12.5px; color: #D1D5DB; margin-top: 6px; line-height: 1.6;">
                    Sellers receive fee charges weeks after shipment events when evidence is lost. <b>Trident Recovery</b> automates end-to-end reconciliation: parsing fee & reimbursement reports, matching charges against upstream operational evidence from <b>Prep, Receiving, Pack, and Returns Managers</b>, and conservatively producing defensible disputes.
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Top KPI Row (Driven dynamically from st.session_state.claims_ledger)
    st.markdown(f"""
    <div class="kpi-row">
        <div class="kpi-card kpi-blue">
            <div>
                <div class="kpi-icon">📋</div>
                <div class="kpi-value">{kpis['open']:,}</div>
                <div class="kpi-label">Total Audited Claims</div>
            </div>
            <div><span class="kpi-delta delta-up">↗ +{kpis['in_review']} pending review</span></div>
        </div>
        <div class="kpi-card kpi-orange">
            <div>
                <div class="kpi-icon">⏱️</div>
                <div class="kpi-value">12.3 <span style="font-size:14px; font-weight:500;">days</span></div>
                <div class="kpi-label">Avg. Resolution Window</div>
            </div>
            <div><span class="kpi-delta delta-up">↘ −1.2d improvement</span></div>
        </div>
        <div class="kpi-card kpi-green">
            <div>
                <div class="kpi-icon">💰</div>
                <div class="kpi-value">${kpis['recovered']:,.2f}</div>
                <div class="kpi-label">Recovered Payouts</div>
            </div>
            <div><span class="kpi-delta delta-up">↗ +100% defensible</span></div>
        </div>
        <div class="kpi-card kpi-dark">
            <div>
                <div class="kpi-icon">⚠️</div>
                <div class="kpi-value">{kpis['flags']}</div>
                <div class="kpi-label">Silent / Uncertain Flags</div>
            </div>
            <div><span class="kpi-delta delta-flat">● {kpis['flags']} conservative guards</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Quick Workflow Action Bar
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">🚀 Recovery Manager Core Pipeline</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-top: 10px; text-align: center;">
        <div style="background: {COLORS['bg']}; padding: 14px; border-radius: 8px; border: 1px solid {COLORS['border']};">
            <div style="font-size: 20px;">📥</div>
            <div style="font-size: 12px; font-weight: 700; margin-top: 6px; color: {COLORS['text']};">1. Ingest Reports</div>
            <div style="font-size: 10.5px; color: {COLORS['muted']}; margin-top: 2px;">Fee & Reimbursements</div>
        </div>
        <div style="background: {COLORS['bg']}; padding: 14px; border-radius: 8px; border: 1px solid {COLORS['border']};">
            <div style="font-size: 20px;">🔍</div>
            <div style="font-size: 12px; font-weight: 700; margin-top: 6px; color: {COLORS['text']};">2. Parse Charges</div>
            <div style="font-size: 10.5px; color: {COLORS['muted']}; margin-top: 2px;">Shipment / SKU / Order</div>
        </div>
        <div style="background: {COLORS['bg']}; padding: 14px; border-radius: 8px; border: 1px solid {COLORS['border']};">
            <div style="font-size: 20px;">📂</div>
            <div style="font-size: 12px; font-weight: 700; margin-top: 6px; color: {COLORS['text']};">3. Retrieve Evidence</div>
            <div style="font-size: 10.5px; color: {COLORS['muted']}; margin-top: 2px;">Prep, Receiving, Pack</div>
        </div>
        <div style="background: {COLORS['bg']}; padding: 14px; border-radius: 8px; border: 1px solid {COLORS['border']};">
            <div style="font-size: 20px;">⚖️</div>
            <div style="font-size: 12px; font-weight: 700; margin-top: 6px; color: {COLORS['text']};">4. Match & Classify</div>
            <div style="font-size: 10.5px; color: {COLORS['muted']}; margin-top: 2px;">Contradict / Support / Silent</div>
        </div>
        <div style="background: {COLORS['bg']}; padding: 14px; border-radius: 8px; border: 1px solid {COLORS['border']};">
            <div style="font-size: 20px;">🛡️</div>
            <div style="font-size: 12px; font-weight: 700; margin-top: 6px; color: {COLORS['text']};">5. Assemble Claim</div>
            <div style="font-size: 10.5px; color: {COLORS['muted']}; margin-top: 2px;">SHA-256 Sealed Dispute</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Dynamic Plotly Visuals
    c1, c2, c3 = st.columns(3, gap="medium")
    plotly_layout_base = dict(
        paper_bgcolor=COLORS['surface'],
        plot_bgcolor=COLORS['bg'],
        font=dict(family="Inter", color=COLORS['muted'], size=11),
        margin=dict(l=35, r=20, t=35, b=35),
        height=260,
    )

    df_ledger = st.session_state.claims_ledger

    with c1:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">Claims Ingestion Velocity</div>', unsafe_allow_html=True)
        if not df_ledger.empty and 'timestamp' in df_ledger.columns:
            df_time = df_ledger.copy()
            df_time['date'] = pd.to_datetime(df_time['timestamp'], errors='coerce').dt.strftime('%m/%d %H:%M')
            df_time = df_time.dropna(subset=['date'])
            if not df_time.empty:
                daily_counts = df_time.groupby('date', sort=False).size().reset_index(name='count')
                daily_counts['cumulative'] = daily_counts['count'].cumsum()
                days = daily_counts['date'].tolist()
                vol = daily_counts['cumulative'].tolist()
            else:
                days = [datetime.now().strftime('%m/%d %H:%M')]
                vol = [len(df_ledger)]
        else:
            days = [(datetime.now() - timedelta(days=i)).strftime('%m/%d') for i in range(7, -1, -1)]
            vol = [0] * len(days)

        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(
            x=days, y=vol, mode='lines+markers' if len(days) <= 5 else 'lines',
            line=dict(color=COLORS['blue'], width=2.5, shape='spline'),
            fill='tozeroy', fillcolor='rgba(59,130,246,0.08)',
        ))
        fig1.update_layout(**plotly_layout_base, title=None, showlegend=False,
                           xaxis=dict(gridcolor="rgba(31,41,55,0.4)"), yaxis=dict(gridcolor="rgba(31,41,55,0.4)"))
        st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">Disputed Amount by Manager</div>', unsafe_allow_html=True)
        if not df_ledger.empty and 'manager' in df_ledger.columns and 'amount' in df_ledger.columns:
            df_chart = df_ledger.copy()
            df_chart['amount'] = pd.to_numeric(df_chart['amount'], errors='coerce').fillna(0.0)
            df_chart['mgr_clean'] = df_chart['manager'].astype(str).apply(
                lambda m: m.replace(" (Silent — no evidence)", "").replace(" Manager", "").strip() or "No Records"
            )
            mgr_grouped = df_chart.groupby('mgr_clean', sort=False)['amount'].sum().reset_index()
            mgr_x = mgr_grouped['mgr_clean'].tolist()
            mgr_y = mgr_grouped['amount'].tolist()
        else:
            mgr_x = ["Prep", "Pack", "Receiving", "Returns", "3PL"]
            mgr_y = [0.0, 0.0, 0.0, 0.0, 0.0]

        bar_colors = [COLORS['orange'], "#FB923C", "#FDBA74", "#FED7AA", "#F3F4F6", "#60A5FA", "#A78BFA"]
        fig2 = go.Figure(go.Bar(
            x=mgr_x,
            y=mgr_y,
            marker=dict(color=bar_colors[:len(mgr_x)] if len(mgr_x) <= len(bar_colors) else COLORS['orange'], cornerradius=6),
        ))
        fig2.update_layout(**plotly_layout_base, title=None, showlegend=False,
                           xaxis=dict(gridcolor="rgba(31,41,55,0.4)"), yaxis=dict(gridcolor="rgba(31,41,55,0.4)"))
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">Tri-State Assessment Ratio</div>', unsafe_allow_html=True)
        if not df_ledger.empty and 'verdict' in df_ledger.columns and len(df_ledger) > 0:
            counts = df_ledger['verdict'].value_counts().to_dict()
            labels = list(counts.keys())
            values = list(counts.values())
            color_lookup = {
                "CONTRADICTED": COLORS['green'],
                "SUPPORTS": COLORS['red'],
                "SILENT": COLORS['amber'],
                "UNCERTAIN": COLORS['blue'],
                "DUPLICATE_CHARGE": COLORS['purple'],
                "ALREADY_REIMBURSED": COLORS['blue'],
            }
            fig3 = go.Figure(go.Pie(
                labels=labels, values=values, hole=0.6,
                marker=dict(colors=[color_lookup.get(k, COLORS['blue']) for k in labels]),
                textinfo='percent', textfont=dict(size=11, color=COLORS['text'])
            ))
        else:
            fig3 = go.Figure(go.Pie(
                labels=["No Audits Recorded"], values=[1], hole=0.6,
                marker=dict(colors=["#1E293B"]),
                textinfo='none', hoverinfo='none'
            ))
            fig3.add_annotation(
                text="No Audits", showarrow=False,
                font=dict(size=12, color=COLORS['muted'], family="Inter")
            )
        fig3.update_layout(**plotly_layout_base, title=None, showlegend=True,
                           legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5, font=dict(size=10)))
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    # Dynamic Real-Time Claims Ledger Table
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">📋 Real-Time Claims Ledger (Session Database)</div>', unsafe_allow_html=True)
    if not df_ledger.empty:
        df_recent = df_ledger.copy()
        if 'amount' in df_recent.columns:
            df_recent['amount'] = pd.to_numeric(df_recent['amount'], errors='coerce').fillna(0.0).apply(lambda x: f"${x:,.2f}")
        col_rename = {
            "order_no": "Order No",
            "charge_type": "Charge Type",
            "amount": "Disputed Fee ($)",
            "verdict": "Tri-State Verdict",
            "manager": "Evidence Source Manager",
            "timestamp": "Audit Timestamp"
        }
        df_recent_display = df_recent.rename(columns=col_rename)
        # Show most recent first
        st.dataframe(df_recent_display.iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("No claim audits recorded in session ledger yet. Navigate to '⚡ AI Auditor' to evaluate fee charges.")
    st.markdown('</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# MODULE 2: INGEST & PARSE REPORTS
# ──────────────────────────────────────────────────────────────────────────────
elif st.session_state.active_page == "Ingest & Parse Reports":
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">📥 Fee & Reimbursement Report Ingestion</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="font-size: 13px; color: {COLORS['muted']}; margin-bottom: 16px;">
        Upload raw Amazon FBA Fee Reports, Settlement Reports, or Reimbursement CSVs. Trident Recovery automatically extracts individual charges, associates them with shipment identifiers, order identifiers, and SKU/ASINs, and identifies duplicate billings.
    </div>
    """, unsafe_allow_html=True)

    up_col1, up_col2 = st.columns([1.5, 1], gap="large")
    with up_col1:
        uploaded_file = st.file_uploader("Upload Fee / Reimbursement Report (CSV or JSON)", type=["csv", "json"])
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df_up = pd.read_csv(uploaded_file)
                    st.session_state.parsed_charges = df_up.to_dict(orient="records")
                    st.success(f"Successfully ingested and parsed {len(df_up)} charge records from {uploaded_file.name}!")
                elif uploaded_file.name.endswith(".json"):
                    data_json = json.load(uploaded_file)
                    st.session_state.parsed_charges = data_json if isinstance(data_json, list) else [data_json]
                    st.success(f"Successfully ingested JSON report with {len(st.session_state.parsed_charges)} records!")
            except Exception as e:
                st.error(f"Error parsing uploaded file: {str(e)}")

    with up_col2:
        st.markdown(f"<div style='font-size: 13px; font-weight: 700; color: {COLORS['blue']}; margin-bottom: 8px;'>QUICK LOAD BENCHMARK DATA</div>", unsafe_allow_html=True)
        if st.button("📁 Load Official Buildathon Fee Report (8 Charges)", use_container_width=True):
            st.session_state.parsed_charges = DEFAULT_FEE_REPORT
            st.success("Loaded 8 multi-scenario charges including duplicate & reimbursement tests!")

        if st.button("🔄 Reset Parsed Table to Defaults", use_container_width=True):
            st.session_state.parsed_charges = DEFAULT_FEE_REPORT
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # Parsed Charges View
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="panel-header">
        <div class="panel-title">🔍 Parsed Individual Charges ({len(st.session_state.parsed_charges)} Found)</div>
        <span class="badge" style="background: rgba(16,185,129,0.15); color: {COLORS['green']}; border: 1px solid {COLORS['green']};">Structured Records Active</span>
    </div>
    """, unsafe_allow_html=True)

    df_parsed = pd.DataFrame(st.session_state.parsed_charges)
    st.dataframe(df_parsed, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown(f"<div style='font-size: 13px; font-weight: 700; margin-bottom: 10px; color: {COLORS['text']};'>⚡ Batch Operations</div>", unsafe_allow_html=True)
    batch_btn_col1, batch_btn_col2 = st.columns([1, 1])
    with batch_btn_col1:
        if st.button("⚡ Run AI Evidence Matcher on All Parsed Charges", type="primary", use_container_width=True):
            with st.spinner("Batch-matching charges against Prep, Receiving, Pack, and Returns evidence..."):
                new_records = []
                for row in st.session_state.parsed_charges:
                    ship_id = row.get("shipment_id", "")
                    ev_match = OPERATIONAL_EVIDENCE_STORE.get(ship_id)
                    ev_list = [ev_match] if ev_match else []
                    
                    audit_res = engine.audit_charge(
                        org_id="org_demo_alpha",
                        fee_row=row,
                        evidence_records=ev_list
                    )
                    outcome = audit_res.outcome
                    new_records.append({
                        "id": f"#CLM-{row.get('charge_id', uuid.uuid4().hex[:6])}",
                        "shipment": ship_id,
                        "sku": row.get("sku", "N/A"),
                        "type": str(row.get("reason", row.get("charge_type", "Fee"))).title(),
                        "amount": float(row.get("amount", row.get("amount_usd", 0.0))),
                        "assessment": outcome.get("assessment", "SILENT"),
                        "decision": outcome.get("decision", "NEEDS_MANUAL_REVIEW"),
                        "recoverable": outcome.get("recoverable_amount", 0.0),
                        "status": "Approved" if outcome.get("decision") == "CLAIM_APPROVED" else ("Denied" if outcome.get("decision") == "NOT_SUPPORTED" else "In Review"),
                        "evidence_source": ev_match.get("source_manager", "None (Silent)") if ev_match else "None (Silent)",
                        "updated": "just now",
                    })

                # Append batch claims to persistent claims_ledger
                batch_ledger_rows = []
                for nr in new_records:
                    batch_ledger_rows.append({
                        "order_no": nr.get("shipment", "ORD-N/A"),
                        "charge_type": nr.get("type", "Fee"),
                        "amount": float(nr.get("amount", 0.0)),
                        "verdict": nr.get("assessment", "SILENT"),
                        "manager": nr.get("evidence_source", "None (Silent)"),
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                if batch_ledger_rows:
                    st.session_state.claims_ledger = pd.concat([
                        st.session_state.claims_ledger,
                        pd.DataFrame(batch_ledger_rows)
                    ], ignore_index=True)

                st.session_state.claims_history = new_records
                st.success(f"Batch audit completed! Processed {len(new_records)} charges with full evidence cross-matching.")
                st.rerun()

    with batch_btn_col2:
        csv_parsed = df_parsed.to_csv(index=False)
        st.download_button("⬇️ Download Parsed Charges CSV", csv_parsed, file_name="parsed_fba_charges.csv", mime="text/csv", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# MODULE 3: AI RECOVERY AUDITOR — STRICT EVIDENCE-BASED REASONING
# No vision. No camera. No invented evidence.
# ──────────────────────────────────────────────────────────────────────────────
elif st.session_state.active_page == "AI Recovery Auditor":

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">⚡ AI Recovery Auditor</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="font-size: 13px; color: {COLORS['muted']}; margin-bottom: 6px;">
        Evaluate individual FBA fee charges against structured upstream operational evidence.<br>
        All four fields below are <b>required</b> to prevent the agent assuming default evidence.
        Tri-state output: <b style="color:#10B981;">CONTRADICTED</b> · <b style="color:#EF4444;">SUPPORTS</b> · <b style="color:#F59E0B;">SILENT</b>
    </div>
    <div class="rule-banner">
        📏 <b>Authoritative Rules:</b> 60-day FBA filing window enforced · No evidence invented ·
        SILENT is a valid and successful evaluation · Tenancy isolation enforced
    </div>
    """, unsafe_allow_html=True)

    # ── SECTION ①: Charge Identification ─────────────────────────────────────
    st.markdown(f"<div style='font-size: 13px; font-weight: 700; color: {COLORS['blue']}; margin: 14px 0 10px;'>① CHARGE IDENTIFICATION</div>", unsafe_allow_html=True)
    id_col1, id_col2, id_col3, id_col4, id_col5 = st.columns(5)
    with id_col1:
        fee_order_id  = st.text_input("Order No.", value="ORD-44910", help="Amazon Order ID associated with this charge")
    with id_col2:
        fee_sku       = st.text_input("SKU / ASIN", value="SKU-9281", help="Product SKU or ASIN")
    with id_col3:
        fee_shipment_id = st.text_input("Shipment ID", value="SHP-10291", help="FBA Inbound Shipment ID")
    with id_col4:
        fee_charge_id = st.text_input("Charge ID", value="48291", help="Unique fee line item ID from report")
    with id_col5:
        fee_org_id = st.text_input("Fee Org ID", value="org_demo_alpha", help="Organization ID for tenancy isolation (Engineering Rule 1). Change to 'org_demo_bravo' to test cross-tenant block.")

    # ── SECTION ②: Charge Type (mandatory dropdown — no free text) ───────────
    st.markdown(f"<div style='font-size: 13px; font-weight: 700; color: {COLORS['blue']}; margin: 14px 0 10px;'>② CHARGE TYPE</div>", unsafe_allow_html=True)
    ct_col, amt_col, days_col = st.columns([2, 1, 1])
    with ct_col:
        fee_charge_type = st.selectbox(
            "Charge Type",
            options=[
                "inbound_defect_unbagged",
                "inbound_defect_barcode",
                "fulfilment_fee_weight_tier",
                "packaging_defect",
                "missing_polybag",
                "weight_handling",
                "oversize_item",
                "unplanned_prep",
                "label_missing",
                "bubble_wrap_required",
                "taping_required",
                "suffocation_warning",
                "item_damaged_in_warehouse",
                "lost_in_transit",
            ],
            help="Select the exact FBA fee category from the fee report",
        )
    with amt_col:
        fee_amount = st.number_input("Charge Amount (USD)", min_value=0.0, value=38.0, step=5.0)
    with days_col:
        ev_days = st.number_input(
            "Days Since Event",
            min_value=0, max_value=120, value=21, step=1,
            help="Days elapsed since the originating shipment event. Claims > 60 days are time-barred."
        )

    # ── SECTION ③: Source Manager (explicit — agent does NOT assume) ──────────
    st.markdown(f"<div style='font-size: 13px; font-weight: 700; color: {COLORS['green']}; margin: 14px 0 10px;'>③ EVIDENCE SOURCE MANAGER</div>", unsafe_allow_html=True)
    src_col, rec_col, ev_org_col = st.columns(3)
    with src_col:
        ev_manager = st.selectbox(
            "Source Manager",
            options=[
                "No Records Available (Silent — no evidence)",
                "Prep Manager",
                "Receiving Manager",
                "Pack Manager",
                "Returns Manager",
                "3PL / Warehouse Storage",
            ],
            help=(
                "Select the upstream manager that holds the primary evidence for this charge. "
                "If no records exist, select 'No Records Available' — the agent will output SILENT."
            ),
        )
    with rec_col:
        ev_record_id = st.text_input(
            "Evidence Record ID",
            value="PRP-9281-OK",
            help="Record ID from the source manager's operational log",
            disabled=(ev_manager == "No Records Available (Silent — no evidence)"),
        )
    with ev_org_col:
        evidence_org_id = st.text_input(
            "Evidence Org ID",
            value="org_demo_alpha",
            help="Organization ID on the evidence record. Set to 'org_demo_bravo' to test tenancy isolation breach.",
            disabled=(ev_manager == "No Records Available (Silent — no evidence)"),
        )

    # ── SECTION ④: Compliance Check (mandatory dropdown) ─────────────────────
    st.markdown(f"<div style='font-size: 13px; font-weight: 700; color: {COLORS['amber']}; margin: 14px 0 10px;'>④ COMPLIANCE CHECK RESULT</div>", unsafe_allow_html=True)
    cc_col, rule_col, photos_col = st.columns(3)
    with cc_col:
        ev_label_check = st.selectbox(
            "Compliance Check Status",
            options=[
                "PASS — Unit compliant, full records",
                "FAIL — Unit non-compliant, defect confirmed",
                "PARTIAL — Gross record only, unit-level data missing",
                "EXEMPT / NOT_REQUIRED — No measurement taken (ambiguous)",
                "MISSING / NO RECORD",
            ],
            help="What the source manager's operational record shows for this compliance attribute",
            disabled=(ev_manager == "No Records Available (Silent — no evidence)"),
        )
    with rule_col:
        compliance_rule = st.selectbox(
            "Compliance Rule Being Evaluated",
            options=[
                "polybag_present_sealed",
                "fnsku_label_placement",
                "barcode_scan_pass",
                "unit_weight_recorded",
                "tare_weight_captured",
                "packaging_check_pass",
                "suffocation_label_present",
                "polybag_aperture_measured",
                "bol_exception_documented",
                "prep_instructions_followed",
                "carton_sealed_compliant",
                "unit_dimensions_recorded",
                "inbound_reconciliation_complete",
            ],
            help="The specific FBA compliance attribute this charge is disputing",
        )
    with photos_col:
        ev_photos = st.slider(
            "Supporting Evidence Count (photos/scans)",
            min_value=0, max_value=10, value=3,
            help="Number of photographs, scan records, or documents attached",
            disabled=(ev_manager == "No Records Available (Silent — no evidence)"),
        )

    st.write("")
    run_audit = st.button("⚡ Execute Recovery Audit", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if run_audit:
        with st.spinner("Gemini 2.0 Flash is auditing charge against evidence contracts..."):
            fee_data = {
                "charge_id":      fee_charge_id,
                "org_id":         fee_org_id,
                "shipment_id":    fee_shipment_id,
                "order_id":       fee_order_id,
                "sku":            fee_sku,
                "charge_type":    fee_charge_type,
                "amount_usd":     float(fee_amount),
                "days_since_event": int(ev_days),
            }

            silent = (
                ev_manager == "No Records Available (Silent — no evidence)"
                or "MISSING" in ev_label_check
            )

            if silent:
                evidence_list = []
            else:
                compliance_map = {
                    "PASS — Unit compliant, full records":                    ("PASS",          "compliant"),
                    "FAIL — Unit non-compliant, defect confirmed":            ("FAIL",          "non_compliant"),
                    "PARTIAL — Gross record only, unit-level data missing":   ("PARTIAL",       "partially_compliant"),
                    "EXEMPT / NOT_REQUIRED — No measurement taken (ambiguous)":("NOT_REQUIRED", "not_required"),
                }
                pkg_chk, label_st = compliance_map.get(ev_label_check, ("UNKNOWN", "unknown"))
                evidence_list = [{
                    "record_id":              ev_record_id,
                    "org_id":                 evidence_org_id,
                    "source_manager":         ev_manager,
                    "compliance_rule":        compliance_rule,
                    "compliance_status":      ev_label_check,
                    "packaging_check":        pkg_chk,
                    "fnsku_label_placement":  label_st,
                    "supporting_evidence_count": ev_photos,
                    "photos_count":           ev_photos,
                    "timestamp":              datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
                    "ambiguous":              "EXEMPT" in ev_label_check or "NOT_REQUIRED" in ev_label_check,
                    "partial_evidence":       "PARTIAL" in ev_label_check,
                }]

            result = engine.audit_charge(
                org_id=fee_org_id,
                fee_row=fee_data,
                evidence_records=evidence_list,
                compliance_rule=compliance_rule,
            )
            st.session_state.audit_result = result
            st.session_state.latest_audit = result
            st.session_state.last_fee_amount = fee_amount
            st.session_state.last_charge_id  = fee_charge_id

            # ── 2. Append Data to Persistent Claims Ledger on Audit Execution ──
            outcome = result.outcome
            a = outcome.get("assessment", "SILENT")
            d = outcome.get("decision",   "NEEDS_MANUAL_REVIEW")

            new_claim_row = pd.DataFrame([{
                "order_no":    fee_order_id,
                "charge_type": fee_charge_type,
                "amount":      float(fee_amount),
                "verdict":     a,
                "manager":     ev_manager,
                "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }])
            st.session_state.claims_ledger = pd.concat([st.session_state.claims_ledger, new_claim_row], ignore_index=True)

            # Also maintain claims_history for backward compatibility
            new_claim = {
                "id":             f"#CLM-{fee_charge_id}",
                "shipment":       fee_shipment_id,
                "sku":            fee_sku,
                "type":           fee_charge_type.replace("_", " ").title(),
                "amount":         float(fee_amount),
                "assessment":     a,
                "decision":       d,
                "recoverable":    float(outcome.get("recoverable_amount", 0.0)),
                "status":         "Approved" if d == "CLAIM_APPROVED" else ("Denied" if d == "NOT_SUPPORTED" else "In Review"),
                "evidence_source": ev_manager,
                "updated":        "just now",
            }
            st.session_state.claims_history = [
                c for c in st.session_state.claims_history if c["id"] != new_claim["id"]
            ]
            st.session_state.claims_history.insert(0, new_claim)

            # ── Persist to Ingest table ───────────────────────────────────
            new_parsed = {
                "charge_id":       fee_charge_id,
                "shipment_id":     fee_shipment_id,
                "order_id":        fee_order_id,
                "sku":             fee_sku,
                "charge_type":     fee_charge_type,
                "reason":          fee_charge_type.replace("_", " ").title(),
                "amount":          float(fee_amount),
                "days_since_event": int(ev_days),
                "status":          f"Audited ({a})",
            }
            st.session_state.parsed_charges = [
                p for p in st.session_state.parsed_charges
                if str(p.get("charge_id")) != str(fee_charge_id)
            ]
            st.session_state.parsed_charges.insert(0, new_parsed)

    # ── VERDICT DISPLAY ───────────────────────────────────────────────────────
    if st.session_state.audit_result:
        rec        = st.session_state.audit_result
        res        = rec.outcome
        assessment = res.get("assessment", "SILENT")
        decision   = res.get("decision",   "NOT_SUPPORTED")
        recoverable = res.get("recoverable_amount", 0.0)
        reason      = res.get("reason", "")
        rule_cited  = res.get("rule_cited", "FBA Evidence Standard")
        supp_ev     = res.get("supporting_evidence", [])
        disputed    = st.session_state.get("last_fee_amount", fee_amount)

        TRI_STATE = {
            "CONTRADICTED":       (COLORS['green'],  "rgba(16,185,129,0.15)",  "CONTRADICTED — Evidence disproves charge → Claim Approved", "CLAIM_APPROVED"),
            "SUPPORTS":           (COLORS['red'],    "rgba(239,68,68,0.15)",   "SUPPORTS — Evidence confirms charge → Not Supported",        "NOT_SUPPORTED"),
            "SILENT":             (COLORS['amber'],  "rgba(245,158,11,0.15)",  "SILENT — Evidence missing/ambiguous → Needs Manual Review", "NEEDS_MANUAL_REVIEW"),
            "UNCERTAIN":          (COLORS['blue'],   "rgba(59,130,246,0.15)",  "UNCERTAIN — Ambiguous Records → Do Not Invent Evidence",     "NEEDS_MANUAL_REVIEW"),
            "DUPLICATE_CHARGE":   (COLORS['purple'], "rgba(139,92,246,0.15)",  "DUPLICATE — Charge billed twice → Claim Approved",           "CLAIM_APPROVED"),
            "ALREADY_REIMBURSED": (COLORS['blue'],   "rgba(59,130,246,0.15)",  "ALREADY REIMBURSED — Credit present → Suppressed",          "NOT_SUPPORTED"),
        }
        badge_color, badge_bg, status_text, _ = TRI_STATE.get(assessment, TRI_STATE["SILENT"])

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="panel-header">
            <div class="panel-title">📊 Recovery Verdict — Tri-State Assessment</div>
            <span class="badge" style="background:{badge_bg}; color:{badge_color}; border:1px solid {badge_color}; font-size:12px; padding: 5px 14px;">
                ● {status_text}
            </span>
        </div>
        """, unsafe_allow_html=True)

        # 4-card result grid
        st.markdown(f"""
        <div class="result-grid">
            <div class="result-card" style="border-left: 4px solid {badge_color};">
                <div class="result-card-label">Tri-State Assessment</div>
                <div class="result-card-value" style="color:{badge_color};">{assessment}</div>
                <div class="result-card-sub">{rule_cited}</div>
            </div>
            <div class="result-card">
                <div class="result-card-label">Claim Decision</div>
                <div class="result-card-value" style="color:{COLORS['text']}; font-size:17px;">{decision.replace('_', ' ')}</div>
                <div class="result-card-sub">Automated Dispute Action</div>
            </div>
            <div class="result-card">
                <div class="result-card-label">Recoverable Amount</div>
                <div class="result-card-value" style="color:{COLORS['green']};">${recoverable:,.2f}</div>
                <div class="result-card-sub">{'Approved' if recoverable > 0 else '$0.00 — not claimable'}</div>
            </div>
            <div class="result-card">
                <div class="result-card-label">Disputed Fee</div>
                <div class="result-card-value" style="color:{COLORS['muted']};">${disputed:,.2f}</div>
                <div class="result-card-sub">Original Invoiced Charge</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        c_left, c_right = st.columns(2, gap="large")
        with c_left:
            st.markdown(f"""
            <div class="evidence-block">
                <div class="evidence-title" style="color:{COLORS['blue']};">📎 Attached Supporting Evidence</div>
            """, unsafe_allow_html=True)
            if supp_ev:
                for ev_item in supp_ev:
                    st.markdown(f"<div style='font-size:12.5px; padding:5px 0; color:#D1D5DB;'>• {ev_item}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='font-size:12.5px; color:#9CA3AF; font-style:italic;'>No supporting evidence — rule: Do not invent evidence.</div>", unsafe_allow_html=True)

            st.markdown(f"""
                <div style="margin-top:14px; border-top:1px solid rgba(31,41,55,0.4); padding-top:10px;">
                    <div class="evidence-row"><span class="evidence-key">Record ID</span><span class="evidence-val">{rec.record_id}</span></div>
                    <div class="evidence-row" style="border:none;"><span class="evidence-key">SHA-256 Hash</span><span class="evidence-val" style="font-size:10px; word-break:break-all;">{rec.content_hash}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with c_right:
            st.markdown(f"""
            <div class="evidence-block">
                <div class="evidence-title" style="color:{COLORS['orange']};">🤖 Defensible Claim Explanation</div>
                <div style="font-size:13px; line-height:1.7; color:#D1D5DB;">{reason}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Live ledger preview
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="panel-header">
            <div class="panel-title">📋 Claims Ledger — Live Update</div>
            <span class="badge" style="background:rgba(16,185,129,0.15); color:{COLORS['green']}; border:1px solid {COLORS['green']};">
                Claim #CLM-{st.session_state.get('last_charge_id', fee_charge_id)} synced
            </span>
        </div>
        """, unsafe_allow_html=True)
        df_preview = pd.DataFrame(st.session_state.claims_history)
        st.dataframe(
            df_preview[["id","shipment","sku","type","amount","assessment","recoverable","status","updated"]],
            use_container_width=True, hide_index=True
        )
        nav1, nav2 = st.columns(2)
        with nav1:
            if st.button("📋 Open Full Claims Ledger", use_container_width=True):
                st.session_state.active_page = "Claims Ledger"; st.rerun()
        with nav2:
            if st.button("📊 Return to Dashboard", use_container_width=True):
                st.session_state.active_page = "Dashboard"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)








    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">🧪 Official Cube Buildathon Test Suite</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="font-size: 13px; color: {COLORS['muted']}; margin-bottom: 16px;">
        Test and verify all 8 required scenarios specified in Track 05: Recovery Manager. Each scenario runs live through the AI engine and verifies conservative decision-making.
    </div>
    """, unsafe_allow_html=True)

    SCENARIOS = [
        {
            "num": 1,
            "title": "Correct claim with full evidence",
            "desc": "Charge 48291 ($38) for packaging defect. Prep Manager has packaging check PASS with 3 photos captured prior to shipment.",
            "expected": "CONTRADICTED → Potential Claim: $38.00",
            "charge": {"charge_id": "48291", "shipment_id": "SHP-10291", "sku": "SKU-9281", "charge_type": "packaging_defect", "amount": 38.00},
            "evidence": [OPERATIONAL_EVIDENCE_STORE["SHP-10291"]],
        },
        {
            "num": 2,
            "title": "Claim with partial evidence",
            "desc": "Charge 48292 ($45) for weight handling. Pallet intake scale exists, but unit carton weigh-in is missing.",
            "expected": "SILENT / UNCERTAIN → Claim NOT SUPPORTED ($0.00)",
            "charge": {"charge_id": "48292", "shipment_id": "SHP-10292", "sku": "SKU-7741", "charge_type": "weight_handling", "amount": 45.00},
            "evidence": [OPERATIONAL_EVIDENCE_STORE["SHP-10292"]],
        },
        {
            "num": 3,
            "title": "Claim with no evidence",
            "desc": "Charge 48293 ($65) for unplanned bubble wrap. No records exist across Prep, Receiving, or Pack managers.",
            "expected": "SILENT — insufficient evidence → Claim NOT SUPPORTED ($0.00)",
            "charge": {"charge_id": "48293", "shipment_id": "SHP-10293", "sku": "SKU-3319", "charge_type": "unplanned_prep", "amount": 65.00},
            "evidence": [],
        },
        {
            "num": 4,
            "title": "Multiple charges same shipment",
            "desc": "Shipment SHP-10294 has 2 charges: Barcode defect ($25) and Missing polybag ($35). Evaluated against Pack Manager logs.",
            "expected": "Barcode CONTRADICTED ($25 claimed) + Polybag SUPPORTS ($0 claimed)",
            "charge": {"charge_id": "48294A", "shipment_id": "SHP-10294", "sku": "SKU-2094", "charge_type": "inbound_defect_barcode", "amount": 25.00},
            "evidence": [OPERATIONAL_EVIDENCE_STORE["SHP-10294"]],
        },
        {
            "num": 5,
            "title": "Fee matches evidence from different Manager",
            "desc": "Charge 48295 ($120) for carton crushed. Matched against Receiving Manager dock intake BOL exception showing carrier caused damage.",
            "expected": "CONTRADICTED → Potential Claim: $120.00",
            "charge": {"charge_id": "48295", "shipment_id": "SHP-10295", "sku": "SKU-5502", "charge_type": "item_damaged_in_warehouse", "amount": 120.00},
            "evidence": [OPERATIONAL_EVIDENCE_STORE["SHP-10295"]],
        },
        {
            "num": 6,
            "title": "Ambiguous evidence",
            "desc": "Charge 48296 ($55) for suffocation warning. Prep record logged 'bagging_exempt' without bag aperture dimension measurement.",
            "expected": "UNCERTAIN → Conservative Decision: NOT_SUPPORTED ($0.00)",
            "charge": {"charge_id": "48296", "shipment_id": "SHP-10296", "sku": "SKU-6610", "charge_type": "suffocation_warning", "amount": 55.00},
            "evidence": [OPERATIONAL_EVIDENCE_STORE["SHP-10296"]],
        },
        {
            "num": 7,
            "title": "Duplicate charges",
            "desc": "Charge 48297 is an identical packaging defect billed twice across monthly billing cycles for Shipment SHP-10291.",
            "expected": "DUPLICATE_CHARGE → Dispute Approved: $38.00",
            "charge": {"charge_id": "48297", "shipment_id": "SHP-10291", "sku": "SKU-9281", "charge_type": "packaging_defect", "amount": 38.00, "is_duplicate": True},
            "evidence": [],
        },
        {
            "num": 8,
            "title": "Already reimbursed charges",
            "desc": "Charge 48298 ($75) matches an existing credit in Reimbursement Report REMB-8820-SETTLED.",
            "expected": "ALREADY_REIMBURSED → Claim Suppressed ($0.00)",
            "charge": {"charge_id": "48298", "shipment_id": "SHP-10298", "sku": "SKU-8820", "charge_type": "lost_in_transit", "amount": 75.00, "already_reimbursed": True, "reimbursement_id": "REMB-8820-SETTLED"},
            "evidence": [],
        },
    ]

    selected_idx = st.selectbox(
        "Select Test Scenario to Execute",
        options=range(len(SCENARIOS)),
        format_func=lambda i: f"Scenario {SCENARIOS[i]['num']}: {SCENARIOS[i]['title']}"
    )

    sc = SCENARIOS[selected_idx]

    st.markdown(f"""
    <div style="background: {COLORS['surface_subtle']}; border: 1px solid {COLORS['border']}; border-radius: 10px; padding: 16px; margin: 12px 0;">
        <div style="font-size: 15px; font-weight: 700; color: {COLORS['text']};">Scenario #{sc['num']}: {sc['title']}</div>
        <div style="font-size: 13px; color: {COLORS['muted']}; margin-top: 4px;">{sc['desc']}</div>
        <div style="font-size: 12px; color: {COLORS['blue']}; margin-top: 6px; font-weight: 600;">Expected Target: {sc['expected']}</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button(f"▶️ Run Scenario #{sc['num']} with Live AI Engine", type="primary", use_container_width=True):
        with st.spinner("Executing Recovery Audit Engine..."):
            res = engine.audit_charge(
                org_id="org_buildathon_eval",
                fee_row=sc["charge"],
                evidence_records=sc["evidence"]
            )
            out = res.outcome
            
            # Immediately record scenario audit into claims_ledger, claims_history, and parsed tables
            sc_manager = sc['evidence'][0].get('source_manager', 'None') if sc['evidence'] else 'No Records Available (Silent)'
            sc_row = pd.DataFrame([{
                "order_no":    sc['charge'].get('order_id', sc['charge'].get('shipment_id', 'ORD-N/A')),
                "charge_type": sc['charge'].get('charge_type', 'Fee'),
                "amount":      float(sc['charge'].get('amount', 0.0)),
                "verdict":     out.get("assessment", "SILENT"),
                "manager":     sc_manager,
                "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }])
            st.session_state.claims_ledger = pd.concat([st.session_state.claims_ledger, sc_row], ignore_index=True)

            sc_claim = {
                "id": f"#CLM-{sc['charge']['charge_id']}",
                "shipment": sc['charge']['shipment_id'],
                "sku": sc['charge'].get('sku', 'N/A'),
                "type": str(sc['charge'].get('charge_type', 'Fee')).replace('_', ' ').title(),
                "amount": float(sc['charge'].get('amount', 0.0)),
                "assessment": out.get("assessment", "SILENT"),
                "decision": out.get("decision", "NEEDS_MANUAL_REVIEW"),
                "recoverable": float(out.get("recoverable_amount", 0.0)),
                "status": "Approved" if out.get("decision") == "CLAIM_APPROVED" else ("Denied" if out.get("decision") == "NOT_SUPPORTED" else "In Review"),
                "evidence_source": sc_manager,
                "updated": "just now",
            }
            st.session_state.claims_history = [c for c in st.session_state.claims_history if c["id"] != sc_claim["id"]]
            st.session_state.claims_history.insert(0, sc_claim)

            sc_parsed = {
                "charge_id": sc['charge']['charge_id'],
                "shipment_id": sc['charge']['shipment_id'],
                "order_id": sc['charge'].get('order_id', 'N/A'),
                "sku": sc['charge'].get('sku', 'N/A'),
                "charge_type": sc['charge'].get('charge_type', 'Fee'),
                "reason": sc['title'],
                "amount": float(sc['charge'].get('amount', 0.0)),
                "days_since_event": 14,
                "status": f"Audited ({out.get('assessment')})",
            }
            st.session_state.parsed_charges = [p for p in st.session_state.parsed_charges if str(p.get("charge_id")) != str(sc['charge']['charge_id'])]
            st.session_state.parsed_charges.insert(0, sc_parsed)

            st.success(f"✅ Scenario #{sc['num']} successfully audited and updated in Claims Ledger & Ingested Tables!")

            st.markdown(f"""
            <div style="background: {COLORS['bg']}; border: 1px solid {COLORS['border']}; border-radius: 10px; padding: 20px; margin-top: 14px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <span style="font-size: 16px; font-weight: 800; color: {COLORS['text']};">LIVE AUDIT OUTPUT</span>
                    <span class="badge" style="background: rgba(16,185,129,0.15); color: {COLORS['green']}; border: 1px solid {COLORS['green']};">
                        Verdict: {out.get('assessment')}
                    </span>
                </div>
                <div style="font-size: 13.5px; line-height: 1.6; color: #E5E7EB; margin-bottom: 10px;">
                    <b>Reason:</b> {out.get('reason')}
                </div>
                <div style="font-size: 12.5px; color: {COLORS['muted']};">
                    <b>Potential Claim Amount:</b> <span style="color: {COLORS['green']}; font-weight: 700;">${out.get('recoverable_amount', 0.0):,.2f}</span> | 
                    <b>Decision:</b> <code>{out.get('decision')}</code> | 
                    <b>Rule:</b> {out.get('rule_cited', 'Standard')}
                </div>
                <div style="margin-top: 8px; font-size: 11px; font-family: monospace; color: {COLORS['muted']};">
                    SHA-256 Hash: {res.content_hash}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Live Updated Table Preview for Scenarios
            st.markdown(f"""
            <div style="margin-top: 14px; padding-top: 12px; border-top: 1px solid rgba(31,41,55,0.4);">
                <div style="font-size: 13px; font-weight: 700; color: {COLORS['text']}; margin-bottom: 8px;">
                    📋 Live Claims Table (Updated with Scenario #{sc['num']} Claim {sc_claim['id']})
                </div>
            </div>
            """, unsafe_allow_html=True)
            df_sc_preview = pd.DataFrame(st.session_state.claims_history[:5])
            st.dataframe(df_sc_preview[["id", "shipment", "sku", "type", "amount", "assessment", "recoverable", "status", "updated"]], use_container_width=True, hide_index=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# MODULE 5: OPERATIONAL EVIDENCE HUB
# ──────────────────────────────────────────────────────────────────────────────
elif st.session_state.active_page == "Evidence Hub":
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">📂 Upstream Operational Evidence Store</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="font-size: 13px; color: {COLORS['muted']}; margin-bottom: 16px;">
        Explore structured records generated across upstream operational managers (Prep, Receiving, Pack, Returns). The AI Recovery Manager searches this evidentiary ledger to validate or contradict late-appearing Amazon charges.
    </div>
    """, unsafe_allow_html=True)

    ev_rows = []
    for shp, data in OPERATIONAL_EVIDENCE_STORE.items():
        ev_rows.append({
            "Shipment": data["shipment_id"],
            "SKU": data["sku"],
            "Source Manager": data["source_manager"],
            "Record ID": data["record_id"],
            "Packaging Check": data["packaging_check"],
            "Label Status": data["fnsku_label_placement"],
            "Photos": data["photos_count"],
            "Timestamp": data["timestamp"],
            "Notes": data["notes"]
        })

    df_ev = pd.DataFrame(ev_rows)
    st.dataframe(df_ev, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# MODULE 6: CLAIMS LEDGER
# ──────────────────────────────────────────────────────────────────────────────
elif st.session_state.active_page == "Claims Ledger":
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">📋 Full Claims & Disputes Ledger</div>', unsafe_allow_html=True)

    df_ledger = st.session_state.claims_ledger

    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        f_status = st.selectbox("Verdict Filter", ["All", "CONTRADICTED", "SUPPORTS", "SILENT", "UNCERTAIN", "DUPLICATE_CHARGE"])
    with f_col2:
        f_mgr = st.selectbox("Manager Filter", ["All", "Prep Manager", "Receiving Manager", "Pack Manager", "Returns Manager", "No Records Available (Silent — no evidence)"])
    with f_col3:
        search_kw = st.text_input("Search Order No or Charge Type", placeholder="e.g. ORD-44910")

    if not df_ledger.empty:
        filtered_df = df_ledger.copy()
        if f_status != "All" and 'verdict' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['verdict'] == f_status]
        if f_mgr != "All" and 'manager' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['manager'] == f_mgr]
        if search_kw:
            kw = search_kw.lower()
            mask = filtered_df.apply(lambda row: kw in str(row.get('order_no', '')).lower() or kw in str(row.get('charge_type', '')).lower(), axis=1)
            filtered_df = filtered_df[mask]

        if not filtered_df.empty:
            df_show = filtered_df.copy()
            if 'amount' in df_show.columns:
                df_show['amount'] = pd.to_numeric(df_show['amount'], errors='coerce').fillna(0.0).apply(lambda x: f"${x:,.2f}")
            df_show = df_show.rename(columns={
                "order_no": "Order No",
                "charge_type": "Charge Type",
                "amount": "Disputed Fee ($)",
                "verdict": "Tri-State Verdict",
                "manager": "Source Manager",
                "timestamp": "Audit Timestamp"
            })
            st.dataframe(df_show.iloc[::-1], use_container_width=True, hide_index=True)
        else:
            st.info("No claims match your filter criteria.")

        st.markdown("---")
        csv_all = df_ledger.to_csv(index=False)
        st.download_button("⬇️ Export Full Audit Ledger (CSV)", csv_all, file_name="trident_recovery_full_claims_ledger.csv", mime="text/csv")
    else:
        st.info("Claims ledger is currently empty. Run an audit in '⚡ AI Auditor' to populate the global database.")
    st.markdown('</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# MODULE 7: ANALYTICS
# ──────────────────────────────────────────────────────────────────────────────
elif st.session_state.active_page == "Analytics":
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">📈 Dispute & Recovery Financial Analytics</div>', unsafe_allow_html=True)

    df_ledger = st.session_state.claims_ledger
    total_claims_count = len(df_ledger)
    total_disp = float(pd.to_numeric(df_ledger['amount'], errors='coerce').fillna(0.0).sum()) if not df_ledger.empty and 'amount' in df_ledger.columns else 0.0
    rate = (kpis['recovered'] / total_disp * 100) if total_disp > 0 else 0.0
    defensible_ratio = (kpis['approved'] / max(total_claims_count, 1) * 100) if total_claims_count > 0 else 0.0

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Ingested Charges", total_claims_count)
    with m2:
        st.metric("Approved Recoverable Payouts", f"${kpis['recovered']:,.2f}")
    with m3:
        st.metric("Dispute Success Rate", f"{rate:.1f}%")
    with m4:
        st.metric("Defensible Claims Ratio", f"{defensible_ratio:.1f}%")

    st.markdown("---")
    # Breakdown Bar Chart
    if not df_ledger.empty and 'verdict' in df_ledger.columns and len(df_ledger) > 0:
        assess_counts = df_ledger['verdict'].value_counts().to_dict()
        color_lookup = {
            "CONTRADICTED": COLORS['green'],
            "SUPPORTS": COLORS['red'],
            "SILENT": COLORS['amber'],
            "UNCERTAIN": COLORS['blue'],
            "DUPLICATE_CHARGE": COLORS['purple'],
            "ALREADY_REIMBURSED": COLORS['blue'],
        }
        fig_bar = go.Figure(go.Bar(
            x=list(assess_counts.keys()),
            y=list(assess_counts.values()),
            marker=dict(color=[color_lookup.get(k, COLORS['blue']) for k in assess_counts.keys()], cornerradius=8)
        ))
    else:
        fig_bar = go.Figure(go.Bar(
            x=["CONTRADICTED", "SUPPORTS", "SILENT"],
            y=[0, 0, 0],
            marker=dict(color=[COLORS['green'], COLORS['red'], COLORS['amber']], cornerradius=8)
        ))

    fig_bar.update_layout(
        paper_bgcolor=COLORS['surface'], plot_bgcolor=COLORS['bg'],
        font=dict(family="Inter", color=COLORS['muted']), height=320,
        margin=dict(l=35, r=20, t=20, b=35),
        xaxis=dict(gridcolor="rgba(31,41,55,0.4)"), yaxis=dict(gridcolor="rgba(31,41,55,0.4)")
    )
    st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# MODULE 8: SETTINGS
# ──────────────────────────────────────────────────────────────────────────────
elif st.session_state.active_page == "Settings":
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">⚙️ Recovery Manager System Configuration</div>', unsafe_allow_html=True)
    st.markdown(f"**Track:** `Track 05 — Recovery Manager (Cube Buildathon)`")
    st.markdown(f"**AI Engine Model:** `gemini-3.8-flash`")
    st.markdown(f"**Inference Mode:** `application/json` (deterministic, temperature: 0.0)")
    st.markdown(f"**Cryptographic Hash Standard:** `SHA-256 (Canonical JSON serialization)`")
    st.markdown(f"**FBA Claim Expiration Window:** `60 Days Statute of Limitations`")
    st.markdown(f"**Conservative Evidence Rule:** `Do Not Invent Evidence (Strict Silent / Uncertain enforcement)`")
    st.markdown(f"**API Authentication:** {'✅ Active (.env)' if env_api_key else '🔑 Manual fallback'}")
    st.markdown('</div>', unsafe_allow_html=True)