# ADR-001: Reliable payment submission and duplicate prevention

- **Status:** Proposed
- **Date:** 2026-10-31
- **Decision owners:** Invoice Approval service, Payments, Azure Platform, Security, and Operations
- **Scope:** Proposed production payment submission flow; this ADR does not describe implemented behavior

## Context and problem statement

The current application is an ASP.NET Core 8 demo. Its `ApprovalService` changes invoice lifecycle state, and `InMemoryInvoiceRepository` holds invoice data in process memory. There is no Azure SQL persistence, outbox, Service Bus, payment worker, or PayEx client in the current application. The repository's operations scenario describes those as planned production components, not deployed implementation.

The production service is expected to process about 40,000 invoices each month. Approximately 60% of monthly volume arrives in the final three working days, with observed/design peak assumptions of roughly 80 approvals per minute. PayEx requests can time out after 30 seconds; a timeout is not proof that PayEx did not accept a payment. Audit records must be retained for seven years.

The business asks for “exactly-once” payment processing. A database and a message broker cannot atomically commit with an independent payment provider. Therefore, the system cannot promise exactly-once external effects solely through local transactions, message deduplication, or retries. The practical objective is:

1. Atomically record an approved invoice, one logical payment submission intent, and its audit event in Azure SQL.
2. Reliably deliver that intent for asynchronous processing, tolerating duplicate messages and process crashes.
3. Ensure retries of the same logical payment reuse one stable provider idempotency key.
4. Persist ambiguous outcomes and reconcile them rather than risking a second charge.
5. Claim an effectively-once external payment outcome only to the extent guaranteed by PayEx's contract and capabilities. Otherwise, stop automatic retries and require reconciliation/manual resolution.

“Exactly once” in this ADR means **at most one external payment effect for a logical payment, plus eventual completion only when the provider and operations can establish the outcome**. It is not a guarantee provided by Service Bus or the outbox.

## Current implementation versus proposal

The following are repository evidence:

- `backend/src/InvoiceApp.Domain/ApprovalService.cs` implements `Submit`, `Approve`, and `Reject`; approval changes invoice status and records the approver and timestamp.
- `backend/src/InvoiceApp.Api/InMemoryInvoiceRepository.cs` implements the repository using an in-memory list.
- `backend/src/InvoiceApp.Api/Program.cs` registers that in-memory repository and `ApprovalService`.
- `ops/README.md` explicitly says its production scenario assumes a database, message topic, and PayEx integration that are not in the code.

All Azure SQL, outbox, publisher, worker, Service Bus, PayEx, reconciliation, and retention controls in this ADR are **proposed and not implemented**.

## Decision drivers and constraints

- Prevent a second logical payment when an approver, API client, publisher, broker, or worker retries.
- Make invoice approval, payment submission intent, and the audit event one atomic SQL commit.
- Treat the outbox publisher and Service Bus delivery as at-least-once; duplicate publication and delivery are normal cases.
- Keep each logical payment's provider key stable across attempts, worker restarts, and message redelivery.
- Treat a timeout or lost connection after sending a request as ambiguous unless PayEx establishes the result.
- Never resolve an ambiguous attempt by generating a new key and blindly resubmitting.
- Separate invoice approval state from payment submission state. An approved invoice is not necessarily a paid invoice.
- Handle peak bursts and long provider calls without holding a SQL transaction open during network I/O.
- Preserve a traceable, access-controlled audit history for seven years.
- Make provider guarantees, Azure configuration, and operating procedures explicit and testable.

### Workload implications

Sixty percent of 40,000 monthly invoices is approximately 24,000 in the final three working days (about 8,000 per day if evenly distributed). A peak of 80 approvals/minute is about 1.33 approvals/second. These figures are planning inputs, not a capacity proof. They favor buffering and controlled concurrency, but require validation against actual burst shape, payment latency, SQL limits, provider quotas, and recovery-time objectives.

## Approaches considered

