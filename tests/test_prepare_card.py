import pytest

from prepare_fields.domain.draft import Draft
from prepare_fields.domain.product import Product, Spec
from prepare_fields.errors import LLMError
from prepare_fields.usecase.prepare_card import PrepareCard

PRODUCT = Product(
    name="Манометр DM 02",
    manufacturer="Манотомь",
    specs=(Spec("Диапазон измерений", "0–1,6 МПа"), Spec("Класс точности", "1,5")),
    description="Прибор для измерения избыточного давления",
)


def draft(title: str = "Манометр DM 02 Манотомь", description: str = "о" * 900) -> Draft:
    return Draft(
        seo_title=title,
        seo_description=description,
        search_queries=("манометр dm 02", "манометр манотомь", "манометр 1,6 МПа"),
        commercial="Подходит сервисным службам",
    )


class FakeWriter:
    def __init__(self, *answers: Draft | Exception) -> None:
        self.answers = list(answers)
        self.prompts: list[str] = []

    def write(self, system: str, user: str) -> Draft:
        assert system == "system"
        self.prompts.append(user)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


class FakePrompts:
    def system(self) -> str:
        return "system"

    def card(self, product: Product, missing: dict[str, str]) -> str:
        return f"card {product.name} missing={sorted(missing)}"

    def retry(
        self,
        product: Product,
        missing: dict[str, str],
        draft: Draft,
        violations: list[str],
    ) -> str:
        return (
            f"retry {product.name} missing={sorted(missing)} "
            f"{draft.seo_title} violations={list(violations)}"
        )


def test_clean_draft_passes_without_retry() -> None:
    writer = FakeWriter(draft())

    card = PrepareCard(writer, FakePrompts())(PRODUCT)

    assert card.warnings == ()
    assert len(writer.prompts) == 1
    assert card.missing == {
        "Питание": "данных нет",
        "Тип корпуса": "данных нет",
        "Интерфейсы": "данных нет",
    }


def test_retry_fixes_violation() -> None:
    writer = FakeWriter(draft(title="з" * 71), draft())

    card = PrepareCard(writer, FakePrompts())(PRODUCT)

    assert card.warnings == ()
    assert card.draft.seo_title == "Манометр DM 02 Манотомь"
    assert "SEO-заголовок: 71 симв., допустимо до 70" in writer.prompts[1]


def test_failed_retry_keeps_first_draft_and_reports_warnings() -> None:
    first = draft(description="о" * 400)
    writer = FakeWriter(first, draft(description="о" * 100))

    card = PrepareCard(writer, FakePrompts())(PRODUCT)

    assert card.draft is first
    assert card.warnings == ("SEO-описание: 400 симв., нужно от 800 до 1200",)


def test_invented_numbers_go_to_retry_and_warnings() -> None:
    invented = draft(description="о" * 880 + " питание 24 В")
    writer = FakeWriter(invented, invented)

    card = PrepareCard(writer, FakePrompts())(PRODUCT)

    assert card.warnings == ("числа, которых нет во входных данных: 24",)
    assert "числа, которых нет во входных данных: 24" in writer.prompts[1]


def test_llm_error_is_propagated() -> None:
    writer = FakeWriter(LLMError("все модели отказали"))

    with pytest.raises(LLMError, match="все модели отказали"):
        PrepareCard(writer, FakePrompts())(PRODUCT)


def test_retry_prompt_carries_input_data() -> None:
    writer = FakeWriter(draft(title="з" * 71), draft())

    PrepareCard(writer, FakePrompts())(PRODUCT)

    assert PRODUCT.name in writer.prompts[1]


def test_failed_retry_request_keeps_first_draft() -> None:
    first = draft(description="о" * 400)
    writer = FakeWriter(first, LLMError("лимит провайдера"))

    card = PrepareCard(writer, FakePrompts())(PRODUCT)

    assert card.draft is first
    assert card.warnings == ("SEO-описание: 400 симв., нужно от 800 до 1200",)
