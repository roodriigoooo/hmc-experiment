# Export dictionary — pilot-4 and historical versions

ZIP contains UTF-8 CSV, structured `bundle.json`, exact `manifests.json`, and protocol/analysis/instrument documentation. JSON is canonical for nested values; CSV uses blank cells for nulls, never zero, and escapes formula-leading strings. Every derived row carries session, protocol, build, stimulus, questionnaire, interface and metric versions. `interface_version` is `placekeeping-4` for pilot-4, `ergonomic-3` for pilot-3, `pilot-2-interface` and `pilot-1-interface` for earlier protocols; it also appears in each new event's context and as `interface_versions` at bundle level. `metrics_versions` at bundle level is a list, not a reinterpretation of older rows. Group analyses by protocol and never pool interface versions. [Archived v1 dictionary](legacy/data-dictionary-v1.md) defines unchanged legacy fields.

Times are milliseconds. `mono` uses the client document clock; `segment` is its UUID and `origin` is `performance.timeOrigin`. UTC receipt time is transport metadata only. Never subtract across segments. Block is 1–3; order is 0–5 in pilot-4 (0–11 earlier); practice_index is 0–8 (first three demonstration, remaining six assessed). Slot/batch/episode/item are zero-based. A point object has `seq`, `mono`, `segment`.

| Table | Revised fields and interpretation |
|---|---|
| sessions | Anonymous ID, mode/synthetic, lifecycle and exclusion status, acknowledged sequence, training outcome/attempts, all version IDs and configuration snapshot. No credentials. Incomplete training is exported without allocation. |
| allocations | Permanent condition permutation, task-set permutation, B form, slot/cycle/batch. C uses the other form. No slot reclamation. |
| raw_events | UUID, sequence, clock, type, payload, UTC receipt and authoritative pre-event context (including phase, expected category and actual last submission). Append-only. `block_start` may have pre-transition practice=true. |
| practice_attempts | Demonstration/assessed stage, separate record index, attempt, condition, sequence, submissions, pass/null, start/end, interruption/card exposures. Passed requires taught selection/submission sequence and eight correct judgments in pilot-4 (four earlier). |
| submitted_checks | Every accepted main submission: category, boolean judgment, factual correctness, expected category, sequence flag, exact timestamp. Repetitions remain separate. |
| checks | All required categories of each started block: first/final judgments and correctness, attempt count, omitted, exposed, completed. Omission is incorrect. Unexposed rows are required opportunities, explicitly marked, not fabricated observations. |
| orders | Correct/first-correct numerator, denominator 8 in pilot-4 (4 earlier), exposed/completed, omissions, duplicate submissions, separate out-of-sequence selection/submission counts, premature finish, planned/missed checkpoint and reason. |
| interruptions | B/C checkpoint position/form/episode; full pre-interruption submission history; actual last submitted category; frozen expected_next_check; return-ready point; actual secondary-screen and stimulus durations; all latency/error fields; applicability, observation-window end, invalid-timing reasons, engagement counts. |
| transitions | A's invisible matched checkpoint observations, labeled ordinary_transition. No interruption recovery claim. |
| secondary_items | Five required item opportunities per actual checkpoint, pair/form/episode, displayed flag, actual onset/end/exposure, response time/choice, omission and correctness. Missing displayed onset/exposure remains null. |
| intervals | Separate secondary/pause components with endpoints, reason, same-segment duration, block-clipped interval, null/invalid reason. Preserve components even when full-block timing is unavailable. |
| questionnaire_items | Exact wording/title/anchors/step, instrument ID, displayed_response, oriented_score, answered/submitted and included_in_tlx. Drafts retained on withdrawal/incompletion. Performance uses identity orientation, 0 Perfect to 100 Failure. |
| questionnaires | Exact responses, submitted flag, answered count, Raw TLX or null, separate exploratory_tracking. Legacy custom records retain their own schema. |
| summaries | Participant × condition × block, required/exposed accuracy denominators, first/final numerators, completed/exposed orders, omissions, repetitions, separate sequence outcomes, premature finishes, planned/actual interruption exposure, timing components, workload and observation counts. |
| quality | Environment, input, document, pause and resume observations with original details. Technical concerns are separate from behavioral errors; no deletion rules. |
| annotations / audit | Append-only researcher review/exclusions and relevant operational audit. Notes should identify the relevant sequence/window; uncaptured disruptions are not assigned invented durations. |

