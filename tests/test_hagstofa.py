import pandas as pd

from pipelines.sources import hagstofa


def test_period_to_date():
    assert hagstofa.period_to_date("2026M10") == "2026-10-01"
    assert hagstofa.period_to_date("2026Q3") == "2026-07-01"
    assert hagstofa.period_to_date("2026H2") == "2026-07-01"
    assert hagstofa.period_to_date("2026") == "2026-01-01"


def _payload():
    # dims: Month (2), Index (2); values in row-major order over [Month, Index]
    return {
        "version": "2.0", "class": "dataset",
        "id": ["Month", "Index"], "size": [2, 2],
        "dimension": {
            "Month": {"label": "Month", "category": {
                "index": {"2026M09": 0, "2026M10": 1},
                "label": {"2026M09": "2026M09", "2026M10": "2026M10"}}},
            "Index": {"label": "Index", "category": {
                "index": {"CPI": 0, "CPILH": 1},
                "label": {"CPI": "Consumer price index", "CPILH": "CPI less housing"}}},
        },
        "value": [700.1, 701.2, 710.5, 711.0],
    }


def test_jsonstat2_to_frame():
    df = hagstofa.jsonstat2_to_frame(_payload())
    assert set(df.columns) == {"Month", "Index", "value"}
    assert len(df) == 4
    row = df[(df["Month"] == "2026M10") & (df["Index"] == "CPILH")].iloc[0]
    assert row["value"] == 711.0


def test_fetch_shapes_frame(monkeypatch):
    spec = {
        "id": "cpi_headline",
        "source": {"lang": "en", "table": "T.px", "time_dim": "Month",
                   "item_dim": "Index", "item_code": "CPI",
                   "selection": {"Item": ["index"]}},
        "validation": {"range": [0, 1e9]},
    }

    class FakePx:
        def __init__(self, lang="en"):
            pass

        def table_meta(self, table):
            return {"title": "t", "variables": [
                {"code": "Month", "text": "Month", "values": ["2026M09", "2026M10"], "time": True},
                {"code": "Index", "text": "Index", "values": ["CPI", "CPILH"]},
                {"code": "Item", "text": "Item", "values": ["index"]},
            ]}

        def query(self, table, selection):
            # emulate the server: keep only the selected Index code, single Item
            return {
                "version": "2.0", "class": "dataset",
                "id": ["Month", "Index"], "size": [2, 1],
                "dimension": {
                    "Month": {"label": "Month", "category": {
                        "index": {"2026M09": 0, "2026M10": 1},
                        "label": {"2026M09": "2026M09", "2026M10": "2026M10"}}},
                    "Index": {"label": "Index", "category": {
                        "index": {"CPI": 0},
                        "label": {"CPI": "Consumer price index"}}},
                },
                "value": [700.1, 710.5],
            }

    monkeypatch.setattr(hagstofa, "PxWeb", FakePx)
    df = hagstofa.fetch(spec)
    assert list(df.columns) == ["date", "period", "value"]
    assert df["period"].tolist() == ["2026M09", "2026M10"]
    assert df["date"].tolist() == ["2026-09-01", "2026-10-01"]
    assert pd.to_numeric(df["value"]).tolist() == [700.1, 710.5]
