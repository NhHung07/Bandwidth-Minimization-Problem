"""AMO sequential counter: s[i] ghi nhận đã có biến đúng trong tiền tố."""

from typing import Sequence

from .common import CardinalityEncoding, prepare


def encode_amo(variables: Sequence[int], top_id: int = 0) -> CardinalityEncoding:
    values, builder = prepare(variables, top_id)
    if len(values) > 1:
        prefix = [builder.fresh() for _ in range(len(values) - 1)]
        builder.clauses.append((-values[0], prefix[0]))
        for index in range(1, len(values) - 1):
            builder.clauses.extend((
                (-values[index], prefix[index]),
                (-prefix[index - 1], prefix[index]),
                (-values[index], -prefix[index - 1]),
            ))
        builder.clauses.append((-values[-1], -prefix[-1]))
    return builder.result()
