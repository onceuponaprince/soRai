from __future__ import annotations

from django.urls import path, re_path

from config.views import api_proxy, health_view

urlpatterns = [
    path("health/", health_view),
    re_path(r"^api/v1/(?P<subpath>.*)$", api_proxy),
]
