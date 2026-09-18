# First-release verification

- Twelve functional tests passed in the independent 2.009 Python environment.
- Browser photo import, numeric ordering, per-photo timing, saved drafts, and video export were exercised.
- Real 1080 × 1920 outputs were generated for silent video, stereo WAV, animated title, transparent ProRes caption, and assembled H.264/AAC MP4.
- The final example lasts 4.2 seconds at 30 fps, with Rec.709 color information and stereo sound.
- Output loudness uses constant gain and a -1 dB true-peak ceiling; the sample reaches its -18 LUFS target without compression.
- Source fingerprints and native video-stream hashes verify reproducibility and preservation.
- The HPR source fingerprints, commits, and clean working copies match the pre-work baseline.

Media files, examples, ingredient-copy records, and detailed runtime reports remain in the ignored local data folder. Creative review is still Danny’s decision.


## 2026 Connect and audio audition update

- All fourteen functional tests passed, including new HTTP checks for saved audio assessments, notes, bucket changes, invalid metadata rejection, bundled Outfit selection, and brand-asset path boundaries.
- Fifteen Adobe shortlist WAV files decode successfully. Each independent copy matches its source hash. All remain unassessed.
- Browser checks at the user's 579-pixel content width covered the brand kit, color copying, the three audio buckets, shortlist controls, native sample playback, and Use in a mix selecting the matching effect. No horizontal overflow was observed.
- A full-size Outfit title rendered at 1080 × 1920, 30 fps, for 1.4 seconds. Its rendered frame was visually reviewed.
- The original 2026 draft is migrated without deleting the older draft key. Existing media and exports are preserved.
- HPR's three repositories still match their original fingerprints and clean working states.
- The final small layout/import refinements passed JavaScript syntax checks; a final automatic browser refresh and additional desktop viewport checks were unavailable because the browser's policy check temporarily failed.
