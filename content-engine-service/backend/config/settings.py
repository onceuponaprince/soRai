from __future__ import annotations

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") in {"1", "true", "TRUE", "yes", "on"}
ALLOWED_HOSTS = [host for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",") if host]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = []
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(BASE_DIR / "db.sqlite3"),
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SORAI_CONTENT_ENGINE_ROOT = os.environ.get("SORAI_CONTENT_ENGINE_ROOT", str(REPO_ROOT / "content-engine"))
SORAI_ARTIFACT_ROOT = os.environ.get("SORAI_ARTIFACT_ROOT", str(REPO_ROOT / "artifacts"))
SORAI_STORE_PATH = os.environ.get("SORAI_STORE_PATH", str(REPO_ROOT / "sorai.sqlite3"))
SORAI_ALLOWLISTS_PATH = os.environ.get("SORAI_ALLOWLISTS_PATH", "")
SORAI_API_KEYS_PATH = os.environ.get("SORAI_API_KEYS_PATH", "")
SORAI_RUNNER = os.environ.get("SORAI_RUNNER", "")
SORAI_DEFAULT_LANE = os.environ.get("SORAI_DEFAULT_LANE", "api")
SORAI_DEFAULT_TOOL = os.environ.get("SORAI_DEFAULT_TOOL", "router-qwen3.6")
SORAI_TIMEOUT = int(os.environ.get("SORAI_TIMEOUT", "180"))
SORAI_MOCK_OUTPUT = os.environ.get("SORAI_MOCK_OUTPUT", "")
