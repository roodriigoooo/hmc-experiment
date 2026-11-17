# Digital checks study

A versioned local implementation of a within-participant Human–Machine Collaboration experiment: typed browser UI, Python standard-library HTTP API, transactional SQLite, researcher administration, versioned stimuli, raw event retention, and reproducible exports. No external AI, analytics, fonts, or runtime services.

## Teammates: clone, run, test

Requires **Python 3.12+**, **Node.js 22+** and Git. On Windows, use WSL with those tools. No Python packages, external services or Docker are needed for local testing. Accept the private GitHub repository invitation first; use your own GitHub credentials to clone.

```sh
git clone git@github.com:roodriigoooo/hmc-experiment.git
cd hmc-experiment
npm ci
npm run demo
```

Open the **Local synthetic demo** URL printed in the terminal and paste the printed **Session code**. Keep the terminal open while testing. For the researcher interface, open the printed `/admin` URL and use its temporary password. The password changes each restart; saved observations remain. Stop with **Ctrl+C**.

The launcher creates only a synthetic **demo** session in `data/local-demo.sqlite`. It ignores existing `DATABASE_PATH` / `ADMIN_PASSWORD` variables so teammate testing cannot accidentally open a collection database. If port 8000 is busy, it automatically chooses another free port and prints the correct URL. Each restart issues another demo; to resume an existing one, visit `/` in its browser instead of `/?join`. Cookies are scoped by host rather than port: avoid simultaneously running multiple study servers in the same browser profile. Use a separate profile if needed.

To get later changes, stop the server, run `git pull`, `npm ci`, then `npm run demo`. Do not use this update workflow on an active collection session. Local databases, credentials, exports, dependencies and build output are ignored by Git. Each teammate has an independent demo database; **never merge these databases into main collection or count teammates as main recruits**.

### What to test

```sh
npm run verify
```

This compiles TypeScript and runs isolated Python/JavaScript tests, including complete synthetic visits, durable ingestion, metrics and version regression. It does not use your demo/collection database. `npm test` runs only Python tests; `npm run test:frontend` uses the latest compiled frontend, so build first if calling it separately.

Then test the actual website: consent/setup → five instruction pages → three guided demonstrations → two consecutive correct practice orders → three blocks → ratings and fixed breaks → saved completion. Use a desktop viewport of at least **1280×720 CSS pixels** and a mouse/trackpad. For a normal rehearsal, allow **20–25 minutes**, possibly longer with extra practice. For error-path testing, try a corrected wrong selection, a wrong-category submission and an early Finish; do not expect main-block correctness feedback. Check the C reminder shows the actual last submitted category and disappears on a fresh category action/Finish. Full acceptance checks: [verification](docs/verification.md) and [pilot checklist](docs/pilot-checklist.md).

To inspect exports: `/admin` → Export research records → **demo** → the `pilot-4-demo-…` protocol printed/created for this build → Download ZIP. Inspect `summaries.csv`, `interruptions.csv`, `submitted_checks.csv`, questionnaire items and manifests; raw observations remain in the bundle. Share bug descriptions and synthetic examples privately, never participant credentials or real observations. Include build, browser/OS, CSS viewport/zoom, phase, expected versus actual behavior and reproduction steps.

### Troubleshooting

- **Address already in use / Errno 48:** use `npm run demo`; it finds a free port without terminating an existing server. With the manual server command below, set `PORT=8001` (and browse that port).
- **Researcher login fails:** use the password printed by the current demo process. `export ADMIN_PASSWORD` alone does not assign a password. The manual server requires a value of at least 16 characters.
- **Another tab owns this session:** close the old task tab and wait 20 seconds. Preserve the original browser until queued responses are saved.
- **Changes do not appear:** stop and rerun `npm run demo` to rebuild; older sessions intentionally keep their old interface. Start the newly printed demo session.
- **GitHub clone denied:** verify that the owner invited your GitHub account and that your SSH key is configured; alternatively use the repository's HTTPS clone URL with GitHub authentication. Never put an access token in the README or a command committed to Git.

