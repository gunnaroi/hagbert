"""Fail if the site name from site.config.yaml is hard-coded outside it.

Scans the user-facing and spec surfaces: site/src and registry. Generated
output (site/public/data is a verbatim copy of site.config.yaml made by
pipelines/build/site_data.py) and prose files (README.md, AGENTS.md, docs/)
are out of scope.
URLs (e.g. the repo address in a User-Agent) are ignored: they name the
repository, not the site shown to users.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipelines import core

SCAN_DIRS = ["site/src", "registry"]


def main() -> int:
    root = core.ROOT
    name = core.site_config(root)["site"]["name"]
    offenders: list[str] = []
    for rel in SCAN_DIRS:
        base = root / rel
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix == ".tmp":
                continue
            if "public/data" in path.relative_to(root).as_posix():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, ValueError):
                continue
            text = re.sub(r"https?://\S+", "", text)
            if name.lower() in text.lower():
                offenders.append(str(path.relative_to(root)))
    if offenders:
        print(f"site name {name!r} hard-coded in:", file=sys.stderr)
        for off in offenders:
            print(f"  {off}", file=sys.stderr)
        print("read it from site.config.yaml instead", file=sys.stderr)
        return 1
    print(f"name check: {name!r} appears only in site.config.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
