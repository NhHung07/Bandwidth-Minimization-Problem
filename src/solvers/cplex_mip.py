"""Giải BMP bằng IBM CPLEX MIP thông qua DOcplex.MP."""

from __future__ import annotations

from time import perf_counter

from ..graph import Graph
from .common import SolverResult, check_options, finite_lower_bound, make_result


def solve_cplex_mip(graph: Graph, time_limit: float | None = None, workers: int = 1) -> SolverResult:
    """Mô hình x[v,p]=1 nếu đỉnh v ở vị trí p; tối thiểu hóa bandwidth.

    Mỗi đỉnh nhận đúng một vị trí và mỗi vị trí có đúng một đỉnh. Với mỗi
    cạnh (u,v), hai bất đẳng thức tuyến tính ép |p[u]-p[v]| <= bandwidth.
    """
    check_options(time_limit, workers)
    try:
        from docplex.mp.model import Model
    except ImportError as exc:
        raise RuntimeError("Cần cài docplex và cplex: python -m pip install docplex cplex") from exc

    build_start = perf_counter()
    model = Model(name=f"bmp_{graph.name}", log_output=False)
    try:
        vertices = range(1, graph.n + 1)
        slots = range(1, graph.n + 1)
        x = model.binary_var_matrix(vertices, slots, name="x")
        bandwidth = model.integer_var(lb=0, ub=graph.n - 1, name="bandwidth")
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
        if time_limit is not None:
            model.set_time_limit(time_limit)
        build_seconds = perf_counter() - build_start

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
