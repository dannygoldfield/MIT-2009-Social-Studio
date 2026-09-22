# 2.009 content pipeline playbook

Status: discovery reviewed; the first complete local application is implemented. Danny asked for a simple, visible product and a repeatable way to check our work. Current scope uses local transformations, with no paid generation or public deployment. See [testing](TESTING.md) for evidence and [limitations](LIMITATIONS.md) for the remaining work.

## Purpose

Help people create entertaining, inspiring stories about MIT 2.009, supporting interest in the December 7, 2026 final presentations livestream. Enable student authorship through comparative judgment.

## Principles

One candidate-selection engine. AI expands possibilities; humans select and remain accountable. Priorities: complete loop, legibility, accountability, reliability, replaceability, quality, speed, features, polish. Discovery was reviewed before proceeding with the complete implementation.

## Inputs

Personal audio; optional musical/sound beds and effects; 1–10 photographs; exactly one Keyword. Preserve uploaded originals and useful source attribution. Never commit private course media or credentials.

## Workflow

Audio → Video → Text → Assembly. Generate 3 → Compare → Rate → Select → Advance. Choose one final mix → Why this one? → Approve → Export. Duration is a project setting fixed to 15 seconds in V1, with no duration control.

## Audio

Three interpretations from different editable style families. Original Mix is separate: preservation plus support from beds/effects. Local transformations are allowed initially and must not be mislabeled as AI. Short/long source handling must be visible; preserve the full original even when an output uses an excerpt.

## Video

Use 1–10 photos and either 9:16 or 16:9. Begin with bold, meaningfully different movement/deformation/repetition. Presets remain editable.

## Text

One Keyword, three transparent 15-second treatments. Keep text content extensible for later phrases without exposing phrase controls now.

## Assembly

Exactly three final mixes, primarily sharing selected strong ingredients with different editorial decisions. Explicit human choice takes precedence over ratings or automatic recommendations. Do not override authorship invisibly.

## Candidate selection

Persist every batch, candidate, rating, five-star winner and selection. Five stars is necessary to earn winner status; winner status never grants approval. Ratings below five may still be selected so progress does not require inventing enthusiasm. Preserve earlier batches without foregrounding endless browsing.

## Contrast + affinity

Use differences/similarities in visual components and rhythm to propose editorial relationships. Measurements and declared intentions are not artistic scores. Unknown rhythm/tempo is valid.

## Accountability

Contribution → Comparison → Selection → Explanation → Approval. A human explicitly approves a chosen final file with a meaningful short explanation. Preserve who/what/when/why. Local named users are declared identities, not authentication.

## Provenance

Store source and output hashes, source/candidate relationships, settings, full preset snapshots, provider/model/version, analysis method/confidence, job attempts, known costs, rating history, selections, approval explanation and timestamps. An approval captures an immutable snapshot of the exact output.

## Decision rules

- Research before major implementation; build one complete loop before optimizing independent generators.
- Reuse the existing canonical repository and mature media libraries. Keep HPR runtime/data completely independent.
- Changing earlier choices preserves existing artifacts and history; the application clears affected downstream selections and requires review/regeneration.
- Provider-generated and locally transformed outputs must disclose how they were made.
- No automatic publishing. No public website today.
- No silent retry of an uncertain paid request. Unknown cost remains unknown.
- Update this playbook when a rule, correction or limitation is discovered.

## Definition of done

A clean GitHub repository Talla can clone, install and run using verified instructions. One realistic complete workflow produces real inspectable media, persists state across restart, supports all selection/accountability concepts and exports approved media plus provenance. Include redistributable demo material, tests, architecture, research, setup/API/environment information, honest limitations and Talla handoff. A polished interface and student infrastructure are not today's requirements.

## Known problems

Learned-provider output quality, reference fidelity, cost and latency have not been live-tested. The app has no authentication, student permissions, moderation, quotas, deletion UI or hosted infrastructure. Heuristic onsets are not verified beats; simple image measurements do not identify subjects. Font coverage is limited. See LIMITATIONS.md for the full list. Technical output checks do not establish artistic quality; Danny still needs to listen and choose.

## Future ideas

Small supervised Story Officer alpha in roughly two weeks; course photo library; authenticated contribution/submission; better reference-conditioned generation; evidence-based rhythm/visual analysis; then broader student access. Key Phrase, other durations and website integration remain later extensions.

## Corrections and decisions recorded during discovery

2026-09-22: The first attached request was truncated. Its continuation and pause instruction are equally authoritative parts of the specification. Discovery must be reviewed before further substantial implementation.

2026-09-22: An initial sandboxed GitHub check appeared to show invalid credentials. A permitted network check succeeded. GitHub is accessible; the private MIT-2009-Social-Studio repository already exists and is the recommended canonical home.

2026-09-22: HPR's existing audio generator mixes sources; it does not synthesize a composition from a hum. Provider reference conditioning may preserve sound/style without melody or waveform fidelity. Original Mix remains a distinct preservation path.

2026-09-22: Simple onsets are not verified beats; low visual variation is not a subject detector; neither analysis measures quality.

## Implementation decisions and verification corrections

2026-09-22: Danny approved continuing after discovery, emphasized simplicity and self-checking, and supplied a personal test recording. The first version uses Python/FastAPI, SQLite, FFmpeg, NumPy/Pillow and plain browser code. Python 3.12 is the tested minimum for the pinned dependencies.

2026-09-22: The full loop renders real 15-second files. Three styles must come from different families; Original Mix is a fourth, separately displayed option. Five-star achievement is retained even after later re-rating. Selection requires a rating, but never requires five stars.

2026-09-22: A full browser test used the provided recording, three existing course photographs and CONNECT. Automated test ratings and approval live in a separate data directory under an explicitly automated test author. Danny's working project has no automatic ratings, selections or approval. No recording or course photograph is committed or sent to a generation service.

2026-09-22: FFmpeg rejected a leading-dot fade duration; use 0.25, not .25. Browser tests now wait for the exact requested job ID. Photo thumbnails use a fixed flex basis to avoid overlap. Retain these lessons in checks instead of assuming an HTTP success proves a correct output.

2026-09-22: A redistributable practice project creates its own geometry and melody. Tests render both orientations, inspect actual alpha pixels, check source preservation, immutable approval/export hashes, failed-job recovery and upstream-selection invalidation. Detailed commands/results are in TESTING.md.
