# Your idea, played beautifully

The product goal is Danny's: **“Make the self identified non-musical person believe they are musical.”** A person offers a phrase, hears it developed with musical intelligence, recognizes their own contribution, and feels ownership. The result must not be a generic good track with a disconnected source upload.

## Revised audio brief

One input: hum, sing, or play a musical phrase, quickly or carefully. Three instrumental ensemble interpretations. No recognizable sung words; no bed/effects buckets; no fourth Original Mix candidate. The original is available as a reference only. The generated performance needs convincing instrumental sound, responsive phrasing, harmonic intention, an arc and a satisfying ending. Describe generated music honestly; no claim that human session musicians performed it.

Three initial directions:

1. **Bass-heavy dance.** The phrase becomes the lead hook. Deep controlled bass, tight drums, a small build, an intentional arrival and a clean ending. Accompaniment leaves room for the hook.
2. **Chamber trio.** Piano, violin and cello share the phrase with breathing room, expressive dynamics, answering figures, restrained harmony and a chamber-room sound.
3. **Jazz trio.** Piano leads; upright bass and drums support and answer. A settled pocket, tasteful reharmonization, a short variation and a clear return to the user's motif.

These are performance briefs, not just equalization settings or three instrument substitutions over the same generic bed.

## Prepared locally

`melody.py` uses [librosa pYIN](https://librosa.org/doc/main/generated/librosa.pyin.html) to estimate monophonic pitches and voicing, groups stable notes, and synthesizes a simple wordless guide from note numbers and timing only. The synthesizer cannot access the source waveform. No speech transcription or source vocal samples enter the guide. Original files remain unchanged.

This guide is a technical handoff, not the promised orchestration. It is deliberately labeled as a melody check in the UI. It can misread octaves, miss quiet/rough notes, or fragment glides. Do not interpret its confidence as a person's musical ability. If the guide does not retain the idea, improve extraction or choose a better melody-conditioned path before generating a polished result from the wrong phrase.

The test recording produced 31 estimated note events, with 38.1% of frames passing the conservative pitch-confidence gate. That is not a verified transcription. A known eight-note synthetic phrase was recovered correctly; noise was rejected. Danny still needs to recognize his phrase in the guide and, more importantly, in the final interpretation.

## First model experiment — pending authorization and access

Candidate: **Stable Audio 3.0 Large**, using audio-to-audio on the wordless guide. [Official guidance](https://stability.ai/guides/stable-audio-3-prompt-guide) describes instrument/style changes with a tradeoff between source preservation and transformation. It does not establish that our melody-to-ensemble task will succeed. [Pricing](https://platform.stability.ai/pricing) lists 26 credits per standard generation at $0.01 per credit: approximately $0.78 for three. Recheck endpoint/billing details before a live request.

Proposed bounded test: three 15-second renders, one per ensemble, total spend cap $1, no automatic retries. Upload only `melody-guide.wav`, not the original voice recording. Record model, prompt, conditioning settings, request IDs, costs, timing and input/output hashes. No live call has been made and no API adapter is claimed tested. API access is not configured on this machine. Do not put keys in the repository or conversation.

Use the same guide for all three. Start with a moderate transformation setting based on the verified API contract; do not copy a UI parameter into an API without checking its name and semantics. If a request has an uncertain outcome, stop and reconcile rather than charge again. No budget expansion without authorization.

[Eleven Music's reference documentation](https://elevenlabs.io/docs/overview/capabilities/music) describes style/sound guidance and warns it is not designed for reliable genre transformation. That makes it a weaker first fit for this precise test despite its sound-quality claims. A local model remains a possible comparison; neither local nor hosted automatically means professional quality.

## Listening acceptance

A successful result must pass both **musical quality** and **recognizable contribution**:

- The distinctive contour and rhythm of the user's phrase remain audible, even with expressive reinterpretation.
- No sung words, spoken words or copied vocal fragments. Check actual listening; an instrumental prompt is not proof.
- The ensemble sounds coherent, expressive and convincing, with parts that respond to each other.
- The three choices differ in arrangement, feel and instrumentation, not merely timbre or volume.
- Each has an intentional beginning, development and ending within 15 seconds.
- A person who calls themselves non-musical can say what in the result began with them and wants to try another phrase.

Do not display an artistic score or tell the person they are musical as a substitute for delivering the experience. Do not approve candidates on the user's behalf. Ask people to compare the source and result, identify their contribution, choose a version and explain why.

After that first listening review, decide whether to integrate this provider, adjust the conditioning, or test another model. Do not build a provider-selection interface or complex prompting panel before the experiment earns it.
