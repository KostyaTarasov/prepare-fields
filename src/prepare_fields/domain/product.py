import re
from collections.abc import Mapping
from dataclasses import dataclass

NO_DATA = "данных нет"

_KEY_ALIASES: Mapping[str, tuple[str, ...]] = {
    "Диапазон измерений": ("диапазон измерений", "диапазон измерения", "пределы измерений"),
    "Класс точности": ("класс точности", "точность"),
    "Питание": ("питание", "напряжение питания", "электропитание"),
    "Тип корпуса": ("тип корпуса", "корпус", "исполнение корпуса"),
    "Интерфейсы": ("интерфейсы", "интерфейс", "выходной сигнал"),
}

_SPACES = re.compile(r"\s+")


@dataclass(frozen=True)
class Spec:
    name: str
    value: str


@dataclass(frozen=True)
class Product:
    name: str
    manufacturer: str
    specs: tuple[Spec, ...]
    description: str

    @property
    def title(self) -> str:
        return f"{self.name} ({self.manufacturer})" if self.manufacturer else self.name


def canonical_key(key: str) -> str:
    normalized = _SPACES.sub(" ", key).strip().lower()
    for canonical, aliases in _KEY_ALIASES.items():
        if normalized in aliases:
            return canonical
    return normalized[:1].upper() + normalized[1:]


def missing_fields(product: Product) -> dict[str, str]:
    """Поля, без которых контент-менеджеру придётся дописывать карточку руками."""
    present = {spec.name for spec in product.specs}
    missing = {key: NO_DATA for key in _KEY_ALIASES if key not in present}
    if not product.description.strip():
        missing["Описание или фрагмент техпаспорта"] = NO_DATA
    return missing
