import json

from prepare_fields.domain.product import Product, Spec, canonical_key
from prepare_fields.errors import InputError

_SCALARS = (str, int, float)


def _text(raw: dict[str, object], key: str) -> str:
    value = raw.get(key, "")
    if value is None:
        return ""
    if not isinstance(value, _SCALARS):
        raise InputError(f"поле {key}: ожидалась строка, получено {type(value).__name__}")
    return str(value).strip()


def _specs(raw: object) -> tuple[Spec, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, dict):
        raise InputError(f"поле specs: ожидался объект, получено {type(raw).__name__}")
    specs = []
    for key, value in raw.items():
        if not isinstance(value, _SCALARS):
            raise InputError(
                f"характеристика {key!r}: ожидалось простое значение, "
                f"получено {type(value).__name__}"
            )
        text = str(value).strip()
        if text:
            specs.append(Spec(name=canonical_key(key), value=text))
    return tuple(specs)


def _product(raw: object, number: int) -> Product:
    if not isinstance(raw, dict):
        raise InputError(f"товар {number}: ожидался объект, получено {type(raw).__name__}")
    try:
        name = _text(raw, "name")
        if not name:
            raise InputError("поле name обязательно и не может быть пустым")
        return Product(
            name=name,
            manufacturer=_text(raw, "manufacturer"),
            specs=_specs(raw.get("specs")),
            description=_text(raw, "description"),
        )
    except InputError as err:
        raise InputError(f"товар {number}: {err}") from err


def parse_products(raw: str) -> tuple[Product, ...]:
    if not raw.strip():
        raise InputError("входные данные пусты")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as err:
        raise InputError(f"некорректный JSON: {err}") from err
    items = data if isinstance(data, list) else [data]
    if not items:
        raise InputError("во входных данных нет ни одного товара")
    return tuple(_product(item, number) for number, item in enumerate(items, 1))
