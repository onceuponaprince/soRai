from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from content_engine_service.frontmatter import load_frontmatter

FILE_DELIM = "\n\n===== FILE: {rel} =====\n"


class RenderError(RuntimeError):
    """Raised when content-engine rendering fails."""


@dataclass(frozen=True)
class ProfileMeta:
    name: str
    summary: str
    sink: str
    content_types: tuple[str, ...]
    safety: dict[str, Any]
    raw: dict[str, Any]


@dataclass(frozen=True)
class RenderedBundle:
    profile: ProfileMeta
    text: str
    rendered_files: tuple[str, ...]


def list_profile_names(engine_root: Path) -> list[str]:
    profiles_dir = Path(engine_root) / "profiles"
    if not profiles_dir.is_dir():
        return []
    return sorted(
        path.name
        for path in profiles_dir.iterdir()
        if path.is_dir() and (path / "profile.toml").is_file()
    )


def render_bundle(engine_root: Path, profile: str, cache: dict | None = None) -> RenderedBundle:
    engine_root = Path(engine_root)
    key = (str(engine_root.resolve()), profile, _engine_rev(engine_root))
    if cache is not None and key in cache:
        return cache[key]

    render_sh = engine_root / "lib" / "render.sh"
    if not render_sh.is_file():
        raise RenderError(f"render.sh not found under {engine_root}")

    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "rendered"
        try:
            subprocess.run(
                ["bash", str(render_sh), "--profile", profile, "--dest", str(dest), "--force"],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            raise RenderError(f"render failed for {profile!r}: {detail}") from exc

        frontmatter = _profile_meta(load_frontmatter(dest / "frontmatter.yaml"))
        parts: list[str] = []
        files: list[str] = []
        for path in sorted(dest.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(dest).as_posix()
            files.append(rel)
            if path.suffix in {".md", ".yaml"}:
                parts.append(FILE_DELIM.format(rel=rel))
                parts.append(path.read_text())
        bundle = RenderedBundle(profile=frontmatter, text="".join(parts), rendered_files=tuple(files))

    if cache is not None:
        cache[key] = bundle
    return bundle


def _profile_meta(data: dict[str, Any]) -> ProfileMeta:
    return ProfileMeta(
        name=str(data["name"]),
        summary=str(data["summary"]),
        sink=str(data["sink"]),
        content_types=tuple(str(item) for item in data.get("content_types", [])),
        safety=dict(data.get("safety", {})),
        raw=data,
    )


def _engine_rev(engine_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(engine_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "no-rev"
