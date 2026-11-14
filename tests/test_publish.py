import json

import pandas as pd

from pipelines import core


def _spec(sid="cpi_headline"):
    return {
        "id": sid, "title": "t", "short_title": "t", "area": "inflation",
        "source": {"agency": "a", "dataset": "d", "module": "pipelines/sources/hagstofa.py", "url": ""},
        "licence": "CC-BY-4.0", "downloadable": True, "fetch": "auto", "frequency": "M",
        "unit": "index", "release": {"calendar": "hagstofa", "rule": "", "lag_days": 45},
        "validation": {"range": [0, 1e9], "revision_alert": 1}, "pages": [],
    }


def _df():
    return pd.DataFrame({
        "date": ["2026-09-01", "2026-10-01"],
        "period": ["2026M09", "2026M10"],
        "value": [700.1, 710.5],
    })


def test_publish_writes_csv_meta_and_status(tmp_path):
    core.publish_series(_spec(), _df(), root=tmp_path)
    df = pd.read_csv(tmp_path / "data" / "series" / "cpi_headline.csv")
    assert len(df) == 2 and df.iloc[-1]["period"] == "2026M10"
    meta = json.loads((tmp_path / "data" / "meta" / "cpi_headline.json").read_text())
    assert meta["rows"] == 2 and meta["last_period"] == "2026M10"
    status = json.loads((tmp_path / "data" / "status.json").read_text())
    assert status["series"]["cpi_headline"]["status"] == "ok"


def test_mark_stale_never_touches_data(tmp_path):
    core.publish_series(_spec(), _df(), root=tmp_path)
    before = (tmp_path / "data" / "series" / "cpi_headline.csv").read_bytes()
    core.mark_stale("cpi_headline", "HTTPError: 500", root=tmp_path)
    assert (tmp_path / "data" / "series" / "cpi_headline.csv").read_bytes() == before
    status = json.loads((tmp_path / "data" / "status.json").read_text())
    assert status["series"]["cpi_headline"]["status"] == "stale"
    assert "500" in status["series"]["cpi_headline"]["error"]


def test_validate_values_rejects_out_of_range(tmp_path):
    spec = _spec()
    spec["validation"]["range"] = [0, 100]
    try:
        core.validate_values(spec, _df())
    except ValueError as exc:
        assert "outside range" in str(exc)
    else:
        raise AssertionError("expected ValueError")
