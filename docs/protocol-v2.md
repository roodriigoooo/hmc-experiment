# Protocol pilot-2 — revision register

Applies to newly issued revised sessions. `hmc-metrics-2`, `synthetic-2-practice`, and `raw-tlx-1` identify the changes; each immutable manifest also stores the application build. Existing `pilot-1`/`hmc-metrics-1` definitions remain in the legacy reducer, metrics, frontend, stylesheet and archived documentation. Do not pool versions. No reallocation of existing sessions and no updates to historical raw events.

| Scientific change | Revised definition | Historical definition retained |
|---|---|---|
| Interaction | Fixed visible categories; category → judgment → Submit; separate Finish | Dropdown; judgment immediately submits |
| Return onset | `task_return_ready`, after restored DOM and two frame callbacks; controls enabled in the same callback before timestamp | `return` before DOM replacement |
| Response measures | Appropriate selection, first action, first submission, expected submission; separate reasons and observation windows | Original recovery/first-action/first-submission fields |
| Training | Three guided orders A/B/C, then two consecutive correct orders in at most six assessed attempts | One C practice plus comprehension, at most two attempts |
| Practice materials | Nine distinct separate P records; worked example uses separate codes | One P record |
| Workload | Six-item unweighted Raw TLX plus exploratory tracking | Three custom ratings |
| Accuracy denominator | All 48 required category judgments for each started block, omissions incorrect; exposed denominator also provided | Completed-order denominator |
| Keyboard | Operable throughout; mouse/trackpad remains instructed study method; keyboard use is logged | Timed keyboard activation blocked |
| Timing review | Explicit intervals, item exposure, environment/input events, reload discontinuities, null outcomes | Original conservative flags and interval derivation |

Retained planning parameters: 36 main completers, 4–6 separate pilot volunteers, 12 orders/block, six interruptions in B/C, five 2-second secondary items per 10-second interruption, 300 ms acknowledgement, 60-second breaks, minimum 1280×720 CSS pixels. These are planning choices, not effect guarantees. Training thresholds are configurable pilot choices in new immutable manifests (`training_consecutive`, `training_attempts`, maximum six), not validated cutoffs. X/Y/Z, mismatch patterns, handling rules, code lengths, seed 481516, irregular schedule, and counterbalancing algorithm are unchanged. Main materials use PR/DL prefixes with numeric suffixes; monospaced slashed-zero presentation distinguishes the characters without changing records.

Allocation remains atomic after training and persists across retries/reloads. Repeating practice never allocates or changes assignments. Each condition-order permutation is crossed with each task-order permutation in a 36-slot cycle. Demo, pilot, and main pools remain separate. Newly allocated synthetic pilot/main sessions use their own pool so they do not consume human slots; existing assigned slots are never moved.

B has no return card or neutral message. C states exactly `Last submitted check: [actual category].` The category comes from actual submission history, including errors and repetitions. The empty reserved area has identical dimensions. The card disappears only on category selection or Finish. Focus traversal, pointer motion and background clicks do not remove it. Source records, control positions, acknowledgement, focus reset, selection clearing and secondary controls are common to B and C. No enforced reading period or card dismissal. All categories remain selectable; Finish permits omissions in assessed practice and main blocks. Guided demonstration alone requires coverage before Finish.

The workflow is deliberately manual with limited progress support. A clear baseline with little resumption burden is a legitimate pilot finding. Do not make it harder to manufacture an advantage.

## Timing implementation and limits

`performance.now()` and `performance.timeOrigin` are recorded with a fresh document segment UUID. Same-segment intervals only; reusing an old segment or changing its origin is rejected. A reload retains local queued events and pauses the restored state. A disrupted secondary task is not replayed. Full-block elapsed/active time is null across a reload, while same-segment components remain available.

The UI commits restored records and reserved card content, then schedules two `requestAnimationFrame` callbacks. In the second callback, it enables task controls, invalidates prior input gestures, and timestamps `task_return_ready` (or ordinary `task_ready`). No network acknowledgement is on this path. Both callbacks are cancelled logically if another render intervenes or the document is hidden. The double frame lets the restored layout reach a rendering opportunity; it cannot establish physical photon onset. Browser scheduling, paint/compositing, display refresh and input delivery remain limitations, not hardware-grade precision. Card content may reach a rendering opportunity before controls become available; that small rendering interval is common to B/C and is not an enforced reading interval.

Secondary screen entry is `ack_end`; stimulus timing starts at `secondary_ready` after frame preparation. `secondary_item` records each actual number-pair DOM commit; `return` removes the secondary screen. `task_return_ready` records restored availability separately. The fixed 10-second task deadline depends on monotonic elapsed time, never on responses. Late callbacks can increase actual exposure and are flagged; skipped items and missing responses remain explicit. Main unavailability and actual item exposure are both exported. No external fonts/images/assets are fetched during a block; fixtures and secondary forms are loaded in the session snapshot.

A new pointer press or nonrepeating activation key press on the current control is required. Screen transitions invalidate both; a double-click activation is rejected. There are no condition-specific shortcuts or expected-category focus jumps. Keyboard activation is possible for accessibility, but is a logged input-method deviation in this mouse/trackpad protocol. Keep that setup constant across conditions.

## Migration and release

Startup adds immutable `pilot-2` only if absent and creates the additive `derived_versions` cache table. Existing tables/rows are not rewritten; old `derived` caches remain. Exports recompute with each session's own metric version and store version/sequence-specific materializations. No production migration or deployment was run. Back up using the existing SQLite backup script, validate on a copy, and use the existing Docker/compose workflow after local rendered acceptance and human piloting.

Never update builds during a live session. Existing live build checks remain enforced: serve started sessions with their original build. The bundled legacy frontend provides semantic routing for legacy demo/replay review; it does not authorize changing a live participant's build midway. New live sessions require a revised protocol and populated contact/study information. New session UI offers revised protocols only; legacy demo issuance remains available via authenticated API for regression testing.
