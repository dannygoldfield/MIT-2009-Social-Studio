# 2.009 Candidate-Selection Engine: discovery report

Date: September 22, 2026. Historical discovery snapshot, subsequently reviewed by Danny. The proposals and state descriptions below describe the pre-implementation review. For the completed local version, use README.md, ARCHITECTURE.md, CONTENT-PIPELINE.md and TESTING.md. The pinned build now requires Python 3.12.

## Specification and current state

The original brief, its completed sections 23–27, and the subsequent pause/discovery instruction form one specification. Priority: complete workflow, legibility, human selection/accountability, reliability, replaceability, generation quality, speed, features, polish.

One application: Audio → Video → Text → Assembly. Each stage offers three meaningfully different candidates, ratings, selection, and advancement. Audio additionally offers a distinct Original Mix. All generated media is 15 seconds. Final approval requires a human choice and explanation. No automatic publishing or public website.

Before the continuation arrived, a local branch was created and preliminary storage/media/preset code was written. That work is uncommitted, untested, incomplete, and paused. It is not a runnable updated product. Nothing from this session has been pushed. No paid generation calls were made and no source media was uploaded to a generation service. The existing repository and original local checkout remain unchanged.

## DECIDE NOW

### 1. Existing work inspected

- Canonical private repository: https://github.com/dannygoldfield/MIT-2009-Social-Studio at `6bc6d1a`. Its current name in the UI is Test Studio. Examined README, project instructions, rendering/media/server code, reuse records, audio implementation, and brand assets. The existing product already has separate audio, video, text, and assembly tools, a library, job records, review flags, transparent text, and exported media. Existing tests describe media verification; they have not been rerun in this discovery phase.
- HPR Audio Generator at `a012dbc3e8c0cd2a4f808edd24be5358c2d9ba63`: inspected generator code and package metadata. Deterministic bed/gesture/music recipes, source selection, loop construction, seeds, and WAV output. It mixes existing sound; it is not a hummed-melody AI composer.
- HPR Video Generator at `42e81e7ebdd97cbdc33b601b22c52d28653a276e`: inspected README and module inventory. Reproducible portrait development; its fixed geometry, one-portrait workflow, and independent audio policy are specific to HPR.
- HPR Umbrella at `7440b09f1e90d55e883beb627eadb1358887af62`: inspected architecture documentation, candidate engine and registry interfaces. Useful candidate/review/lineage boundaries, but substantially more archive/publication machinery than this application needs.
- 2.009 vertical-video renderers and export verification; Rubber Reality's strip-based deformation and frame blending; 2026 Connect branding and bundled Outfit fonts; existing local MIT sound samples and their source manifest.
- Read the three synced course PDFs. Relevant lessons: rapid turnaround, enabling students and TAs to tell stories independently, and keeping ownership/deliverables understandable. Old annual dates are not requirements for 2026. Personal planning notes will not be copied into developer documentation.

### 2. Reuse, generalize, rewrite, discard

| Decision | Material | Reason |
|---|---|---|
| Reuse/adapt | FFmpeg export boundary, frame sizing, image orientation/color handling, audio level measurement, alpha export, technical verification | Existing engineering directly supports the new output requirements; revalidate after adaptation. |
| Reuse | 2026 assets and Outfit with its included OFL notice | Consistent course identity without new design work. |
| Generalize | Seeded recipes, immutable source hashes, generation manifests, candidate/review concepts | Common behavior across four stages. |
| Rewrite | Four-tool navigation, mutable JSON library/review storage, approval flags | Need a project-centered loop, transactional history, explicit selections and explain-then-approve. |
| Reference | Rubber Reality deformation and HPR assembly/registry design | Borrow techniques and boundaries, not entire applications. |
| Exclude from new runtime | HPR registry dependencies, publication machinery, portrait-specific restrictions, old duration controls | They would make this application harder to understand and conflict with its brief. |

Retain old behavior in Git history; do not delete or migrate HPR data. The new store must not silently reinterpret legacy approvals. Use the existing canonical GitHub repository, with one documented default launch path when the replacement is ready.

### 3. Open-source findings

