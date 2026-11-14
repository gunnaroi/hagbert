"""Central Bank of Iceland (Seðlabanki Íslands) data client.

Primary machine-readable feed: the NSDP SDMX API at https://data.sedlabanki.is/
(Iceland's IMF Special Data Dissemination Standard page; SDMX 3.0 JSON, no key).
Fallbacks for series the NSDP does not carry: databank.is and the XML time-series
feed under https://cb.is/statistics/xml-data/ — pin exact keys during harvest
(see registry/backlog.yaml).

A series spec carries (under source.):
  dataflow: SDMX dataflow id, e.g. "NSDP"
  key:      either an exact SDMX key string, or {search: "label substring"} which is
            resolved against the dataflow's structure on first fetch and recorded
            in data/meta/<id>.json
"""
from __future__ import annotations

import re

import pandas as pd

from pipelines import core

BASE = "https://data.sedlabanki.is"
API = f"{BASE}/api/v3"


def _get(path: str, params: dict | None = None) -> dict:
    return core.http_get(f"{API}/{path}", params=params, min_interval=0.1).json()


def resolve_key(dataflow: str, query: str) -> str:
    """Find the first series key in a dataflow whose name matches `query`."""
    doc = _get(f"metadata/dataflow/{dataflow}", {"detail": "full"})
    needle = query.lower()

    def walk(node):
        if isinstance(node, dict):
            name = node.get("name") or node.get("Name")
            if isinstance(name, str) and needle in name.lower() and node.get("id"):
                return node["id"]
            for value in node.values():
                found = walk(value)
                if found:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = walk(item)
                if found:
                    return found
        return None

    key = walk(doc)
    if not key:
        raise ValueError(f"no series in dataflow {dataflow!r} matching {query!r}")
    return key


def parse_sdmx_json(payload: dict) -> pd.DataFrame:
    """SDMX 3.0 JSON data message -> DataFrame(period, value) using TIME_PERIOD."""
    data = payload["data"]
    structure = data["structures"][0]
    obs_dims = structure["dimensions"]["observation"]
    time_idx = next(i for i, d in enumerate(obs_dims) if d["id"] == "TIME_PERIOD")
    time_values = obs_dims[time_idx]["values"]
    records = []
    for series in data["dataSets"][0].get("series", {}).values():
        for obs_idx, obs in series.get("observations", {}).items():
            records.append({
                "period": time_values[int(obs_idx)]["id"],
                "value": obs[0],
            })
    df = pd.DataFrame(records)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"]).sort_values("period").reset_index(drop=True)
    df["date"] = df["period"].map(_period_to_date)
    return df[["date", "period", "value"]]


def _period_to_date(period: str) -> str:
    m = re.fullmatch(r"(\d{4})-(\d{2})", period)
    if m:
        return f"{m.group(1)}-{m.group(2)}-01"
    if re.fullmatch(r"\d{4}-Q[1-4]", period):
        year, q = period[:4], int(period[-1])
        return f"{year}-{(q - 1) * 3 + 1:02d}-01"
    if re.fullmatch(r"\d{4}", period):
        return f"{period}-01-01"
    return period


def fetch(spec: dict) -> pd.DataFrame:
    src = spec["source"]
    dataflow = src["dataflow"]
    key = src["key"]
    if isinstance(key, dict) and "search" in key:
        query = key["search"]
        key = resolve_key(dataflow, query)
        src["key"] = key  # mutate so publish_series stores the resolved key in meta
        src["resolved_from_search"] = query
    payload = _get(f"data/{dataflow}/{key}",
                   {"startPeriod": "1990-01-01", "format": "JSON", "detail": "dataonly"})
    return parse_sdmx_json(payload)
