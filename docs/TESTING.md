# Testing and observed results

## Everyday checks

Install from the root README, with FFmpeg and FFprobe on PATH, then run:

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
```

The suite uses temporary data, creates its own sound/images, and does not alter working projects or call a paid provider. Tests exercise rules and exported media, rather than only checking that rendering functions returned successfully.

| Coverage | Evidence checked |
|---|---|
| Workflow | Distinct families; single Keyword; fixed duration; valid stars; rate before select; complete batches before approval; cross-project input rejection |
| Accountability | Rating history; retained five-star winners; no approval from a rating; explicit explanation/confirmation; immutable snapshots and export hashes |
| Persistence | Reopen the database; retain artifacts/history after upstream changes; invalidate affected downstream selections |
| Jobs | Single-worker lock; interrupted-job recovery; completed candidates retained; explicit retry; recorded rendering failures |
| Media | Real 15-second audio/video/alpha text/final outputs in both orientations at reduced test dimensions; 450 frames at 30 fps; 48 kHz stereo; actual transparent and opaque pixels |
| Audio | All nine styles produce finite audible output; Original Mix preserves the source excerpt; supplied bed/effect change the mix |
| API | Local Host/Origin and mutation-header checks; invalid file/setting rejection; failed uploads leave no asset record |

GitHub Actions runs the Python checks on Ubuntu with Python 3.12 and FFmpeg. It does not run the optional browser test or claim subjective creative quality.

## Optional complete browser test

This test rates, selects and creates an explicitly labeled **automated test approval**. Always use the disposable data directory below. It generates all 13 candidates at the application's full 1080 × 1920 size, exports a ZIP, reloads saved work, checks a narrow viewport, and records screenshots/browser errors.

In one terminal:

```sh
.venv/bin/python -m mit2009_studio.server --port 8774 --data-dir data/verification/studio
```

In another:

```sh
npm ci
npx playwright install chromium
node scripts/browser_smoke.cjs
```

An already installed Google Chrome can be used with `STUDIO_CHROME=1 node scripts/browser_smoke.cjs`. Node/Playwright are optional verification tools, not application runtime requirements. The default test creates a synthetic practice project.

Optional environment settings:

- `STUDIO_TEST_URL`: disposable server URL; default `http://127.0.0.1:8774`.
- `STUDIO_QA_OUTPUT`: report/screenshot directory; default `data/verification/browser`.
- `STUDIO_TEST_AUDIO`: absolute path to a local recording.
- `STUDIO_TEST_PHOTOS`: JSON array of 1–10 absolute photo paths, used with a supplied recording.

Inspect the resulting media yourself. Numerical checks cannot establish legibility across every photograph, aesthetic difference, musical suitability, or a satisfying story.

## Observed on September 22, 2026

- **21 tests passed** in 19.52 seconds on Danny's Mac. Ruff and JavaScript syntax checks passed. Two upstream Starlette/AnyIO test-client deprecation warnings remain; neither is a test failure.
- A complete full-resolution browser run with Danny's 19.712-second recording, three existing course photographs and CONNECT completed generation, rating, selection, all three final mixes, automated test approval, export and reload. It produced 13 candidates and no browser script errors. Desktop and 390-pixel layouts had no horizontal overflow; screenshots were inspected.
- In that one run, audio took 1.930 seconds, video 26.073, text 23.203 and assembly 17.704. These are observations for this Mac and input, not promised latency.
- The complete source recording remains saved. The generated candidates use its first 15 seconds. Private inputs, outputs and browser reports are under ignored `data/`, not in Git.
- Automated decisions are confined to the verification store. Danny's separate working project contains generated audio options but no automatic stars, selection or approval.
- The read-only HPR audit passed for all three repositories: their commits and tracked-file fingerprints matched the pre-work baseline.

Clean-install and hosted CI results are recorded below when completed. No learned model/provider, paid request, cloud deployment, student access control or subjective listening approval is claimed by these checks.