Exactly these three approaches were evaluated.

| Approach | How it works | Duplicate prevention | Crash and retry behavior | PayEx accepts, response times out | Concurrency | Operational complexity | Build cost / ongoing running cost | Advantages | Disadvantages |
|---|---|---|---|---|---|---|---|---|---|
| **1. Idempotency key + deduplication table** | The API transactionally records the approved invoice, one payment-submission/deduplication row, and audit event in SQL. The API then calls PayEx synchronously using the stored stable key. A repeat command finds the existing row rather than creating a second logical payment. A recovery process is still needed for committed rows whose API process crashed before making or finishing the provider call. | A SQL unique constraint prevents duplicate logical submissions; provider-side idempotency with the same key is required to suppress duplicate external effects. SQL deduplication alone cannot prevent PayEx from charging twice. | Before SQL commit, transaction rolls back and the request can be retried. After commit but before provider call, the durable row needs a sweeper/retry/reconciliation path. After request acceptance but before the response is persisted, retry must reuse the same provider key; without proven provider idempotency, mark Unknown and reconcile. | Persist `Unknown`; query PayEx by key/reference or use a settlement report. Retry with the same key only if PayEx's contract guarantees safe replay within its retention window. Never mint a new key for the same logical payment. | SQL uniqueness and conditional state updates serialize logical creation. Provider idempotency is still required for concurrent requests that pass application checks or for response-loss retries. Long synchronous calls consume API capacity. | Medium. Requires deduplication/state schema, provider-call timeouts, durable recovery, and alerting. API availability is coupled to PayEx latency unless the API returns after persisting intent and moves processing off-request (which begins to converge on approach 2). | Medium initial build; low-to-medium infrastructure cost without a broker/worker, but API capacity, provider-call duration, recovery jobs, and operational handling can raise cost. Actual spend depends on SQL HA/retention, provider pricing, and traffic. | Small component count; straightforward synchronous user feedback; durable command deduplication. | Does not close the SQL-to-PayEx atomicity gap. Request threads wait on PayEx; scale and availability are coupled. Recovery after a crash requires an additional mechanism. Ambiguous outcomes remain dependent on PayEx. |
| **2. Transactional outbox + background worker** | One SQL transaction updates approval, inserts one `PaymentSubmission`, appends the audit event, and inserts an outbox event. A publisher repeatedly publishes undispatched events to Service Bus and marks them dispatched after broker acknowledgment. A worker consumes at-least-once messages, claims the durable submission, and calls PayEx using the stable key. | A SQL unique constraint ensures one submission per logical operation; worker state/lease and conditional updates ensure duplicate messages do not create a second logical submission or concurrently initiate uncontrolled work. Service Bus duplicate detection can be an optimization, not the correctness boundary. PayEx idempotency or authoritative reconciliation is necessary to bound external duplicate effects. | SQL transaction failure leaves none of approval/submission/audit/outbox committed. Publisher crash before publishing leaves the event for a later poll; crash after broker acknowledgment but before marking dispatched can publish a duplicate. Worker crash before calling PayEx can be retried. Crash after PayEx acceptance but before saving the result is ambiguous; mark/derive `Unknown`, retain the same key, and reconcile. | `Unknown` is durable and blocks a new logical payment/key. Query provider status or settlement evidence. Repeat the same key only if PayEx confirms that idempotency is enforced and retained for the relevant interval; otherwise pause for manual reconciliation. | SQL unique constraints plus optimistic concurrency/rowversion and short-lived worker leases coordinate concurrent API requests, publishers, and workers. Do not hold SQL locks or a transaction over the PayEx call. Fence stale worker attempts when persisting results. | Highest of the three. Requires schema/migrations, outbox claim/publish, Service Bus, worker lifecycle, state machine, retries/DLQ, observability, reconciliation, and operational runbooks. | Highest initial build and more Azure components to operate. Ongoing cost includes SQL, Service Bus, worker/publisher hosting, logs/alerts, backups, and seven-year audit storage. Provides buffering, independent scaling, and avoids blocking the API on a 30-second provider call. Price only after region/SKU/HA/retention/throughput assumptions are known. | Atomic local intent; resilient to broker/provider outages; scales consumers independently; durable, inspectable processing state; duplicate delivery is expected and controlled. | More moving parts and delayed payment completion; outbox and broker still do not provide exactly-once external effects; must manage poison messages, stale leases, key expiry, provider ambiguity, and eventual consistency. |
| **3. Optimistic payment submission + nightly reconciliation** | On approval, record the submission as sent/assumed successful (or otherwise optimistically advance state), then compare internal records with PayEx status or settlement reports nightly and correct discrepancies. For this comparison, approval/submission/audit still need one SQL transaction; a durable submission record is required to reconcile. | Local unique constraints can prevent duplicate logical rows, but optimistic status is not a provider-side duplicate guard. Avoiding external duplicate effects still requires PayEx idempotency or withholding retry until reconciliation establishes the first outcome. | A crash before sending can leave a false “submitted/paid” state; a crash after provider acceptance can leave an unrecorded charge; delayed nightly reconciliation means the discrepancy persists. Recovery depends on complete provider reports, replayable internal evidence, and manual/automated correction. | Record the outcome as unknown, not paid. Nightly reconciliation may eventually find the charge, but delay leaves the business state uncertain. Do not retry with a new key while unresolved. If the provider report is late/incomplete, escalate manually. | SQL uniqueness protects local creation; a conditional state transition is needed. There is no synchronous claim/lease around the external call unless separately added. Concurrent retries may still submit duplicates. | Low initial complexity only if “optimistic” is interpreted loosely; production-grade reconciliation, report ingestion, matching, exception queues, and manual controls make it medium-to-high. | Potentially lower initial infrastructure cost without a continuously running worker/broker, but report ingestion, delayed detection, support effort, and financial exception handling add ongoing cost. | Simple initial path; reconciliation can detect provider/internal mismatches and supports settlement control. | Does not prevent duplicate charges by itself; falsely confident status; slow detection; weak recovery time; relies on reliable complete settlement data. Not sufficient as the primary payment safety mechanism. |

