import io
import json
import urllib.error
import urllib.request

import pytest

from prepare_fields.adapters.llm import ChatDraftWriter
from prepare_fields.config import Config, Provider
from prepare_fields.errors import LLMError

ANSWER = {
    "seo_title": "Манометр DM 02",
    "seo_description": "Описание",
    "search_queries": ["манометр dm 02"],
    "commercial": "Для сервисных служб",
}

CONFIG = Config(
    providers=(
        Provider("основной", "https://api.groq.com/openai/v1", "секретный-ключ", ("m1", "m2")),
        Provider("резервный", "https://openrouter.ai/api/v1", "ключ-2", ("m3",)),
    ),
    timeout=1.0,
    temperature=0.5,
    concurrency=1,
)


def _body(payload: object) -> io.BytesIO:
    return io.BytesIO(json.dumps(payload).encode("utf-8"))


def _reply(content: object) -> dict[str, object]:
    return {"choices": [{"message": {"content": content}}]}


def _rate_limited(body: bytes = b'{"error": "rate limit"}') -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://api", 429, "Too Many Requests", {}, io.BytesIO(body))


class FakeAPI:
    def __init__(self, *answers: object) -> None:
        self.answers = list(answers)
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    def __call__(self, request: urllib.request.Request, timeout: float | None = None) -> io.BytesIO:
        payload = json.loads(request.data or b"{}")
        self.calls.append((request.full_url, request.headers["Authorization"], payload))
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        if isinstance(answer, bytes):
            return io.BytesIO(answer)
        return _body(answer)


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> object:
    def install(*answers: object) -> FakeAPI:
        fake = FakeAPI(*answers)
        monkeypatch.setattr(urllib.request, "urlopen", fake)
        return fake

    return install


def test_models_and_providers_are_tried_in_order(api) -> None:
    fake = api(_rate_limited(), _reply("не json"), _reply(json.dumps(ANSWER)))

    draft = ChatDraftWriter(CONFIG).write("system", "user")

    assert draft.seo_title == "Манометр DM 02"
    assert [call[2]["model"] for call in fake.calls] == ["m1", "m2", "m3"]
    assert fake.calls[0][0] == "https://api.groq.com/openai/v1/chat/completions"
    assert fake.calls[2][0] == "https://openrouter.ai/api/v1/chat/completions"
    assert fake.calls[2][1] == "Bearer ключ-2"
    assert fake.calls[0][2]["temperature"] == 0.5


def test_all_models_failed_reports_every_reason(api) -> None:
    api(TimeoutError("таймаут"), urllib.error.URLError("нет сети"), ConnectionResetError("обрыв"))

    with pytest.raises(LLMError) as failure:
        ChatDraftWriter(CONFIG).write("system", "user")

    message = str(failure.value)
    assert "основной / m1" in message
    assert "основной / m2" in message
    assert "резервный / m3" in message


def test_api_key_is_not_leaked_into_error(api) -> None:
    api(
        _rate_limited(b'{"error": "invalid key sk-secret"}'),
        _rate_limited(b'{"error": "secret"}'),
        _rate_limited(b'{"error": "secret"}'),
    )

    with pytest.raises(LLMError, match=r"\*\*\*"):
        ChatDraftWriter(
            Config(
                providers=(Provider("основной", "https://api", "sk-secret", ("m1",)),),
                timeout=1.0,
                temperature=0.5,
                concurrency=1,
            )
        ).write("system", "user")


@pytest.mark.parametrize(
    ("answer", "message"),
    [
        (b"not json at all", "тело ответа не прочитано как JSON"),
        ({"choices": []}, "неожиданная структура ответа"),
        ({"error": "quota"}, "неожиданная структура ответа"),
        (_reply(""), "модель вернула пустой ответ"),
        (_reply(None), "модель вернула пустой ответ"),
    ],
)
def test_broken_api_answers_are_wrapped(api, answer: object, message: str) -> None:
    api(answer)
    single = Config(
        providers=(Provider("основной", "https://api", "key", ("m1",)),),
        timeout=1.0,
        temperature=0.5,
        concurrency=1,
    )

    with pytest.raises(LLMError, match=message):
        ChatDraftWriter(single).write("system", "user")
