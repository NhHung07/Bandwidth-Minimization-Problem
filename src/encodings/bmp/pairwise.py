"""Mã hóa câu hỏi BMP có bandwidth không quá k thành công thức SAT.

Biến x[v,p] đúng khi đỉnh v nằm ở vị trí p. Mỗi đỉnh và mỗi vị trí
phải xuất hiện đúng một lần; hai đầu cạnh không được cách nhau quá k.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import chain
from typing import Sequence

from ..cardinality import CardinalityName, encode_exactly_one
from ...graph import Graph
from ...verify import verify_solution


def _variable_id(n: int, vertex: int, position: int) -> int:
    """Đánh số biến SAT liên tiếp từ 1, theo thứ tự đỉnh rồi đến vị trí."""
    return (vertex - 1) * n + position


@dataclass(frozen=True, slots=True)
class PairwiseEncoding:
    """Công thức CNF và thông tin cần để đọc lại nghiệm của một ngưỡng k."""

    graph: Graph
    k: int
    num_vars: int
    clauses: tuple[tuple[int, ...], ...]
    cardinality: CardinalityName = "binomial"

    def variable(self, vertex: int, position: int) -> int:
        """Trả mã biến x[vertex,position] (cả hai đều đánh số từ 1)."""
        if not (1 <= vertex <= self.graph.n and 1 <= position <= self.graph.n):
            raise ValueError(f"đỉnh và vị trí phải nằm trong 1..{self.graph.n}")
        return _variable_id(self.graph.n, vertex, position)


def encode_pairwise(graph: Graph, k: int, cardinality: CardinalityName = "binomial") -> PairwiseEncoding:
    """Tạo CNF khả thi khi và chỉ khi tồn tại hoán vị có bandwidth <= k.

    Mỗi clause là tuple số nguyên theo chuẩn DIMACS: số dương là biến đúng,
    số âm là phủ định. Hàm chỉ tạo công thức, chưa gọi SAT solver.
    """
    if type(k) is not int or k < 0:
        raise ValueError("ngưỡng k phải là số nguyên không âm")

    n = graph.n
    clauses: list[tuple[int, ...]] = []
    top_id = n * n

    # Mỗi đỉnh phải ở ít nhất một vị trí (ALO) và nhiều nhất một vị trí (AMO).
    for vertex in range(1, n + 1):
        constraint = encode_exactly_one(
            tuple(_variable_id(n, vertex, p) for p in range(1, n + 1)), cardinality, top_id,
        )
        clauses.extend(constraint.clauses)
        top_id = constraint.num_vars

    # Mỗi vị trí phải chứa ít nhất một đỉnh và nhiều nhất một đỉnh.
    for position in range(1, n + 1):
        constraint = encode_exactly_one(
            tuple(_variable_id(n, v, position) for v in range(1, n + 1)), cardinality, top_id,
        )
        clauses.extend(constraint.clauses)
        top_id = constraint.num_vars

    # Nếu (u,v) là cạnh và |p-q| > k, cấm x[u,p] và x[v,q] cùng đúng.
    for u, v in graph.edges:
        for p in range(1, n + 1):
            for q in chain(range(1, p - k), range(p + k + 1, n + 1)):
                clauses.append((-_variable_id(n, u, p), -_variable_id(n, v, q)))

    return PairwiseEncoding(graph=graph, k=k, num_vars=top_id, clauses=tuple(clauses), cardinality=cardinality)


def decode_pairwise_model(encoding: PairwiseEncoding, model: Sequence[int]) -> tuple[int, ...]:
    """Đọc model SAT thành positions[v-1] và tự kiểm lại bandwidth.

    Model gồm literal có dấu như PySAT trả về. Literal phụ lớn hơn n²
    (nếu solver thêm biến riêng) không ảnh hưởng đến cách đọc vị trí.
    """
    values: dict[int, bool] = {}
    for literal in model:
        if type(literal) is not int or literal == 0:
            raise ValueError("model phải chứa các literal nguyên khác 0")
        variable = abs(literal)
        if variable > encoding.graph.n * encoding.graph.n:
            continue
        value = literal > 0
        if variable in values and values[variable] != value:
            raise ValueError(f"model gán mâu thuẫn cho biến {variable}")
        values[variable] = value

    positions: list[int] = []
    for vertex in range(1, encoding.graph.n + 1):
        selected = [p for p in range(1, encoding.graph.n + 1) if values.get(encoding.variable(vertex, p))]
        if len(selected) != 1:
            raise ValueError(f"đỉnh {vertex} phải có đúng một vị trí trong model")
        positions.append(selected[0])

    # verify_solution bắt cả vị trí trùng giữa các đỉnh và cạnh vượt ngưỡng.
    result = tuple(positions)
    actual = verify_solution(encoding.graph, result)
    if actual > encoding.k:
        raise ValueError(f"model có bandwidth {actual}, vượt ngưỡng k={encoding.k}")
    return result


def solve_pairwise(graph: Graph, k: int, cardinality: CardinalityName = "binomial") -> tuple[int, ...] | None:
    """Giải một ngưỡng bằng PySAT: trả nghiệm hoặc None nếu UNSAT.

    Mỗi lần gọi dùng solver mới. Chiến lược tìm k tối ưu và incremental SAT
    thuộc giai đoạn sau; hàm này chỉ giải một bài toán quyết định.
    """
    encoding = encode_pairwise(graph, k, cardinality)
    try:
        from pysat.solvers import Solver
    except ImportError as exc:
        raise RuntimeError("cần cài python-sat để giải CNF: python -m pip install python-sat") from exc

    with Solver(name="g3", bootstrap_with=encoding.clauses) as solver:
        if not solver.solve():
            return None
        model = solver.get_model()
        if model is None:
            raise RuntimeError("SAT solver báo SAT nhưng không trả model")
        return decode_pairwise_model(encoding, model)
