"""Statistics Iceland (Hagstofa Íslands) PxWeb API client and series fetcher.

API:   https://px.hagstofa.is/pxen/api/v1/en/...   (English)
       https://px.hagstofa.is/pxis/api/v1/is/...   (Icelandic)
Format: JSON-stat2, no authentication, licence CC BY 4.0.
Limits: 30 calls/second and 150,000 values per call (enforced below).
Docs:  https://statice.is/publications/open-data-access/

A series spec carries (under source.):
  table:     full path to the .px table, e.g. "Efnahagur/visitolur/1_vnv/1_vnv/VIS01000.px"
  time_dim:  code of the time dimension (e.g. "Month")
  item_dim:  code of the dimension whose single value we want (e.g. "Index")
  item_code: the value of item_dim (e.g. "CPI")
  selection: remaining dimensions pinned to lists of codes, e.g. {Item: ["index"]}

Run `python -m pipelines.sources.hagstofa <path>` to browse nodes/tables and
`python -m pipelines.sources.hagstofa --meta <table path>` to print a table's
dimensions and codes while harvesting.
"""
from __future__ import annotations

import itertools
import re
import sys

import pandas as pd

from pipelines import core

BASE = {
    "en": "https://px.hagstofa.is/pxen/api/v1/en",
    "is": "https://px.hagstofa.is/pxis/api/v1/is",
}
MAX_VALUES_PER_CALL = 150_000
MIN_CALL_INTERVAL = 0.05  # 30 calls/s allows 33.3 ms; keep a margin


def period_to_date(period: str) -> str:
    """PxWeb time codes -> ISO date of the period start ("2026M10" -> "2026-10-01")."""
    m = re.fullmatch(r"(\d{4})M(\d{2})", period)
    if m:
        return f"{m.group(1)}-{m.group(2)}-01"
    m = re.fullmatch(r"(\d{4})Q([1-4])", period)
    if m:
        return f"{m.group(1)}-{(int(m.group(2)) - 1) * 3 + 1:02d}-01"
    m = re.fullmatch(r"(\d{4})H([12])", period)
    if m:
        return f"{m.group(1)}-{(int(m.group(2)) - 1) * 6 + 1:02d}-01"
    if re.fullmatch(r"\d{4}", period):
        return f"{period}-01-01"
    return period


def jsonstat2_to_frame(payload: dict) -> pd.DataFrame:
    """Flatten a JSON-stat2 response into a long DataFrame (one column per dimension + value)."""
    ids = payload["id"]
    sizes = payload["size"]
    dims = payload["dimension"]
    strides = []
    stride = 1
    for size in reversed(sizes):
        strides.insert(0, stride)
        stride *= size
    code_by_pos = {
        d: {pos: code for code, pos in dims[d]["category"]["index"].items()} for d in ids
    }
    records = []
    for pos in itertools.product(*[range(n) for n in sizes]):
        flat = sum(p * s for p, s in zip(pos, strides))
        rec = {d: code_by_pos[d][p] for d, p in zip(ids, pos)}
        rec["value"] = payload["value"][flat]
        records.append(rec)
    return pd.DataFrame(records)


class PxWeb:
    def __init__(self, lang: str = "en"):
        if lang not in BASE:
            raise ValueError(f"lang must be one of {sorted(BASE)}")
        self.base = BASE[lang]

    def list_nodes(self, path: str = "") -> list[dict]:
        url = f"{self.base}/{path}" if path else self.base
        return core.http_get(url, min_interval=MIN_CALL_INTERVAL).json()

    def table_meta(self, table_path: str) -> dict:
        return core.http_get(f"{self.base}/{table_path}", min_interval=MIN_CALL_INTERVAL).json()

    def resolve_table(self, path: str, hint: str | None = None) -> str:
        """If path is a folder, descend to the first table (matching hint if given)."""
        nodes = self.list_nodes(path)
        tables = [n for n in nodes if n.get("type") == "t"]
        if not tables:
            raise ValueError(f"{path}: no tables here; children: {[n['id'] for n in nodes]}")
        if hint:
            tables = [t for t in tables if hint.lower() in t.get("text", "").lower()] or tables
        return f"{path}/{tables[0]['id']}"

    def query(self, table_path: str, selection: dict[str, list[str]]) -> dict:
        n_values = 1
        for values in selection.values():
            n_values *= len(values)
        if n_values > MAX_VALUES_PER_CALL:
            raise ValueError(
                f"{table_path}: query would return {n_values} values "
                f"(limit {MAX_VALUES_PER_CALL}); chunk the time dimension"
            )
        body = {
            "query": [
                {"code": code, "selection": {"filter": "item", "values": values}}
                for code, values in selection.items()
            ],
            "response": {"format": "json-stat2"},
        }
        return core.http_post(f"{self.base}/{table_path}", json_body=body,
                              min_interval=MIN_CALL_INTERVAL).json()


def fetch(spec: dict) -> pd.DataFrame:
    """Fetch one registered series from PxWeb -> DataFrame(date, period, value)."""
    src = spec["source"]
    px = PxWeb(lang=src.get("lang", "en"))
    table = src["table"]
    selection = {k: list(v) for k, v in src.get("selection", {}).items()}
    time_dim = src.get("time_dim", "Month")
    item_dim = src.get("item_dim")
    if item_dim:
        selection[item_dim] = [src["item_code"]]
    meta = px.table_meta(table)
    codes = {v["code"] for v in meta["variables"]}
    missing = set(selection) - codes
    if missing:
        raise ValueError(f"{table}: unknown dimension codes {sorted(missing)}; have {sorted(codes)}")
    if time_dim not in codes:
        raise ValueError(f"{table}: time dimension {time_dim!r} not found; have {sorted(codes)}")
    selection.setdefault(time_dim, [v for v in next(v for v in meta["variables"] if v["code"] == time_dim)["values"]])
    payload = px.query(table, selection)
    df = jsonstat2_to_frame(payload)
    if df.groupby(time_dim).size().max() != 1:
        raise ValueError(
            f"{table}: selection leaves more than one row per {time_dim}; "
            "pin the remaining dimensions in source.selection"
        )
    out = pd.DataFrame({
        "period": df[time_dim].astype(str),
        "value": pd.to_numeric(df["value"], errors="coerce"),
    })
    out["date"] = out["period"].map(period_to_date)
    out = out.dropna(subset=["value"]).sort_values("period").reset_index(drop=True)
    return out[["date", "period", "value"]]


def _discover(argv: list[str]) -> int:
    path = argv[0] if argv else ""
    px = PxWeb()
    if argv and argv[0] == "--meta":
        meta = px.table_meta(argv[1])
        print(meta.get("title", ""))
        for var in meta["variables"]:
            values = var.get("values", [])
            print(f"  {var['code']} ({var['text']}): {len(values)} values"
                  + (f", time" if var.get("time") else ""))
            if len(values) <= 12:
                print(f"    {values}")
        return 0
    for node in px.list_nodes(path):
        print(f"  {node['type']}  {node['id']}  {node.get('text', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(_discover(sys.argv[1:]))
