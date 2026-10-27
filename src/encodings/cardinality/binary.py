"""AMO binary: mỗi biến đúng buộc một mã bit riêng của bộ chọn."""

from typing import Sequence

from .common import CardinalityEncoding, prepare


def encode_amo(variables: Sequence[int], top_id: int = 0) -> CardinalityEncoding:
    values, builder = prepare(variables, top_id)
    if len(values) > 1:
        bits = [builder.fresh() for _ in range((len(values) - 1).bit_length())]
        for index, variable in enumerate(values):
            for offset, bit in enumerate(bits):
                builder.clauses.append((-variable, bit if (index >> offset) & 1 else -bit))
    return builder.result()
