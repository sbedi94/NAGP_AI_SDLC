# Task 5 --- Security Risk Audit

## Verdict

The repository does **not** evidence a complete, active lethal trifecta.
It does contain a conditional path to consequential actions and
untrusted content if an agent uses the configured browser tool against a
running application. Actual access to sensitive production data is not
evidenced.

## Trifecta assessment

  ----------------------------------------------------------------------------
  Trifecta leg                        Evidence and assessment
  ----------------------------------- ----------------------------------------
  **Sensitive data access**           The invoice model has fields that could
                                      be sensitive if populated with real
                                      records---customer name, amount, and
                                      decision note (`Invoice.cs:3–12`). The
                                      running demo uses an in-memory
                                      repository seeded with illustrative
                                      records
                                      (`InMemoryInvoiceRepository.cs:5–18`);
                                      the app README describes it as local and
                                      in-memory and labels its accounts as
                                      demo-only (`README.md:3, 11–18`). Ops
                                      artifacts describe a planned production
                                      system, not the current app, and state
                                      that names, hosts, and figures are
                                      invented (`ops/README.md:15–23`). No
                                      actual sensitive production-data access
                                      is shown.

  **Untrusted content**               The API accepts user-supplied customer
                                      names and rejection reasons
                                      (`InvoicesController.cs:20, 47–64`;
                                      `ApprovalsController.cs:19, 25–27`). A
                                      browser agent could encounter such
                                      content, but the repository does not
                                      show an LLM ingesting it or an agent
                                      runtime directing it into model
                                      instructions. `AGENTS.md` contains
                                      project conventions; `CLAUDE.md` only
                                      includes that file (`AGENTS.md:1–23`;
                                      `CLAUDE.md:1`).

  **Consequential actions**           The app implements invoice creation,
                                      submission, approval, rejection, and
                                      deletion (`InvoicesController.cs:47–75`;
                                      `ApprovalsController.cs:21–27`). API
                                      access requires a bearer session
                                      (`SessionAuthMiddleware.cs:3, 18–35`);
                                      approvals require the Approver/Admin
                                      role and deletion requires Admin. The
                                      MCP config launches Playwright and
                                      registers a remote Mermaid MCP endpoint
                                      (`.mcp.json:4–10`). These are configured
                                      capabilities, not evidence that an agent
                                      invoked them against this app or a
                                      deployed service.
  ----------------------------------------------------------------------------

## Configuration and operational context

The Mermaid MCP entry is an external service; content deliberately
supplied in tool requests could therefore leave the local environment.
The repository does not show tool invocations, production credentials,
or a connection to production data.

The ops README says its material does not run as part of the application
or tests and that the database, message topic, and payment-provider
integration are not yet in the code (`ops/README.md:3–4, 15–20`).
`INC-2047` describes read-only evidence and says production changes need
a named approver (`ops/incidents/INC-2047/README.md:18–33`). This is
workflow context, not evidence that the configured MCP tools access
those systems.

## Decision

**Accept the current configuration for local demo use only.**

Do not accept it for an agent handling real invoices or production
sessions without redesign. At minimum:

-   Keep production data and production credentials outside the browser
    agent's reach unless access is explicitly required and tightly
    scoped.
-   Require explicit human approval for invoice approvals, rejections,
    deletions, payments, and other consequential actions.
-   Enforce least-privilege roles and server-side authorization for
    every sensitive operation.
-   Treat customer names, rejection reasons, invoice content, and
    browser-visible page content as untrusted input; keep them separate
    from system and developer instructions.
-   Restrict and review external MCP services and the data sent to them.
-   Add audit logging, monitoring, and a tested rollback or recovery
    process for consequential actions.

## Evidence boundary

This assessment distinguishes repository evidence from possible runtime
behavior. The repository shows application capabilities and tool
configuration, but does not establish that an agent has used those
tools, that production data is connected, or that production credentials
are available. Reassess the risk if those conditions change.