## Revised events

`practice_start` begins the fixed demonstration; `practice_next` advances feedback to another practice order or training outcome. `select`, `judge`, `submit`, `finish` are distinct. `ack_end` retains the invisible checkpoint flag in A. `secondary_ready` starts the fixed secondary clock; `secondary_item` marks actual pair display; `secondary_response` logs accepted choice. `return` prepares restored records; `task_return_ready` marks frame-aware availability and freezes expected next category. `task_ready` marks ordinary task availability, including block start and pause resumption. `questionnaire_item` retains deliberate item responses; `questionnaire` finalizes a complete set. `environment` records visibility/viewport and participant-reported pause reasons; `input_problem` records rejected transition/duplicate activation and keyboard deviations. `pause`/`resume` bound observed disruptions; reload uses a new `document` segment.

Expected = earliest category in Product, Quantity, Packaging, Delivery with no submission. A wrong judgment still counts as submitted. A history with repetitions/out-of-order checks is retained and flagged. No expected category means not applicable, not an invented next step.

## Latency fields in interruptions

- `appropriate_next_check_selection_ms` (`recovery_ms` compatibility alias): task_return_ready to first selection of the frozen expected check; earlier wrong selections do not reset it. `recovery_observed`, `unobserved_reason` and `window_end` accompany it.
- `first_action_ms`: readiness to first category selection or Finish; retain action type/category and nullable `first_action_sequence_error`. An action selecting another category, or finishing with required checks remaining, is an error.
- `first_submission_ms`: readiness to first accepted judgment; retain `first_submission_category` and `first_submission_correct`.
- `expected_check_submission_ms`: readiness to first expected-category submission, with `expected_submission_correct`, observation flag and missing reason. It may be much later than selection.
- `applicable`, `not_applicable_reason`, `invalid_timing_reasons` and `technically_compromised` are explicit. Null reasons distinguish order end, withdrawal, incomplete session, missing return, no remaining check and clock discontinuity. No arbitrary penalty or success imputation.

`latency_summaries` contains observed/unobserved/not-applicable counts, mean and median for each measure. Top-level compatibility recovery counts refer only to the expected-selection outcome. First-action error numerator/denominator count observed actions. Unfiltered summaries retain long and flagged responses. Optional timing sensitivity tables add a predefined technical filter (v1/v2 metric versions also filter prior sequence deviations); they never replace raw/unfiltered tables.

## Block timing and accuracy

Elapsed = first task_ready in block to final Finish order. Scheduled breaks, ratings and instructions are outside the window. Active = elapsed minus the union of actual secondary-screen intervals and recorded pauses. Recovery, response acknowledgement and ordinary rendering remain included. Overlap is removed once; `secondary_union_ms`, `technical_pause_union_ms`, `excluded_union_ms`, and each interval are retained. Secondary screen begins at checkpoint `ack_end` and ends when `return` or a pause/withdrawal removes it; `stimulus_exposure_ms` begins at secondary_ready. Restore readiness is measured separately. A reload or incomplete full block yields null elapsed/active with reasons. Long valid responses are not removed.

