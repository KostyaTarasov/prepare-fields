import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from prepare_fields.errors import ConfigError

_DURATION = re.compile(r"^(\d+(?:\.\d+)?)(ms|s|m)?$")
_UNITS = {"ms": 0.001, "s": 1.0, "m": 60.0, None: 1.0}


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    api_key: str = field(repr=False)
    models: tuple[str, ...]


@dataclass(frozen=True)
class Config:
    providers: tuple[Provider, ...]
    timeout: float
    temperature: float
    concurrency: int


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _duration(raw: str, name: str) -> float:
    match = _DURATION.match(raw.strip())
    if not match:
        raise ConfigError(f"{name}: ожидается длительность вида 60s или 500ms, получено {raw!r}")
    seconds = float(match.group(1)) * _UNITS[match.group(2)]
    if seconds <= 0:
        raise ConfigError(f"{name}: должно быть больше нуля, получено {raw!r}")
    return seconds


def _number(raw: str, name: str, low: float, high: float) -> float:
    try:
        value = float(raw)
    except ValueError as err:
        raise ConfigError(f"{name}: ожидается число, получено {raw!r}") from err
    if not low <= value <= high:
        raise ConfigError(f"{name}: ожидается значение от {low} до {high}, получено {value}")
    return value


def _models(raw: str) -> tuple[str, ...]:
    return tuple(model.strip() for model in raw.split(",") if model.strip())


def _provider(name: str, base_url: str, api_key: str, models: str) -> Provider | None:
    if not api_key.strip() or not base_url.strip():
        return None
    if not base_url.startswith(("http://", "https://")):
        raise ConfigError(f"{name}: базовый URL должен начинаться с http:// или https://")
    parsed = _models(models)
    if not parsed:
        raise ConfigError(f"{name}: не задана ни одна модель")
    return Provider(name=name, base_url=base_url.rstrip("/"), api_key=api_key, models=parsed)


def load(env_file: Path | None = Path(".env")) -> Config:
    if env_file is not None:
        load_env_file(env_file)

    providers = tuple(
        provider
        for provider in (
            _provider(
                "основной",
                os.environ.get("LLM_BASE_URL", ""),
                os.environ.get("LLM_API_KEY", ""),
                os.environ.get("LLM_MODEL", ""),
            ),
            _provider(
                "резервный",
                os.environ.get("LLM_FALLBACK_BASE_URL", ""),
                os.environ.get("LLM_FALLBACK_API_KEY", ""),
                os.environ.get("LLM_FALLBACK_MODELS", ""),
            ),
        )
        if provider is not None
    )
    if not providers:
        raise ConfigError(
            "не задан ни один провайдер LLM: заполните LLM_BASE_URL, LLM_API_KEY и LLM_MODEL "
            "(см. .env.example)"
        )

    return Config(
        providers=providers,
        timeout=_duration(os.environ.get("LLM_TIMEOUT", "60s"), "LLM_TIMEOUT"),
        temperature=_number(os.environ.get("LLM_TEMPERATURE", "0.6"), "LLM_TEMPERATURE", 0.0, 2.0),
        concurrency=int(_number(os.environ.get("LLM_CONCURRENCY", "4"), "LLM_CONCURRENCY", 1, 32)),
    )
