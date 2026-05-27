# content-engine-service

Service-library checkpoint for soRai.

This package is intentionally API-free for now. It proves the core execution path:

1. discover profiles from `content-engine`
2. render a profile bundle
3. read `frontmatter.yaml`
4. dispatch through an injectable runner
5. validate boundary rules
6. route output to a workspace artifact or approval event

## Test

```bash
python3 -m pytest -q
```