In hmc-metrics-3, accuracy_denominator and first_accuracy_denominator are eight times the number of finished orders. hmc-metrics-2 retains 48 per started block. planned_accuracy_denominator is 48 for v4, while unfinished_exposed_checks counts categories on exposed but unfinished orders. `accuracy_numerator` counts correct final judgments, omissions incorrect; first responses remain separate. `exposed_accuracy_denominator`, exposed_orders and exposed_omissions disclose how much work actually appeared. Withdrawals/exclusions remain in raw/session tables but derived rows are omitted by default; `include_excluded=true` restores them for review. Never treat an incomplete visit as an ordinary completed block. Legacy v1 retains its completed-order denominator.

Each export recomputes from raw events using the manifest's metric version. `derived_versions` caches session × version × through-sequence without overwriting historical `derived` materializations. Manifests contain exact stimuli and answer keys, schedule, secondary forms, question text/anchors/orientation and build/configuration. These support reconstruction without relying on current application defaults.

## Pilot-4 procedure fields (hmc-metrics-3 only)

Exact earlier meanings: [legacy/data-dictionary-v2-v3.md](legacy/data-dictionary-v2-v3.md). `recovery_ms` remains the compatibility alias for appropriate-next-check selection latency; it is secondary in v4. Metric definition version, not the field name alone, determines the analysis hierarchy.

| Table / field | Definition |
|---|---|
| interruptions/transitions: primary_outcome | `first_committed_continuation_error`; A observations remain ordinary transitions |
| first_committed_action / type / category | Point and identity of first accepted submit or Finish after return-ready (A: checkpoint task-ready); null if none |
| first_committed_correct | Factual correctness for a submitted judgment, independently of sequence; null for Finish/no submission |
| first_committed_ms | Same-segment ready-to-commit interval; null if unavailable/discontinuous, even if category outcome is observed |
| procedure_error / procedure_observed | Nullable boolean: first commit submits another category than frozen expected, or finishes with required checks remaining. Observation requires ready, a defined expected check and an accepted commit |
| procedure_unobserved_reason | Null when observed; `not_applicable_no_remaining_check`, `return_not_observed`, `withdrawn`, or `no_committed_action_before_window_end`. No success/penalty imputation |
| procedure_window_end | First committed action point, or last known order/withdrawal/window-end point when no commit |
| procedure_review_reasons / procedure_flagged | Recorded disruption from checkpoint through commit/window end, plus missing return or actual secondary exposure duration/item timing deviations >250 ms. Pre-existing sequence errors are separate and not a filter |
| corrected_selection_before_commit | First deliberate selection was out of sequence but the first committed continuation was in sequence. Does not imply factual correctness |
| summaries: procedure_error_numerator / denominator / rate | Errors / observed applicable outcomes per participant-condition. Rate null for zero observed denominator. Includes flagged observations by default |
| procedure_unobserved / not_applicable | Counts within reached checkpoints, not silently omitted |
| checkpoints_not_reached | Six planned checkpoints minus actual checkpoint markers; paired with missed-checkpoint reason at order level |
| procedure_flagged_observed | Observed outcomes with procedure-specific technical review flags |
| unflagged_procedure_error_numerator / denominator | Prespecified technical sensitivity counts; retain original/default counts beside them |
| corrected_selections | Count of corrected-selection-before-commit episodes |
| participant_contrasts | One C-minus-B rate difference per allocated session; explicit B/C numerator/denominator, missing-pair reason and complete_opportunities flag. Null if either observed denominator is zero. No significance or equivalence claim |
| unflagged_procedure_episodes | Optional sensitivity export, v4 B/C rows without procedure flags; includes unobserved rows when otherwise unflagged. Not a replacement for interruptions.csv |

`accuracy_numerator` / first numerator and `omissions` in v4 summaries concern finished orders only; missing required submissions count incorrect. `exposed_omissions` also includes unfinished exposed orders; `checks.csv` retains planned unexposed opportunities with exposed=false. `planned_accuracy_denominator`, exposed denominator, unfinished_exposed_checks and completed/exposed orders allow reconstruction and prevent attrition being mistaken for judgment failure. Counts are never silently pooled across versions. Raw events remain append-only; derived tables recompute from the immutable session manifest.
