# Analysis — pilot-4 (hmc-metrics-3)

Apply this plan only to pilot-4-derived protocols, separately by protocol/build. Earlier v2/v3 latency-primary definitions are retained in [legacy/analysis-v2-v3.md](legacy/analysis-v2-v3.md); v1 in [legacy/analysis-v1.md](legacy/analysis-v1.md). Never pool versions silently. Finalize registration, inferential method and smallest worthwhile effect **before main collection**. No software result is a psychological validation.

## Claim and endpoint hierarchy

Primary C–B: probability of a **first committed continuation error**, among observed applicable returns. At each checkpoint freeze the earliest category with no submitted judgment; factual correctness does not change this. After frame-aware `task_return_ready`, take the first accepted `submit` or `finish`. Submitting another category, or finishing while any required category remains, is an error. Selecting incorrectly and then correcting before submission is not this primary event. The full selection history, corrected-selection count, first-action sequence error, final/first judgment accuracy, omissions and repeated submissions remain available. Rechecking may be intentional: “procedure error” here is an operational deviation from the taught continuation, not a diagnosis of cognitive failure.

For each participant and condition, export error numerator / observed applicable denominator, unobserved/not-applicable counts, missed checkpoints and technical flags. Six checkpoints are planned per condition. Missing returns, withdrawal without a committed continuation, and undefined expected checks never count as successful responses or arbitrary penalties. Do not use six as the denominator when fewer outcomes were observed. Always show opportunity loss beside the rates; an apparently low error rate accompanied by more missing returns is not evidence of improvement.

Primary descriptive contrast: each person's C rate minus B rate, then the mean of those paired differences (negative favors fewer C errors). A participant needs at least one observed applicable outcome in both B and C for that contrast; absent pairs are reported, not imputed. This is an **observed-return estimand**, vulnerable to informative missingness/attrition. Present a complete-opportunity sensitivity description, and best/worst bounds for missing applicable outcomes where meaningful; do not assert an intention-to-treat causal rate when outcomes are unobserved. A binary repeated-measures model may be prespecified for inference (participant clustering, condition, block period and task set); sparse errors/separation need a declared fallback. Do not choose the model by which makes C significant. No automated significance tests or winner labels are added.

| Priority | Comparison / measure | Interpretation |
|---|---|---|
| Primary | C–B first committed continuation errors | Net effect of providing the card on an executed immediate continuation deviation |
| Secondary | C–B first-action errors/corrected selections; whole-block procedure counts, omissions and judgment accuracy | Distinguishes recoverable selections, downstream performance and opportunity loss |
| Secondary | C–B appropriate selection, first action, first submission, expected submission latencies | Behavioral performance; retain category/correctness, observed/unobserved counts, no valid-long-response trimming |
| Secondary | B–A committed continuation errors at matched checkpoints, active task time and accuracy | Interruption effects, with A checkpoints invisible and ordinary transitions |
| Secondary | Raw TLX; exploratory tracking separately | Self-reported whole-block workload; not adjustment covariates for the default performance comparison |
| Descriptive | C–A | Relative to uninterrupted work, not equivalence or full restoration from nonsignificance |

Analyze all conditions regardless of B–A significance. Time is not pure retrieval, cognitive load or general productivity; a correct selection does not establish complete recovery. Raw TLX remains unweighted six-item mean, not a mechanism test. C–B includes card appearance, reading and attention guidance. No neutral card or fourth condition is introduced. Secondary outcomes do not rescue a failed primary claim; if inferential secondary tests are reported, preregister a multiplicity policy and label exploratory analyses.

## Inclusion, attrition and review rules

