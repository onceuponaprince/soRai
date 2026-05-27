# content-engine

Profile-driven skill renderer.

This checkpoint rebuilds the standalone renderer only:

- reads `profiles/<profile>/profile.toml`
- merges the profile with `core/SKILL.template.md`
- copies profile references
- writes `SKILL.md`
- writes `frontmatter.yaml` for tooling and AI skill discovery

## Render

```bash
lib/render.sh --profile general --dest /tmp/soRai-general --force
```

## Test

```bash
tests/run_all.sh
```
