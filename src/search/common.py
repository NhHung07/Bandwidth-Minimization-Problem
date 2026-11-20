"""Kiểu kết quả và thao tác dùng chung cho hai cách tối ưu SAT."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from ..encodings.cardinality import CARDINALITY_ENCODINGS, CardinalityName
from ..encodings.bmp.order import OrderEncoding, decode_order_model, encode_order
from ..encodings.bmp.pairwise import PairwiseEncoding, decode_pairwise_model, encode_pairwise
from ..graph import Graph
from ..verify import compute_bandwidth


EncodingName = Literal["pairwise", "order"]
DecisionEncoding = PairwiseEncoding | OrderEncoding


@dataclass(frozen=True, slots=True)
class ThresholdTrial:
    """Kết quả của một lần hỏi SAT ở ngưỡng k."""

    k: int
    satisfiable: bool
    bandwidth: int | None
    num_variables: int
    num_clauses: int
    build_seconds: float
    solve_seconds: float


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Nghiệm tối ưu đã chứng minh và lịch sử những ngưỡng được thử."""

    encoding: EncodingName
    method: Literal["repeated", "incremental"]
    bandwidth: int
    positions: tuple[int, ...]
    initial_k: int
    trials: tuple[ThresholdTrial, ...]
    cardinality: CardinalityName = "binomial"

    @property
    def sat_calls(self) -> int:
        """Số lần gọi SAT solver, gồm cả lần trả UNSAT."""
        return len(self.trials)

    @property
    def build_seconds(self) -> float:
        """Tổng thời gian dựng CNF và nạp clause vào solver."""
        return sum(trial.build_seconds for trial in self.trials)

    @property
    def solve_seconds(self) -> float:
        """Tổng thời gian các lời gọi solve()."""
        return sum(trial.solve_seconds for trial in self.trials)


def initial_upper_bound(graph: Graph) -> int:
    """Thứ tự đỉnh 1..n luôn khả thi và cho một cận trên ban đầu."""
    return compute_bandwidth(graph, range(1, graph.n + 1))


def build_encoding(
    graph: Graph, k: int, encoding: EncodingName, cardinality: CardinalityName = "binomial",
) -> DecisionEncoding:
    """Chọn một trong hai cách mã hóa BMP, cùng ngưỡng k."""
    if cardinality not in CARDINALITY_ENCODINGS:
        raise ValueError(f"cardinality phải thuộc {CARDINALITY_ENCODINGS}")
    if encoding == "pairwise":
        return encode_pairwise(graph, k, cardinality)
    if encoding == "order":
        if cardinality != "binomial":
            raise ValueError("cardinality mở rộng chỉ áp dụng cho encoding pairwise")
        return encode_order(graph, k)
    raise ValueError("encoding phải là 'pairwise' hoặc 'order'")


def decode_model(encoding: DecisionEncoding, model: Sequence[int]) -> tuple[int, ...]:
    """Giải mã model theo đúng ý nghĩa biến của công thức đã tạo."""
    if isinstance(encoding, PairwiseEncoding):
        return decode_pairwise_model(encoding, model)
    return decode_order_model(encoding, model)
