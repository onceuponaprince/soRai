# content-engine-service

Service-library checkpoint for soRai.

Current surfaces:

1. Core library pipeline (`render -> dispatch -> boundary -> sink -> store`)
2. CLI for profiles/render/run/serve
3. Local HTTP API (WSGI)
4. Django backend scaffold that proxies `/api/v1/*` into the same core handler
5. Panel scaffold (`panel/`) for browser-based operator/admin flows

## Test

```bash
python3 -m pytest -q
```

## Front-Facing Panel Tests

```bash
python3 -m pytest -q tests/test_panel_interactions.py
```

If browsers are not installed yet:

```bash
python3 -m playwright install chromium
```

## Run Local HTTP API

```bash
PYTHONPATH=src python3 -m content_engine_service.cli serve \
  --engine-root ../content-engine \
  --artifact-root /tmp/sorai-artifacts \
  --store /tmp/sorai.sqlite3 \
  --mock-output "mock output"
```

## Run Django Scaffold

```bash
cd backend
python manage.py runserver 127.0.0.1:9000
```

## Run Panel Scaffold

```bash
cd panel
python3 -m http.server 8787
```