| Rule | Rationale / implementation |
|---|---|
| Informed consent, locally approved target population/eligibility, ability to understand the instruction language and operate the supported interface with permitted accessibility settings | Defines population and task accessibility. Site-specific age/recruitment restrictions must have an actual approval/rationale; none are invented by the application. No blanket exclusions for demographics, disability or neurodivergence |
| One study visit per main participant; pilot volunteers separate from main | Avoid prior exposure changing the intended sample. Researcher tracks recruitment privately outside anonymous exports; app does not collect identifying information to deduplicate people |
| Fixed demonstrations and two consecutive correct assessed orders within six attempts | Establish procedural knowledge before measuring continuation. Pilot thresholds, not validated cutoffs. Failed training is retained and reported, not assigned a main slot. No private coaching exceptions |
| Retain all assigned main visits and realized allocation, including incomplete visits | Report recruitment, consent, training failure, assignment, withdrawal, technical loss and complete pairs. Never recycle an allocated slot. Preserve partial raw/derived observations subject to consent/withdrawal policy |
| Withdrawals excluded from default derived analysis; raw retention follows disclosed local policy | Voluntary withdrawal, not performance selection. Explicit permanent exclusions require a recorded reason and should be reviewed without condition outcomes |
| Technical quality is episode/measure specific | Blur, hidden tab, viewport/input problems, reload, assistance/external pause, missing/irregular secondary exposure are explicit flags. A clock discontinuity can invalidate latency without erasing a known category action |
| No automatic exclusion for slow responses, sequence errors before interruption, low engagement, poor main accuracy, high workload or an unfavorable cue effect | Avoid outcome-dependent selection. Retain history, first responses and engagement; no arbitrary latency cutoff. Repetitions are descriptive |

Default v4 procedure rates retain all observed outcomes, including flagged ones. A separate predefined sensitivity excludes episodes with recorded disruptions between checkpoint and first committed action (or window end), missing return, or secondary duration/item-onset deviations over the existing 250 ms tolerance. The tolerance is an engineering review threshold, not a psychological or validated precision cutoff. Prior sequence deviations do **not** trigger this filter. Timing sensitivity separately uses the existing broader timing flags; label it accordingly. An annotation cannot provide exact pause boundaries after the fact. Preserve raw records and report counts/reasons for every sensitivity; do not edit data or decide exclusions from effect direction.

Final/first accuracy denominators are eight checks per finished order, including omissions as incorrect. Unfinished exposed and planned/unexposed checks remain separate. This prevents withdrawal/unexposed records being scored as factual mistakes; completion/omission outcomes accompany accuracy. Active block time subtracts the union of secondary-screen and documented pause intervals, never twice when overlapping; cross-document full-block timing remains null. Recovery stays included. Never subtract A times from B/C and call the remainder pure cognition.

Retain 36 main completers and 4–6 separate pilots as planning parameters, not claims of power. Record all additional recruitment/attrition; stop according to the declared sample/resource plan, not significance. Small event counts and coarse per-person rates require a precision/sensitivity discussion before main collection. Allocation crosses six condition permutations and six task-set permutations independently, with forms balanced; do not re-randomize during practice/reload. Universal C demonstration means even B-first participants have seen a card. Report period, prior main C exposure and actual secondary engagement.

## Alternative explanations

| Explanation | Control | Remaining limitation |
|---|---|---|
| Button search | Eight visible fixed numbered controls; common training | Actions still require visual search and motor control |
| Knowledge rather than placekeeping | Worked example, fixed demonstrations, criterion practice, static sequence | Longer sequence is unvalidated; extra training can create selection bias |
| Hard comparisons / predictable answers | Matched fields, code lengths, mismatch operations, balanced but differently ordered keys | Equal perceived difficulty is not guaranteed; eight checks may still be easy |
| Card shifts layout or focus | Reserved space; shared B/C markup, return/fresh-input policy | Card salience and reading remain part of treatment |
| Wrong factual judgment mistaken for procedure error | Separate category/sequence and judgment scoring | Intentional revisiting can resemble a procedural deviation |
| Unequal interruptions | Same duration, positions, procedure; matched forms and logged exposure | Internal workload can vary; one interruption/order may become predictable |
| Learning / carryover | Separate matched sets; independent counterbalancing | Training on all configurations and learned strategies may persist |
| Selective missingness / technical exclusions | Explicit denominators, raw retention, predefined sensitivity, no outcome-based trimming | Observed-return comparison cannot identify missing outcomes |
| Sparse events | Fixed opportunities and participant-level comparisons | Six episodes/condition and 36 people may yield imprecise estimates |
| Browser artifacts | Monotonic clock segments and frame-aware availability, actual intervals | Ordinary browser timestamps, not hardware onset precision |

Rationale and source links are in [protocol-v4.md](protocol-v4.md); workload wording and scoring sources remain [questionnaire-sources.md](questionnaire-sources.md).
