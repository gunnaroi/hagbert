"""Nightly check for measures/ — the pattern ported from econvitals/replication (CC0).

Each measures/<slug>/ holds README.md, replicate.py and check.json:

  {"outputs": {"output/series.csv": {"against": "data/series/<id>.csv",
                                      "last_n": 24, "tolerance": 1e-9}}}

This runs replicate.py in each folder, then compares the newest `last_n` rows of
each output with the published series within tolerance. A failure never touches
data/ — it only fails the run (and in CI, the PR).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def check_measure(folder: Path) -> list[str]:
    errors: list[str] = []
    check = json.loads((folder / "check.json").read_text(encoding="utf-8"))
    proc = subprocess.run([sys.executable, "replicate.py"], cwd=folder,
                          capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        return [f"{folder.name}: replicate.py failed: {proc.stderr.strip()[:300]}"]
    for rel_out, rule in check.get("outputs", {}).items():
        out = folder / rel_out
        against = ROOT / rule["against"]
        if not out.exists():
            errors.append(f"{folder.name}: missing output {rel_out}")
            continue
        if not against.exists():
            errors.append(f"{folder.name}: nothing published at {rule['against']}")
            continue
        a = pd.read_csv(out)
        b = pd.read_csv(against)
        last_n = int(rule.get("last_n", 24))
        tol = float(rule.get("tolerance", 1e-9))
        a, b = a.tail(last_n), b.tail(last_n)
        if len(a) != len(b):
            errors.append(f"{folder.name}/{rel_out}: {len(a)} rows vs {len(b)} in {rule['against']}")
            continue
        if (a["period"] != b["period"]).any():
            errors.append(f"{folder.name}/{rel_out}: periods do not align")
            continue
        diff = (a["value"] - b["value"]).abs().max()
        if diff > tol:
            errors.append(f"{folder.name}/{rel_out}: max |diff| {diff} > {tol}")
    return errors


def main() -> int:
    measures = sorted(p for p in (ROOT / "measures").iterdir()
                      if p.is_dir() and (p / "check.json").exists())
    if not measures:
        print("no measures yet (measures/ holds only README.md)")
        return 0
    failures: list[str] = []
    for folder in measures:
        errs = check_measure(folder)
        if errs:
            failures.extend(errs)
            print(f"FAIL  {folder.name}")
            for e in errs:
                print(f"      {e}")
        else:
            print(f"PASS  {folder.name}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
