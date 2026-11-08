import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass

from prepare_fields.config import Config, Provider
from prepare_fields.domain.draft import Draft
from prepare_fields.errors import LLMError

log = logging.getLogger(__name__)

_SNIPPET = 300
_USER_AGENT = "prepare-fields/0.1"


def _snippet(raw: bytes | str) -> str:
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
    return text[:_SNIPPET].replace("\n", " ")


def parse_draft(content: str) -> Draft:
    start, end = content.find("{"), content.rfind("}")
    if start < 0 or end <= start:
        raise LLMError(f"в ответе нет JSON-объекта: {_snippet(content)}")
    try:
        data = json.loads(content[start : end + 1])
    except json.JSONDecodeError as err:
        raise LLMError(f"ответ не разбирается как JSON: {err}") from err

    missing = [
        key
        for key in ("seo_title", "seo_description", "search_queries", "commercial")
        if key not in data
    ]
    if missing:
        raise LLMError(f"в ответе нет полей: {', '.join(missing)}")

    for key in ("seo_title", "seo_description", "commercial"):
        if not isinstance(data[key], str):
            raise LLMError(f"поле {key} должно быть строкой")
    queries = data["search_queries"]
    if not isinstance(queries, list) or not all(isinstance(item, str) for item in queries):
        raise LLMError("поле search_queries должно быть списком строк")

    return Draft(
        seo_title=data["seo_title"].strip(),
        seo_description=data["seo_description"].strip(),
        search_queries=tuple(item.strip() for item in queries if item.strip()),
        commercial=data["commercial"].strip(),
    )


@dataclass(frozen=True)
class ChatDraftWriter:
    """OpenAI-совместимый /chat/completions: модели перебираются по очереди."""

    config: Config

    def write(self, system: str, user: str) -> Draft:
        failures: list[str] = []
        for provider in self.config.providers:
            for model in provider.models:
                try:
                    return parse_draft(self._complete(provider, model, system, user))
                except LLMError as err:
                    failures.append(f"{provider.name} / {model}: {err}")
                    log.warning("модель %s (%s) не подошла: %s", model, provider.name, err)
        raise LLMError("ни одна модель не вернула корректный черновик:\n" + "\n".join(failures))

    def _complete(self, provider: Provider, model: str, system: str, user: str) -> str:
        body = json.dumps(
            {
                "model": model,
                "temperature": self.config.temperature,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{provider.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {provider.api_key}",
                "Content-Type": "application/json",
                "User-Agent": _USER_AGENT,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as err:
            raise LLMError(f"HTTP {err.code}: {_snippet(err.read())}") from err
        except (urllib.error.URLError, TimeoutError) as err:
            raise LLMError(f"запрос не выполнен: {err}") from err
        except json.JSONDecodeError as err:
            raise LLMError(f"ответ API не является JSON: {err}") from err

        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as err:
            raise LLMError(
                f"неожиданная структура ответа: {_snippet(json.dumps(payload))}"
            ) from err
        if not isinstance(content, str) or not content.strip():
            raise LLMError("модель вернула пустой ответ")
        return content
