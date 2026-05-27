# content-engine-service

Service-library checkpoint for soRai.

Current surfaces:

1. Core library pipeline (`render -> dispatch -> boundary -> sink -> store`)
2. CLI for profiles/render/run/serve
3. Local HTTP API (WSGI)
4. Django backend scaffold that proxies `/api/v1/*` into the same core handler

## Test

```bash
python3 -m pytest -q
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
