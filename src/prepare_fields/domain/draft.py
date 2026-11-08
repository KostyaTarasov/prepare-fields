import re
from collections.abc import Mapping
from dataclasses import dataclass

from prepare_fields.domain.product import Product

TITLE_MAX = 70
DESCRIPTION_MIN = 800
DESCRIPTION_MAX = 1200
QUERIES_MIN = 3
QUERIES_MAX = 5

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


@dataclass(frozen=True)
class Draft:
    seo_title: str
    seo_description: str
    search_queries: tuple[str, ...]
    commercial: str


@dataclass(frozen=True)
class Card:
    product: Product
    draft: Draft
    missing: Mapping[str, str]
    warnings: tuple[str, ...]


def check_limits(draft: Draft) -> tuple[str, ...]:
    problems: list[str] = []
    title_length = len(draft.seo_title)
    if not draft.seo_title.strip():
        problems.append("SEO-заголовок пустой")
    elif title_length > TITLE_MAX:
        problems.append(f"SEO-заголовок: {title_length} симв., допустимо до {TITLE_MAX}")

    description_length = len(draft.seo_description)
    if not DESCRIPTION_MIN <= description_length <= DESCRIPTION_MAX:
        problems.append(
            f"SEO-описание: {description_length} симв., "
            f"нужно от {DESCRIPTION_MIN} до {DESCRIPTION_MAX}"
        )

    if not QUERIES_MIN <= len(draft.search_queries) <= QUERIES_MAX:
        problems.append(
            f"поисковых запросов: {len(draft.search_queries)}, "
            f"нужно от {QUERIES_MIN} до {QUERIES_MAX}"
        )

    if not draft.commercial.strip():
        problems.append("commercial-блок пустой")
    return tuple(problems)


def _normalize_number(token: str) -> str:
    value = token.replace(",", ".")
    if "." in value:
        return value.rstrip("0").rstrip(".")
    return value.lstrip("0") or "0"


def _numbers(text: str) -> set[str]:
    return {_normalize_number(match.group()) for match in _NUMBER.finditer(text)}


def source_text(product: Product) -> str:
    specs = " ".join(f"{spec.name} {spec.value}" for spec in product.specs)
    return f"{product.name} {product.manufacturer} {specs} {product.description}"


def invented_numbers(draft: Draft, product: Product) -> tuple[str, ...]:
    known = _numbers(source_text(product))
    generated = _numbers(
        " ".join([draft.seo_title, draft.seo_description, draft.commercial, *draft.search_queries])
    )
    return tuple(sorted(generated - known))