### Manual researcher server

For an explicitly selected **test** database, after `npm ci` and `npm run build`:

```sh
export DATABASE_PATH="$PWD/data/local-test.sqlite"
export BUILD_ID="$(python3 scripts/build-id.py)"
# Set a private password of at least 16 characters locally; do not commit it.
export ADMIN_PASSWORD='replace-with-a-private-password'
export PORT=8001
python3 -m server.app
```

Open `http://127.0.0.1:8001/admin`, create a demo, and enter its code at `/?join`. Missing administrator configuration disables researcher login. Participant access uses an opaque bearer code and HttpOnly cookie. No public self-enrollment or default production password is provided. `npm run dev` builds and starts this manual server using your environment; `npm run demo` is the safer teammate shortcut.

## Researcher workflow

1. Inspect the immutable demo manifest, answer keys, and protocol in administration.
2. Duplicate the configuration with a new version identifier. Populate researcher contact and study information; keep the scientific defaults. Creating live pilot/main sessions is blocked while these are blank.
3. Issue separate demo, pilot, and main session codes. Mark technical sessions synthetic. Admin never exposes a public self-enrolment route.
4. Participants consent, check their setup, page through the illustrated instructions, complete the guided A/B/C demonstrations, then pass two consecutive correct practice orders within six assessed attempts before receiving the next allocation atomically. Pilot-4 blocks each include six distinct eight-check orders and six-item unweighted Raw TLX plus a separate tracking question, followed by the two 60-second inter-block breaks.
5. Review status, assignment balance, flags, and saved sequences. Add permanent annotations without editing raw data. Export by mode and protocol. Preserve raw ZIP bundles alongside database backups.

Every raw event is inserted atomically with reducer state. Duplicate UUID retries are idempotent; conflicting UUIDs or sequence gaps are rejected and audited. Batches are sorted by sequence, never server arrival time. A gap is retried by resending the retained ordered queue, not by discarding it. Browser localStorage is a write-ahead queue, not the sole record. Web Locks prevent two same-device tabs; a 20-second server lease prevents cross-device concurrent ingestion. Offline work queues locally; closing/clearing storage before sync can lose unsaved observations and must be avoided. Server acknowledgement determines saved completion.

## Deployment

Use `Dockerfile` and `compose.yaml` on a single host with a persistent volume. Public deployment is **not** performed here. Terminate HTTPS at your managed reverse proxy, set `COOKIE_SECURE=1`, disable IP/request logging where your policy permits, and restrict researcher access operationally. The server does not log IP addresses or request paths. Proxy/hosting logs may still contain IPs; configure and disclose their retention separately. Do not put SQLite on ephemeral hosting disk or network filesystems; use one application replica. SQLite WAL plus FULL synchronous durability and immediate allocation transactions suit this study's scale. Use a managed relational database adaptation if multiple replicas become necessary.

Create `.env` outside version control with `ADMIN_PASSWORD`, `BUILD_ID`, and optional `COOKIE_SECURE=1`; then `docker compose up --build -d`. The service listens internally on 8000 and publishes only loopback. Preserve the named `research-data` volume across updates. Password rotation/restart expires researcher sessions. Do not change builds during active sessions; live sessions require their original manifest build. After a build change, create a new protocol version before issuing live sessions. The deployment uses one authenticated researcher role; institutional SSO and per-person researcher identity are outside this first iteration.

### Backup and restore

Use the online SQLite backup API; copying a live `.sqlite` alone can miss WAL data:

```sh
python3 scripts/backup.py data/study.sqlite /private/tmp/study-backup.sqlite
# Verify and copy the backup to institution-approved encrypted storage.
python3 scripts/backup.py --verify /private/tmp/study-backup.sqlite
```

Schedule encrypted off-host backups according to the institution's retention policy. Test restoration periodically: stop the service, preserve the current database and WAL together, restore the verified backup to `DATABASE_PATH`, set volume ownership to the app user, and restart. Never merge independent copies of an allocation database. Restore can only recover events included in the last backup. Exercise `--verify` before returning to collection.

