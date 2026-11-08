import pytest

from prepare_fields.adapters.json_input import parse_products
from prepare_fields.domain.product import missing_fields
from prepare_fields.errors import InputError


def test_single_object_and_array_are_both_accepted() -> None:
    one = parse_products('{"name": "БП14Б", "manufacturer": "ОВЕН"}')
    many = parse_products('[{"name": "БП14Б"}, {"name": "ТРМ1"}]')

    assert len(one) == 1
    assert [product.name for product in many] == ["БП14Б", "ТРМ1"]


def test_specs_are_normalized_and_empty_values_marked() -> None:
    raw = """
    {
      "name": "Манометр DM 02",
      "manufacturer": "Манотомь",
      "specs": {"диапазон измерения": "0–1,6 МПа", "класс точности": "  ", "артикул": 15064},
      "description": null
    }
    """

    product = parse_products(raw)[0]

    assert [(spec.name, spec.value) for spec in product.specs] == [
        ("Диапазон измерений", "0–1,6 МПа"),
        ("Класс точности", "данных нет"),
        ("Артикул", "15064"),
    ]
    assert product.description == ""


def test_spec_without_value_stays_in_missing() -> None:
    product = parse_products('{"name": "a", "specs": {"класс точности": ""}}')[0]

    assert "Класс точности" in missing_fields(product)


def test_boolean_is_not_a_characteristic() -> None:
    with pytest.raises(InputError, match="получено bool"):
        parse_products('{"name": "a", "specs": {"класс точности": true}}')


def test_synonym_keys_collapse_into_one_spec() -> None:
    product = parse_products(
        '{"name": "a", "specs": {"точность": "1,5", "класс точности": "0,6"}}'
    )[0]

    assert [(spec.name, spec.value) for spec in product.specs] == [("Класс точности", "0,6")]


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ("", "входные данные пусты"),
        ("{сломано}", "некорректный JSON"),
        ("[]", "нет ни одного товара"),
        ("[1]", "товар 1: ожидался объект, получено int"),
        ('{"manufacturer": "ОВЕН"}', "товар 1: поле name обязательно"),
        ('{"name": "  "}', "товар 1: поле name обязательно"),
        ('[{"name": "a"}, {"name": "b", "specs": []}]', "товар 2: поле specs: ожидался объект"),
        (
            '{"name": "a", "specs": {"диапазон": ["1"]}}',
            "ожидалось простое значение, получено list",
        ),
        ('{"name": {"a": 1}}', "товар 1: поле name: ожидалась строка, получено dict"),
    ],
)
def test_broken_input_is_rejected(raw: str, message: str) -> None:
    with pytest.raises(InputError, match=message):
        parse_products(raw)
