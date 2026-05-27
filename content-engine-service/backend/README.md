# Django Backend Scaffold

Minimal Django surface that mirrors the current local HTTP API behavior by proxying into `content_engine_service.api_server.handle_request`.

## Run

```bash
cd backend
python manage.py runserver 127.0.0.1:9000
```

## Endpoints

- `GET /health/`
- `GET|POST /api/v1/*` (proxied to core API handlers)

## Settings

Configured via `backend/config/settings.py` and environment variables prefixed with `SORAI_`.
