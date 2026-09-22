# Immediate playback update

28 tests passed in 23.99 seconds on September 22. Added checks for soft opening notes, internal rests, unchanged originals/15-second masters, cached listening copies, byte-range playback and actual candidate preview endpoints. The melody API test now includes room noise before the phrase. Ruff and JavaScript syntax checks passed.

Danny's current reference preview skips 2.864 seconds; the melody preview skips about 2.939 seconds. Both contain substantial audio in the first 100 ms. The local measurement report is under ignored `data/verification/playback/`. Reference and melody Play controls, shorter player durations, and switching between tracks were verified in the embedded browser. One browser tab crashed during automation; a fresh tab successfully played both files. These checks establish playback behavior, not professional orchestration quality.

---

# Current music/Connect milestone

25 tests passed in 20.77 seconds on September 22, including four new melody checks: recovery of a known eight-note phrase and timing, rejection of noise, synthesis from only notes/timing, and API persistence/caching with the old voice-effects route disabled. Code and JavaScript syntax checks passed. The existing 21 tests retain coverage of the earlier DSP and downstream media infrastructure; they do not establish professional orchestration quality.

The Connect logo/palette/Outfit preview and preparation of Danny's melody were exercised in the in-app browser. Its guide appeared and earlier experiments remained collapsed in history. The original graphics ZIP's seven icons and Outfit font match the existing kit byte-for-byte. No live model, paid request, ensemble performance or human approval has been tested or generated in this milestone.

The current `scripts/browser_smoke.cjs` tests the melody/Connect preview against a disposable local server, generates a synthetic sample, checks the single-input interface and three planned ensembles, prepares a guide, reloads saved work and checks desktop/narrow layouts. Use the setup below. The older full four-stage browser script and report remain preserved at `0cfe313`; the historical results below describe that version.

---

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

## Optional browser test

The current browser test prepares a note-only melody guide and does not rate, approve, export or call a cloud provider. Always use the disposable data directory below. The earlier full workflow test is preserved in Git history as described above.

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
- `STUDIO_TEST_AUDIO`: supported by the historical full-workflow script only.
- `STUDIO_TEST_PHOTOS`: supported by the historical full-workflow script only.

Inspect the resulting media yourself. Numerical checks cannot establish legibility across every photograph, aesthetic difference, musical suitability, or a satisfying story.

## Observed on September 22, 2026

- **21 tests passed** in 19.52 seconds on Danny's Mac. Ruff and JavaScript syntax checks passed. Two upstream Starlette/AnyIO test-client deprecation warnings remain; neither is a test failure.
- A complete full-resolution browser run with Danny's 19.712-second recording, three existing course photographs and CONNECT completed generation, rating, selection, all three final mixes, automated test approval, export and reload. It produced 13 candidates and no browser script errors. Desktop and 390-pixel layouts had no horizontal overflow; screenshots were inspected.
- In that one run, audio took 1.930 seconds, video 26.073, text 23.203 and assembly 17.704. These are observations for this Mac and input, not promised latency.
- The complete source recording remains saved. The generated candidates use its first 15 seconds. Private inputs, outputs and browser reports are under ignored `data/`, not in Git.
- Automated decisions are confined to the verification store. Danny's separate working project contains generated audio options but no automatic stars, selection or approval.
- The read-only HPR audit passed for all three repositories: their commits and tracked-file fingerprints matched the pre-work baseline.

A fresh temporary Git clone with a new Python 3.12 environment installed successfully from the pinned requirements. Dependency consistency, the command-line launcher and Ruff passed; all 21 tests passed again in 21.26 seconds. Full-resolution artifacts were independently probed: all 13 outputs are 15 seconds, all nine video/text/final files contain 450 frames at 1080 × 1920, alpha masters use ProRes, and the export hash matches its automated approval snapshot. The independent [GitHub Actions run](https://github.com/dannygoldfield/MIT-2009-Social-Studio/actions/runs/35749953362) passed on Ubuntu for implementation commit `9416a3c`, including installation, code checks and all 21 tests. The canonical Mac checkout was then confirmed running from `Projects/MIT-2009-Social-Studio`; all 164 pre-existing private files retained their original hashes. No learned model/provider, paid request, cloud deployment, student access control or subjective listening approval is claimed by these checks.