Approaches 1 and 3 still must atomically persist approval, payment intent, and audit event in SQL to meet the stated business requirement. The distinction is that approach 1 calls the provider from the request path and approach 3 relies on optimistic state plus periodic reconciliation; neither provides the outbox's durable, independently retried dispatch path.

## Selected approach and rationale

Select **Approach 2: transactional outbox + background worker**, with a stable provider idempotency key, durable payment state machine, SQL uniqueness/concurrency controls, and provider reconciliation.

This best addresses burst load, a 30-second PayEx timeout, process crashes, and asynchronous recovery. It allows approval to commit its business decision and durable payment intent without waiting for PayEx, and it keeps the API path independent of provider latency. It makes the internal intent reliable; it does not make an external side effect exactly-once.

### Required conditional guarantee

The service may claim **effectively-once payment effect per logical payment** only if:

1. PayEx atomically deduplicates requests by the submitted idempotency key, with documented scope and payload-mismatch behavior.
2. The same key remains valid for longer than the maximum automated retry, outage recovery, replay, and reconciliation window—or the system stops replay before expiry and resolves the operation first.
3. Duplicate responses can be interpreted as the original operation's status/result (or can be followed by an authoritative status query).
4. The system never issues a new key for an unresolved attempt of the same logical payment.
5. Internal unique constraints and state transitions prevent creation of a second logical submission.

If any provider condition is absent or not contractually supported, the system cannot automatically guarantee no duplicate external effect and eventual payment completion simultaneously. It must preserve the ambiguous state, stop automatic resubmission when safe replay cannot be established, and route the case to provider-supported or manual reconciliation.

## End-to-end payment flow

