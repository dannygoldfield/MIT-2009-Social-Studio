# MIT 2.009 Social Studio

A separate, local studio for Danny Goldfield’s 2.009 social media work. Four tools share this project’s own media library and make downloadable files.

1. **Video:** arrange class photographs and edited video clips, change timing, adjust crop focus, choose still frames or gentle motion, and export silent MP4s.
2. **Audio:** create seeded soundtracks from a main sound, optional music layer, and optional accent. Export 48 kHz stereo WAV files at a consistent listening level, with peak-safe constant gain, and listen before approving.
3. **Text animator:** make standalone animated titles, add text over photographs or videos, or export transparent ProRes MOV overlays. Four styles: Rise & settle, Soft reveal, Word by word, and Typewriter.
4. **Assemble:** combine selected video, sound, and optional transparent text into a new MP4. Without an overlay the video stream is copied without re-encoding.

## Open the studio

1. Double-click **Open 2.009 Studio.command**.
2. Keep its Terminal window open while using the studio.
3. Add files, make an export, review it, and use its Download button.

The studio opens at http://127.0.0.1:8772/. It runs on this Mac; that address is not a public sharing link. Media and export history stay in this repository’s ignored `data/` folder. Closing the browser does not stop a render; closing the launcher does.

The first setup uses a dedicated `.venv`. For another computer, install Python 3.11+, FFmpeg, and the package:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m mit2009_studio.server
```

## HPR isolation

HPR repositories, media banks, databases, review decisions, and environments are independent. This code has no HPR runtime imports, symlinks, shared database, Git submodule, or automatic synchronization. `docs/hpr-read-only-baseline.json` records the three HPR commits and source fingerprints inspected at the start.

The audio mixing core is independently adapted from Danny’s HPR Audio Generator. Photo framing and motion are adapted from the existing 2.009 social-video work. Assembly follows the HPR pattern of combining separately selected components. HPR-specific portrait-development effects and its Registry are not runtime dependencies here.

Any starting sound ingredients are independent local copies. They are excluded from Git and have no inherited 2.009 approval. Changing or approving a 2.009 output cannot change an HPR bank.

## Formats and review

- Vertical: 1080 × 1920; square: 1080 × 1080; wide: 1920 × 1080.
- Video exports use 30 fps H.264, with MP4 headers arranged for browser playback.
- Each photo/clip occupies its selected duration. Dissolves occur inside that duration.
- The Video tool produces silent edits. The Text tool preserves existing audio when adding text to a video. The Assembler adds or replaces the soundtrack.
- Transparent text exports are MOV files; an MP4 preview shows the animation against gray.
- Every render is a draft. “Keep for comparison” and “Approved by me” are local review decisions; neither publishes anything.
- Export names, settings, and output fingerprints are saved with each job. Originals are preserved.

## First-version scope

This version works with class photographs, edited clips, and sound files. It does not select useful moments from raw footage, replace the TAs’ editing workflow or Aaron’s independent edits, synthesize speech from text, automatically transcribe captions, or post to social accounts.

## Verification

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/check_hpr_unchanged.py
```

Tests render actual audio, video, animated text, transparent overlays, and assembled MP4s. They check timing, dimensions, image coverage, alpha channels, audio preservation, repeatability, and the media-library path boundary.
