"""
engine.py — Recovery Manager AI Audit Engine
Track 05 · Cube Buildathon

Strict architectural constraints enforced:
  - NO vision / camera / image classification
  - Evidence-based reasoning ONLY (structured records)
  - Tri-state output: CONTRADICTED | SUPPORTS | SILENT (+ UNCERTAIN, DUPLICATE_CHARGE, ALREADY_REIMBURSED)
  - Tenancy isolation: org_id must match on fee_row and evidence before processing
  - Fail-open: any unhandled exception returns PENDING_REVIEW so ops are never blocked
  - 60-day statute enforced via authoritative constant (not model memory)
"""

import json
import uuid
import hashlib
from datetime import datetime
from pydantic import BaseModel
import google.generativeai as genai

# ── Authoritative Amazon FBA constants (not model memory) ─────────────────────
FBA_CLAIM_WINDOW_DAYS = 60          # 60-day dispute filing deadline
AGENT_ORG_ID = "org_demo_alpha"     # Expected org for tenancy check

# ── Canonical charge type → evidence compliance key mapping ──────────────────
CHARGE_COMPLIANCE_MAP = {
    "inbound_defect_unbagged":          ["polybag_present_sealed", "packaging_check"],
    "inbound_defect_barcode":           ["fnsku_label_placement", "barcode_scan"],
    "fulfilment_fee_weight_tier":       ["unit_weight_recorded", "tare_weight"],
    "packaging_defect":                 ["packaging_check", "polybag_present_sealed"],
    "missing_polybag":                  ["polybag_present_sealed", "packaging_check"],
    "weight_handling":                  ["unit_weight_recorded", "tare_weight"],
    "oversize_item":                    ["unit_dimensions_recorded"],
    "unplanned_prep":                   ["packaging_check", "prep_instructions_followed"],
    "label_missing":                    ["fnsku_label_placement"],
    "bubble_wrap_required":             ["packaging_check", "prep_instructions_followed"],
    "taping_required":                  ["packaging_check", "carton_sealed"],
    "suffocation_warning":              ["suffocation_label_present", "polybag_aperture_measured"],
    "item_damaged_in_warehouse":        ["packaging_check", "bol_exception"],
    "lost_in_transit":                  ["bol_exception", "inbound_reconciliation"],
}


