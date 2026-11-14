from pipelines import core


def test_registry_loads_and_validates():
    registry = core.load_registry()
    assert len(registry) >= 3
    assert core.validate_registry() == {}


def test_ids_are_unique_and_match_filenames():
    root = core.ROOT
    for path in (root / "registry" / "series").glob("*.yaml"):
        if path.name.startswith("_"):
            continue
        spec = core.yaml.safe_load(path.read_text(encoding="utf-8"))
        assert spec["id"] == path.stem


def test_seed_series_point_at_existing_modules():
    for sid, spec in core.load_registry().items():
        assert (core.ROOT / spec["source"]["module"]).exists(), sid


def test_show_only_series_are_not_downloadable():
    for sid, spec in core.load_registry().items():
        if spec["licence"] in core.SHOW_ONLY_LICENCES:
            assert spec["downloadable"] is False, sid
