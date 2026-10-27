"""Kiểu kết quả chung cho các solver CP và MIP của bài toán BMP."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal, Sequence

from ..graph import Graph
from ..verify import verify_solution


SolverStatus = Literal["OPTIMAL", "FEASIBLE", "TIMEOUT"]


@dataclass(frozen=True, slots=True)
class SolverResult:
    """Kết quả đã kiểm tra, với vị trí thứ v nằm ở ``positions[v-1]``.

    ``bandwidth`` là giá trị của nghiệm khả thi, còn ``lower_bound`` là cận
    dưới đã được solver chứng minh. Chỉ ``OPTIMAL`` khẳng định hai giá trị bằng nhau.
    ``TIMEOUT`` nghĩa là chưa tìm thấy nghiệm trước giới hạn thời gian.
    """

    method: str
    status: SolverStatus
    positions: tuple[int, ...] | None
    bandwidth: int | None
    lower_bound: float | None
    build_seconds: float
    solve_seconds: float

    @property
    def total_seconds(self) -> float:
        """Tổng thời gian dựng mô hình và gọi solver."""
        return self.build_seconds + self.solve_seconds


def check_options(time_limit: float | None, workers: int) -> None:
    """Chặn tham số không hợp lệ trước khi tạo mô hình hay gọi solver."""
    if time_limit is not None and (not isfinite(time_limit) or time_limit <= 0):
        raise ValueError("time_limit phải là số giây dương và hữu hạn")
    if type(workers) is not int or workers < 1:
        raise ValueError("workers phải là số nguyên dương")


def make_result(
    graph: Graph,
    method: str,
    status: SolverStatus,
    positions: Sequence[int] | None,
    lower_bound: float | None,
    build_seconds: float,
    solve_seconds: float,
    objective: float | None = None,
) -> SolverResult:
    """Kiểm lại nghiệm từ solver trước khi trả kết quả cho benchmark."""
    if positions is None:
        if status != "TIMEOUT":
            raise RuntimeError(f"{method} báo {status} nhưng không có nghiệm")
        return SolverResult(method, status, None, None, lower_bound, build_seconds, solve_seconds)

    # MIP trả số thực cho biến nguyên; chỉ làm tròn sai số số học rất nhỏ.
    if any(not isfinite(value) or abs(value - round(value)) > 1e-5 for value in positions):
        raise RuntimeError(f"{method} trả vị trí không nguyên")
    permutation = tuple(round(value) for value in positions)
    bandwidth = verify_solution(graph, permutation)
    if status == "OPTIMAL":
        # Nếu tối ưu được chứng minh, biến mục tiêu phải trùng bandwidth thật.
        if objective is None or abs(objective - bandwidth) > 1e-5:
            raise RuntimeError(f"{method} báo tối ưu nhưng mục tiêu không khớp nghiệm")
        lower_bound = float(bandwidth)
    elif status != "FEASIBLE":
        raise RuntimeError(f"{method} có nghiệm nhưng báo trạng thái {status}")

    if lower_bound is not None and (not isfinite(lower_bound) or lower_bound > bandwidth + 1e-5):
        raise RuntimeError(f"{method} trả cận dưới không hợp lệ")
    return SolverResult(method, status, permutation, bandwidth, lower_bound, build_seconds, solve_seconds)


def finite_lower_bound(value: float | None, n: int) -> float | None:
    """Bỏ cận vô cực/chưa xác định; bandwidth luôn nằm trong 0..n-1."""
    if value is None or not isfinite(value) or value > n - 1 + 1e-5:
        return None
    return max(0.0, float(value))
