# Trident Recovery Architecture

## Tech Stack
* **Frontend:** Streamlit (Custom CSS injected for a stateful, dark-mode SaaS Command Center)
* **Backend:** Python 3.10+
* **AI Engine:** Google Gemini (`gemini-3.5-flash`) via `google-generativeai`
* **State Management:** Pandas DataFrame (Session State Ledger)

## Data Flow & Traceability
To ensure complete evidence traceability, the system maps the charge to the exact upstream event rather than hallucinating logic.

```text
[Amazon CSV/JSON] --> (Ingestion Parser) --> [Extracted Fee Row]
                                                    |
[Upstream JSON]   --> (Evidence Hub)     -----> [Match on unit_id & org_id]
                                                    |
[Gemini 3.5 Engine] <--- (System Prompt + Authoritative FBA 60-Day Rules)
       |
       +---> [CONTRADICTED] -> Generate Immutable Claim JSON with Attached Proof
       +---> [SUPPORTS] -----> Log $0.00 Recovery (Defect Confirmed)
       +---> [SILENT] -------> Flag for Manual Review (Missing Evidence/Expired)