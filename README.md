# Trident Recovery: Command Center (Track 05)

Trident Recovery is an AI-powered Recovery Manager built for the Cube Buildathon (Commerce Context). It automates Amazon FBA fee reconciliation by parsing financial reports and matching individual charges against upstream operational evidence (Prep, Pack, Returns).

## Problem & Solution
Amazon sellers face constant erroneous fees, but disputing them requires hard evidence. Instead of relying on a camera or image-capture workflow, Trident Recovery ingests structured text data and uses a Gemini-powered AI engine to execute a strict Tri-State evaluation:
* **CONTRADICTED:** Evidence proves the warehouse was compliant. Claim approved.
* **SUPPORTS:** Evidence confirms the defect. Claim dropped.
* **SILENT:** Evidence is missing, ambiguous, or the authoritative deadline expired. Flagged for review.

## Engineering Rules Enforced
1. **Tenancy Isolation:** Row-level security blocks execution if the fee `org_id` does not match the evidence `org_id`.
2. **Fail Open:** API timeouts or dependency failures gracefully return a `PENDING_REVIEW` status without crashing the dashboard, preserving data for operators.
3. **Authoritative Rules:** The AI enforces Amazon's strict 60-day FBA claim eligibility window.
4. **No Invented Evidence:** Missing records or cross-tenant mismatches strictly result in a `SILENT` outcome.

## Run Locally
```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run submissions/vishruth-16/app.py