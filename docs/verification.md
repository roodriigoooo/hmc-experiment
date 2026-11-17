# Verification record — pilot-4

Date: 2026-11-17. Final `npm run verify` passed: TypeScript build, **38 Python tests and 6 JavaScript tests**. Python tests completed in 76.1 seconds. Application fingerprint: `hmc-9db0289c3d7da7a5`. All synthetic visits use temporary SQLite stores, not existing collection/demo databases.

| Executed check | Evidence |
|---|---|
| Complete pilot-4 visit | Three demonstrations, two assessed orders, persistent allocation, 18 main orders / 144 submissions, 12 actual secondary tasks, 6 A markers, all ratings and breaks; every state replayed through compiled TypeScript and compared with Python |
| Primary endpoint | Corrected wrong selection is separate from wrong-category submission; quick appropriate selection followed by delayed wrong judgment; early Finish, skipped expected check, missing commit and undefined expected category retain correct flags/nulls/counts |
| Quality window | Disruption before first commit flags procedure sensitivity; disruption after commit does not retroactively flag that procedure outcome. Default observed denominator remains unchanged |
| Export and historical definitions | Export recomputes and matches derived summaries; primary contrast and item/episode data present; training failures export without allocation; full v1/v3 regression and mixed-version checks pass |
| Stimulus/allocation invariants | Six distinct rows/set, category/handling balance, mismatch-count distribution, matching code lengths, separate practice codes, nonidentical key sequences, balanced shuffled secondary sides; 36 crossed condition/set permutations preserved |
| Card/input | Actual repeated/out-of-order last category retained; B/C reducer states identical except cue; no availability before return-ready; passive events retain card; selection/Finish remove it; shared fresh-input tests reject stale/duplicate gestures |
| Persistence/timing/workload regression | Duplicate ingestion, allocation retry/reload, clock discontinuities, interval unions, omissions, training failure, six-item TLX completeness and Performance orientation, authenticated API checks |
| Teammate launcher | Busy-port fallback and loopback-only address tested with mocked sockets; separate demo database and synthetic mode verified; existing database/password variables ignored; permission denial stops cleanly |
| Source package review | Explicit source allowlist, no SQLite/credentials/export payloads; staged whitespace check and token-pattern scan clear. No real observations included |

**Rendered inspection is still blocked here.** Pre-edit `python3 -m server.app` on an isolated database and post-edit `scripts/local-demo.py` both failed with `PermissionError: [Errno 1] Operation not permitted` at loopback bind. Browser skill setup/discovery returned no available browser (`[]`). No pilot-4 screenshots, viewport measurements, actual pointer transitions or visual usability results are claimed. Historical pilot-3 browser evidence below cannot establish eight-row fit, current card visibility or reflow. Run the manual acceptance checklist below on a browser-enabled workstation before collection.

Target remains desktop Chromium, mouse/trackpad, at least 1280×720 CSS pixels. Record the actual browser/OS/display/scaling/zoom/input setup; test all instruction/training/task/return/rating/completion screens, whole-workspace fit, 200% zoom and narrow reflow, B/C geometry/focus, held/double input and actual offline/reconnect. Human Stage 1 walkthroughs and Stage 2 silent rehearsals are still needed for understanding, comfort, training sufficiency, matched difficulty, error floors, 20–25 minute feasibility and construct validity. Passing software tests cannot supply these findings.

No active environment was deployed or production data migrated. Startup migration is additive only (new immutable pilot-4 manifest). Existing sessions and assignments remain under their original versions/build requirements. The source workspace forbids `.git` writes, so private-repository publication uses an isolated, source-only checkout; clone that repository for normal Git collaboration.

# Verification record — pilot-3 interface

Date: 2026-10-30. `npm run verify`: TypeScript build, **29 Python tests and 5 JavaScript tests passed**. The two new tests check that pilot-3 leaves configuration, fixtures, answer keys, schedule, secondary forms and TLX items unchanged apart from the documented title; that pilot-1 and pilot-2 are retained; that live sessions on pilot-2 interface versions are rejected; and that `interface_version` reaches event context and exports. Build fingerprint after the final edit: `hmc-6cc2b8bbcfadc057`. That last edit was CSS only: it restored button styling on the researcher export link after the rendered checks.

