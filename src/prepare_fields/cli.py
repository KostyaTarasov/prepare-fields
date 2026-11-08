import argparse
import json
import logging
import sys
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from prepare_fields.adapters.json_input import parse_products
from prepare_fields.adapters.llm import ChatDraftWriter
from prepare_fields.adapters.prompts import FilePrompts
from prepare_fields.adapters.render import render_json, render_markdown
from prepare_fields.config import load
from prepare_fields.domain.draft import Card
from prepare_fields.domain.product import Product
from prepare_fields.errors import ConfigError, InputError, LLMError
from prepare_fields.usecase.prepare_card import PrepareCard

EXIT_INPUT = 1
EXIT_CONFIG = 2
EXIT_LLM = 3

log = logging.getLogger("prepare_fields")


def _arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="prepare-fields",
        description="Черновик карточки товара по данным о контрольно-измерительном приборе",
    )
    parser.add_argument("source", help="путь к JSON-файлу или - для чтения из stdin")
    parser.add_argument(
        "--format",
        choices=("md", "json"),
        default="md",
        help="формат вывода, по умолчанию md",
    )
    return parser.parse_args(argv)


def _read(source: str) -> str:
    if source == "-":
        return sys.stdin.read()
    path = Path(source)
    if not path.is_file():
        raise InputError(f"файл не найден: {source}")
    return path.read_text(encoding="utf-8")


def _prepare(prepare: PrepareCard, product: Product) -> Card | None:
    try:
        return prepare(product)
    except LLMError as err:
        log.error("товар %r: %s", product.name, err)
        return None


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stderr)
    arguments = _arguments(argv)

    try:
        products = parse_products(_read(arguments.source))
    except InputError as err:
        log.error("%s", err)
        return EXIT_INPUT
    try:
        config = load()
    except ConfigError as err:
        log.error("%s", err)
        return EXIT_CONFIG

    prepare = PrepareCard(writer=ChatDraftWriter(config), prompts=FilePrompts())
    with ThreadPoolExecutor(max_workers=config.concurrency) as pool:
        results = pool.map(lambda product: _prepare(prepare, product), products)
        cards = [card for card in results if card is not None]

    if arguments.format == "json":
        print(json.dumps([render_json(card) for card in cards], ensure_ascii=False, indent=2))
    else:
        print("\n\n---\n\n".join(render_markdown(card) for card in cards))

    if len(cards) != len(products):
        return EXIT_LLM
    return 0


if __name__ == "__main__":
    sys.exit(main())
