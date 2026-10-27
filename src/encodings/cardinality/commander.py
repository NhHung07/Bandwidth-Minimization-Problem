"""AMO commander: chia nhóm 3, rồi đệ quy AMO trên các biến chỉ huy."""

from itertools import combinations
from typing import Sequence

from .common import CardinalityEncoding, prepare


def encode_amo(variables: Sequence[int], top_id: int = 0) -> CardinalityEncoding:
    values, builder = prepare(variables, top_id)

    def constrain(items: tuple[int, ...]) -> None:
        if len(items) <= 3:
            builder.clauses.extend((-a, -b) for a, b in combinations(items, 2))
            return
        commanders = []
        for start in range(0, len(items), 3):
            group = items[start:start + 3]
            commander = builder.fresh()
            commanders.append(commander)
            builder.clauses.extend((-a, -b) for a, b in combinations(group, 2))
            builder.clauses.extend((-item, commander) for item in group)
            # Commander đúng khi và chỉ khi một phần tử trong nhóm đúng.
            builder.clauses.append((-commander, *group))
        constrain(tuple(commanders))

    constrain(values)
    return builder.result()
