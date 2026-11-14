"""Validate every registry/series/*.yaml against registry/series/_schema.md."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipelines import core


def main() -> int:
    registry = core.load_registry()
    errors = core.validate_registry()
    for sid, errs in errors.items():
        for err in errs:
            print(f"INVALID {err}", file=sys.stderr)
    print(f"registry: {len(registry)} series, {len(errors)} invalid")
    for sid in sorted(registry):
        if sid not in errors:
            print(f"  ok  {sid}  [{registry[sid].get('area')}] {registry[sid]['title']}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
