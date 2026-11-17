"""Giải BMP bằng IBM CPLEX MIP thông qua DOcplex.MP."""

from __future__ import annotations

from time import perf_counter

from ..graph import Graph
from ..graph_bounds import compute_graph_bounds
from .common import (PhaseCallback, SolverResult, check_options, finite_lower_bound,
                     make_result, remaining_solve_time)


def solve_cplex_mip(graph: Graph, time_limit: float | None = None, workers: int = 1,
                    on_phase: PhaseCallback | None = None) -> SolverResult:
    """Mô hình x[v,p]=1 nếu đỉnh v ở vị trí p; tối thiểu hóa bandwidth.

    Mỗi đỉnh nhận đúng một vị trí và mỗi vị trí có đúng một đỉnh. Với mỗi
    cạnh (u,v), hai bất đẳng thức tuyến tính ép |p[u]-p[v]| <= bandwidth.
    """
    check_options(time_limit, workers)
    run_start = perf_counter()
    try:
        from docplex.mp.model import Model
    except ImportError as exc:
        raise RuntimeError("Cần cài docplex và cplex: python -m pip install docplex cplex") from exc

    build_start = perf_counter()
    graph_bound = compute_graph_bounds(graph).strongest
    model = Model(name=f"bmp_{graph.name}", log_output=False)
    try:
        vertices = range(1, graph.n + 1)
        slots = range(1, graph.n + 1)
        x = model.binary_var_matrix(vertices, slots, name="x")
        bandwidth = model.integer_var(lb=graph_bound, ub=graph.n - 1, name="bandwidth")
        for v in vertices:
            model.add_constraint(model.sum(x[v, p] for p in slots) == 1)
        for p in slots:
            model.add_constraint(model.sum(x[v, p] for v in vertices) == 1)
        position = {v: model.sum(p * x[v, p] for p in slots) for v in vertices}
        for u, v in graph.edges:
            model.add_constraint(position[u] - position[v] <= bandwidth)
            model.add_constraint(position[v] - position[u] <= bandwidth)
        model.minimize(bandwidth)
        model.parameters.threads = workers
        model.parameters.emphasis.mip = 3  # BESTBOUND: ưu tiên cải thiện cận dưới.
        build_seconds = perf_counter() - build_start
        if on_phase is not None:
            on_phase("build_end", build_seconds)

        remaining = remaining_solve_time(time_limit, run_start)
        if remaining == 0:
            return make_result(graph, "cplex_mip", "TIMEOUT", None, None, build_seconds, 0.0)
        if remaining is not None:
            model.set_time_limit(remaining)
        if on_phase is not None:
            on_phase("solve_start", 0.0)

        solve_start = perf_counter()
        try:
            solution = model.solve(log_output=False)
        except Exception as exc:
            raise RuntimeError("Không chạy được CPLEX MIP; kiểm tra cplex và license") from exc
        solve_seconds = perf_counter() - solve_start
        details = model.solve_details
        raw_status = details.status.lower()
        if solution is not None and "optimal" in raw_status:
            status = "OPTIMAL"
        elif solution is not None:
            status = "FEASIBLE"
        elif "infeasible" in raw_status:
            raise RuntimeError("BMP luôn có hoán vị khả thi nhưng CPLEX MIP báo infeasible")
        elif time_limit is not None and details.has_hit_limit():
            status = "TIMEOUT"
        else:
            raise RuntimeError(f"CPLEX MIP không tìm được nghiệm: {details.status}")

        positions = (
            tuple(next(p for p in slots if solution.get_value(x[v, p]) > 0.5) for v in vertices)
            if solution is not None
            else None
        )
        objective = float(solution.objective_value) if solution is not None else None
        lower_bound = finite_lower_bound(details.best_bound, graph.n)
        return make_result(graph, "cplex_mip", status, positions, lower_bound, build_seconds, solve_seconds, objective)
    finally:
        model.end()
