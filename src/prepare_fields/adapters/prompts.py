import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from importlib import resources
from string import Template

from prepare_fields.domain.draft import Draft
from prepare_fields.domain.product import Product

_ALL_PRESENT = "все обязательные поля заполнены"


def _read(name: str) -> str:
    return resources.files("prepare_fields").joinpath("prompts", name).read_text(encoding="utf-8")


def _dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _payload(product: Product) -> dict[str, object]:
    return {
        "name": product.name,
        "manufacturer": product.manufacturer,
        "specs": {spec.name: spec.value for spec in product.specs},
        "description": product.description,
    }


class FilePrompts:
    def system(self) -> str:
        return _read("system.tmpl")

    def card(self, product: Product, missing: Mapping[str, str]) -> str:
        return Template(_read("card.tmpl")).substitute(
            input_json=_dump(_payload(product)),
            missing=", ".join(missing) or _ALL_PRESENT,
        )

    def retry(
        self,
        product: Product,
        missing: Mapping[str, str],
        draft: Draft,
        violations: Sequence[str],
    ) -> str:
        return Template(_read("retry.tmpl")).substitute(
            input_json=_dump(_payload(product)),
            missing=", ".join(missing) or _ALL_PRESENT,
            previous=_dump(asdict(draft)),
            violations="\n".join(f"- {item}" for item in violations),
        )
