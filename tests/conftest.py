import urllib.request

import pytest


@pytest.fixture(autouse=True)
def _deny_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def deny(*args: object, **kwargs: object) -> None:
        raise AssertionError("тест не должен выходить в сеть")

    monkeypatch.setattr(urllib.request, "urlopen", deny)
