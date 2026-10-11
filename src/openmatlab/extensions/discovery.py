"""Discover plugins from load path and optional entry points."""

from __future__ import annotations

import logging
import os
import warnings
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from openmatlab.extensions.manifest import ManifestError, PluginManifest, load_manifest

log = logging.getLogger("openmatlab.extensions")

ENV_PLUGIN_PATH = "OPENMATLAB_PLUGIN_PATH"
ENTRY_POINT_GROUP = "openmatlab.plugins"


def default_user_plugin_dir() -> Path:
    return Path.home() / ".openmatlab" / "plugins"


def iter_plugin_path_roots(
    *,
    extra: Optional[Sequence[Path | str]] = None,
    env: Optional[str] = None,
    include_user_dir: bool = True,
) -> List[Path]:
    """Ordered roots to scan for plugin folders."""
    roots: List[Path] = []
    if extra:
        for item in extra:
            roots.append(Path(item).expanduser())
    env_val = env if env is not None else os.environ.get(ENV_PLUGIN_PATH, "")
    if env_val:
        for part in env_val.split(os.pathsep):
            part = part.strip()
            if part:
                roots.append(Path(part).expanduser())
    if include_user_dir:
        roots.append(default_user_plugin_dir())
    # de-dupe while preserving order
    seen = set()
    out: List[Path] = []
    for r in roots:
        key = str(r.resolve()) if r.exists() else str(r)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def discover_in_root(root: Path) -> List[PluginManifest]:
    """Discover plugins: either ``root`` itself is a plugin, or children are."""
    root = Path(root)
    found: List[PluginManifest] = []
    if not root.exists():
        return found
    # Direct plugin root
    if (root / "plugin.yaml").is_file() or (root / "openmatlab.plugin.json").is_file():
        try:
            found.append(load_manifest(root))
        except ManifestError as exc:
            log.warning("skip invalid plugin at %s: %s", root, exc)
        return found
    if not root.is_dir():
        return found
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if (child / "plugin.yaml").is_file() or (
            child / "openmatlab.plugin.json"
        ).is_file():
            try:
                found.append(load_manifest(child))
            except ManifestError as exc:
                log.warning("skip invalid plugin at %s: %s", child, exc)
    return found


def discover_from_paths(
    roots: Sequence[Path | str],
) -> Tuple[List[PluginManifest], List[str]]:
    """Discover from roots; first id wins; duplicates → warning strings."""
    manifests: List[PluginManifest] = []
    seen_ids: dict[str, Path] = {}
    warnings_out: List[str] = []
    for root in roots:
        for manif in discover_in_root(Path(root)):
            if manif.id in seen_ids:
                msg = (
                    f"duplicate plugin id {manif.id!r}: "
                    f"keeping {seen_ids[manif.id]}, ignoring {manif.root}"
                )
                warnings_out.append(msg)
                warnings.warn(msg, UserWarning, stacklevel=2)
                continue
            seen_ids[manif.id] = manif.root
            manifests.append(manif)
    return manifests, warnings_out


def discover_entry_points() -> Tuple[List[PluginManifest], List[str]]:
    """Optional Option-A discovery via importlib.metadata group."""
    warnings_out: List[str] = []
    manifests: List[PluginManifest] = []
    try:
        from importlib.metadata import entry_points
    except ImportError:
        return manifests, warnings_out

    try:
        eps = entry_points()
    except Exception as exc:  # pragma: no cover
        warnings_out.append(f"entry_points() failed: {exc}")
        return manifests, warnings_out

    # Python 3.10+ SelectableGroups vs legacy dict
    selected = []
    if hasattr(eps, "select"):
        selected = list(eps.select(group=ENTRY_POINT_GROUP))
    else:  # pragma: no cover
        selected = list(eps.get(ENTRY_POINT_GROUP, []))  # type: ignore[arg-type]

    for ep in selected:
        try:
            loaded = ep.load()
        except Exception as exc:
            warnings_out.append(f"entry point {ep.name} failed to load: {exc}")
            continue
        root: Optional[Path] = None
        if isinstance(loaded, (str, Path)):
            root = Path(loaded)
        elif callable(loaded):
            result = loaded()
            if isinstance(result, (str, Path)):
                root = Path(result)
            elif hasattr(result, "root"):
                root = Path(result.root)
            elif isinstance(result, PluginManifest):
                manifests.append(result)
                continue
        elif hasattr(loaded, "root"):
            root = Path(loaded.root)
        if root is None:
            warnings_out.append(
                f"entry point {ep.name} did not resolve to a plugin root"
            )
            continue
        try:
            manifests.append(load_manifest(root))
        except ManifestError as exc:
            warnings_out.append(f"entry point {ep.name} invalid manifest: {exc}")
    return manifests, warnings_out


def discover_all(
    *,
    extra: Optional[Sequence[Path | str]] = None,
    env: Optional[str] = None,
    include_user_dir: bool = True,
    include_entry_points: bool = True,
) -> Tuple[List[PluginManifest], List[str]]:
    """Full discovery order: path roots, then entry points (first id wins)."""
    roots = iter_plugin_path_roots(
        extra=extra, env=env, include_user_dir=include_user_dir
    )
    manifests, warns = discover_from_paths(roots)
    seen = {m.id for m in manifests}
    if include_entry_points:
        ep_manifs, ep_warns = discover_entry_points()
        warns.extend(ep_warns)
        for m in ep_manifs:
            if m.id in seen:
                msg = (
                    f"duplicate plugin id {m.id!r} from entry points; "
                    f"keeping earlier discovery"
                )
                warns.append(msg)
                warnings.warn(msg, UserWarning, stacklevel=2)
                continue
            seen.add(m.id)
            manifests.append(m)
    return manifests, warns
