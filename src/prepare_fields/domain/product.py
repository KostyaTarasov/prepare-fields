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

_REQUIRED_SPECS = (
    "Диапазон измерений",
    "Класс точности",
    "Питание",
    "Тип корпуса",
    "Интерфейсы",
)

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
        manufacturer = self.manufacturer.strip()
        return f"{self.name} ({manufacturer})" if manufacturer else self.name


def canonical_key(key: str) -> str:
    normalized = _SPACES.sub(" ", key).strip().lower()
    for canonical, aliases in _KEY_ALIASES.items():
        if normalized in aliases:
            return canonical
    return normalized[:1].upper() + normalized[1:]


def missing_fields(product: Product) -> dict[str, str]:
    present = {spec.name for spec in product.specs if spec.value != NO_DATA}
    missing = {key: NO_DATA for key in _REQUIRED_SPECS if key not in present}
    if not product.manufacturer.strip():
        missing["Производитель"] = NO_DATA
    if not product.description.strip():
        missing["Описание или фрагмент техпаспорта"] = NO_DATA
    return missing
