# Submission tracker

Status summary: **12/15 complete**, **2/15 partial**, **1/15 pending**.

| # | Assignment item | Status | Evidence / file | Notes |
| ---: | --- | --- | --- | --- |
| 1 | As-built container diagram | Complete | `docs/submission/01-architecture/as-built-container.mmd` | Local Mermaid source now present with file/symbol citations. |
| 2 | Approval sequence diagram | Complete | `docs/submission/01-architecture/approval-sequence.mmd` | Local Mermaid sequence source now present with citations. |
| 3 | Citation and inference register | Complete | `docs/submission/01-architecture/citation-and-inference-register.md` | Separates verified code facts from proposed/inferred production components. |
| 4 | Target production architecture | Complete | `docs/submission/01-architecture/target-architecture.mmd` | Marks proposed/not implemented components and exactly-once limitation. |
| 5 | Executable architecture test | Complete | `backend/tests/InvoiceApp.Tests/ArchitectureTests.cs` | Command: `dotnet test backend/InvoiceApp.sln --filter ArchitectureTests`. Verified 2026-11-01: 1 passed, 0 failed. |
| 6 | Exactly-once ADR | Complete | `docs/submission/02-decisions/ADR-001-exactly-once-payment.md` | Compares idempotency key + dedupe, transactional outbox + worker, and optimistic reconciliation. |
| 7 | `Where the agent was wrong or useless` | Complete | `docs/submission/02-decisions/ADR-001-exactly-once-payment.md` | Section exists with concrete gaps and limitations. |
| 8 | One-page autonomy policy | Complete | `docs/submission/03-autonomy/incident-summary-policy.md` | Day-one level is L1 assisted drafting. |
| 9 | Two custom evaluation cases | Complete | `ops/evals/cases/case-11.diff`, `ops/evals/cases/case-12.diff` | One defect case and one clean refactor case. |
| 10 | Three baseline evaluation runs | Partial | `docs/submission/04_evaluation/report.md`, `docs/submission/04_evaluation/results.csv` | Only partial retrievable baseline outputs; report states the full 3-run requirement was not completed. |
| 11 | One changed-variable evaluation run | Partial | `docs/submission/04_evaluation/report.md`, `docs/submission/04_evaluation/results.csv` | Comparison prompt was run partially; not a complete matched run. |
| 12 | Lethal trifecta risk audit | Complete | `docs/submission/task-5-security-risk-audit.md` | Includes decision: accept current configuration for local demo use only. |
| 13 | Measurement plan and two actual numbers | Complete | `docs/submission/task-5-production-measurement-plan.md` | Captures CI duration and CI success rate; explicitly does not treat CI as production lead time. |
| 14 | AI augmentation JSONL and summary | Complete | `docs/submission/ai-augmentation/ai-activity.jsonl`, `docs/submission/ai_augmentation/ai-activity-summary.md` | JSONL has Task 4, Task 5 security audit, and Task 6 measurement records appended. |
| 15 | 8-to-10-minute demo MP4 | Pending | None found in repository | Record, upload, and add the link before submission. |

## Remaining steps

1. Complete the evaluation requirement: run the full 12-case set three times with the baseline prompt, then one complete changed-variable run, and update `docs/submission/04_evaluation/results.csv` and `report.md`.
2. Record the 8-to-10-minute demo video, upload the MP4, and add the link to this tracker.
3. Run the architecture test command before final submission and keep the terminal result or screenshot for the demo.
4. Do a final evidence pass: confirm no item is marked complete without a file, command, or explicit limitation.
