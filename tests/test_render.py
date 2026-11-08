from prepare_fields.adapters.render import render_json, render_markdown
from prepare_fields.domain.draft import Card, Draft
from prepare_fields.domain.product import Product, Spec

DRAFT = Draft(
    seo_title="Манометр DM 02 Манотомь",
    seo_description="Описание прибора",
    search_queries=("манометр dm 02", "манометр манотомь", "манометр 1,6 МПа"),
    commercial="Подходит сервисным службам",
)


def card(specs: tuple[Spec, ...], missing: dict[str, str], warnings: tuple[str, ...]) -> Card:
    return Card(
        product=Product("Манометр DM 02", "Манотомь", specs, "Текст"),
        draft=DRAFT,
        missing=missing,
        warnings=warnings,
    )


def test_markdown_has_all_required_sections() -> None:
    text = render_markdown(
        card((Spec("Класс точности", "1,5"),), {"Питание": "данных нет"}, ("число 24",))
    )

    assert "# Манометр DM 02 (Манотомь)" in text
    assert "## SEO-заголовок (23 симв.)" in text
    assert "| Класс точности | 1,5 |" in text
    assert "1. манометр dm 02" in text
    assert "2. манометр манотомь" in text
    assert "3. манометр 1,6 МПа" in text
    assert "## Для менеджера\nПодходит сервисным службам" in text
    assert "- Питание — данных нет" in text
    assert "- число 24" in text


def test_markdown_skips_empty_sections_and_reports_absent_specs() -> None:
    text = render_markdown(card((), {}, ()))

    assert "Во входных данных характеристик нет." in text
    assert "Требует уточнения" not in text
    assert "Проверьте перед публикацией" not in text


def test_markdown_escapes_pipe_in_values() -> None:
    text = render_markdown(card((Spec("Диапазон", "4–20 мА | 0–10 В"),), {}, ()))

    assert "| Диапазон | 4–20 мА \\| 0–10 В |" in text


def test_json_keeps_lengths_and_input_specs() -> None:
    payload = render_json(card((Spec("Класс точности", "1,5"),), {"Питание": "данных нет"}, ()))

    assert payload == {
        "name": "Манометр DM 02",
        "manufacturer": "Манотомь",
        "seo_title": "Манометр DM 02 Манотомь",
        "seo_title_length": 23,
        "seo_description": "Описание прибора",
        "seo_description_length": 16,
        "specs": [{"name": "Класс точности", "value": "1,5"}],
        "search_queries": ["манометр dm 02", "манометр манотомь", "манометр 1,6 МПа"],
        "commercial": "Подходит сервисным службам",
        "missing": {"Питание": "данных нет"},
        "warnings": [],
    }
    assert payload["seo_description_length"] == len("Описание прибора")
    assert payload["specs"] == [{"name": "Класс точности", "value": "1,5"}]
    assert payload["missing"] == {"Питание": "данных нет"}
    assert payload["warnings"] == []
