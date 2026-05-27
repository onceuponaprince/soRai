from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from content_engine_service.access_policy import AccessPolicy
from content_engine_service.api_auth import ApiKeyAuthenticator
from content_engine_service.api_server import ApiConfig, handle_request


@lru_cache(maxsize=1)
def _api_config() -> ApiConfig:
    policy = (
        AccessPolicy.from_json_file(settings.SORAI_ALLOWLISTS_PATH)
        if settings.SORAI_ALLOWLISTS_PATH
        else AccessPolicy.default()
    )
    authenticator = (
        ApiKeyAuthenticator.from_json_file(settings.SORAI_API_KEYS_PATH)
        if settings.SORAI_API_KEYS_PATH
        else None
    )
    return ApiConfig(
        engine_root=Path(settings.SORAI_CONTENT_ENGINE_ROOT),
        artifact_root=Path(settings.SORAI_ARTIFACT_ROOT),
        policy=policy,
        store_path=Path(settings.SORAI_STORE_PATH) if settings.SORAI_STORE_PATH else None,
        runner=Path(settings.SORAI_RUNNER) if settings.SORAI_RUNNER else None,
        default_lane=settings.SORAI_DEFAULT_LANE,
        default_tool=settings.SORAI_DEFAULT_TOOL,
        timeout=settings.SORAI_TIMEOUT,
        mock_output=settings.SORAI_MOCK_OUTPUT,
        authenticator=authenticator,
    )


def health_view(request):
    del request
    return JsonResponse({"status": "ok"})


@csrf_exempt
def api_proxy(request, subpath: str):
    body: dict = {}
    if request.method in {"POST", "PUT", "PATCH"}:
        if request.body:
            body = json.loads(request.body.decode("utf-8"))

    query = {key: request.GET.getlist(key) for key in request.GET.keys()}
    headers = {key.lower(): value for key, value in request.headers.items()}
    path = "/api/v1/" + subpath

    status, payload = handle_request(
        config=_api_config(),
        method=request.method,
        path=path,
        query=query,
        body=body,
        headers=headers,
    )
    return JsonResponse(payload, status=status)