Activity dates below were checked through GitHub repository metadata on September 22. A recent push is evidence of activity, not a quality guarantee. No large application examined warrants a fork.

| Project | Decision; useful lesson/component | License/activity and cost of adoption |
|---|---|---|
| [FFmpeg](https://ffmpeg.org/legal.html) | USE: decode, encode, mix, composite, inspect actual outputs. Keep it behind small file-to-file functions. | LGPL/GPL depends on build and enabled components, including libx264. Last push Sep 22. External executable; codec availability must be checked. |
| [Pillow](https://github.com/python-pillow/Pillow), [NumPy](https://github.com/numpy/numpy) | USE: photo/text frames and simple audio/visual measurements; avoid a new graphics framework for the first loop. | Established projects, both pushed Sep 22. Retain applicable bundled notices; do not mistake GitHub's NOASSERTION metadata for a missing license. CPU frame processing can be expensive. |
| [FastAPI](https://github.com/fastapi/fastapi) | USE: typed API validation, file uploads, generated API documentation. | MIT; Sep 18. Adds Starlette/Pydantic/Uvicorn, but removes hand-built HTTP parsing. |
| [SQLite](https://www.sqlite.org/whentouse.html) | USE: project, candidate, rating, selection and approval transactions. | Public-domain database engine; built into Python. One writer at a time; keep render operations outside transactions. Reassess before multiple worker hosts. |
| [librosa](https://github.com/librosa/librosa) | TEST/ADAPT: onset, beat, tempo and spectral analysis. Reuse analysis functions if they improve real examples. | ISC; Sep 21. SciPy/Numba and related dependencies add weight. Beat detection is unreliable on some humming/environmental sources. No artistic score. |
| [MoviePy](https://github.com/Zulko/moviepy) | REFERENCE; reserve as an alternative if compositing becomes clearer with its clip abstraction. | MIT; Aug 26. v2 differs from v1. Its documentation acknowledges overhead relative to direct FFmpeg; do not introduce a second rendering layer without a clear benefit. |
| [Remotion](https://www.remotion.dev/docs/license) | REFERENCE/DEFER: strong option for richer programmable typography and previews. | Custom licensing/eligibility terms; active Sep 22. React/Node/browser-rendering stack and license review add work today. |
| [ComfyUI](https://github.com/Comfy-Org/ComfyUI) | REFERENCE/DEFER: reproducible generation recipes and queued jobs. Could later live behind an adapter. | GPL-3.0; Sep 22. GPU/model/custom-node dependency graph is excessive as the core application. Do not copy its graph editor or plugin ecosystem. |
| [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) | TEST: local reference-driven music experiments through a separate service/process. | Project MIT; Sep 3. Supports Apple Silicon MLX as well as GPU backends. Check the exact checkpoint and dependency terms. No local quality/performance benchmark yet. |
| [stable-audio-tools](https://github.com/Stability-AI/stable-audio-tools) | REFERENCE/TEST LATER: conditional audio model tooling. | Code MIT; Sep 18. PyTorch/model downloads; checkpoint licenses are separate. Do not pull its training stack into the core application. |
| [AudioCraft/MusicGen](https://github.com/facebookresearch/audiocraft) | REFERENCE/BOUNDED TEST: melody-conditioned generation is pertinent to humming. | Code MIT, weights CC-BY-NC 4.0; Mar 3. PyTorch and model dependencies; resolve intended-use permissions before production adoption. |
| [Wan2.2](https://github.com/Wan-Video/Wan2.2) | DEFER: candidate for later image-to-video experiments. | Apache-2.0 model terms in repository; Sep 21. Compute, identity preservation, timing and temporal consistency must be tested. Not required to prove the selection loop. |

### 4. Recommended architecture and stack

A small modular Python application served locally in a browser. Python 3.11+, FastAPI/Uvicorn, SQLite, local media files, FFmpeg/FFprobe, Pillow/NumPy, and simple HTML/CSS/JavaScript. No frontend build system, Redis, distributed scheduler, or mandatory cloud service today.

Browser → application API → shared candidate/workflow service → persisted jobs → one background rendering worker → media modules/provider adapters.

The core owns projects, source assets, candidate batches, candidates, rating history, selections, job attempts, provenance, approvals and exports. Winners can be derived from ratings plus a retained five-star achievement record; a separate complex Winner service is unnecessary. User records initially identify a declared local author, not an authenticated person.

Each candidate stores its input IDs, earlier candidate IDs, full preset snapshot, seed, duration/aspect, provider/model/version when applicable, analysis method/confidence, output hashes and attempt results. Record timing, failures, retries and known costs; unknown cost is null, never zero.

Keep files immutable. Approval captures an immutable manifest and output hash. Re-rating or selecting later cannot rewrite an earlier approval. Changing upstream selection preserves downstream files but marks incompatible selections as needing review/regeneration. A rating is never approval.

One typed request/result boundary per media stage is sufficient. Shared job outcomes include artifacts, metadata, errors and provider references. Do not build a universal AI plugin framework before a second actual integration exists.

### 5. Media behavior for the first complete loop

- Audio: three different local interpretations plus a visually separate Original Mix. Label local transformations honestly. Original Mix retains the reference's timing/pitch/order, with restrained supporting audio. A short recording requires padding; a recording longer than 15 seconds requires an explicitly identified excerpt. Preserve the complete uploaded original.
- Video: 1–10 photographs; three distinct treatments such as elastic deformation, mirrored repetition, and aggressive crop/cut motion. Local procedural rendering is sufficient for this first test.
- Text: exactly one Keyword, three alpha animations; no elaborate typography controls. Keep future content modeled as text with a v1 single-word validation rule.
- Assembly: selected Audio/Video/Text are authoritative. Generate three edits from the same ingredients: rhythmic affinity, deliberate counterpoint, and buildup/release. Ratings/winners are fallback recommendations, not permission to replace a human choice.
- Technical proposal: 15 seconds, 30 fps, 1080×1920 or 1920×1080; final H.264/yuv420p MP4 with AAC 48 kHz stereo and fast-start headers. Audio candidates: 48 kHz stereo WAV. Alpha text: ProRes 4444 MOV plus browser-friendly preview. These are proposed house specifications informed by [YouTube's encoding guidance](https://support.google.com/youtube/answer/1722171?hl=en), not universal platform requirements. Verify frame count, duration, audio, alpha and readable text in actual files.

### 6. First generation tests

After the complete local loop works, compare providers using the same short original hum, rhythm, and environmental recording. Judge recognizable contribution, meaningful difference among three, audible artifacts, completion rate, cost and wall-clock time. Danny's listening judgment is decisive.

1. [Stable Audio 3.0](https://platform.stability.ai/pricing): first hosted audio-to-audio comparison. Suitable product claim for transforming a source, but no fidelity or speed promise until tested. Listed 26 credits with $0.01/credit implies $0.78 for three standard generations, excluding retries and other charges; confirm endpoint billing before enabling paid requests.
2. [Eleven Music v2.5](https://elevenlabs.io/docs/overview/capabilities/music): second hosted reference test. Its documentation says reference audio influences style/sound and is not designed for reliable genre transformation. [Conditioning controls](https://elevenlabs.io/docs/eleven-api/guides/how-to/music/inpainting) are useful, but do not promise hummed-melody preservation. Uploads can incur charges. [Pricing](https://elevenlabs.io/pricing/api) advertises $0.15/minute but also describes per-generation metering: confirm actual minimums/model/upload charges instead of promising a pennies-per-batch figure.
3. ACE-Step 1.5: local alternative and possible Talla ownership area. Assess setup, hardware/memory, reference behavior and 15-second latency before integration.

MusicGen melody is a targeted reference-fidelity baseline, subject to its weight license. No paid calls or model installations are required to meet today's acceptance criteria.

### 7. Contrast and affinity

[Block's framework](https://www.routledge.com/The-Visual-Story/Blockah2/p/book/9781315794839) and the [supplied slides](https://www.slideshare.net/slideshow/bruce-blocks-visual-components-for-filmmakers/11355392) concern relationships across space, line, shape, tone, color, movement and rhythm. Greater difference may increase visual intensity; similarity can establish continuity. Neither guarantees emotional impact or quality.

First implementation: share audio onsets/energy, estimated tempo with confidence, selected video cut times, measured tone/color, and preset-declared motion. Use these to propose synchronization, deliberate offsets, readable text contrast and an editorial arc. Store intended relationships in the recipe. Do not infer narrative meaning, facial subjects or artistic merit from simple statistics.

### 8. Highest risks and challenges to the brief

- Personal contribution can disappear in a technically valid AI result. Preservation and interpretation must remain distinct, and listening tests must precede provider commitment.
- Three random styles may still be similar. Choose distinct style families; do not rely on randomness alone.
- A global assembler choosing “the strongest” could erase the user's earlier choices. Explicit selection should outrank stars and algorithmic suggestions.
- Five stars should create a saved winner, not be required to advance. Preserve all rating history; document what happens after a later lower rating.
- Audio rhythm may be absent or ambiguous. Unknown tempo is valid; deterministic fallback pacing must be labeled as such.
- Alpha files and full-resolution frames may make local rendering/storage the bottleneck. Benchmark actual batches; no seconds-level speed claim yet. CPU output can plausibly take minutes per batch.
- Crashes, partial batches and retries can duplicate expensive work or lose lineage. Persist work before starting, retain completed candidates, retry failed work explicitly, and never auto-charge an uncertain cloud request again.
- Local declared identity is useful accountability, not verified authorship or tamper-proof auditing. Student hosting needs authentication, isolation, retention/consent, rate/cost limits, upload validation and backup policy before access.
- Ten audio presets are a ceiling, not today's minimum. Three clearly differentiated families prove more than ten under-tested labels.

### 9. Realistic end-of-day outcome

A cloneable local application in the existing private repository, one complete four-stage 15-second workflow with actual media, persisted projects/ratings/winners/selections, three final outputs, explanation-gated approval and export with a provenance manifest. Include a rights-clear redistributable demo, a separate real 2.009 local test, clean-install verification, meaningful automated tests, known limitations, the playbook and Talla's handoff.

High-quality AI reinterpretation and a live-tested hosted adapter are stretch goals. Student accounts, a public site, production scale and polished UI are outside today's acceptance criteria. Existing dependencies installed locally do not count as tested installation instructions, and the new application is not yet runnable.

### 10. Exact proposed build sequence after review

1. Record approved scope and acceptance checks in the playbook; preserve legacy history and select one new launch path.
2. Build shared persistence and the smallest compare/rate/select UI. Use a clearly labeled redistributable fixture set. Verify reopen/restart persistence.
3. Complete assembly → three final options → choose → explanation → explicit approval → downloadable file/manifest. Test approval rejection and history before sophisticated rendering.
4. Replace fixture stages with minimal actual 15-second audio, bold photo animation and alpha Keyword rendering; add Original Mix. Finish one real end-to-end example before expanding styles.
5. Add measured cross-stage timing/contrast, output validation, persisted job progress and failure/retry recovery. Keep one worker.
6. Run representative 2.009 material through the full loop; inspect and listen to exported files. Validate both orientations, actual alpha, changed upstream choices, failed jobs and restart state.
7. If the loop is reliable, run the bounded audio-provider comparison and integrate only the most useful adapter. Otherwise leave a documented contract and test plan.
8. Test a clean clone/install, remove scaffolding/dead paths, finalize architecture/research/limitations and Talla handoff, run checks, then commit/push the reviewed implementation to the canonical repository. No media or credentials in Git. Collaborator invitation needs Talla's exact GitHub identity if requested.

## CAN WAIT

- Final provider commitment; adaptive generation; automatic artistic ranking; a detailed typography interface; sophisticated semantic/vision analysis; more preset breadth.
- GPU deployment, a distributed queue, PostgreSQL/object storage and other infrastructure until measured need or student hosting requires them.
- Authentication/moderation implementation today, but not their design review before student access.
- Course-library ingestion automation, Key Phrase, durations other than 15 seconds, automatic posting, and 009connect.com.

Two-week direction: use the next few days for Talla's architecture review and observed TA trials, then harden identity, per-project access, quotas, storage and consent for a small supervised Story Officer alpha around October 6. That date is a target, conditional on the readiness checks, not a deployment promise.
