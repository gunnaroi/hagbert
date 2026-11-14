"""Shared plumbing for the pipelines: cached HTTP, the series registry, publishing.

Layout contract (see AGENTS.md):
  registry/series/<id>.yaml   one spec per series
  data/series/<id>.csv        tidy published series: columns date, period, value
  data/meta/<id>.json         spec metadata + fetch bookkeeping
  data/status.json            freshness/health of every series

A failed fetch never overwrites good data: publish_series writes atomically and
mark_stale touches only data/status.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "data-pipelines (+https://github.com/gunnaroi/hagbert)"
CACHE_DIR = Path(os.environ.get("HAGBERT_CACHE", str(ROOT / ".cache" / "hagbert")))
CACHE_HOURS = float(os.environ.get("HAGBERT_CACHE_HOURS", "6"))

AREAS = {
    "growth", "inflation", "jobs", "activity", "money",
    "markets", "fiscal", "external", "housing", "population",
}
FREQUENCIES = {"D", "W", "F", "M", "Q", "A"}
FETCH_MODES = {"auto", "manual"}
SHOW_ONLY_LICENCES = {"show-only", "unverified"}

REQUIRED = ["id", "title", "short_title", "area", "source", "licence", "downloadable",
            "fetch", "frequency", "unit", "release", "validation", "pages"]

_last_call: dict[str, float] = {}


def site_config(root: Path | None = None) -> dict:
    root = root or ROOT
    return yaml.safe_load((root / "site.config.yaml").read_text(encoding="utf-8"))


def _cache_path(url: str, params: dict | None) -> Path:
    key = hashlib.sha256((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()
    return CACHE_DIR / f"{key}.json"


def http_get(url: str, *, params: dict | None = None, min_interval: float = 0.0,
             cache: bool = True, timeout: float = 30.0) -> requests.Response:
    """GET with a per-host rate limit and an hours-long on-disk cache."""
    host = requests.utils.urlparse(url).netloc
    if min_interval > 0:
        wait = min_interval - (time.monotonic() - _last_call.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        _last_call[host] = time.monotonic()
    if cache:
        path = _cache_path(url, params)
        if path.exists() and time.time() - path.stat().st_mtime < CACHE_HOURS * 3600:
            resp = requests.Response()
            resp.status_code = 200
            resp._content = path.read_bytes()
            resp.url = url
            return resp
    resp = requests.get(url, params=params, timeout=timeout,
                        headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    if cache:
        path = _cache_path(url, params)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(resp.content)
    return resp


def http_post(url: str, *, json_body: dict, min_interval: float = 0.0,
              timeout: float = 60.0) -> requests.Response:
    host = requests.utils.urlparse(url).netloc
    if min_interval > 0:
        wait = min_interval - (time.monotonic() - _last_call.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        _last_call[host] = time.monotonic()
    resp = requests.post(url, json=json_body, timeout=timeout,
                         headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    return resp


def load_registry(root: Path | None = None) -> dict[str, dict]:
    root = root or ROOT
    registry: dict[str, dict] = {}
    for path in sorted((root / "registry" / "series").glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        spec = yaml.safe_load(path.read_text(encoding="utf-8"))
        registry[spec["id"]] = spec
    return registry


def validate_spec(spec: dict, root: Path | None = None) -> list[str]:
    root = root or ROOT
    errors: list[str] = []
    sid = spec.get("id", "")
    if not re.fullmatch(r"[a-z0-9_]+", sid or ""):
        errors.append(f"{sid}: id must be lower_snake")
    for field in REQUIRED:
        if field not in spec:
            errors.append(f"{sid}: missing required field {field!r}")
    if spec.get("area") not in AREAS:
        errors.append(f"{sid}: area {spec.get('area')!r} not in {sorted(AREAS)}")
    if spec.get("fetch") not in FETCH_MODES:
        errors.append(f"{sid}: fetch must be one of {sorted(FETCH_MODES)}")
    if spec.get("frequency") not in FREQUENCIES:
        errors.append(f"{sid}: frequency must be one of {sorted(FREQUENCIES)}")
    src = spec.get("source", {})
    module = src.get("module", "")
    if module and not (root / module).exists():
        errors.append(f"{sid}: source.module {module!r} does not exist")
    if spec.get("licence") in SHOW_ONLY_LICENCES and spec.get("downloadable"):
        errors.append(f"{sid}: downloadable must be false for licence {spec['licence']!r}")
    rng = spec.get("validation", {}).get("range")
    if not (isinstance(rng, list) and len(rng) == 2 and rng[0] < rng[1]):
        errors.append(f"{sid}: validation.range must be [min, max] with min < max")
    for page in spec.get("pages", []):
        if not isinstance(page, dict) or "page" not in page or "section" not in page:
            errors.append(f"{sid}: each pages entry needs page and section")
    return errors


def validate_registry(root: Path | None = None) -> dict[str, list[str]]:
    root = root or ROOT
    registry = load_registry(root)
    errors: dict[str, list[str]] = {}
    seen: set[str] = set()
    for sid, spec in registry.items():
        errs = validate_spec(spec, root)
        if sid in seen:
            errs.append(f"{sid}: duplicate id")
        seen.add(sid)
        if errs:
            errors[sid] = errs
    return errors


def validate_values(spec: dict, df: pd.DataFrame) -> pd.DataFrame:
    """Range- and shape-check a fetched frame. Raises on violation (caller marks stale)."""
    if not {"date", "period", "value"}.issubset(df.columns):
        raise ValueError(f"{spec['id']}: frame must have columns date, period, value")
    if df.empty:
        raise ValueError(f"{spec['id']}: empty frame")
    if df["value"].isna().any():
        raise ValueError(f"{spec['id']}: null values in fetched data")
    if df["period"].duplicated().any():
        raise ValueError(f"{spec['id']}: duplicate periods in fetched data")
    lo, hi = spec["validation"]["range"]
    bad = df[(df["value"] < lo) | (df["value"] > hi)]
    if not bad.empty:
        raise ValueError(f"{spec['id']}: {len(bad)} values outside range [{lo}, {hi}]")
    return df.sort_values("period").reset_index(drop=True)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def read_status(root: Path | None = None) -> dict:
    root = root or ROOT
    path = root / "data" / "status.json"
    if not path.exists():
        return {"series": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def publish_series(spec: dict, df: pd.DataFrame, root: Path | None = None) -> None:
    """Write data/series/<id>.csv, data/meta/<id>.json and mark the series ok."""
    root = root or ROOT
    sid = spec["id"]
    df = validate_values(spec, df)
    _atomic_write(root / "data" / "series" / f"{sid}.csv", df.to_csv(index=False))
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    meta = {**spec, "fetched_at": fetched_at, "rows": int(len(df)),
            "last_period": str(df.iloc[-1]["period"])}
    _atomic_write(root / "data" / "meta" / f"{sid}.json",
                  json.dumps(meta, ensure_ascii=False, indent=1, default=str))
    status = read_status(root)
    status.setdefault("series", {})[sid] = {
        "status": "ok", "fetched_at": fetched_at,
        "last_period": str(df.iloc[-1]["period"]), "rows": int(len(df)),
    }
    _atomic_write(root / "data" / "status.json", json.dumps(status, ensure_ascii=False, indent=1))


def mark_stale(sid: str, error: str, root: Path | None = None) -> None:
    """Record a failure in data/status.json. Never touches data/series or data/meta."""
    root = root or ROOT
    status = read_status(root)
    entry = status.setdefault("series", {}).setdefault(sid, {})
    entry["status"] = "stale"
    entry["error"] = error[:500]
    entry["failed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _atomic_write(root / "data" / "status.json", json.dumps(status, ensure_ascii=False, indent=1))
