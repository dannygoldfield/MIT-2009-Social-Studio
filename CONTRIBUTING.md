# Contributing

Read README.md and docs/TALLA.md first. This is one candidate-selection application; preserve the complete human decision loop when improving any generator.

1. Create a focused branch from main.
2. Make the smallest change that improves a real workflow or solves an observed failure.
3. Run `ruff check mit2009_studio tests` and the relevant `pytest` checks in the project environment.
4. For rendering changes, inspect actual exports and include a useful example or verification result in the PR. Do not commit private media.
5. Update `docs/CONTENT-PIPELINE.md` and relevant technical docs for changed behavior or learned rules.
6. Describe the concrete user-visible behavior, validation, and limitations in the pull request.

Do not silently approve media, change historical approval snapshots, overwrite sources, import HPR at runtime, or add automatic publishing. Cloud requests need explicit user-facing choice, clear costs/data handling, and failure handling before they are enabled.

Code sharing is currently through this private repository. No open-source license is granted for the application by this update. Third-party licenses, including the bundled font license, still apply.
