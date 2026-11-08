import pytest

from prepare_fields.config import load
from prepare_fields.errors import ConfigError

PRIMARY = {
    "LLM_BASE_URL": "https://api.groq.com/openai/v1",
    "LLM_API_KEY": "key",
    "LLM_MODEL": "openai/gpt-oss-120b, openai/gpt-oss-20b",
}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "LLM_BASE_URL",
        "LLM_API_KEY",
        "LLM_MODEL",
        "LLM_FALLBACK_BASE_URL",
        "LLM_FALLBACK_API_KEY",
        "LLM_FALLBACK_MODELS",
        "LLM_TIMEOUT",
        "LLM_TEMPERATURE",
        "LLM_CONCURRENCY",
    ):
        monkeypatch.delenv(name, raising=False)


def _set(monkeypatch: pytest.MonkeyPatch, **values: str) -> None:
    for name, value in {**PRIMARY, **values}.items():
        monkeypatch.setenv(name, value)


def test_primary_provider_and_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    _set(monkeypatch)

    config = load(env_file=None)

    assert [provider.name for provider in config.providers] == ["основной"]
    assert config.providers[0].models == ("openai/gpt-oss-120b", "openai/gpt-oss-20b")
    assert config.providers[0].base_url == "https://api.groq.com/openai/v1"
    assert (config.timeout, config.temperature, config.concurrency) == (60.0, 0.6, 4)


def test_fallback_provider_is_added(monkeypatch: pytest.MonkeyPatch) -> None:
    _set(
        monkeypatch,
        LLM_FALLBACK_BASE_URL="https://openrouter.ai/api/v1",
        LLM_FALLBACK_API_KEY="key",
        LLM_FALLBACK_MODELS="google/gemma:free",
    )

    assert [provider.name for provider in load(env_file=None).providers] == [
        "основной",
        "резервный",
    ]


def test_provider_without_key_is_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    _set(monkeypatch, LLM_FALLBACK_BASE_URL="https://openrouter.ai/api/v1", LLM_API_KEY="")

    with pytest.raises(ConfigError, match="не задан ни один провайдер"):
        load(env_file=None)


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"LLM_MODEL": " , "}, "не задана ни одна модель"),
        ({"LLM_BASE_URL": "api.groq.com"}, "должен начинаться с http"),
        ({"LLM_TIMEOUT": "минута"}, "LLM_TIMEOUT: ожидается длительность"),
        ({"LLM_TEMPERATURE": "5"}, "LLM_TEMPERATURE: ожидается значение от 0.0 до 2.0"),
        ({"LLM_CONCURRENCY": "нет"}, "LLM_CONCURRENCY: ожидается число"),
    ],
)
def test_invalid_values_are_rejected(
    monkeypatch: pytest.MonkeyPatch, values: dict[str, str], message: str
) -> None:
    _set(monkeypatch, **values)

    with pytest.raises(ConfigError, match=message):
        load(env_file=None)


@pytest.mark.parametrize(
    ("raw", "seconds"), [("500ms", 0.5), ("30s", 30.0), ("2m", 120.0), ("45", 45.0)]
)
def test_duration_units(monkeypatch: pytest.MonkeyPatch, raw: str, seconds: float) -> None:
    _set(monkeypatch, LLM_TIMEOUT=raw)

    assert load(env_file=None).timeout == seconds


def test_api_key_is_hidden_from_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    _set(monkeypatch, LLM_API_KEY="секретный-ключ")

    assert "секретный-ключ" not in repr(load(env_file=None))


def test_zero_timeout_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _set(monkeypatch, LLM_TIMEOUT="0s")

    with pytest.raises(ConfigError, match="должно быть больше нуля"):
        load(env_file=None)