1. An authorized approver submits an approval command. The API validates the invoice and command identity.
2. In one Azure SQL transaction, the application:
   - transitions the invoice to the approved state using a concurrency check;
   - inserts exactly one `PaymentSubmission` for the logical payment, initially `Pending`;
   - appends the corresponding audit event; and
   - inserts a versioned outbox event referencing the payment submission.
   The transaction commits all four changes or none. No PayEx request is made inside this transaction.
3. The outbox publisher claims ready events with a short database lease, publishes a message to Azure Service Bus, and marks the outbox event dispatched only after broker acknowledgment. If it crashes between publish and marking, it republishes; the consumer must tolerate the duplicate.
4. Service Bus delivers at least once. The worker validates the message and claims the existing `PaymentSubmission` using a short SQL transaction, a lease, and optimistic concurrency. A duplicate message does not create another submission.
5. Before calling PayEx, the worker persists an attempt and the stable key associated with that payment. It then calls PayEx outside any SQL transaction.
6. On a definitive provider acceptance, the worker records provider reference, response, state, and audit event in SQL, then completes the broker message. A definitive decline/failure is recorded according to the agreed business policy.
7. On transient failure proven to have occurred before PayEx could accept the request, retry with bounded backoff and the same key. If acceptance may have occurred, transition to `Unknown` and reconcile; do not blindly retry or generate a new key.
8. Reconciliation queries PayEx by key/reference when supported, otherwise matches settlement reports and escalates mismatches. It records the evidence and final state. A retry is permitted only after the outcome is safely established or PayEx guarantees idempotent replay with the same key.

## Payment state machine

The following is a proposed durable state machine, not a current application feature:

```text
Pending
  -> InFlight
       -> Succeeded
       -> Declined                 (definitive provider result)
       -> RetryScheduled           (definitively not accepted; same key)
       -> Unknown                  (request may have been accepted)

RetryScheduled -> InFlight         (same logical payment and same key)
Unknown
  -> Succeeded                     (provider confirms acceptance)
  -> Declined                      (provider confirms definitive failure)
  -> RetryScheduled                (provider proves no payment was accepted,
                                    or same-key replay is contractually safe)
  -> ReconciliationRequired        (provider status unavailable/ambiguous)

ReconciliationRequired
  -> Succeeded | Declined | RetryScheduled
                                    (only with documented evidence and
                                     authorized transition)
```

`Pending`, `InFlight`, `RetryScheduled`, `Unknown`, and `ReconciliationRequired` are not paid states. Only a definitive provider result or approved reconciliation evidence may transition to `Succeeded` or `Declined`. Use guarded transitions, attempt IDs, row versions/fencing, and append-only audit events. A stale worker must not overwrite a newer reconciliation decision.

## Failure scenarios

