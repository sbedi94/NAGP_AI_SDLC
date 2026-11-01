# Incident Summary Autonomy Policy

- **Status:** Proposed — governance policy; not evidence of implemented agent access or controls
- **Policy owner:** Proposed: Invoice Approval service owner
- **Applies to:** AI-assisted first-response incident summaries for the Invoice Approval service

## 1. Purpose and scope

This policy governs AI use to summarize incident logs and metrics for an ASP.NET Core 8 service hosted on Azure App Service in the proposed production architecture. It applies to a six-person engineering team, including two engineers new to the service, and 24x7 on-call operations. It does not grant infrastructure, agent, or production access. Production deployment and operational automation are high-impact and require the controls and approvals below.

## 2. Autonomy levels

| Level | Allowed activities | Restrictions | Required controls |
|---|---|---|---|
| **L0 — Manual investigation** | Engineers inspect incident evidence and write summaries manually. | No agent actions or AI-generated incident findings. | Preserve source evidence and use normal incident records. |
| **L1 — Assisted drafting (recommended day one)** | AI drafts a summary only from logs and metrics an engineer explicitly supplies. It may identify suspected causes, affected components, timelines, and suggested investigation steps. | AI cannot declare resolution, modify production data, restart services, change configuration, or deploy code. No autonomous evidence collection. | Engineer verifies every material finding and evidence reference before sharing or recording it. Label hypotheses as hypotheses and unknowns as unknown. Preserve originals. |
| **L2 — Bounded read-only investigation** | Agent collects only explicitly approved logs and metrics, correlates events, and creates structured incident reports. | Read-only access only; no production-changing actions or deployment. | Least-privilege scoped access, approved source/time window, data redaction, evidence links for material claims, and auditable access and outputs. |
| **L3 — Pre-approved low-risk operational actions** | Agent performs only explicitly allowlisted, reversible, low-risk actions. | No unrestricted shell, arbitrary production changes, payment operations, or deployment permissions. | Strong authorization, action allowlist, complete audit trail, tested rollback procedure, monitoring, defined limits, and immediate human escalation on unexpected results. |

## 3. Day-one recommendation

Adopt **L1** for day one. It provides drafting assistance without granting an agent production access or operational authority. Because two engineers are new to the service, a named experienced engineer or incident lead must verify the summary; AI output must not substitute for service knowledge, evidence review, or incident-command judgment. L1 does not assume that any agent integration or control has been implemented.

## 4. Accountability and incident safeguards

- The on-call engineer prepares or reviews the summary. A designated experienced engineer/service owner verifies material technical findings and evidence references, especially when the incident author is new to the service.
- The incident commander or designated human incident lead owns severity, diagnosis decisions, mitigation, communications, and the decision that an incident is resolved. AI output is advisory and is never the incident source of truth.
- Every material claim must link to the supplied or approved source evidence. Unsupported statements must be removed or clearly labelled as hypotheses; unknown facts must be labelled **unknown**.
- AI must not declare an incident resolved. At L1 and L2, it must not change production data, restart services, change configuration, deploy code, or perform payment operations.
- Preserve original logs, metrics, and incident records. AI summaries are derived artifacts and must not overwrite source evidence. Redact secrets and sensitive data before use.

## 5. Promotion criteria and approval authority

Promotion above L1 requires all of the following: at least **30 representative incident-summary evaluations**; **zero critical unsupported findings** in the validation sample; verified source links for material findings; approved access controls and redaction; and approval from the service owner and Security.

These are **proposed governance roles**, not evidence that such approvals or controls currently exist:

- **L1 → L2:** Service owner and Security approval.
- **L2 → L3:** Service owner, Security, and Operations approval, plus documented rollback testing.

Record evaluation results, approval, permitted data/actions, and the effective policy level before promotion. Approval is scoped; it does not grant general agent access.

## 6. Rollback, review, and policy ownership

Immediately suspend AI use at the affected level and revert to the prior approved level upon any critical fabricated or unsupported finding, secret/sensitive-data exposure, unauthorized access or action, missing or incorrect evidence links, repeated inaccurate summaries, or audit failure. Preserve evidence, notify the incident lead and Security as appropriate, investigate, and require re-approval before promotion resumes.

The proposed policy owner is the Invoice Approval service owner, with Security and Operations as reviewers. Review this policy at least every six months and after any material incident, data-access change, model/tool change, or policy-triggering failure. Revalidate evaluation results and access controls before each autonomy-level promotion.
