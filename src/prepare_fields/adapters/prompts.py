import json
from collections.abc import Mapping, Sequence
from importlib import resources
from string import Template

from prepare_fields.domain.draft import Draft
from prepare_fields.domain.product import Product

_ALL_PRESENT = "все обязательные поля заполнены"


def _read(name: str) -> str:
    return resources.files("prepare_fields").joinpath("prompts", name).read_text(encoding="utf-8")


def _dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


class FilePrompts:
    """Шаблоны промптов из prompts/*.tmpl, подстановка без склейки текста в коде."""

    def system(self) -> str:
        return _read("system.tmpl")

    def card(self, product: Product, missing: Mapping[str, str]) -> str:
        payload = {
            "name": product.name,
            "manufacturer": product.manufacturer,
            "specs": {spec.name: spec.value for spec in product.specs},
            "description": product.description,
        }
        return Template(_read("card.tmpl")).substitute(
            input_json=_dump(payload),
            missing=", ".join(missing) or _ALL_PRESENT,
        )

    def retry(self, draft: Draft, violations: Sequence[str]) -> str:
        previous = {
            "seo_title": draft.seo_title,
            "seo_description": draft.seo_description,
            "search_queries": list(draft.search_queries),
            "commercial": draft.commercial,
        }
        return Template(_read("retry.tmpl")).substitute(
            previous=_dump(previous),
            violations="\n".join(f"- {item}" for item in violations),
        )
