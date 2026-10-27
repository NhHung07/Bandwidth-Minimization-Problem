"""Giải BMP bằng Gurobi MIP."""

from __future__ import annotations

from time import perf_counter

from ..graph import Graph
from .common import SolverResult, check_options, finite_lower_bound, make_result


def solve_gurobi(graph: Graph, time_limit: float | None = None, workers: int = 1) -> SolverResult:
    """Dùng ma trận gán nhị phân và hai bất đẳng thức cho mỗi cạnh.

    Công thức tương đương với CPLEX MIP để có thể so sánh hai engine trên
    cùng một mô hình toán học.
    """
    check_options(time_limit, workers)
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except ImportError as exc:
        raise RuntimeError("Cần cài gurobipy: python -m pip install gurobipy") from exc

    build_start = perf_counter()
    try:
        model = gp.Model(f"bmp_{graph.name}")
    except Exception as exc:
        raise RuntimeError("Không tạo được mô hình Gurobi; kiểm tra bản cài và license") from exc
    try:
        model.Params.OutputFlag = 0
        model.Params.Threads = workers
        if time_limit is not None:
            model.Params.TimeLimit = time_limit
        vertices = range(1, graph.n + 1)
        slots = range(1, graph.n + 1)
        x = model.addVars(vertices, slots, vtype=GRB.BINARY, name="x")
        bandwidth = model.addVar(vtype=GRB.INTEGER, lb=0, ub=graph.n - 1, name="bandwidth")
        for v in vertices:
            model.addConstr(gp.quicksum(x[v, p] for p in slots) == 1)
        for p in slots:
            model.addConstr(gp.quicksum(x[v, p] for v in vertices) == 1)
        position = {v: gp.quicksum(p * x[v, p] for p in slots) for v in vertices}
        for u, v in graph.edges:
            model.addConstr(position[u] - position[v] <= bandwidth)
            model.addConstr(position[v] - position[u] <= bandwidth)
        model.setObjective(bandwidth, GRB.MINIMIZE)
        build_seconds = perf_counter() - build_start

        solve_start = perf_counter()
        try:
            model.optimize()
        except Exception as exc:
            raise RuntimeError("Không chạy được Gurobi; kiểm tra license và giới hạn bản cài") from exc
        solve_seconds = perf_counter() - solve_start
        if model.Status == GRB.INFEASIBLE:
            raise RuntimeError("BMP luôn có hoán vị khả thi nhưng Gurobi báo INFEASIBLE")
        if model.Status == GRB.OPTIMAL:
            status = "OPTIMAL"
        elif model.SolCount:
            status = "FEASIBLE"
        elif model.Status == GRB.TIME_LIMIT:
            status = "TIMEOUT"
        else:
            raise RuntimeError(f"Gurobi không tìm được nghiệm, trạng thái {model.Status}")

        positions = (
            tuple(next(p for p in slots if x[v, p].X > 0.5) for v in vertices)
            if model.SolCount
            else None
        )
        objective = float(model.ObjVal) if model.SolCount else None
        lower_bound = finite_lower_bound(model.ObjBound, graph.n)
        return make_result(graph, "gurobi", status, positions, lower_bound, build_seconds, solve_seconds, objective)
    finally:
        model.dispose()
