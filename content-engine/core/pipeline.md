# Pipeline

1. Parse content type, raw context, platforms, and mode.
2. Read the relevant type spec.
3. Apply the configured voice rules.
4. Draft the canonical piece.
5. Adapt it for each target platform.
6. Run quality gates.
7. Route through the configured sink when mode is `stage`.
8. Report what was produced and where it went.
