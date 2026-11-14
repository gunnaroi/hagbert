"""Validate every registry/series/*.yaml against registry/series/_schema.md,
and syntax-check every other YAML in the repo (calendars, backlog, config)."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipelines import core


def check_yaml_syntax(root: Path) -> list[str]:
    errors: list[str] = []
    targets = list((root / "registry").rglob("*.yaml")) + [root / "site.config.yaml"]
    for path in targets:
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"YAML parse error in {path.relative_to(root)}: {exc}")
    return errors


def main() -> int:
    root = core.ROOT
    syntax_errors = check_yaml_syntax(root)
    for err in syntax_errors:
        print(f"INVALID {err}", file=sys.stderr)
    registry = core.load_registry()
    errors = core.validate_registry()
    for sid, errs in errors.items():
        for err in errs:
            print(f"INVALID {err}", file=sys.stderr)
    print(f"registry: {len(registry)} series, {len(errors)} invalid, "
          f"{len(syntax_errors)} yaml syntax errors")
    for sid in sorted(registry):
        if sid not in errors:
            print(f"  ok  {sid}  [{registry[sid].get('area')}] {registry[sid]['title']}")
    return 1 if (errors or syntax_errors) else 0


if __name__ == "__main__":
    sys.exit(main())
