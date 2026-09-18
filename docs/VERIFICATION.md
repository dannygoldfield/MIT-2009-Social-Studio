# First-release verification

- Twelve functional tests passed in the independent 2.009 Python environment.
- Browser photo import, numeric ordering, per-photo timing, saved drafts, and video export were exercised.
- Real 1080 × 1920 outputs were generated for silent video, stereo WAV, animated title, transparent ProRes caption, and assembled H.264/AAC MP4.
- The final example lasts 4.2 seconds at 30 fps, with Rec.709 color information and stereo sound.
- Output loudness uses constant gain and a -1 dB true-peak ceiling; the sample reaches its -18 LUFS target without compression.
- Source fingerprints and native video-stream hashes verify reproducibility and preservation.
- The HPR source fingerprints, commits, and clean working copies match the pre-work baseline.

Media files, examples, ingredient-copy records, and detailed runtime reports remain in the ignored local data folder. Creative review is still Danny’s decision.
