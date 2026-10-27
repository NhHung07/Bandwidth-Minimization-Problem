"""AMO + một clause ALO tạo Exactly-One cho hàng/cột của pairwise BMP."""

from typing import Sequence

from . import binary, binomial, commander, product, sequential
from .common import CARDINALITY_ENCODINGS, CardinalityEncoding, CardinalityName

_ENCODERS = {
    "binomial": binomial.encode_amo,
    "binary": binary.encode_amo,
    "commander": commander.encode_amo,
    "product": product.encode_amo,
    "sequential": sequential.encode_amo,
}


def encode_amo(
    variables: Sequence[int], encoding: CardinalityName = "binomial", top_id: int = 0,
) -> CardinalityEncoding:
    if encoding not in _ENCODERS:
        raise ValueError(f"cardinality phải thuộc {CARDINALITY_ENCODINGS}")
    return _ENCODERS[encoding](variables, top_id)


def encode_exactly_one(
    variables: Sequence[int], encoding: CardinalityName = "binomial", top_id: int = 0,
) -> CardinalityEncoding:
    """ALO là một clause OR; AMO thay đổi theo encoding. Dãy rỗng là UNSAT."""
    values = tuple(variables)
    amo = encode_amo(values, encoding, top_id)
    return CardinalityEncoding(amo.num_vars, (values, *amo.clauses))
