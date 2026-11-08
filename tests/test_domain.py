import pytest

from prepare_fields.domain.draft import (
    Draft,
    check_limits,
    invented_numbers,
)
from prepare_fields.domain.product import NO_DATA, Product, Spec, canonical_key, missing_fields


def product(specs: tuple[Spec, ...] = (), description: str = "текст") -> Product:
    return Product(
        name="Манометр DM 02",
        manufacturer="Манотомь",
        specs=specs,
        description=description,
    )


def draft(
    title: str = "Манометр DM 02",
    description: str = "о" * 900,
    queries: tuple[str, ...] = ("манометр dm 02", "манометр манотомь", "купить манометр"),
    commercial: str = "Подходит для сервисных служб",
) -> Draft:
    return Draft(
        seo_title=title,
        seo_description=description,
        search_queries=queries,
        commercial=commercial,
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("диапазон измерения", "Диапазон измерений"),
        ("  ДИАПАЗОН   ИЗМЕРЕНИЙ ", "Диапазон измерений"),
        ("пределы измерений", "Диапазон измерений"),
        ("точность", "Класс точности"),
        ("напряжение питания", "Питание"),
        ("выходной сигнал", "Интерфейсы"),
        ("артикул", "Артикул"),
    ],
)
def test_canonical_key(raw: str, expected: str) -> None:
    assert canonical_key(raw) == expected


def test_missing_fields_lists_required_specs_and_description() -> None:
    result = missing_fields(product(specs=(Spec("Класс точности", "1,5"),), description=" "))

    assert result == {
        "Диапазон измерений": NO_DATA,
        "Питание": NO_DATA,
        "Тип корпуса": NO_DATA,
        "Интерфейсы": NO_DATA,
        "Описание или фрагмент техпаспорта": NO_DATA,
    }


def test_missing_fields_reports_absent_manufacturer() -> None:
    bare = Product(name="БП14Б", manufacturer=" ", specs=(), description="текст")

    assert bare.title == "БП14Б"
    assert "Производитель" in missing_fields(bare)


def test_missing_fields_empty_when_everything_filled() -> None:
    specs = tuple(
        Spec(name, "значение")
        for name in ("Диапазон измерений", "Класс точности", "Питание", "Тип корпуса", "Интерфейсы")
    )

    assert missing_fields(product(specs=specs)) == {}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (draft(), ()),
        (draft(title="з" * 70), ()),
        (draft(description="о" * 800), ()),
        (draft(description="о" * 1200), ()),
        (draft(queries=("один", "два", "три")), ()),
        (draft(queries=("1", "2", "3", "4", "5")), ()),
        (
            draft(queries=("1", "2", "3", "4", "5", "6")),
            ("поисковых запросов: 6, нужно от 3 до 5",),
        ),
        (draft(title="з" * 71), ("SEO-заголовок: 71 симв., допустимо до 70",)),
        (draft(title="  "), ("SEO-заголовок пустой",)),
        (draft(description="о" * 799), ("SEO-описание: 799 симв., нужно от 800 до 1200",)),
        (draft(description="о" * 1201), ("SEO-описание: 1201 симв., нужно от 800 до 1200",)),
        (draft(queries=("один", "два")), ("поисковых запросов: 2, нужно от 3 до 5",)),
        (draft(commercial=""), ("commercial-блок пустой",)),
    ],
)
def test_check_limits(value: Draft, expected: tuple[str, ...]) -> None:
    assert check_limits(value) == expected


@pytest.mark.parametrize(
    ("generated", "expected"),
    [
        ("Диапазон 0–1,6 МПа, класс 1,5", ()),
        ("Диапазон 0–1.6 МПа", ()),
        ("Корпус 100 мм", ()),
        ("Питание 24 В", ("24",)),
        ("Корпус 10 мм", ("10",)),
    ],
)
def test_invented_numbers(generated: str, expected: tuple[str, ...]) -> None:
    source = product(
        specs=(Spec("Диапазон измерений", "0–1,6 МПа"), Spec("Класс точности", "1,5")),
        description="Диаметр корпуса 100 мм",
    )

    assert invented_numbers(draft(description=generated, commercial=""), source) == expected


@pytest.mark.parametrize("field", ["title", "commercial", "queries"])
def test_invented_numbers_cover_every_generated_field(field: str) -> None:
    source = product(specs=(Spec("Класс точности", "1,5"),), description="")
    fields = {
        "title": {"title": "Прибор 777"},
        "commercial": {"commercial": "Выдерживает 777 циклов"},
        "queries": {"queries": ("прибор 777", "прибор", "манометр")},
    }

    assert invented_numbers(draft(**fields[field]), source) == ("777",)


def test_known_numbers_from_name_and_manufacturer_are_allowed() -> None:
    source = Product(name="ТРМ1", manufacturer="ОВЕН 2", specs=(), description="")

    assert invented_numbers(draft(description="ТРМ1 от ОВЕН 2"), source) == ()


def test_leading_zeros_do_not_look_invented() -> None:
    source = Product(name="Манометр DM 02", manufacturer="Манотомь", specs=(), description="")

    assert invented_numbers(draft(description="Манометр DM 2"), source) == ()
