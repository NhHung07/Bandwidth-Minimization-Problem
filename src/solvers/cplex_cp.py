"""Giải BMP bằng IBM CP Optimizer thông qua DOcplex.CP."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from time import perf_counter

from ..graph import Graph
from ..graph_bounds import compute_graph_bounds
from .common import (PhaseCallback, SolverResult, check_options, finite_lower_bound,
                     make_result, remaining_solve_time)


def _find_cp_optimizer() -> Path | None:
    """Tìm executable do người dùng chỉ định, trong PATH hoặc thư mục IBM chuẩn."""
    configured = os.environ.get("CP_OPTIMIZER_EXECUTABLE")
    if configured:
        path = Path(configured).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"CP_OPTIMIZER_EXECUTABLE không tồn tại: {path}")
        return path

    on_path = shutil.which("cpoptimizer.exe") or shutil.which("cpoptimizer")
    if on_path:
        return Path(on_path)

    # IBM Studio trên Windows thường cài ở Program Files nhưng không thêm PATH.
    program_files = os.environ.get("ProgramFiles")
    if program_files:
        root = Path(program_files) / "IBM" / "ILOG"
        candidates = sorted(root.glob("CPLEX_Studio*/cpoptimizer/bin/*/cpoptimizer.exe"), reverse=True)
        if candidates:
            return candidates[0]
    return None


def solve_cplex_cp(graph: Graph, time_limit: float | None = None, workers: int = 1,
                   on_phase: PhaseCallback | None = None) -> SolverResult:
    """Dùng biến vị trí nguyên, AllDifferent và trị tuyệt đối trên mỗi cạnh.

    ``docplex`` là thư viện mô hình; để solve còn cần chương trình CP
    Optimizer thuộc IBM ILOG CPLEX Optimization Studio.
    """
    check_options(time_limit, workers)
    run_start = perf_counter()
    try:
        from docplex.cp.model import CpoModel
    except ImportError as exc:
        raise RuntimeError("Cần cài docplex: python -m pip install docplex") from exc

    build_start = perf_counter()
    graph_bound = compute_graph_bounds(graph).strongest
    model = CpoModel(name=f"bmp_{graph.name}")
    position = [model.integer_var(min=1, max=graph.n, name=f"p_{v}") for v in range(1, graph.n + 1)]
    model.add(model.all_diff(position))
    bandwidth = model.integer_var(min=graph_bound, max=graph.n - 1, name="bandwidth")
    for u, v in graph.edges:
        model.add(model.abs(position[u - 1] - position[v - 1]) <= bandwidth)
    model.add(model.minimize(bandwidth))
    build_seconds = perf_counter() - build_start
    if on_phase is not None:
        on_phase("build_end", build_seconds)

    remaining = remaining_solve_time(time_limit, run_start)
    if remaining == 0:
        return make_result(graph, "cplex_cp", "TIMEOUT", None, None, build_seconds, 0.0)

    options: dict[str, object] = {"Workers": workers, "LogVerbosity": "Quiet"}
    if remaining is not None:
        options["TimeLimit"] = remaining
    optimizer = _find_cp_optimizer()
    if optimizer is not None:
        # DOcplex nhận tên thuộc tính lá của context ngay trong solve().
        options["execfile"] = str(optimizer)
    if on_phase is not None:
        on_phase("solve_start", 0.0)
    solve_start = perf_counter()
    try:
        solution = model.solve(**options)
    except Exception as exc:
        raise RuntimeError(
            "Không chạy được IBM CP Optimizer; kiểm tra bản cài Optimization Studio và license"
        ) from exc
    solve_seconds = perf_counter() - solve_start

    if solution.is_solution_optimal():
        status = "OPTIMAL"
    elif solution.is_solution():
        status = "FEASIBLE"
    elif solution.get_solve_status() == "Infeasible":
        raise RuntimeError("BMP luôn có hoán vị khả thi nhưng CP Optimizer báo Infeasible")
    elif time_limit is not None and "Limit" in str(solution.get_stop_cause()):
        status = "TIMEOUT"
    else:
        raise RuntimeError(f"CP Optimizer không tìm được nghiệm: {solution.get_solve_status()}")

    positions = tuple(solution.get_value(var) for var in position) if solution.is_solution() else None
    objective = float(solution.get_objective_value()) if positions is not None else None
    lower_bound = finite_lower_bound(solution.get_objective_bound(), graph.n)
    return make_result(graph, "cplex_cp", status, positions, lower_bound, build_seconds, solve_seconds, objective)
