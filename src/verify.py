"""Kiểm tra độc lập nghiệm BMP do SAT, CP hoặc MIP trả về."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .graph import Graph


def validate_positions(graph: Graph, positions: Sequence[int] | Mapping[int, int]) -> tuple[int, ...]:
    """Kiểm tra đầu vào có gán mỗi đỉnh vào đúng một vị trí hay không.

    Nếu truyền tuple/list, ``positions[v - 1]`` là vị trí của đỉnh ``v``.
    Nếu truyền dict, dùng dạng ``{mã_đỉnh: vị_trí}``. Các vị trí phải là
    hoán vị của 1..n. Đây KHÔNG phải danh sách mã đỉnh từ trái sang phải.
    """
    if isinstance(positions, Mapping):
        # Dict phải có đủ và chỉ có các khóa 1, 2, ..., n.
        expected_vertices = set(range(1, graph.n + 1))
        if any(type(vertex) is not int for vertex in positions) or set(positions) != expected_vertices:
            raise ValueError(f"các khóa mã đỉnh phải đúng bằng 1..{graph.n}")
        # Đưa dict về tuple để phần tính bandwidth chỉ cần xử lý một kiểu dữ liệu.
        permutation = tuple(positions[vertex] for vertex in range(1, graph.n + 1))
    else:
        if isinstance(positions, (str, bytes)):
            raise TypeError("positions phải là dãy số nguyên hoặc dict mã đỉnh → vị trí")
        permutation = tuple(positions)

    if len(permutation) != graph.n:
        raise ValueError(f"cần {graph.n} vị trí, thực tế có {len(permutation)}")
    # bool là kiểu con của int trong Python, nên dùng type(...) is int để loại True/False.
    if any(type(position) is not int for position in permutation):
        raise ValueError("mọi vị trí phải là số nguyên; True/False không phải vị trí")
    # Set đủ 1..n cộng với độ dài n đồng nghĩa không có vị trí bị thiếu hoặc lặp.
    if set(permutation) != set(range(1, graph.n + 1)):
        raise ValueError(f"các vị trí phải là một hoán vị của 1..{graph.n}")
    return permutation


def compute_bandwidth(graph: Graph, positions: Sequence[int] | Mapping[int, int]) -> int:
    """Tính khoảng cách vị trí lớn nhất giữa hai đầu của mọi cạnh.

    Công thức: ``max(|positions[u-1] - positions[v-1]|)`` với (u,v) là cạnh.
    Vẫn kiểm tra hoán vị trước, kể cả khi đồ thị không có cạnh. Khi không có
    cạnh, quy ước bandwidth bằng 0.
    """
    permutation = validate_positions(graph, positions)
    # default=0 xử lý trường hợp graph.edges rỗng, tránh max() báo lỗi.
    return max((abs(permutation[u - 1] - permutation[v - 1]) for u, v in graph.edges), default=0)


def verify_solution(
    graph: Graph,
    positions: Sequence[int] | Mapping[int, int],
    claimed_bandwidth: int | None = None,
) -> int:
    """Tự tính bandwidth và đối chiếu với số solver công bố (nếu có).

    Hàm trả bandwidth tính lại. Hoán vị sai hoặc giá trị công bố không khớp
    sẽ gây ValueError. Việc này chưa chứng minh nghiệm là tối ưu.
    """
    actual = compute_bandwidth(graph, positions)
    if claimed_bandwidth is not None:
        # Chỉ so sánh sau khi chắc chắn số solver báo là số nguyên không âm.
        if type(claimed_bandwidth) is not int or claimed_bandwidth < 0:
            raise ValueError("bandwidth được công bố phải là số nguyên không âm")
        if actual != claimed_bandwidth:
            raise ValueError(f"bandwidth công bố {claimed_bandwidth} khác giá trị tính lại {actual}")
    return actual
