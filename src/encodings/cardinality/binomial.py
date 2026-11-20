"""AMO đôi một: cấm mọi cặp biến cùng đúng, không dùng biến phụ."""

from itertools import combinations
from typing import Sequence

from .common import CardinalityEncoding, prepare


def encode_amo(variables: Sequence[int], top_id: int = 0) -> CardinalityEncoding:
    values, builder = prepare(variables, top_id)
    builder.clauses.extend((-a, -b) for a, b in combinations(values, 2))
    return builder.result()