This time, rendered checks **were** executed. They used a local server on a temporary database and headless Chromium 128 (Playwright build 1134) at a 1280×720 CSS viewport with mouse input. The walkthrough scripts were throwaway and are not part of the repository.

| Check | Result |
|---|---|
| Full participant visit through the UI: join, consent, setup, onboarding, three demonstrations, two assessed practice orders, allocation, three blocks, questionnaires, two real 60-second breaks, completion | Completed with no page errors. The server accepted every event, including timing validation. The completion screen confirmed acknowledgement |
| No-scroll fit | `scrollHeight ≤ innerHeight` and `scrollWidth ≤ innerWidth` on every demonstration, practice, A, B and C task screen |
| B vs C return screen | Bounding rectangles identical for the card slot, table, rules, panel, four category buttons, both judgments, Submit, Finish, Pause, Withdraw, top bar and heading. Main-area button ids, classes, disabled and pressed states identical. Focus on the heading in A, B and C; scroll 0. Rectangles also identical after a category selection |
| Card behavior | C only: “Last submitted check: Quantity.” B slot has no child elements. Pointer motion and a background click left the C card in place; selecting a category removed it |
| Version routing | A pilot-2 demo session loaded `v2-style.css` and the pilot-2 interface. Creating a pilot session on pilot-2 returned 409 (current interface required) |
| Export | Bundle lists `interface_versions` `['ergonomic-3','pilot-2-interface']`. pilot-3 summary rows carry `ergonomic-3` / `raw-tlx-2`. `protocol-v3.md` is included |

Still not verified: 200% zoom and narrow reflow, other browsers and physical displays, real offline/reconnect, screen readers, and any human use. The Stage 1 and Stage 2 pilots remain required. Passing these checks says nothing about usability for real participants or about any cue effect.

# Verification record — revised protocol (pilot-2)

Revision date: 2026-10-30. Automated participants are synthetic, held in temporary SQLite databases. No human observations or study findings were fabricated. Repository contains no Git metadata, so no commit/diff provenance is claimed; runtime build fingerprinting is provided by `scripts/build-id.py`.

## Executed evidence

`npm run verify`: TypeScript compilation/static build, **27 Python tests and 5 JavaScript tests passed** in the latest completed pass. The complete revised visit includes consent, three demonstrations, two successful assessed practice orders, persistent allocation, all 36 orders, 12 main secondary tasks, seven ratings after each block, two breaks and completion. Every event in a complete revised visit is replayed through the actual compiled TypeScript reducer and compared with Python's resulting state. Separate full legacy visits retain v1 definitions. This is state/API verification, **not rendered browser end-to-end evidence**.

| Requirement | Executed evidence | Remaining direct check |
|---|---|---|
| Allocation persistence/balance | Seeded 36 combinations; six balanced batches; 37 concurrent allocations; stable retries; synthetic pools isolated | Actual browser refresh/reconnect |
| B/C identity and card history | Reducer states differ only in cue; repetitions/wrong judgments preserve actual last; passive events retain cue | Screen geometry/focus comparison |
| Latency/error distinctions | Wrong first selection then expected selection; delayed wrong judgment; missed expected selection/submission; premature finish; null applicability | Actual frame/input timing observation |
| Active time/clock validity | Recorded secondary pause, all omissions, fixed secondary duration, interval union, reload nulls, segment reuse rejection | Device/browser scheduling and real overlap disruption |
| Training | All configurations; success parity; six failed assessed attempts block allocation; failed training exported | Unfamiliar volunteers' comprehension |
| Questionnaire | Six-item completeness; intentional event requirement; Performance identity orientation; exploratory/legacy exclusion; drafts and exact wording exports | Digital administration comprehension |
| Integrity | Idempotent retries, conflicts/gaps, sorted batches, lease/session isolation, immutable events/manifests, legacy/new export recomputation | Real network interruption and restore drill |
| Access control | Actual HTTP parser/handler on in-memory connection; unauthenticated researcher/export access rejected; scoped cookies; CSRF check | HTTPS/proxy/production configuration |
| Matching | X/Y/Z byte-for-byte retained; distinct P records; matching code lengths, mismatch patterns and handling demands | Human matched-set difficulty |
| Contrast | Calculated sRGB ratios: body #243831 on #f5f6f2 11.48:1; muted #4c6055 6.22:1; cue #345747 7.44:1; white on #234c3f 9.65:1; sequence text 10.59:1; error text 7.43:1 | Rendered focus/contrast and user perception |

