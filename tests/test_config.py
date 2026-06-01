from pathlib import Path

from keel.config import load_config


def test_config_loads_approved_contracts(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "sample.keel.yml"
    (tmp_path / ".keel.yml").write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    config = load_config(tmp_path)

    assert config.version == 1
    assert config.layers["UI"] == ["src/components"]
    assert config.approved_contracts[0].id == "ui_never_touches_database"

