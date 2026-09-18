# Source reuse and independent evolution

This project belongs to Danny Goldfield and is versioned separately from his HPR tools.

- `mit2009_studio/audio_core/generator.py`: adapted from `HPR-Audio-Generator/src/hpr_audio_generator/generator.py` at the commit recorded in the baseline. Allows optional accents and fractional social-video durations. Local configuration dataclasses replace HPR’s XML/runtime bindings.
- Photo framing: adapted from the 2.009 full-bleed social-video renderer. Adds selectable formats, independent crop focus, clip input, and per-item durations.
- AV assembly: reimplemented as a local file-to-file operation following HPR’s selected-component and video-stream-copy boundary. It does not connect to HPR Registry or its approval records.
- Text animation, the shared local library, review state, job queue, and browser UI are new for 2.009.

HPR read-only references in documentation and the optional isolation audit are not runtime dependencies. This repository can run with all HPR directories unavailable.
