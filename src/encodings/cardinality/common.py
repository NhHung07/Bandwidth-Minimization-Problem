"""Kiểu CNF và cấp phát biến phụ riêng cho từng ràng buộc AMO."""

from dataclasses import dataclass, field
from typing import Literal, Sequence

CardinalityName = Literal["binomial", "binary", "commander", "product", "sequential"]
CARDINALITY_ENCODINGS = ("binomial", "binary", "commander", "product", "sequential")


@dataclass(frozen=True, slots=True)
class CardinalityEncoding:
    """num_vars là ID lớn nhất đã dùng, kể cả top_id của công thức trước."""

    num_vars: int
    clauses: tuple[tuple[int, ...], ...]


@dataclass
class Builder:
    top: int
    clauses: list[tuple[int, ...]] = field(default_factory=list)

    def fresh(self) -> int:
        self.top += 1
        return self.top

    def result(self) -> CardinalityEncoding:
        return CardinalityEncoding(self.top, tuple(self.clauses))


def prepare(variables: Sequence[int], top_id: int) -> tuple[tuple[int, ...], Builder]:
    """Nhận các ID biến dương phân biệt, cấp biến phụ sau toàn bộ ID đã dùng."""
    values = tuple(variables)
    if type(top_id) is not int or top_id < 0:
        raise ValueError("top_id phải là số nguyên không âm")
    if any(type(value) is not int or value <= 0 for value in values):
        raise ValueError("variables phải chứa các ID nguyên dương")
    if len(set(values)) != len(values):
        raise ValueError("variables không được trùng ID")
    return values, Builder(max(top_id, max(values, default=0)))
