"""Giải BMP chính xác bằng Google OR-Tools CP-SAT."""

from __future__ import annotations

from time import perf_counter

from ..graph import Graph
from ..graph_bounds import compute_graph_bounds
from .common import (PhaseCallback, SolverResult, check_options, finite_lower_bound,
                     make_result, remaining_solve_time)


def solve_cpsat(graph: Graph, time_limit: float | None = None, workers: int = 1,
                on_phase: PhaseCallback | None = None) -> SolverResult:
    """Tối thiểu hóa bandwidth với biến vị trí và ràng buộc AllDifferent.

    Nếu hết giờ, trả nghiệm hiện có và cận dưới; không gắn nhãn OPTIMAL
    khi CP-SAT chưa chứng minh xong.
    """
    check_options(time_limit, workers)
    run_start = perf_counter()
    try:
        from ortools.sat.python import cp_model
    except ImportError as exc:
        raise RuntimeError("Cần cài ortools: python -m pip install ortools") from exc

    build_start = perf_counter()
    graph_bound = compute_graph_bounds(graph).strongest
    model = cp_model.CpModel()
    position = [model.new_int_var(1, graph.n, f"p_{v}") for v in range(1, graph.n + 1)]
    model.add_all_different(position)
    bandwidth = model.new_int_var(graph_bound, graph.n - 1, "bandwidth")
    for u, v in graph.edges:
        distance = model.new_int_var(0, graph.n - 1, f"d_{u}_{v}")
        model.add_abs_equality(distance, position[u - 1] - position[v - 1])
        model.add(distance <= bandwidth)
    model.minimize(bandwidth)
    build_seconds = perf_counter() - build_start
    if on_phase is not None:
        on_phase("build_end", build_seconds)

    remaining = remaining_solve_time(time_limit, run_start)
    if remaining == 0:
        return make_result(graph, "cpsat", "TIMEOUT", None, None, build_seconds, 0.0)

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = workers
    if remaining is not None:
        solver.parameters.max_time_in_seconds = remaining
    if on_phase is not None:
        on_phase("solve_start", 0.0)
    solve_start = perf_counter()
    state = solver.solve(model)
    solve_seconds = perf_counter() - solve_start

    if state == cp_model.MODEL_INVALID:
        raise RuntimeError("Mô hình CP-SAT không hợp lệ")
    if state == cp_model.INFEASIBLE:
        raise RuntimeError("BMP luôn có hoán vị khả thi nhưng CP-SAT báo INFEASIBLE")
    if state not in (cp_model.OPTIMAL, cp_model.FEASIBLE, cp_model.UNKNOWN):
        raise RuntimeError(f"Trạng thái CP-SAT chưa xử lý: {state}")
    if state == cp_model.UNKNOWN and time_limit is None:
        raise RuntimeError("CP-SAT dừng mà chưa có kết luận khi không đặt time_limit")
    status = "OPTIMAL" if state == cp_model.OPTIMAL else "FEASIBLE" if state == cp_model.FEASIBLE else "TIMEOUT"
    positions = tuple(solver.value(var) for var in position) if state in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None
    objective = float(solver.objective_value) if positions is not None else None
    lower_bound = finite_lower_bound(solver.best_objective_bound, graph.n)
    return make_result(graph, "cpsat", status, positions, lower_bound, build_seconds, solve_seconds, objective)
