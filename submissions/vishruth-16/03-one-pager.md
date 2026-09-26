# Recovery Manager: Operational One-Pager

## Core Objective
Ingest fee and reimbursement reports, join line items against upstream operational evidence (Receiving, Prep, Pack, Returns), and produce defensible, evidence-backed dispute records.

## Metric Targets

| Metric | Target | Rationale |
| :--- | :--- | :--- |
| **Claim Precision** | $\ge 95\%$ | Prevents seller account health penalties from baseless disputes. |
| **Silent / Uncertain Handling** | $100\%$ | Strict adherence to conservative decision rule: no invented evidence. |
| **Join Coverage** | $\ge 98\%$ | Accurate unit-to-charge matching across FBA and MFN pipelines. |
| **P95 Audit Latency** | $< 250$ ms | Rapid batch reconciliation of multi-thousand-row fee reports. |

## The Kill Condition
> **Kill Condition:** If upstream evidence records lack verifiable check keys, timestamps, or image references for more than 50% of audited units within a fee cycle, Recovery Manager halts automated claim generation and trips a circuit-breaker to manual review. Automated claims are never dispatched on degraded evidence foundations.
