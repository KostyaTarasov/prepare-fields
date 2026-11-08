import io
import json
from pathlib import Path

import pytest

from prepare_fields import cli
from prepare_fields.domain.draft import Draft
from prepare_fields.errors import LLMError

DRAFT = Draft(
    seo_title="БП14Б-Д4.2-24 блок питания ОВЕН",
    seo_description="о" * 900,
    search_queries=("бп14б", "бп14б овен", "блок питания овен"),
    commercial="Подходит инженерам АСУТП",
)


class FakeWriter:
    def __init__(self, *failing: str) -> None:
        self.failing = failing

    def write(self, system: str, user: str) -> Draft:
        if any(name in user for name in self.failing):
            raise LLMError("HTTP 429: rate limit\nвторая строка")
        return DRAFT


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("LLM_API_KEY", "ключ")
    monkeypatch.setenv("LLM_MODEL", "m1")
    monkeypatch.delenv("LLM_FALLBACK_API_KEY", raising=False)


@pytest.fixture
def writer(monkeypatch: pytest.MonkeyPatch) -> object:
    def install(*failing: str) -> None:
        monkeypatch.setattr(cli, "ChatDraftWriter", lambda config: FakeWriter(*failing))  # noqa: ARG005

    return install


def _source(tmp_path: Path, raw: str) -> str:
    path = tmp_path / "products.json"
    path.write_text(raw, encoding="utf-8")
    return str(path)


def test_successful_run_prints_markdown(tmp_path, env, writer, capsys) -> None:
    writer()
    source = _source(tmp_path, '[{"name": "БП14Б-Д4.2-24"}, {"name": "БП14Б-Д4.4-24"}]')

    assert cli.main([source]) == 0

    out = capsys.readouterr().out
    assert out.count("## SEO-заголовок") == 2
    assert "## Для менеджера" in out
    assert "\n---\n" in out


def test_json_format_returns_parsed_cards(tmp_path, env, writer, capsys) -> None:
    writer()
    source = _source(tmp_path, '{"name": "БП14Б-Д4.2-24", "manufacturer": "ОВЕН"}')

    assert cli.main([source, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["manufacturer"] == "ОВЕН"
    assert payload[0]["seo_title_length"] == len(DRAFT.seo_title)


def test_stdin_is_accepted(env, writer, monkeypatch, capsys) -> None:
    writer()
    monkeypatch.setattr("sys.stdin", io.StringIO('{"name": "БП14Б-Д4.2-24"}'))

    assert cli.main(["-"]) == 0
    assert "БП14Б-Д4.2-24" in capsys.readouterr().out


def test_failed_product_is_visible_in_output(tmp_path, env, writer, capsys) -> None:
    writer("БП14Б-Д4.4-24")
    source = _source(tmp_path, '[{"name": "БП14Б-Д4.2-24"}, {"name": "БП14Б-Д4.4-24"}]')

    assert cli.main([source]) == cli.EXIT_LLM

    out = capsys.readouterr().out
    assert "# Не удалось сформировать" in out
    assert "- БП14Б-Д4.4-24: HTTP 429: rate limit" in out
    assert out.count("## SEO-заголовок") == 1


def test_failed_product_is_visible_in_json(tmp_path, env, writer, capsys) -> None:
    writer("БП14Б-Д4.4-24")
    source = _source(tmp_path, '[{"name": "БП14Б-Д4.2-24"}, {"name": "БП14Б-Д4.4-24"}]')

    assert cli.main([source, "--format", "json"]) == cli.EXIT_LLM

    payload = json.loads(capsys.readouterr().out)
    assert payload[1] == {"name": "БП14Б-Д4.4-24", "error": "HTTP 429: rate limit"}


def test_missing_file_returns_input_error_code() -> None:
    assert cli.main(["нет-такого.json"]) == cli.EXIT_INPUT


def test_directory_instead_of_file(tmp_path) -> None:
    assert cli.main([str(tmp_path)]) == cli.EXIT_INPUT


def test_file_not_in_utf8(tmp_path, caplog) -> None:
    source = tmp_path / "products.json"
    source.write_bytes('{"name": "Манометр"}'.encode("cp1251"))

    assert cli.main([str(source)]) == cli.EXIT_INPUT
    assert "не в UTF-8" in caplog.text


def test_broken_json_returns_input_error_code(tmp_path) -> None:
    assert cli.main([_source(tmp_path, "{сломано}")]) == cli.EXIT_INPUT


def test_config_error_returns_its_own_code(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    for name in ("LLM_API_KEY", "LLM_FALLBACK_API_KEY"):
        monkeypatch.setenv(name, "")

    assert cli.main([_source(tmp_path, '{"name": "БП14Б"}')]) == cli.EXIT_CONFIG
