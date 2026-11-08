from typing import Any

from prepare_fields.domain.draft import Card

_NO_SPECS = "Во входных данных характеристик нет."


def _cell(value: str) -> str:
    return value.replace("|", "\\|")


def render_json(card: Card) -> dict[str, Any]:
    return {
        "name": card.product.name,
        "manufacturer": card.product.manufacturer,
        "seo_title": card.draft.seo_title,
        "seo_title_length": len(card.draft.seo_title),
        "seo_description": card.draft.seo_description,
        "seo_description_length": len(card.draft.seo_description),
        "specs": [{"name": spec.name, "value": spec.value} for spec in card.product.specs],
        "search_queries": list(card.draft.search_queries),
        "commercial": card.draft.commercial,
        "missing": dict(card.missing),
        "warnings": list(card.warnings),
    }


def render_markdown(card: Card) -> str:
    draft = card.draft
    blocks = [
        f"# {card.product.title}",
        f"## SEO-заголовок ({len(draft.seo_title)} симв.)\n{draft.seo_title}",
        f"## SEO-описание ({len(draft.seo_description)} симв.)\n{draft.seo_description}",
        f"## Характеристики\n{_specs_table(card)}",
        "## Поисковые запросы\n"
        + "\n".join(f"{number}. {query}" for number, query in enumerate(draft.search_queries, 1)),
        f"## Для менеджера\n{draft.commercial}",
    ]
    if card.missing:
        blocks.append(
            "## Требует уточнения\n"
            + "\n".join(f"- {field} — {value}" for field, value in card.missing.items())
        )
    if card.warnings:
        blocks.append(
            "## Проверьте перед публикацией\n"
            + "\n".join(f"- {warning}" for warning in card.warnings)
        )
    return "\n\n".join(blocks) + "\n"


def _specs_table(card: Card) -> str:
    if not card.product.specs:
        return _NO_SPECS
    rows = "\n".join(f"| {_cell(spec.name)} | {_cell(spec.value)} |" for spec in card.product.specs)
    return f"| Характеристика | Значение |\n| --- | --- |\n{rows}"