## Protocol and implementation

- [Pilot-4 procedural endpoint and task revision](docs/protocol-v4.md)
- [Revision audit](docs/revision-audit.md)
- [Protocol pilot-3: interface and ergonomics revision](docs/protocol-v3.md)
- [Protocol pilot-2: changes and migration](docs/protocol-v2.md)
- [Analysis and limitations](docs/analysis.md)
- [Researcher script](docs/researcher-script.md)
- [Two-stage human pilot checklist](docs/pilot-checklist.md)
- [Verified questionnaire sources and administration](docs/questionnaire-sources.md)
- [Data dictionary and metric definitions](docs/data-dictionary.md)
- [Verification record and manual checklist](docs/verification.md)

`server/protocol.py` generates fixed synthetic materials and manifests. `server/domain.py` dispatches authoritative reducers by protocol; `web/v4-state.ts` mirrors pilot-4; `web/state.ts` retains v2/v3 for offline interaction. `legacy_domain.py`, `legacy_metrics.py`, and the legacy frontend preserve v1 definitions. `web/main.ts` + `style.css` are the current (pilot-4, `placekeeping-4`) participant interface; `web/v3-main.ts` + `v3-style.css` preserve pilot-3; `web/v2-main.ts` + `v2-style.css` preserve the pilot-2 interface; `web/admin.ts` is the researcher workspace and `web/ui.ts` holds shared helpers. `web/launch.ts` routes existing sessions to their interface version. `server/store.py` owns append-only transactions, leases, versions and allocation. `server/metrics.py` recomputes all analysis tables from raw observations. `server/app.py` provides scoped participant and authenticated researcher routes. Main-task answer keys are not sent to participant endpoints; practice feedback includes separate practice keys.

The browser uses monotonic timestamps per document. Revised task availability is logged after DOM restoration and two frame callbacks, with controls enabled before the readiness timestamp, independently of network acknowledgements; this is browser timing, not hardware-grade onset precision. Backgrounding, window blur, resizing and reload generate explicit conservative flags. Technical interruptions preserve work and do not replay exposed materials. After a reload during a timed secondary task, the task returns with a technical flag rather than showing an unlogged fresh task. A disrupted acknowledgement may skip a checkpoint; the missed exposure remains auditable.

## Validation and remaining release work

`npm run verify` builds the application and runs isolated synthetic backend/API/reducer checks. Revised tests replay a complete visit through both TypeScript and Python reducers and compare every resulting state; they check error/omission timing, exposure, Raw TLX orientation, versioned exports and legacy regression. See [the verification record](docs/verification.md) for actual results and limits.

Historical evidence only: the pilot-3 revision was checked in headless Chromium at 1280×720: a complete visit, no-scroll fit of every task screen, and identical B/C return geometry, focus and control state (see the verification record). Zoom/reflow, other browsers and displays, and browser offline/reconnect behavior remain unverified. Pilot-4 has not yet had a rendered walkthrough in this environment (socket permission denied; no browser connection). Do not transfer pilot-3 visual results to the new eight-row interface. The app has not been behaviorally validated. Complete the technical checklist and both human pilot stages before live collection. Do not equate passing software tests with usability, instrument validation or a psychological effect.

The existing local database contains one synthetic demo session and no pilot/main records. An early legacy test import initialized the new immutable default protocol alongside it; raw demo observations and assignments were not changed. Server imports are now side-effect-free so future test/export imports cannot open a collection database. No production migration or deployment was performed.

## Private repository sharing

The owner can invite teammates from the repository's **Settings → Collaborators**. Teammates clone and run locally; the private repository is source sharing, not a hosted participant site. Do not enable Pages or upload SQLite/exports. CI runs only synthetic tests on pushes/pull requests. Docker/Compose deployment remains available as before, but no active collection deployment or production migration is part of this revision.
