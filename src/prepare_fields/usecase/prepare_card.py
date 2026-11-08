from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from prepare_fields.domain.draft import Card, Draft, check_limits, invented_numbers
from prepare_fields.domain.product import Product, missing_fields


class DraftWriter(Protocol):
    def write(self, system: str, user: str) -> Draft: ...


class Prompts(Protocol):
    def system(self) -> str: ...

    def card(self, product: Product, missing: Mapping[str, str]) -> str: ...

    def retry(self, draft: Draft, violations: Sequence[str]) -> str: ...


def problems(draft: Draft, product: Product) -> tuple[str, ...]:
    found = list(check_limits(draft))
    invented = invented_numbers(draft, product)
    if invented:
        found.append("числа, которых нет во входных данных: " + ", ".join(invented))
    return tuple(found)


@dataclass(frozen=True)
class PrepareCard:
    writer: DraftWriter
    prompts: Prompts

    def __call__(self, product: Product) -> Card:
        missing = missing_fields(product)
        system = self.prompts.system()
        draft = self.writer.write(system, self.prompts.card(product, missing))
        found = problems(draft, product)
        if found:
            draft, found = self._repair(system, product, draft, found)
        return Card(product=product, draft=draft, missing=missing, warnings=found)

    def _repair(
        self,
        system: str,
        product: Product,
        draft: Draft,
        found: tuple[str, ...],
    ) -> tuple[Draft, tuple[str, ...]]:
        """Один повтор с замечаниями; черновик заменяем только если замечаний стало меньше."""
        repaired = self.writer.write(system, self.prompts.retry(draft, found))
        repaired_problems = problems(repaired, product)
        if len(repaired_problems) < len(found):
            return repaired, repaired_problems
        return draft, found
