# MIT 2.009 Test Studio · 2026 Connect

A separate, local studio for Danny Goldfield’s 2.009 social media work. Four tools share this project’s own media library and make downloadable files.

1. **Video:** arrange class photographs and edited video clips, change timing, adjust crop focus, choose still frames or gentle motion, and export silent MP4s.
2. **Audio:** create seeded soundtracks from a main sound, optional music layer, and optional accent. Export 48 kHz stereo WAV files at a consistent listening level, with peak-safe constant gain, and listen before approving.
3. **Text animator:** make standalone animated titles, add text over photographs or videos, or export transparent ProRes MOV overlays. Four styles: Rise & settle, Soft reveal, Word by word, and Typewriter.
4. **Assemble:** combine selected video, sound, and optional transparent text into a new MP4. Without an overlay the video stream is copied without re-encoding.

## Open the studio

1. Double-click **Open 2.009 Test Studio.command**.
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

## 2026 Connect edition

This copy is permanently branded for 2026: supplied Connect logos, the Outfit typeface, course palette, and mascots. The interface uses a #F4F4F4 background with white panels. The text animator uses bundled Outfit Bold in both its preview and new exports; existing exports are preserved. Its color swatches apply the course palette in one click. The header's **2026 brand kit** offers the logos, colors, font, and mascot references.

Brand assets are independent local files in `mit2009_studio/web/brand-2026/`. The supplied PNGs are unchanged. Screen hex colors were sampled from a color-managed rendering of the supplied CMYK Illustrator palette. Outfit is redistributed under its included SIL Open Font License. No remote fonts or external brand services are used.

The 2026 draft key migrates an existing draft without deleting it. If a 2027 studio is wanted, create another repository and independent data folder, port, brand folder, and browser draft key. Do not turn this installation into the next year's studio.

## Audio: listen before mixing

Audio starts with **Listen & choose**. The three buckets are **Sound beds**, **Sound Effects**, and **Wildcards** (the former music/stem bucket). Each file has a player, Keep / Maybe / Pass assessment, editable bucket, and a note saved when the field loses focus. Playback stops any other audio player. Passed files stay out of the mix menus.

The **New Adobe shortlist** filter contains 15 independently copied, unassessed candidates from Danny's local Adobe library: springs, toys, water, and other playful sound effects. These are filename-based editorial suggestions, not claims of listening approval. Source filenames, source hashes, and suggested uses are kept in the local library and provenance record. The originals are unchanged.

Choose **Use in a mix** to place a file in its bucket's layer, or open **Make a mix**. Sound beds and Wildcards loop; a Sound Effect plays once, away from the boundaries. Each layer has its own player and volume control. The render engine retains its existing internal Bed/Gesture/Music recipe fields for compatibility; user-facing language uses the new bucket names.
