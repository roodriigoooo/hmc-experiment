# Pilot-4 — procedural continuation, 20–25 minute target

Decision recorded 2026-11-17. The investigator prioritizes **fewer procedural mistakes** and authorizes a longer sequence, assuming the four-check task has insufficient placekeeping demand. That assumption motivates redesign; it is not a measured pilot finding. Pilot-4 supersedes the earlier latency-primary plan for **new sessions only**.

Primary question: Does showing the last submitted check reduce an out-of-sequence **committed continuation** immediately after a standardized interruption? This is narrower than claiming fewer mistakes of every kind, general workplace productivity, or a demonstrated memory mechanism.

## Changes and invariants

| Component | Pilot-3 | Pilot-4 / rationale |
|---|---|---|
| Primary endpoint | Appropriate-next-check selection latency | First committed continuation error: a submitted category other than the frozen earliest unsubmitted check, or Finish with required checks remaining. Measures an executed procedure deviation; corrected selections remain separate |
| Sequence | Product, Quantity, Packaging, Delivery | Product code, Batch code, Quantity, Packaging, Delivery code, Shipping service, Dispatch date, Seal code. Eight meaningful audit fields; seven direct comparisons and the same visible packaging rule |
| Main workload | 12 orders × 4 checks per block | 6 orders × 8 checks per block: still 48 required checks/block and 144 overall |
| Checkpoints (zero-based order: accepted submissions) | 1:2, 3:3, 4:2, 7:3, 9:2, 11:3 | 0:3, 1:6, 2:2, 3:5, 4:7, 5:4. Six positions from 2 through 7, fixed and matched in A/B/C. One per order can become predictable; acknowledged limitation |
| Records | Two mismatches/order, repeating answer pattern | 2, 3, 4, 4, 5, 6 mismatches across six orders, independently arranged by set; every category matches three times and mismatches three times. One match/one mismatch per category within each handling pair. Distinct seven-character codes, same one-digit mismatch operation; equal field lengths, date format, quantities, service frequencies and handling demands across X/Y/Z |
| Secondary forms | Alternating correct sides | Seeded shuffled 15 left / 15 right per 30-item form; same two-digit numbers and difference of four. No outcome-dependent generation |
| Interface | Four large aligned rows, card above records | Eight aligned rows, numbered static sequence, reserved card space above response panel. All choices visible; no completed-step checklist or next-step highlight in main blocks |
| Partial-block accuracy | 48 planned checks, including unexposed | Required checks in **finished orders**, omissions incorrect. Planned/exposed/unfinished denominators remain explicit; no unexposed record silently becomes a judgment error |

Unchanged: within-person A/B/C (A no interruption/no card; B standardized number task/no card; C same number task/actual-last card); independent condition/task-set cross-counterbalance; seeded allocation after training, persistent thereafter; planning target **36 main completers**, **4–6 separate pilot volunteers**; 10-second interruptions, five 2-second items, 300 ms acknowledgement, two 60-second breaks; three fixed demonstrations (A/B/C), then two consecutive fully correct assessed orders within at most six; seven intentional ratings after each block, Raw TLX `raw-tlx-2` plus exploratory tracking item. No fourth condition, new notification/music manipulation, or significance gate.

B/C share markup, source rows, control positions, focus, fresh-input protection, acknowledgement, secondary task and availability timing. C alone fills reserved space with “Last submitted check: [actual category].” Card names actual submitted history, including wrong judgments and repetitions; it disappears on category selection or Finish. No forced reading/dismissal. The comparison includes visual presence, reading and guidance, not information alone. A has invisible matched checkpoints, with ordinary transition measures.

## Time budget, not a deadline

Minimum training: 3 × 8 demonstration checks + 2 × 8 assessed checks = 40; main = 144. A planning example at 4–5 seconds/check gives 12.3–15.3 minutes of checking, plus 140 seconds of secondary tasks (including demonstrations), 120 seconds of breaks, about 80 seconds of ratings and 150 seconds of consent/instruction/feedback: approximately **20.4–23.4 minutes**. These component estimates are assumptions, not observations. Extra practice (up to 32 further checks), questions, pauses and slow accurate work can exceed 25 minutes. Never rush, terminate or exclude a participant to fit the estimate. Rehearse full visits before promising a duration.

## Versions and additive migration

New configuration `pilot-4`, interface `placekeeping-4`, stimuli `synthetic-3-eight-check`, metric definitions `hmc-metrics-3`; unchanged questionnaire `raw-tlx-2`. Application fingerprint remains independently recorded. On startup, `INSERT OR IGNORE` adds the new immutable manifest; no event/state/assignment is rewritten. No schema-destructive migration is needed. Existing v1/v2/v3 manifests, reducers, stimuli and derived definitions remain available; v3 UI is archived in `v3-main.ts` / `v3-style.css`, old metric derivation in `v2_metrics.py`. Existing live sessions still require their original build. Do not update a collection deployment during active sessions.

Create a new site-specific protocol identifier with correct contact, eligibility/consent and study information after technical/human rehearsal. Live creation requires v4 configuration and matching build; demo sessions can exercise historical versions. Existing seeded assignments are never regenerated. New protocol versions have separate allocation pools; do not merge them to claim one counterbalanced sample.

## Scientific rationale and limits

Sequencing errors and factual judgment errors are distinct outcomes. Training, a visible static procedure, and a longer repeated sequence aim to make keeping one's place relevant without hiding controls or introducing harder-to-read records. This is an inference from sequential-task research, not a replication or guarantee of an effect. [Altmann, Trafton & Hambrick (2014)](https://interruptions.net/literature/Altmann-JExpPsycholGen14.pdf) studied interruption-related sequence and nonsequence errors in a different task.

Eight rather than four checks is an investigator-approved design choice, not a validated optimum. Six return opportunities/condition are sparse: one error changes an individual's rate by 16.7 percentage points. Thirty-six people do not become 216 independent recruits because each has six returns. Retaining 36 respects the resource plan, but provides no new power justification. Before main collection, specify a smallest worthwhile difference and assess precision/sensitivity across plausible baseline rates and within-person dependence; or explicitly frame the study as resource-constrained estimation. See [Lakens (2022), Sample Size Justification](https://online.ucpress.edu/collabra/article/8/1/33267/120491/Sample-Size-Justification).

This deliberately manual interface has limited progress support. If an understandable eight-check baseline still produces few errors, report that result and revisit the research design. Do not degrade usability or tune using emerging main-study effects. Pilot checks assess comprehension and interpretability, not whether C wins. Detailed estimands and criteria: [analysis.md](analysis.md).
