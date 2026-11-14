"""Build the JSON the site reads.

Writes into site/public/data/ (git-ignored build output):
  site.json            site.config.yaml, verbatim
  index.json           every registered series with its latest value and health
  series/<id>.json     full history of one series

Run before every astro build (make build / make dev / deploy.yml do this).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from pipelines import core


def main() -> None:
    root = core.ROOT
    out = root / "site" / "public" / "data"
    (out / "series").mkdir(parents=True, exist_ok=True)
    (out / "site.json").write_text(
        json.dumps(core.site_config(root), ensure_ascii=False, indent=1), encoding="utf-8")

    registry = core.load_registry(root)
    status = core.read_status(root).get("series", {})
    index = []
    for sid, spec in sorted(registry.items()):
        entry = {
            "id": sid,
            "title": spec["title"],
            "short_title": spec.get("short_title"),
            "area": spec.get("area"),
            "unit": spec.get("unit"),
            "frequency": spec.get("frequency"),
            "agency": spec.get("source", {}).get("agency"),
            "licence": spec.get("licence"),
            "downloadable": spec.get("downloadable"),
            "step": bool(spec.get("step")),
            "status": status.get(sid, {}).get("status", "pending"),
        }
        csv = root / "data" / "series" / f"{sid}.csv"
        if csv.exists():
            df = pd.read_csv(csv)
            entry["rows"] = int(len(df))
            entry["last_period"] = str(df.iloc[-1]["period"])
            entry["last_value"] = float(df.iloc[-1]["value"])
            payload = {"id": sid, "title": spec["title"], "unit": spec.get("unit"),
                       "frequency": spec.get("frequency"),
                       "data": df.to_dict("records")}
            (out / "series" / f"{sid}.json").write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        else:
            entry["rows"] = 0
        index.append(entry)
    (out / "index.json").write_text(
        json.dumps({"series": index}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"site data: {len(index)} series -> {out}")


if __name__ == "__main__":
    main()