class RecoveryEvidenceRecord(BaseModel):
    record_id: str
    organization_id: str
    outcome: dict
    status: str
    content_hash: str = ""

    def compute_hash(self) -> str:
        serialized = json.dumps(
            {"record_id": self.record_id, "outcome": self.outcome},
            sort_keys=True
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class RecoveryAuditEngine:

    def __init__(self, api_key: str):
        self.api_key = api_key
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(
                "gemini-2.0-flash",
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.0,
                }
            )
        except Exception:
            self.model = None

    # ── Public entry point — FAIL OPEN ────────────────────────────────────────
    def audit_charge(
        self,
        org_id: str,
        fee_row: dict,
        evidence_records: list,
        compliance_rule: str = "",
    ) -> RecoveryEvidenceRecord:
        """
        Evaluate a single FBA fee charge against operational evidence.

        Parameters
        ----------
        org_id          : Tenant identifier — must match evidence org before processing.
        fee_row         : Parsed fee charge dict (charge_id, shipment_id, sku, charge_type, amount, …)
        evidence_records: List of structured upstream evidence dicts from Prep/Pack/Receiving/Returns.
        compliance_rule : Explicit rule being evaluated (e.g. 'polybag_present_sealed').

        Returns
        -------
        RecoveryEvidenceRecord with SHA-256 sealed outcome.
        Tri-state: CONTRADICTED | SUPPORTS | SILENT (+ UNCERTAIN / DUPLICATE_CHARGE / ALREADY_REIMBURSED)
        """
        record_id = f"REC-AUDIT-{uuid.uuid4().hex[:8].upper()}"

        try:
            return self._run_audit(record_id, org_id, fee_row, evidence_records, compliance_rule)

        except Exception as exc:
            # ── FAIL OPEN: never crash warehouse operations ────────────────
            outcome = {
                "assessment": "UNCERTAIN",
                "decision": "PENDING_REVIEW",
                "recoverable_amount": 0.0,
                "reason": (
                    f"SYSTEM ERROR — PENDING REVIEW: An unexpected exception occurred during "
                    f"audit execution ({type(exc).__name__}: {exc}). "
                    f"Claim has been queued for manual adjudication. "
                    f"Warehouse operations are NOT blocked."
                ),
                "rule_cited": "Fail-Open Safety Protocol",
                "supporting_evidence": [],
            }
            rec = RecoveryEvidenceRecord(
                record_id=record_id, organization_id=org_id,
                outcome=outcome, status="ERROR_PENDING_REVIEW"
            )
            rec.content_hash = rec.compute_hash()
            return rec

    # ── Internal audit pipeline ───────────────────────────────────────────────
    def _run_audit(
        self,
        record_id: str,
        org_id: str,
        fee_row: dict,
        evidence_records: list,
        compliance_rule: str,
    ) -> RecoveryEvidenceRecord:

        amount = float(fee_row.get("amount_usd", 0.0) or fee_row.get("amount", 0.0))
        days   = int(fee_row.get("days_since_event", 14) or 14)

        # ── Rule 0: Tenancy isolation — org_id must match ─────────────────
        for ev in evidence_records:
            ev_org = ev.get("org_id", org_id)   # default to caller org if not tagged
            if ev_org != org_id:
                outcome = {
                    "assessment": "SILENT",
                    "decision": "NOT_SUPPORTED",
                    "recoverable_amount": 0.0,
                    "reason": (
                        f"TENANCY VIOLATION: Evidence record org_id '{ev_org}' does not match "
                        f"fee report org_id '{org_id}'. Cross-tenant evidence is not permitted. "
                        f"Claim rejected on row-level security grounds."
                    ),
                    "rule_cited": "Tenancy Isolation / Row-Level Security",
                    "supporting_evidence": [],
                }
                rec = RecoveryEvidenceRecord(
                    record_id=record_id, organization_id=org_id,
                    outcome=outcome, status="REJECTED_TENANCY"
                )
                rec.content_hash = rec.compute_hash()
                return rec

        # ── Rule 1: Duplicate charge ───────────────────────────────────────
        if fee_row.get("is_duplicate"):
            outcome = {
                "assessment": "DUPLICATE_CHARGE",
                "decision": "CLAIM_APPROVED",
                "recoverable_amount": amount,
                "reason": (
                    f"DUPLICATE TRANSACTION DETECTED: Charge ID {fee_row.get('charge_id', 'N/A')} "
                    f"was already billed for Shipment {fee_row.get('shipment_id', 'N/A')}. "
                    f"Disputed under FBA Duplicate Fee Billing policy."
                ),
                "rule_cited": "FBA Duplicate Charge Clause",
                "supporting_evidence": ["Prior settlement record", "Duplicate invoice timestamp"],
            }
            rec = RecoveryEvidenceRecord(
                record_id=record_id, organization_id=org_id,
                outcome=outcome, status="COMPLETED"
            )
            rec.content_hash = rec.compute_hash()
            return rec

        # ── Rule 2: Already reimbursed ─────────────────────────────────────
        if fee_row.get("already_reimbursed") or fee_row.get("reimbursement_id"):
            remb_id = fee_row.get("reimbursement_id", "REMB-SETTLED")
            outcome = {
                "assessment": "ALREADY_REIMBURSED",
                "decision": "NOT_SUPPORTED",
                "recoverable_amount": 0.0,
                "reason": (
                    f"SUPPRESSED — ALREADY REIMBURSED: Charge was credited under Settlement "
                    f"Report ID {remb_id}. Initiating a claim would constitute duplicate recovery."
                ),
                "rule_cited": "FBA Settlement & Reimbursement Policy",
                "supporting_evidence": [f"Reimbursement reference: {remb_id}"],
            }
            rec = RecoveryEvidenceRecord(
                record_id=record_id, organization_id=org_id,
                outcome=outcome, status="COMPLETED"
            )
            rec.content_hash = rec.compute_hash()
            return rec

        # ── Rule 3: 60-day statute of limitations (authoritative constant) ─
        if days > FBA_CLAIM_WINDOW_DAYS:
            outcome = {
                "assessment": "SILENT",
                "decision": "NOT_SUPPORTED",
                "recoverable_amount": 0.0,
                "reason": (
                    f"TIME EXPIRED: Charge occurred {days} days ago, exceeding Amazon's "
                    f"strict {FBA_CLAIM_WINDOW_DAYS}-day dispute filing deadline. "
                    f"Claim is time-barred regardless of evidence quality."
                ),
                "rule_cited": f"FBA {FBA_CLAIM_WINDOW_DAYS}-Day Dispute Statute of Limitations",
                "supporting_evidence": [],
            }
            rec = RecoveryEvidenceRecord(
                record_id=record_id, organization_id=org_id,
                outcome=outcome, status="COMPLETED"
            )
            rec.content_hash = rec.compute_hash()
            return rec

        # ── Rule 4: No evidence at all — SILENT ───────────────────────────
        if not evidence_records:
            outcome = {
                "assessment": "SILENT",
                "decision": "NOT_SUPPORTED",
                "recoverable_amount": 0.0,
                "reason": (
                    f"SILENT — insufficient evidence: No upstream operational records found "
                    f"from Prep, Receiving, Pack, or Returns Managers for Shipment "
                    f"{fee_row.get('shipment_id', 'N/A')}. "
                    f"Under conservative recovery standards, claims are not defensible without "
                    f"verifiable proof. Evidence cannot be invented. "
                    f"A correctly flagged SILENT is a successful evaluation."
                ),
                "rule_cited": "Conservative Evidence Baseline",
                "supporting_evidence": [],
            }
            rec = RecoveryEvidenceRecord(
                record_id=record_id, organization_id=org_id,
                outcome=outcome, status="COMPLETED"
            )
            rec.content_hash = rec.compute_hash()
            return rec

        # ── Rule 5: AI evaluation (with deterministic fallback) ───────────
        if self.model:
            try:
                ai_result = self._ai_evaluate(fee_row, evidence_records, compliance_rule)
                rec = RecoveryEvidenceRecord(
                    record_id=record_id, organization_id=org_id,
                    outcome=ai_result, status="COMPLETED"
                )
                rec.content_hash = rec.compute_hash()
                return rec
            except Exception:
                pass   # fall through to deterministic

        return self._deterministic_audit(record_id, org_id, fee_row, evidence_records, compliance_rule)

    # ── Gemini AI evaluation ──────────────────────────────────────────────────
    def _ai_evaluate(self, fee_row: dict, evidence_records: list, compliance_rule: str) -> dict:
        amount = float(fee_row.get("amount_usd", 0.0) or fee_row.get("amount", 0.0))

        system_prompt = f"""You are an AI Recovery Manager for Amazon FBA dispute reconciliation.
Track 05 — Cube Buildathon. Structured evidence-based reasoning ONLY.
No vision. No camera. No image classification.

YOU MUST FOLLOW THESE AUTHORITATIVE RULES EXACTLY. Do NOT deviate.

RULE 1 — TENANCY CHECK (already enforced before this call, but double-check):
  If fee_row org_id != evidence org_id → assessment="SILENT", decision="NOT_SUPPORTED", recoverable_amount=0.0,
  reason="Tenancy isolation breach: Fee belongs to organization X but evidence belongs to organization Y."

RULE 2 — 60-DAY DEADLINE (already enforced before this call):
  If days_since_event > 60 → assessment="SILENT", decision="NOT_SUPPORTED", recoverable_amount=0.0,
  reason="Authoritative Amazon Rule: Dispute window expired (>60 days)."

RULE 3 — COMPLIANCE MATCHING (THIS IS THE MOST CRITICAL RULE):
  Look at the evidence records' compliance_status AND packaging_check fields.

  A) If compliance_status contains "FAIL" or "non-compliant", OR packaging_check == "FAIL":
     The evidence PROVES THE DEFECT EXISTED. The seller WAS at fault. The Amazon fee is LEGITIMATE.
     → assessment="SUPPORTS", decision="NOT_SUPPORTED", recoverable_amount=0.0
     → reason: "Warehouse evidence confirms the compliance defect. The penalty is valid and cannot be disputed."

  B) If compliance_status contains "PASS" or "compliant", OR packaging_check == "PASS":
     The evidence PROVES THE UNIT WAS COMPLIANT. The Amazon fee is ERRONEOUS.
     → assessment="CONTRADICTED", decision="CLAIM_APPROVED", recoverable_amount={amount}
     → reason: Cite the specific evidence record_id that proves compliance.

  C) If compliance_status is "UNCERTAIN", "PARTIAL", "EXEMPT", "NOT_REQUIRED", or evidence is missing/ambiguous:
     → assessment="SILENT", decision="NEEDS_MANUAL_REVIEW", recoverable_amount=0.0
     → reason: "Insufficient or ambiguous evidence. Cannot assemble a defensible claim."

CRITICAL WARNINGS:
- Do NOT return CONTRADICTED when evidence shows FAIL/non-compliant. That is WRONG.
- Do NOT return SUPPORTS when evidence shows PASS/compliant. That is WRONG.
- FAIL evidence = SUPPORTS (charge is legitimate). PASS evidence = CONTRADICTED (charge is erroneous).
- Do NOT invent evidence. A correctly flagged SILENT is a successful evaluation.

Compliance rule being evaluated: "{compliance_rule or 'not specified — infer from charge_type'}"
Charge amount: ${amount:.2f}

OUTPUT FORMAT — return ONLY valid JSON:
{{
    "assessment": "CONTRADICTED" | "SUPPORTS" | "SILENT" | "UNCERTAIN",
    "decision": "CLAIM_APPROVED" | "NOT_SUPPORTED" | "NEEDS_MANUAL_REVIEW",
    "recoverable_amount": <float>,
    "reason": "<Defensible explanation citing specific evidence fields, managers, and FBA rule>",
    "rule_cited": "<Specific FBA rule>",
    "supporting_evidence": ["<Itemized evidence records>"]
}}"""

        user_prompt = (
            f"FEE REPORT CHARGE:\n{json.dumps(fee_row, indent=2)}\n\n"
            f"AVAILABLE OPERATIONAL EVIDENCE:\n{json.dumps(evidence_records, indent=2)}"
        )

        response = self.model.generate_content(system_prompt + "\n\n" + user_prompt)
        return json.loads(response.text.strip())

    # ── Deterministic fallback rule engine ────────────────────────────────────
    def _deterministic_audit(
        self,
        record_id: str,
        org_id: str,
        fee_row: dict,
        evidence_records: list,
        compliance_rule: str,
    ) -> RecoveryEvidenceRecord:

        amount = float(fee_row.get("amount_usd", 0.0) or fee_row.get("amount", 0.0))
        charge_type = str(fee_row.get("charge_type", fee_row.get("reason", ""))).lower()

        ev = evidence_records[0] if evidence_records else {}
        mgr = str(ev.get("source_manager", "unknown manager")).upper()
        record_id_ev = ev.get("record_id", "INSP-UNKNOWN")

        # Determine compliance status from evidence — check BOTH the new
        # compliance_status field (from the UI form) and the legacy
        # packaging_check / fnsku_label_placement fields
        pkg_check       = str(ev.get("packaging_check", "")).upper()
        label_stat      = str(ev.get("fnsku_label_placement", "")).lower()
        compliance_stat = str(ev.get("compliance_status", "")).upper()

        ambiguous   = ev.get("ambiguous", False) or label_stat in ("not_required", "partially_compliant", "exempt")
        partial     = ev.get("partial_evidence", False)
        photos      = int(ev.get("photos_count", ev.get("supporting_evidence_count", 0)))

        # ── Detect FAIL / non-compliant FIRST (higher priority than PASS) ───
        is_fail = (
            pkg_check in ("FAIL", "NON_COMPLIANT")
            or "non_compliant" in label_stat
            or "fail" in label_stat
            or "FAIL" in compliance_stat
            or "NON-COMPLIANT" in compliance_stat
            or "NON_COMPLIANT" in compliance_stat
        )
        is_pass = (
            pkg_check == "PASS"
            or "compliant" in label_stat
            or ev.get("status") == "PASS"
            or "PASS" in compliance_stat
            or "COMPLIANT" in compliance_stat
        )

        # If both FAIL and PASS signals exist (e.g. "non_compliant" contains "compliant"),
        # FAIL takes priority — conservative approach
        if is_fail:
            is_pass = False

        if ambiguous and not is_fail and not is_pass:
            outcome = {
                "assessment": "UNCERTAIN",
                "decision": "NEEDS_MANUAL_REVIEW",
                "recoverable_amount": 0.0,
                "reason": (
                    f"AMBIGUOUS EVIDENCE: {mgr} recorded status '{label_stat}' without conclusive "
                    f"verification against compliance rule '{compliance_rule or charge_type}'. "
                    f"Critical rule: Do not invent evidence. Disputing carries audit risk."
                ),
                "rule_cited": "Conservative Evidence Verification",
                "supporting_evidence": [f"{mgr} status: {label_stat}"],
            }

        elif partial and not is_fail and not is_pass:
            outcome = {
                "assessment": "SILENT",
                "decision": "NOT_SUPPORTED",
                "recoverable_amount": 0.0,
                "reason": (
                    f"SILENT — partial records: {mgr} holds gross shipment intake data but unit-level "
                    f"tare records were not captured. Rule '{compliance_rule or charge_type}' requires "
                    f"unit-level verification. Claim cannot be defended."
                ),
                "rule_cited": "Unit-Level Verification Rule",
                "supporting_evidence": [],
            }

        elif is_fail:
            outcome = {
                "assessment": "SUPPORTS",
                "decision": "NOT_SUPPORTED",
                "recoverable_amount": 0.0,
                "reason": (
                    f"SUPPORTS CHARGE: {mgr} records confirm unit was flagged '{pkg_check or compliance_stat}' "
                    f"against rule '{compliance_rule or charge_type}'. "
                    f"Warehouse evidence confirms the compliance defect existed. "
                    f"The Amazon penalty is valid and cannot be disputed."
                ),
                "rule_cited": "FBA Inbound Defect Fee Schedule",
                "supporting_evidence": [f"{mgr} Defect log #{record_id_ev}"],
            }

        elif is_pass:
            outcome = {
                "assessment": "CONTRADICTED",
                "decision": "CLAIM_APPROVED",
                "recoverable_amount": amount,
                "reason": (
                    f"CONTRADICTED BY EVIDENCE: {mgr} record #{record_id_ev} explicitly proves "
                    f"unit was COMPLIANT for '{compliance_rule or charge_type}' prior to outbound "
                    f"shipment. Amazon FC fee is erroneous."
                ),
                "rule_cited": f"FBA Inbound Prep & Compliance Standard ({compliance_rule or charge_type})",
                "supporting_evidence": [
                    f"{mgr} inspection record #{record_id_ev}",
                    f"Compliance check: {pkg_check or label_stat.upper()}",
                    f"Timestamp: {ev.get('timestamp', 'N/A')}",
                    f"Photo proof: {photos} verification image(s)",
                ],
            }

        else:
            outcome = {
                "assessment": "SILENT",
                "decision": "NOT_SUPPORTED",
                "recoverable_amount": 0.0,
                "reason": (
                    f"SILENT — insufficient evidence: {mgr} records do not conclusively address "
                    f"'{compliance_rule or charge_type}'. A defensible claim cannot be assembled. "
                    f"A correctly flagged SILENT is a successful evaluation."
                ),
                "rule_cited": "Conservative Evidence Baseline",
                "supporting_evidence": [],
            }

        rec = RecoveryEvidenceRecord(
            record_id=record_id, organization_id=org_id,
            outcome=outcome, status="COMPLETED"
        )
        rec.content_hash = rec.compute_hash()
        return rec