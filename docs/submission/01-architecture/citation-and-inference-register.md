# Architecture citation and inference register

## Citation register

| Element or interaction | Evidence |
| --- | --- |
| ASP.NET Core API host registers controllers, static files, session middleware, repository and approval service | `backend/src/InvoiceApp.Api/Program.cs` |
| Browser UI is served from the API project | `backend/src/InvoiceApp.Api/wwwroot/app.js`, `backend/src/InvoiceApp.Api/Program.cs` |
| Sign-in and sign-out create/remove bearer-token sessions | `backend/src/InvoiceApp.Api/Controllers/AuthController.cs`, `backend/src/InvoiceApp.Api/Auth/SessionStore.cs` |
| API requests require a session except login | `backend/src/InvoiceApp.Api/Auth/SessionAuthMiddleware.cs` |
| Role checks are enforced by an action filter | `backend/src/InvoiceApp.Api/Auth/RequireRoleAttribute.cs` |
| Approval and rejection endpoints are role-gated for Approver/Admin | `backend/src/InvoiceApp.Api/Controllers/ApprovalsController.cs` |
| Invoice deletion is Admin-only | `backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs` |
| Approval lifecycle rules live in the Domain project | `backend/src/InvoiceApp.Domain/ApprovalService.cs` |
| Invoice state and decision fields | `backend/src/InvoiceApp.Domain/Invoice.cs`, `backend/src/InvoiceApp.Domain/InvoiceStatus.cs` |
| Repository abstraction belongs to Domain | `backend/src/InvoiceApp.Domain/IInvoiceRepository.cs` |
| Current storage is an in-memory implementation in the API project | `backend/src/InvoiceApp.Api/InMemoryInvoiceRepository.cs` |
| The target production diagram is proposed and marks Azure SQL, Service Bus, workers, PayEx, outbox and reconciliation as not implemented | `docs/submission/01-architecture/target-architecture.mmd`, `ops/README.md` |
| The target architecture must not claim exactly-once external payment effects from outbox or broker alone | `docs/submission/01-architecture/target-architecture.mmd`, `docs/submission/02-decisions/ADR-001-exactly-once-payment.md` |

## Inferred or proposed items

These items are not current implementation facts unless a later production build proves them:

- Azure App Service hosting for production.
- Azure SQL persistence for invoices, payment submissions, outbox rows and audit records.
- Transactional outbox publisher.
- Azure Service Bus payment submission queue and dead-letter queue.
- Background payment worker.
- PayEx integration.
- Stable PayEx idempotency-key behavior.
- Payment reconciliation job and provider status lookup.
- Seven-year audit retention controls.
- Operations alerting, manual replay workflow and production rollback workflow.

## Corrections and evidence boundary

- The as-built architecture uses in-memory storage; it does not currently use Azure SQL.
- The current application has no outbox, Service Bus worker, PayEx client or reconciliation code.
- `ops/` describes planned production and incident evidence, not current running code.
- Mermaid Chart links in the AI activity log are useful evidence of prior work, but local source files are now recorded in this folder for hand-in.