| Failure point | Durable state / observed outcome | Required recovery |
|---|---|---|
| Approval SQL transaction fails before commit | No approved transition, payment row, audit event, or outbox event is committed | Return a failure; retry the approval command safely. Do not call PayEx. |
| API crashes after SQL commit, before responding | Approved invoice, payment row, audit event, and outbox event exist; client may retry | Return existing approval/payment result for the same logical operation. Unique constraint prevents a second submission. Publisher eventually sees outbox row. |
| Publisher crashes before broker publish | Outbox event remains undispatched/lease expires | Poll and publish later; alert on outbox age/backlog. |
| Publisher publishes, then crashes before marking dispatched | Broker may contain message while outbox still appears ready | Publish again after lease; duplicate is expected. Worker deduplicates via durable `PaymentSubmissionId` and state. |
| Service Bus unavailable | SQL intent/outbox remains durable; queue delivery is delayed | Publisher retries with backoff; monitor oldest outbox age and SQL growth. Apply an agreed backpressure policy if outage exceeds safe buffer/SLO. |
| Duplicate/reordered Service Bus messages | Multiple deliveries may refer to the same payment | Unique submission row and guarded state transition/lease permit at most one active claim. Complete duplicates after confirming durable state; do not create a new logical payment. |
| Worker crashes before external call | Attempt may be absent or `InFlight` lease expires; provider was not called only if this is provable from persisted execution ordering | Recover expired lease. Retry with the same key. If the system cannot prove request was not sent, classify as `Unknown` and reconcile. |
| PayEx returns a definitive success; worker crashes before saving it | PayEx may have charged; local state lacks confirmation | Expired in-flight attempt becomes `Unknown`; query by key/reference. If resubmission is supported, use only the same key under contract guarantees. |
| PayEx request times out at about 30 seconds / connection drops after send | Acceptance is unknown; timeout is not a decline | Persist `Unknown`, stop new-key retries, query PayEx/status report, and escalate if unresolved. Never assume failure from timeout alone. |
| PayEx returns a definitive decline | Provider has rejected the request, subject to contract semantics | Persist `Declined` and evidence; retry only if business/provider rules define a safe retryable decline, with the same logical operation and key as applicable. |
| PayEx outage / throttling | Calls fail or time out; some may have been accepted | Bound concurrency, use exponential backoff with jitter and circuit breaking for known transient failures. Distinguish proven pre-acceptance failures from ambiguous outcomes. Do not hot-loop or rotate keys. |
| Worker cannot persist a provider response because SQL is unavailable | External effect may have happened but result is not durable | Do not acknowledge as completed. On recovery, treat stale in-flight attempt as `Unknown`, reconcile before deciding to call again. |
| Poison message / retry limit reached | Message is dead-lettered; payment row remains durable and should not be marked paid | Alert and inspect. Reconcile provider status before controlled redrive. A dead-letter replay uses the same payment ID/key and records operator/action audit. |
| Nightly/periodic reconciliation finds provider payment missing internally or internal submission absent in provider report | Mismatch, delayed settlement, or incomplete provider evidence | Keep unresolved state; compare amount/currency/reference/time window; handle late reports and duplicate rows; route to finance/operations. Do not automatically create a replacement payment. |
| Provider idempotency key has expired while outcome remains unknown | Safe replay guarantee may have expired | Do not submit again automatically. Use authoritative status/settlement evidence or provider escalation/manual financial control. |
| Two approval requests race for one invoice | Concurrent state transition attempts | Conditional update/rowversion allows one winner; unique logical-operation constraint ensures one payment submission. Loser reads existing state and returns a conflict or existing result per API contract. |

## Idempotency key design

- Generate a cryptographically random `PaymentSubmissionId` once when inserting the logical payment in the approval SQL transaction. It is the durable identity of the external payment operation.
- Derive the provider key deterministically from a versioned namespace and that immutable ID, for example `invoice-payment-v1:<PaymentSubmissionId>` if PayEx's allowed syntax/length supports it. Otherwise map the ID to a stable opaque representation. Persist the exact submitted key; never regenerate it per delivery or attempt.
- Do not put customer names, invoice amount, credentials, or other sensitive data in the key. Use tenant/account scoping only as required by PayEx's documented uniqueness scope.
- Bind the key to an immutable request payload fingerprint (amount, currency, payee, and operation identity). Reusing the key with a changed payload must be rejected locally and audited; never mutate an existing logical payment payload.
- A new payment operation/key is allowed only for a separately authorized logical payment after prior status is definitively resolved and any required reversal/cancellation/adjustment workflow is complete. It is not a retry strategy.
- Confirm maximum key length/character set, uniqueness scope (merchant/account/endpoint), retention duration, concurrent duplicate behavior, payload mismatch behavior, and whether duplicate responses return the original result.
- Retain key/reference mappings at least as long as required for automated retry, dispute support, reconciliation, and audit policy. Key retention must not exceed/contradict data retention or privacy rules.

## Data model and constraints to consider

Names are illustrative; schema design and migration strategy require review.

