import pytest

from prepare_fields.adapters.llm import parse_draft
from prepare_fields.errors import LLMError

VALID = """
{
  "seo_title": "Манометр DM 02",
  "seo_description": "Описание",
  "search_queries": ["манометр dm 02", " ", "манометр манотомь"],
  "commercial": "Для сервисных служб"
}
"""


def test_parse_draft_reads_fields_and_drops_empty_queries() -> None:
    draft = parse_draft(VALID)

    assert draft.seo_title == "Манометр DM 02"
    assert draft.search_queries == ("манометр dm 02", "манометр манотомь")


def test_parse_draft_ignores_fences_and_comments() -> None:
    draft = parse_draft(f"Вот карточка:\n```json{VALID}```\nГотово.")

    assert draft.commercial == "Для сервисных служб"


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("без json", "в ответе нет JSON-объекта"),
        ("{сломано}", "не разбирается как JSON"),
        ('{"seo_title": "a"}', "в ответе нет полей: seo_description, search_queries, commercial"),
        (
            '{"seo_title": 1, "seo_description": "a", "search_queries": [], "commercial": "a"}',
            "поле seo_title должно быть строкой",
        ),
        (
            '{"seo_title": "a", "seo_description": "a", "search_queries": "a", "commercial": "a"}',
            "поле search_queries должно быть списком строк",
        ),
    ],
)
def test_parse_draft_rejects_broken_answers(content: str, message: str) -> None:
    with pytest.raises(LLMError, match=message):
        parse_draft(content)
