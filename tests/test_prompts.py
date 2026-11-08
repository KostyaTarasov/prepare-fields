from prepare_fields.adapters.prompts import FilePrompts
from prepare_fields.domain.draft import Draft
from prepare_fields.domain.product import Product, Spec, missing_fields

PRODUCT = Product(
    name="Манометр DM 02",
    manufacturer="Манотомь",
    specs=(Spec("Класс точности", "1,5"),),
    description="Измеряет избыточное давление",
)
DRAFT = Draft("Заголовок", "Описание", ("запрос",), "Для менеджера")


def test_card_prompt_contains_input_data_and_missing_fields() -> None:
    text = FilePrompts().card(PRODUCT, missing_fields(PRODUCT))

    assert '"Класс точности": "1,5"' in text
    assert "Измеряет избыточное давление" in text
    assert "Диапазон измерений" in text


def test_card_prompt_reports_complete_input() -> None:
    full = Product(
        name="Прибор",
        manufacturer="ОВЕН",
        specs=tuple(
            Spec(name, "значение")
            for name in (
                "Диапазон измерений",
                "Класс точности",
                "Питание",
                "Тип корпуса",
                "Интерфейсы",
            )
        ),
        description="Описание",
    )

    assert "все обязательные поля заполнены" in FilePrompts().card(full, missing_fields(full))


def test_retry_prompt_repeats_input_and_lists_violations() -> None:
    text = FilePrompts().retry(PRODUCT, missing_fields(PRODUCT), DRAFT, ["SEO-заголовок пустой"])

    assert '"Класс точности": "1,5"' in text
    assert '"seo_title": "Заголовок"' in text
    assert "- SEO-заголовок пустой" in text


def test_system_prompt_is_loaded_from_package() -> None:
    assert "Единственный источник технических значений" in FilePrompts().system()
