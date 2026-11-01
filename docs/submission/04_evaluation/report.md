# Review prompt evaluation

## Status and method

The original prompt is preserved verbatim in [ops/evals/README.md](../../../ops/evals/README.md). The comparison prompt adds only a request to examine concurrency, authorization, state transitions, failure/retry behavior, data consistency, and side effects. The target design was a matched 3-run comparison of both prompts over the same 12 cases (72 fresh sessions).

Cases 11 and 12 are saved as [case-11.diff](../../../ops/evals/cases/case-11.diff) and [case-12.diff](../../../ops/evals/cases/case-12.diff). The concurrency regression test passed on the unmodified implementation and failed on case 11 because both approvals succeeded. The existing seven `ApprovalServiceTests` passed against case 12's refactoring.

The full comparison could not be completed in this run. The isolated-session tool reached its limit of 50 new sessions per hour before the 72-session plan was done. Of the sessions started, 15 complete assistant responses were retrievable for scoring: seven baseline-prompt responses and eight comparison-prompt responses. The remaining records are not treated as findings or negatives. The response excerpts and scoring for the retrievable sessions are in [results.csv](./results.csv).

## Partial observed metrics

Ground truth was traced against the application and its stated conventions. Cases 3 and 7 are marked uncertain: the repository does not specify a monetary rounding policy or prohibit the logged invoice fields. Those rows are excluded from metrics rather than counted as defects or false alarms.

| Prompt | Scored responses | Caught / actual defects | Recall | Miss rate | False alarms / clean cases | False-alarm rate | Precision |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline v1, partial run 1 | 6 | 3 / 3 | 100% | 0% | 1 / 3 | 33.3% | 75% |
| Comparison v2, partial run 1 | 6 | 5 / 5 | 100% | 0% | 0 / 1 | 0% | 100% |

These are descriptive partial-set figures, **not a valid prompt comparison**: the cases scored differ between prompt versions, and only three known-ground-truth cases overlap. On those overlapping cases (8, 11, and 12), both prompts had the same outcomes: both defects were caught and the clean refactor was not reported as defective.

## Conclusions

- **Did v2 improve defect detection?** Not demonstrated. The partial observations show no improvement on the three paired, scorable cases.
- **Did v2 increase false alarms?** No increase is visible in the partial observations, but the comparison is too small and unbalanced to establish a rate change.
- **Was the result consistent across three baseline runs?** This could not be assessed; complete baseline responses from three runs were not retrievable.
- **Confidence:** Very low. Only 12 of 15 retrievable responses had determinate ground truth, the prompt versions did not have complete matched coverage, and the repeated-run requirement was unmet.
- **Deployment recommendation:** Do not use this evidence to deploy the reviewer as an automated PR gate. It may be used as an advisory reviewer with human verification while the full matched evaluation is completed.
