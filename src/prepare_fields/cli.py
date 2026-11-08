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
    try:
        if source == "-":
            return sys.stdin.read()
        path = Path(source)
        if path.is_dir():
            raise InputError(f"указан каталог, а не файл: {source}")
        if not path.is_file():
            raise InputError(f"файл не найден: {source}")
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as err:
        raise InputError(f"файл не в UTF-8: {err}") from err
    except OSError as err:
        raise InputError(f"файл не прочитан: {err}") from err


def _prepare(prepare: PrepareCard, product: Product) -> Card | str:
    try:
        return prepare(product)
    except LLMError as err:
        log.error("товар %r: %s", product.name, err)
        return str(err).splitlines()[0]


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

    log.info(
        "провайдеры: %s",
        "; ".join(
            f"{provider.name} ({', '.join(provider.models)})" for provider in config.providers
        ),
    )
    prepare = PrepareCard(writer=ChatDraftWriter(config), prompts=FilePrompts())
    with ThreadPoolExecutor(max_workers=config.concurrency) as pool:
        results = list(pool.map(lambda product: _prepare(prepare, product), products))

    cards = [result for result in results if isinstance(result, Card)]
    failures = [
        (product.name, result)
        for product, result in zip(products, results, strict=True)
        if isinstance(result, str)
    ]

    if arguments.format == "json":
        payload = [render_json(card) for card in cards]
        payload += [{"name": name, "error": error} for name, error in failures]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        documents = [render_markdown(card) for card in cards]
        if failures:
            rows = "\n".join(f"- {name}: {error}" for name, error in failures)
            documents.append(f"# Не удалось сформировать\n\n{rows}\n")
        print("\n\n---\n\n".join(documents))

    return EXIT_LLM if failures else 0