### `Invoices`

- Invoice ID primary key; status; immutable approved payment amount/currency/payee snapshot or a link to the approved version; approver and UTC decision timestamp.
- `rowversion`/equivalent concurrency token.
- State transition constraint/checks where practical. Do not use invoice status alone to imply payment success.

### `PaymentSubmissions`

- `PaymentSubmissionId` primary key.
- Invoice ID foreign key; logical operation type/version; amount/currency/payee snapshot; provider/merchant account identifier.
- Stable provider idempotency key and request fingerprint.
- Status/state; attempt count; next-attempt time; lease owner/expiry and fencing/version; last error classification.
- Provider reference, definitive response metadata, `UnknownSince`, reconciliation outcome/evidence reference, created/updated UTC times.
- Unique constraint on the intended logical payment identity, e.g. `(InvoiceId, PaymentOperationType, OperationVersion)`. The business must define when operation versions can increase.
- Unique constraint on provider idempotency key within the provider's actual key scope (or provider/account/key composite).
- Guard updates with state predicates and rowversion so stale workers cannot overwrite final/reconciled state.

### `Outbox`

- Outbox event ID primary key; event type/schema version; aggregate/payment ID; minimized payload or reference; created time; dispatch state; attempt count; next attempt; lease/claim metadata; dispatched time.
- Unique constraint on `(PaymentSubmissionId, EventType, EventVersion)` to prevent generating multiple intents for the same logical operation.
- Index for ready/expired claims and oldest undispatched event.
- Do not mark dispatched until broker acknowledgment. The publish/mark gap intentionally allows duplicate publication.

### `AuditRecords`

- Append-only event ID; entity/payment ID; event type; actor/system identity; UTC timestamp; correlation/causation IDs; old/new state or safe change summary; provider reference and evidence pointer as appropriate.
- No credentials, full payment secrets, or unnecessary personal/payment data. Restrict updates/deletes and log privileged access.
- Retention and archive controls for seven years, with legal hold and deletion behavior defined by policy.

Avoid one large transaction spanning Azure SQL, Service Bus, and PayEx. Only the local approval/submission/audit/outbox records are atomic together.

## Retry, dead-letter, and operational monitoring

- **Outbox publisher:** short SQL claim transaction/lease; bounded retries with jitter; publish then mark dispatched after acknowledgment; handle lease expiry; alert on publisher health, oldest pending event, backlog size, and repeated publish failures.
- **Service Bus:** treat delivery as at-least-once regardless of broker duplicate-detection settings. Use a message ID based on the logical payment/outbox event for diagnostics/optional broker-side duplicate detection, not as the only dedupe mechanism. Configure lock duration/renewal, delivery count, TTL, DLQ retention, and capacity with the platform team.
- **Worker:** bounded concurrency/rate limits coordinated with PayEx quotas; durable per-attempt state; exponential backoff with jitter for known transient failures; circuit breaker for provider outage. Do not endlessly requeue an ambiguous payment. Persist `Unknown`/`ReconciliationRequired` and defer resolution to reconciliation.
- **Acknowledgment:** acknowledge a message only after the worker has durably saved a state that makes redelivery safe. If SQL is unavailable, do not acknowledge an unrecorded result.
- **Dead-letter:** alert with payment ID/correlation ID, not sensitive payload; inspect failure cause; verify provider status before redrive; require authorization for replay; record operator, evidence, and outcome in audit. Redrive retains original payment ID and key.
- **Reconciliation:** run at a cadence agreed with PayEx settlement/status freshness. Compare local submissions, provider status/query results, and settlement reports; account for time zones, late settlement, reversals, fees, and partial/multiple provider reports. Produce aging queues for `Unknown` and mismatches with named ownership and escalation.
- **Core metrics/alerts:** approval-to-outbox latency; oldest undispatched age; outbox backlog and publish failures; queue depth/oldest age; worker throughput/concurrency; retries and DLQ count/age; PayEx latency, timeout, throttling, and error rates; `Unknown` count/age; reconciliation mismatch count/age; SQL deadlocks/availability; audit write failures and retention/archive health.
- **Operational limits:** define SLOs, alert thresholds, maximum retry duration, provider outage backpressure, manual approval for replay, recovery objectives, and customer/finance communication. Test these in load and failure-injection exercises.

