"""Mã hóa BMP bằng biến ngưỡng t[v,p] mang nghĩa vị trí(v) <= p.

Chuỗi ngưỡng của mỗi đỉnh là False...False, True...True. Điểm chuyển
sang True chính là vị trí của đỉnh đó trong hoán vị.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Sequence

from ...graph import Graph
from ...verify import verify_solution


def _threshold_id(n: int, vertex: int, position: int) -> int:
    """Đánh số biến SAT liên tiếp từ 1, theo đỉnh rồi theo ngưỡng."""
    return (vertex - 1) * n + position


@dataclass(frozen=True, slots=True)
class OrderEncoding:
    """CNF của một ngưỡng k cùng thông tin để giải mã model SAT."""

    graph: Graph
    k: int
    num_vars: int
    clauses: tuple[tuple[int, ...], ...]

    def threshold(self, vertex: int, position: int) -> int:
        """Trả mã t[vertex,position], với hai chỉ số đều bắt đầu từ 1."""
        if not (1 <= vertex <= self.graph.n and 1 <= position <= self.graph.n):
            raise ValueError(f"đỉnh và ngưỡng vị trí phải nằm trong 1..{self.graph.n}")
        return _threshold_id(self.graph.n, vertex, position)


def encode_order(graph: Graph, k: int) -> OrderEncoding:
    """Tạo CNF khả thi đúng khi có hoán vị với bandwidth không quá k.

    Clause là tuple literal nguyên theo chuẩn DIMACS. Hàm chỉ tạo công
    thức; gọi SAT solver và giải mã nằm ở các hàm bên dưới.
    """
    if type(k) is not int or k < 0:
        raise ValueError("ngưỡng k phải là số nguyên không âm")

    n = graph.n
    clauses: list[tuple[int, ...]] = []

    for vertex in range(1, n + 1):
        # Mọi đỉnh đều có vị trí <= n. Tính đơn điệu buộc chuỗi chỉ đổi False -> True.
        clauses.append((_threshold_id(n, vertex, n),))
        for p in range(1, n):
            clauses.append((-_threshold_id(n, vertex, p), _threshold_id(n, vertex, p + 1)))

    # Đỉnh v ở đúng vị trí p khi t[v,p] đúng và t[v,p-1] sai.
    # Cấm hai đỉnh cùng chuyển trạng thái tại p. Có n đỉnh và n vị trí,
    # nên không trùng vị trí đồng nghĩa mỗi vị trí được dùng đúng một lần.
    for p in range(1, n + 1):
        for u, v in combinations(range(1, n + 1), 2):
            if p == 1:
                clauses.append((-_threshold_id(n, u, 1), -_threshold_id(n, v, 1)))
            else:
                clauses.append(
                    (
                        -_threshold_id(n, u, p),
                        _threshold_id(n, u, p - 1),
                        -_threshold_id(n, v, p),
                        _threshold_id(n, v, p - 1),
                    )
                )

    # Nếu vị trí(u) <= p thì vị trí(v) <= p+k; áp dụng cả hai chiều cạnh.
    # Các ngưỡng p+k > n tự đúng vì mọi đỉnh đều có vị trí <= n.
    for u, v in graph.edges:
        for p in range(1, n - k + 1):
            clauses.append((-_threshold_id(n, u, p), _threshold_id(n, v, p + k)))
            clauses.append((-_threshold_id(n, v, p), _threshold_id(n, u, p + k)))

    return OrderEncoding(graph=graph, k=k, num_vars=n * n, clauses=tuple(clauses))


def decode_order_model(encoding: OrderEncoding, model: Sequence[int]) -> tuple[int, ...]:
    """Lấy điểm False -> True của mỗi đỉnh rồi kiểm chứng hoán vị/BMP."""
    values: dict[int, bool] = {}
    for literal in model:
        if type(literal) is not int or literal == 0:
            raise ValueError("model phải chứa các literal nguyên khác 0")
        variable = abs(literal)
        if variable > encoding.num_vars:
            continue
        value = literal > 0
        if variable in values and values[variable] != value:    
            raise ValueError(f"model gán mâu thuẫn cho biến {variable}")
        values[variable] = value

    positions: list[int] = []
    for vertex in range(1, encoding.graph.n + 1):
        states: list[bool] = []
        for p in range(1, encoding.graph.n + 1):
            variable = encoding.threshold(vertex, p)
            if variable not in values:
                raise ValueError(f"model thiếu biến ngưỡng t[{vertex},{p}]")
            states.append(values[variable])
        if not states[-1] or any(states[p] and not states[p + 1] for p in range(len(states) - 1)):
            raise ValueError(f"chuỗi ngưỡng của đỉnh {vertex} không đơn điệu hoặc thiếu vị trí")
        positions.append(states.index(True) + 1)

    # Kiểm tra lại cả vị trí trùng và khoảng cách cạnh bằng module độc lập.
    result = tuple(positions)
    actual = verify_solution(encoding.graph, result)
    if actual > encoding.k:
        raise ValueError(f"model có bandwidth {actual}, vượt ngưỡng k={encoding.k}")
    return result


def solve_order(graph: Graph, k: int) -> tuple[int, ...] | None:
    """Giải một ngưỡng bằng PySAT; trả hoán vị hoặc None nếu UNSAT."""
    encoding = encode_order(graph, k)
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
        return decode_order_model(encoding, model)
