from pathlib import Path

import pytest

from prepare_fields.cli import main


def test_missing_file_returns_input_error_code() -> None:
    assert main(["нет-такого.json"]) == 1


def test_broken_json_returns_input_error_code(tmp_path: Path) -> None:
    source = tmp_path / "products.json"
    source.write_text("{сломано}", encoding="utf-8")

    assert main([str(source)]) == 1


def test_config_error_returns_its_own_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "products.json"
    source.write_text('{"name": "БП14Б"}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    for name in ("LLM_API_KEY", "LLM_FALLBACK_API_KEY"):
        monkeypatch.setenv(name, "")

    assert main([str(source)]) == 2