The prior muted color measured 4.45:1 on the page background; revised CSS replaces it. [WCAG text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) specifies 4.5:1 for ordinary text. Primary buttons target at least 44 CSS pixels; [WCAG 2.2 target-size minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) has a 24×24 criterion with exceptions, not a universal 44-pixel rule. Color calculations and source layout inspection are not full accessibility certification.

Final build fingerprint: `hmc-42bcde1b48af3fec`. After the full pass, the secondary-item boundary validation was refined to retain a delayed actual display; the targeted delayed-display/pause test passed, TypeScript rebuilt, and all five frontend tests passed again. Rendering remains unverified.

## Exact blockers and scope of claims

Before editing, attempted `DATABASE_PATH=/private/tmp/hmc-review-original.sqlite ... PORT=8123 python3 -m server.app`; socket bind failed with `PermissionError: [Errno 1] Operation not permitted`. Browser skill bootstrap returned “No browser is available”; documented discovery returned `[]`. Therefore no actual browser/display/input setup was tested, and no screenshots or actual-screen inspection are claimed. Target remains desktop Chromium, mouse/trackpad, 1280×720 CSS pixels minimum. Rendered fit, 200% zoom/reflow, actual B/C transitions, physical display scaling and keyboard focus remain release checks. The same environmental limits prevent a meaningful local serving/interactive demonstration here. No deployment was attempted.

An early legacy test imported the old app module, which initialized an additive default protocol in the existing local database. Read-only inspection found one synthetic demo and no pilot/main sessions. No raw events or assignments were altered. The import side effect has been removed; subsequent tests use only temporary stores. Existing old cache rows are preserved. No production data migration was run.

## Technical acceptance on a browser-enabled workstation

1. Build/start using a temporary `DATABASE_PATH`, sign into `/admin`, issue a synthetic demo and join at `/?join`. Record build fingerprint, browser version, OS, physical display, scaling, zoom, CSS viewport and input device.
2. Inspect instructions, all demonstration types, practice feedback, A, B return, C return, questionnaire and completion. At 1280×720 ensure the entire main workspace fits without scrolling, text is legible, source rows align, controls are findable and every focus target is visible. Compare B/C bounding boxes before and after card removal. Only C has card content.
3. Test 200% zoom/narrow reflow without clipping; timed unsupported configurations must log/pause. Restore the configured workstation before measuring. Browser zoom must remain enabled.
4. Make wrong judgments, repetitions, out-of-order selections and an early Finish. Main feedback is only “Response recorded.” Verify no current-progress hints. Practice can explain errors. Test both successful and incomplete training.
5. Observe actual 10-second secondary tasks with early/missing answers; neither alters duration. Hold mouse/key across return, double click, traverse focus and click background. Only a fresh category action or Finish removes the C card. Never auto-focus the expected check.
6. Go offline, work, reconnect, verify exact UUID/sequence counts and final acknowledgement. Reload during an order and secondary task: assignment/history survive; clock segment changes; exposed secondary task is not replayed. Check two-tab/device lease behavior.
7. Record assistance/external interruption/extra rest with Pause, reason and annotation. Compare interval components/union and null timing reasons with the raw export. Check missing expected-check windows and denominators, not only successful recoveries.
8. Leave ratings blank, then intentionally choose 0/100. Verify six TLX items plus the exploratory item, no default response, Performance direction, no incomplete mean, ratings before each fixed break, and withdrawal during ratings.
9. Download normal and sensitivity bundles, verify protocol/version separation, manifests/keys, item wording, and exclusion/withdrawal raw retention. Recompute. Use the existing backup helper and perform a local restore drill. Test the deployment workflow separately without an active collection volume.

After technical acceptance, perform both stages in [pilot-checklist.md](pilot-checklist.md). All usability, training sufficiency, floor/ceiling, matched difficulty, session duration, comfort and construct-validity findings still require human participants. The aim is interpretable measurement, not a significant C advantage.
