"""Run harvesters.

Usage:
  uv run python -m pipelines.run                    # all fetch:auto series
  uv run python -m pipelines.run --fetch auto       # same, explicit
  uv run python -m pipelines.run cpi_headline       # one series id
  uv run python -m pipelines.run hagstofa           # one source module / provider

Each series spec names its source module; the module's fetch(spec) must return a
DataFrame with columns date, period, value. Failures mark the series stale and
never overwrite good data (AGENTS.md rule 3).
"""
from __future__ import annotations

import argparse
import importlib
import sys

from pipelines import core


def _matches(spec: dict, needle: str) -> bool:
    if spec["id"] == needle:
        return True
    module = spec["source"]["module"]
    if module == needle or module.removesuffix(".py").replace("/", ".") == needle:
        return True
    if module.rsplit("/", 1)[-1].removesuffix(".py") == needle:
        return True
    return spec["source"].get("agency", "").lower().split()[0] == needle


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", nargs="?", help="series id, module path, or provider name")
    ap.add_argument("--fetch", choices=["auto", "manual"], default=None)
    args = ap.parse_args()

    errors = core.validate_registry()
    if errors:
        for sid, errs in errors.items():
            print(f"INVALID {sid}: {'; '.join(errs)}", file=sys.stderr)
        return 2

    registry = core.load_registry()
    if args.source:
        selected = {sid: spec for sid, spec in registry.items() if _matches(spec, args.source)}
    elif args.fetch:
        selected = {sid: spec for sid, spec in registry.items() if spec.get("fetch") == args.fetch}
    else:
        selected = {sid: spec for sid, spec in registry.items() if spec.get("fetch") == "auto"}

    if not selected:
        print("nothing to run")
        return 0

    failures: dict[str, str] = {}
    for sid, spec in selected.items():
        module_path = spec["source"]["module"].removesuffix(".py").replace("/", ".")
        module = importlib.import_module(module_path)
        try:
            df = module.fetch(spec)
            core.publish_series(spec, df)
            print(f"ok    {sid}: {len(df)} rows, last {df.iloc[-1]['period']}")
        except Exception as exc:  # noqa: BLE001 - any failure marks stale, never overwrites
            core.mark_stale(sid, f"{type(exc).__name__}: {exc}")
            failures[sid] = str(exc)
            print(f"STALE {sid}: {type(exc).__name__}: {exc}")

    if failures:
        print(f"\n{len(failures)} series marked stale; published data untouched.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
