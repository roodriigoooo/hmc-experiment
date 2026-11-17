# Protocol pilot-3 — revision register

Applies to newly issued sessions on `pilot-3` or versions derived from it. Identifiers: `interface_version = ergonomic-3`, `questionnaire_version = raw-tlx-2`. Metrics remain `hmc-metrics-2`, stimuli remain `synthetic-2-practice` (byte-identical fixtures, answer keys, schedule and secondary forms), and the event vocabulary and reducers are unchanged. `pilot-2` sessions keep the `pilot-2-interface` (bundled as `web/v2-main.ts` / `v2-style.css`, routed by `web/launch.ts`) and `raw-tlx-1`. Exports label every row and event context with `interface_version`; do not pool interface versions in summaries.

pilot-3 is a presentation revision. It changes what participants see and where controls are, which plausibly changes absolute latencies and possibly the size of the C−B difference, so it is a new protocol version. It does not change the conditions, the card wording template, timing, scoring or allocation.

| Scientific change | pilot-3 definition | pilot-2 definition retained |
|---|---|---|
| Source records | One comparison table, one row per check in taught order (numbered 1–4); requested and packed values adjacent; values 24 px monospaced with slashed zero, word values capitalized; field sublabels in each cell | Two separate record cards plus a rules card; 17 px values; lowercase words |
| Rule table | Continuously visible directly beneath the table (Handling → Required packaging) | Third card to the right |
| Category controls | Dedicated button as each row's header (spatially mapped to its data); not whole-row click targets, to avoid incidental selections | Horizontal strip of four buttons below the records |
| Judgment / Submit / Finish | Right-hand panel: step 2 judgment buttons with ✓/✗ icons, step 3 full-width Submit, Finish separated at the bottom with “Moves to the next order. You cannot return to this one.” | Single row: judgments, Submit, Finish |
| Step guidance | The current micro-step of the *current* check (select → judge → submit) is highlighted. Nothing marks submitted categories | Numbered labels only |
| Return card (C) | Same template, `Last submitted check: [category].`, with the category spelled exactly as its button (`Product code`, `Quantity`, `Packaging`, `Delivery code`). High-contrast amber card with icon in a fixed 64 px slot directly above the check list. Static (no animation). Removal rule unchanged | 40 px plain text line between records and controls; short names (`Product`, `Delivery`) |
| B / A slot | Same 64 px slot, empty. No placeholder, outline or neutral text | Same principle, 40 px |
| Onboarding | Live setup checklist; five-page “How it works” using the real task components; demonstrations show a guide note and highlight the next control (demonstrations only) | Single instruction page; one-line demonstration hint |
| Practice feedback | Scorecard with per-check result, sequence/judgment verdicts, streak and attempt indicators; Continue always visible | Text table |
| Secondary task | Same wording, items, timing; larger number buttons; the chosen button is filled after a response (in addition to “Response recorded”) | Status text only |
| Workload | `raw-tlx-2`: identical six TLX items, wording, anchors, keys, 0–100/step 5 values and Raw TLX scoring. Responses are given on one 21-mark horizontal scale per item (endpoint labels, no numerals, no default mark). The exploratory item is shown as “Keeping track” after the TLX items | `raw-tlx-1`: typed numeric inputs; exploratory title “Exploratory progress tracking (separate item)” |
| Other UI | Study-progress header (Setup, Training, Blocks 1–3, Done); order pips within a block; save indicator updates after acknowledgement; withdrawal requires inline confirmation; consent/setup buttons enabled only when satisfied; participant brand is not a navigation link | Static tags; save text could remain “queued” after acknowledgement; one-click withdrawal |

Retained planning parameters (no discrepancies found): 36 main completers, 4–6 separate pilot volunteers, 12 orders per block, six 10-second interruptions in B/C (five 2-second items), 300 ms acknowledgement, two 60-second breaks, 1280×720 CSS-pixel minimum, mouse/trackpad, seed 481516, irregular schedule, 36-slot counterbalancing, training criterion 2 consecutive within 6. Allocation, assignments and existing sessions were not touched.

## Constraints kept deliberately

- No checklist, completed-check marks, disabled categories or progress inferred from submissions. Order pips are order-level and identical across conditions.
- The step highlight depends only on the current selection/judgment, which are cleared on submit and on return in both B and C.
- B and C return screens differ only in card content: rendered bounding boxes, button classes, disabled states and focus target were compared programmatically (see verification).
- No countdown or item counter in the secondary task: making the interruption's end predictable would change the interruption.
- No difference highlighting in the records; no inline rule answers in the Packaging row.
- The demonstration guide and highlighted controls appear only in the three demonstrations; assessed practice and main blocks have none.
- Timing path unchanged: render, two animation frames, enable controls, timestamp `task_ready` / `task_return_ready`. The only animation (guide pulse) exists only in demonstrations and respects reduced-motion settings.

## Release

Startup inserts immutable `pilot-3` if absent alongside `pilot-1` and `pilot-2`. New live (pilot/main) sessions require a protocol with the current `interface_version`, the current build, and populated contact/study information; derive a site version from `pilot-3`. Demo sessions on `pilot-2` remain available for regression review. No production data were migrated.
