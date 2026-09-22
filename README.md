# MIT 2.009 Candidate Studio

**One local application for making choices across Audio → Video → Keyword → Assembly.**

Generate three possibilities, compare, rate, select, and advance. Make three final mixes from your selected ingredients. Explain **“Why this one?”**, explicitly approve a version, and export the media with its provenance.

Built for Danny, Talla, and the 2.009 TAs, with a small student trial as the next milestone. The purpose is entertaining, inspiring stories about the course and interest in the **December 7, 2026 final presentations livestream**. Humans retain taste, authorship, and approval.

## What works in this version

- Persistent projects, uploaded originals, generation settings, rating history, saved five-star winners, selections, jobs, and approval records.
- **15 seconds throughout.** Vertical 9:16 or horizontal 16:9.
- Three audio interpretations, plus a separately presented **Original Mix** that preserves the recording's timing, pitch, and order within the excerpt.
- Three bold photographic treatments from 1–10 images; three transparent animations of one Keyword.
- Three final edits using the exact selected Audio, Video, and Text ingredients.
- Changes to earlier selections clear affected later selections without deleting media or history.
- Explicit explanation and approval, followed by an MP4 + provenance ZIP export. Nothing is published automatically.
- A built-in practice project with locally generated sample images and sound. No private student media is included in Git.

**Generation is currently local signal/image processing, not a learned AI model.** The files are real, not mock players. Cloud generation is researched but not integrated or live-tested. This release proves the complete interaction and preserves a small provider boundary for the next iteration.

## Run locally

Use **Python 3.12+** and **FFmpeg/FFprobe** on macOS or Linux. Windows users should use WSL; native Windows is not supported by the worker lock.

```sh
git clone https://github.com/dannygoldfield/MIT-2009-Social-Studio.git
cd MIT-2009-Social-Studio
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
.venv/bin/python -m mit2009_studio.server
```

Open **http://127.0.0.1:8773**. Keep the terminal running while rendering. The server binds only to this computer. A fresh installation does not need an API key, GPU, account, or paid service.

Install FFmpeg with `brew install ffmpeg` on macOS or `sudo apt install ffmpeg` on Ubuntu/Debian. Check `ffmpeg -version` and `ffprobe -version` before starting. The build must include H.264/libx264 and ProRes encoders.

On a Mac, after setup, double-click **Open 2.009 Studio.command**. The older Test Studio shortcut also opens the new application.

Click **Try the sample project**, then Generate, rate a candidate, select it, and continue through the four stages. Use **CONNECT** as the sample Keyword. Sample selections and approvals are yours to make; the app does not automatically make them.

## Keep your work

By default, private work lives in **`data/candidate-engine/`**, separate from the previous studio's data layout. Back up that entire folder while the server is stopped. Source media and generated artifacts remain local and are excluded from Git.

```sh
.venv/bin/python -m mit2009_studio.server --port 8773 --data-dir /path/to/private/studio-data
```

Do not run two studio processes against the same folder. The app deliberately does not migrate old library records or reinterpret old approval flags. The previous implementation is preserved in Git at commit `6bc6d1a`.

## Verify your setup

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check mit2009_studio tests
```

Tests render actual 15-second audio/video/text/assembly at smaller dimensions for speed, in both orientations. They inspect duration, frame counts, audio, actual transparent pixels, persistence, approval/export integrity, failure recovery, and selection rules. A separate browser test exercises full-resolution output and is described in [TESTING.md](docs/TESTING.md).

## Start here, Talla

Read [TALLA.md](docs/TALLA.md), then [ARCHITECTURE.md](docs/ARCHITECTURE.md). Please challenge the design. In particular, help decide how to improve personal-audio interpretation and how little infrastructure we need for a small student alpha.

- [Content pipeline playbook](docs/CONTENT-PIPELINE.md): the accumulated product rules.
- [Architecture and data](docs/ARCHITECTURE.md): modules, persistence, jobs, provenance, APIs.
- [Discovery and research](docs/DISCOVERY-2026-09-22.md): inspected prior work, alternatives, licenses, and provider shortlist.
- [Testing](docs/TESTING.md): repeatable checks and observed results.
- [Known limitations and student alpha](docs/LIMITATIONS.md): unfinished work and readiness gates.
- [Reuse and licensing](docs/REUSE.md): origins and dependency considerations.

The API reference is available locally at `/docs`. Source-level configuration is in `mit2009_studio/presets.json`; `STUDIO_PRESETS` can point to a separate editable JSON file. There is deliberately no style editor or elaborate prompting interface yet.