## Security and seven-year audit implications

- Use managed identities where supported for App Service/worker access to SQL, Service Bus, and secret storage. Separate identities and least-privilege permissions by workload. Keep PayEx credentials in an approved secret store with rotation and access auditing; never log them.
- Enforce TLS for service-to-service and provider calls, private network access where required, encryption at rest, and controlled egress to PayEx. Threat-model replay, forged messages, compromised workers, and unauthorized state transitions.
- Authenticate approvers and authorize role checks in the API. The current demo session mechanism is not evidence that production identity/security is implemented.
- Append audit events for approval, logical submission creation, every attempt/state transition, provider result/reference, timeout ambiguity, reconciliation evidence, manual action, replay, and access to sensitive records. Use correlation IDs across API, SQL, outbox, broker, worker, and PayEx.
- Define whether “seven years” is measured from invoice creation, payment completion, or another legal trigger. Compliance/legal must decide record scope, immutability/WORM needs, permitted corrections, legal holds, privacy deletion conflicts, archival tier, retrieval time, and end-of-retention deletion.
- Validate backup and restore, archive integrity, access review, encryption key lifecycle, and a retention/deletion test. A timestamp field or a stated policy alone does not enforce seven-year retention.

## Build cost and ongoing operational cost

No Azure prices or effort estimates are asserted here. Region, service tiers, availability requirements, message size/rate, database growth, log retention, and PayEx pricing are not yet established.

| Approach | Relative build cost | Main ongoing cost drivers |
|---|---|---|
| Idempotency key + dedup table | Medium; schema, synchronous provider client, request dedupe, timeout/recovery path, and provider-contract tests | API capacity held during provider calls, SQL, provider fees, monitoring, recovery support, and any sweeper/reconciliation job |
| Transactional outbox + worker (selected) | High; atomic SQL model, outbox leases/publisher, Service Bus, worker/state machine, idempotency, DLQ, reconciliation, runbooks, load/failure tests | Azure SQL/HA/backups/storage, Service Bus operations/capacity, worker and publisher compute, observability, seven-year audit retention/archive, provider fees, and on-call/reconciliation effort |
| Optimistic submission + nightly reconciliation | Low-to-medium only for a prototype; production-grade report ingestion, matching, exception workflow, and safe replay increase effort | Reconciliation/report storage and compute, delayed-discrepancy support/finance labor, audit retention, provider fees, and potentially higher loss/duplicate-payment exposure |

Obtain a cost estimate using the approved Azure region and Pricing Calculator. Include production and non-production environments, SQL HA/backup/storage growth, Service Bus tier/operations, worker minimum and burst scale, network/egress, monitoring ingestion/retention, seven-year audit storage/retrieval, and disaster-recovery requirements. Obtain PayEx transaction, idempotency, status-query, and settlement-report costs separately. Compare the estimate with measured load tests at and above the 80-approvals/minute peak and recovery bursts.

## Consequences and trade-offs

### Positive

- Approval and payment intent cannot be separated by an application crash after SQL commit.
- Payment work is buffered and independently scaled; API availability is not tied to a 30-second PayEx response.
- Duplicate publishing and broker redelivery are first-class expected behavior.
- Durable per-payment state allows safe retries, explicit ambiguity, operational review, and audit.
- Stable keys plus provider contract support can suppress duplicate provider effects for the same logical operation.

### Negative / residual risk

