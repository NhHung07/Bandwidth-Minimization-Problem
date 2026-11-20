"""AMO 2-product: mỗi biến chọn một ô duy nhất trong lưới hàng/cột."""

from itertools import combinations
from math import isqrt
from typing import Sequence

from .common import CardinalityEncoding, prepare


def encode_amo(variables: Sequence[int], top_id: int = 0) -> CardinalityEncoding:
    values, builder = prepare(variables, top_id)

    def constrain(items: tuple[int, ...]) -> None:
        if len(items) <= 4:
            builder.clauses.extend((-a, -b) for a, b in combinations(items, 2))
            return
        height = isqrt(len(items))
        width = (len(items) + height - 1) // height
        rows = tuple(builder.fresh() for _ in range(height))
        columns = tuple(builder.fresh() for _ in range(width))
        for index, variable in enumerate(items):
            builder.clauses.append((-variable, rows[index // width]))
            builder.clauses.append((-variable, columns[index % width]))
        constrain(rows)
        constrain(columns)

    constrain(values)
    return builder.result()
