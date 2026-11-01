# Task 5 - Production measurement plan

Prepared: 2026-11-01

## Purpose and scope

This plan establishes a pre-on-call baseline for the invoice approval service before
moving to 24x7 support. It focuses on the requested delivery and reliability
metrics:

| Metric | Definition | Required evidence source |
| --- | --- | --- |
| Lead time for changes | Time from change start to production deployment | GitHub PR and deployment history |
| Change failure rate | Failed production changes / total production changes | Deployment history and incident records |
| Review turnaround | PR ready-for-review to first substantive review | GitHub PR timeline |

The repository does not contain production deployment history, complete incident
records tied to all production deployments, or GitHub PR review timeline data. The
available repository evidence supports two actual baseline numbers: CI execution
duration and CI success rate. These are useful 24x7 readiness signals, but they
are not substitutes for production lead time, production change failure rate, or
review turnaround.

`ops/pipeline/README.md` is referenced in the task, but it is not present in this
checkout. The available pipeline files are `ops/pipeline/run-timings.csv` and
`ops/pipeline/ci-pipeline.yml`. The pipeline timings are supplied scenario
evidence, not a live telemetry query. The latest run is dated 2026-02-02, so this
is a historical baseline for the supplied 20-run window, not a fresh November
2026 operational baseline; capture a new rolling window before the on-call
rotation starts.

## Actual baseline numbers captured

| Baseline number | Exact source | Query or calculation | Date/time window | Number of observations | Actual result | Limitations |
| --- | --- | --- | --- | --- | --- | --- |
| CI execution duration | `ops/pipeline/run-timings.csv`; `ops/pipeline/ci-pipeline.yml` confirms a single sequential GitHub Actions job named `Build, test and scan` | Group CSV rows by `run_number`; sum recorded `duration_seconds` for each run; calculate min, median, mean, nearest-rank p95 (`ceil(0.95 × n)`), and max across run totals | 2026-01-19T09:12:00Z to 2026-02-02T15:38:00Z | 20 workflow runs, 378 step timing rows | Median 31.26 minutes; mean 31.34 minutes; p95 34.70 minutes; min 28.37 minutes; max 35.13 minutes | This is the sum of recorded step durations, not measured wall-clock time; one failed workflow has only 17 step rows. The supplied scenario evidence is historical and not live telemetry. It excludes PR coding time, review time, merge wait, deployment queueing, approval gates, rollout time, and production verification. It must not be reported as lead time for changes. |
| CI success rate | `ops/pipeline/run-timings.csv` column `conclusion` | Group CSV rows by `run_number`; count runs whose conclusion is `success`; divide by total runs | 2026-01-19T09:12:00Z to 2026-02-02T15:38:00Z | 20 workflow runs | 18 successful runs / 20 total runs = 90.0% CI success rate; 2 failed runs = 10.0% CI failure rate | This is a pre-production pipeline health metric from the supplied historical scenario dataset. CI failures are not failed production changes, so this must not be reported as change failure rate. |

## Pipeline stage performance

The slowest stages in the 20-run timing history are:

| Stage | Observations | Mean | Median | p95 |
| --- | ---: | ---: | ---: | ---: |
| Static analysis | 20 | 497.1s | 480.5s | 600s |
| End-to-end tests | 19 | 223.4s | 220.0s | 328s |
| Build container image | 20 | 168.0s | 163.0s | 223s |
| Integration tests | 20 | 140.9s | 142.5s | 178s |
| Install Playwright browsers | 20 | 127.7s | 125.0s | 149s |

`End-to-end tests` and `Start application for end-to-end tests` have 19
observations because one failed run did not reach those steps.
For each stage, the summary groups rows by the `step` column and calculates
mean, median, and nearest-rank p95 from the observed `duration_seconds` values.

## Calculation detail

The CI execution duration calculation is:

```text
For each distinct run_number in ops/pipeline/run-timings.csv:
  run_total_seconds = sum(duration_seconds for that run_number)

Across the 20 run_total_seconds values:
  min = 1702s
  median = (1869s + 1882s) / 2 = 1875.5s = 31.26m
  mean = 1880.5s = 31.34m
  p95 = nearest-rank p95 = 2082s = 34.70m
  max = 2108s = 35.13m
```

The CI success rate calculation is:

```text
successful_runs = count(distinct run_number where conclusion == "success") = 18
total_runs = count(distinct run_number) = 20
CI success rate = 18 / 20 = 90.0%
CI failure rate = 2 / 20 = 10.0%
```

## DORA-style measurement status

| Requested metric | Baseline status today | Why it cannot be completed from this checkout | How to capture once deployed |
| --- | --- | --- | --- |
| Lead time for changes | Not measurable from available repository files | The available CI timing history starts when CI begins and ends before any production deployment evidence. Local Git history does not provide PR ready time, review time, merge time, or production deployment completion. | For each production deployment, store deployment environment, release id, commit SHA, deployment start, deployment completed, result, and verification result. Join the deployed commit to the merged PR and first commit or PR creation time in GitHub. Report median and p75 lead time weekly. |
| Change failure rate | Not measurable as a baseline rate from available repository files | `ops/incidents` contains scenario incident packs, but not a complete denominator of all production deployments for the same measurement window. The repository instructions also state that operations material describes a planned production version and should not be treated as current application behavior. | Maintain a production deployment ledger and incident records with fields for causing release or commit, rollback/hotfix linkage, severity, customer impact, and whether the incident was caused by a production change. Calculate failed production deployments / total production deployments for the same window. |
| Review turnaround | Not measurable from available repository files | The checkout has Git commits, but no GitHub PR timeline events showing when PRs became ready for review or when the first substantive human review occurred. | Query GitHub PR timeline events. For each PR, record `ready_for_review` time, first non-bot substantive review or review comment time, author, reviewer, and PR size. Calculate median and p75 turnaround by week. |

## Day-one instrumentation plan

- Add a production deployment record for every release, including release id,
  commit SHA, deployment start and finish time, environment, result, approver,
  rollback flag, and verification status.
- Require incident records to link back to the causing deployment when a
  production change caused or contributed to the incident.
- Add PR timeline extraction from GitHub for `ready_for_review`, first human
  review, merge time, and deployed commit SHA.
- Keep CI execution duration and CI success rate as supporting operational
  indicators, but report them separately from DORA-style production metrics.
- Establish the first production baseline after at least one complete on-call
  reporting window, with the same date window used for deployments and
  incidents.