- The architecture adds services, schema, deployment, monitoring, and on-call responsibilities.
- Payments complete asynchronously; UI and downstream consumers must distinguish “approved/pending payment” from “paid”.
- An outbox cannot atomically commit with PayEx. A successful provider request followed by lost response remains ambiguous without provider idempotency/status evidence.
- Key expiry, provider eventual consistency, incomplete settlement reports, or provider outages can require manual holds and delay payment.
- At-least-once delivery and retries may increase provider traffic; rate limits and overload behavior need testing.
- Seven-year audit storage and retrieval create cost and compliance obligations.

## Open questions and assumptions requiring confirmation

### PayEx contract / Payments team

1. Does PayEx support idempotency keys for this payment endpoint? Is enforcement atomic across concurrent requests?
2. What is the key scope, format/length limit, and retention/expiry period? Is the original response returned for duplicates?
3. What happens when the same key is reused with a different payload?
4. Can status be queried by idempotency key, merchant reference, or provider reference? What are consistency delay, retention, rate limits, and authoritative terminal statuses?
5. Are settlement reports complete and uniquely matchable? What is their delivery cadence, correction/reversal behavior, and retention?
6. Which errors prove the request was not accepted, versus requiring `Unknown`? What retry guidance and rate limits apply?
7. What are payment cancellation, reversal, partial payment, currency, and duplicate-charge escalation procedures?

### Azure / Infrastructure team

1. Which hosting service will run publisher, worker, and reconciliation? Confirm scaling, graceful shutdown, lease behavior, identity, network, availability zones/regions, and deployment model.
2. Which SQL tier/HA/backup/restore objectives, Service Bus tier, duplicate-detection configuration, lock duration, TTL, delivery count, and DLQ retention meet requirements?
3. What are peak burst and recovery throughput targets, quotas, backlog limits, and backpressure policy when SQL, Service Bus, or PayEx is unavailable?
4. How are private endpoints, egress restrictions, managed identities, secret management, key rotation, monitoring, and disaster recovery implemented?

### Security, Compliance, Finance, and Operations

1. What identity provider, approver role source, service identity, and privileged replay approval are required?
2. What exactly is covered by seven-year retention, and what is the legal retention trigger, immutability requirement, legal hold process, privacy/deletion rule, and retrieval objective?
3. Who owns `Unknown`, DLQ, and reconciliation queues, and what are response SLAs, escalation contacts, and manual controls?
4. What evidence is required to classify a provider outcome as definitive and authorize retry/replay?
5. What customer/finance status should be shown while payment is pending or unknown?
6. What business action is allowed if PayEx cannot resolve an ambiguous outcome before the key expires?

Until these are answered, the design is a proposed pattern, not a claim that external payment effects are exactly once.

## Where the agent was wrong or useless

No prior suggestion in this AI-assisted design process has been verified as technically false based on the repository evidence reviewed for this ADR. The following **confirmed incompleteness** should be addressed before treating the prior diagram as an implementation-ready design:

- The target diagram labels a stable key derived from `PaymentSubmissionId` and says to enforce a unique submission, but it does not specify the provider's idempotency-key scope, retention/expiry, concurrent duplicate semantics, or payload-mismatch behavior. A local stable key is not, by itself, proof that PayEx will deduplicate.
- The target diagram shows an `Unknown` timeout path and reconciliation, but does not define a full durable payment state machine, a rule preventing key rotation while unresolved, or a stale-worker fencing/concurrency protocol.
- The diagram says status lookup is “if supported” but does not establish that PayEx offers an authoritative query or complete settlement report. If neither is available, the recovery path and achievable guarantee remain unresolved.
- The architecture discussion names Azure SQL, Service Bus, and worker components without approved deployment tiers, quotas, hosting choice for background processes, retention implementation, or measured capacity/cost. These remain decisions for the Azure, Compliance, and Operations teams, not verified architecture facts.

These are gaps in the proposed design artifacts, not evidence that the components exist or that the previous design caused a production defect. Human reviewers should amend this ADR when contract, infrastructure, and operational evidence is available.
