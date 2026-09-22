# Talla: start here

Danny wants this to become a tool you can understand, challenge, improve, and potentially take substantial ownership of. Your first job is not to preserve the architecture out of politeness.

## The product hypothesis

Three meaningfully different possibilities → a human compares and selects → the next stage responds. Repeat across Audio, Video, Keyword, and Assembly. The final author explains “Why this one?” and explicitly approves the result. Choice and authorship are the product, not just a wrapper around generation.

## Try it first

Follow the root README, click **Try the sample project**, and complete one 15-second story. No account/API key/GPU is needed. Practice images and melody are generated locally. Read `service.py` for the rules, `jobs.py` for work handling, and `render.py` / `providers/local.py` for media. Run the tests before changing them.

## What exists

A functioning local four-stage workflow with persistent projects, files, three-option batches, Original Mix, ratings, saved winners, selections, provenance, transparent text, three final edits, explain-then-approve, and downloadable approved output/manifest. One SQLite database, one worker, one browser UI.

Generation is currently procedural. No cloud adapter is claimed to work. Source-aware music generation and genuinely stronger aesthetic alternatives remain open creative/engineering work. Local user identity is self-declared; this is not a student-ready hosted service.

## Why this design

Python and FFmpeg reuse existing media knowledge. SQLite keeps setup small and decisions transactional. A small audio adapter boundary contains likely provider changes. Framework-heavy frontend, distributed jobs, training infrastructure and publishing were deliberately left out. Changing upstream selections preserves history while forcing downstream choices to be reconsidered.

## Please challenge these decisions

- Is this architecture unnecessarily complicated? What would you simplify or replace?
- Does the shared candidate model help, or hide important media differences?
- Are we storing the right provenance? What will be impossible to reconstruct?
- Is the audio provider boundary useful or premature? Where are we reinventing solved problems?
- Which work should move into an isolated background process before student access?
- What fails first when 100+ students use it: jobs, storage, cost, moderation, usability, or identity?
- What privacy/security issues must be resolved before a small alpha?
- What should we build now to avoid rewriting in two weeks? What should we deliberately defer?
- Do three alternatives actually feel different and worth choosing between?
- Which parts would you most want to own?

## Valuable ownership areas

1. **Reference audio:** compare Stable Audio, Eleven Music, and ACE-Step using the same hum/rhythm/environmental sources. Measure recognizable contribution, variation, failures, latency and cost. Do not choose solely by a provider demo.
2. **Workflow research:** observe Danny/TAs making choices. Identify controls people actually need. Compare whether a second batch improves a decision or only extends browsing.
3. **Student alpha:** propose the smallest authenticated, isolated, budget-limited deployment for a supervised Story Officer test. Write a readiness check before inviting students.
4. **Rendering:** strengthen visual variety, text readability, and rhythm-aware assembly without turning the interface into an editing suite.

## How to contribute

Use a small branch and pull request. Describe the behavior that improves, show an example output when rendering changes, and include relevant tests. Keep private media and credentials out of Git. Update `docs/CONTENT-PIPELINE.md` when a rule or assumption changes.

The repository is private. Danny can grant you collaborator access in GitHub Settings → Collaborators using your exact GitHub username. No invitation has been sent as part of this build.
