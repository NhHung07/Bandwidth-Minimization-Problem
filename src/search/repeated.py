"""Tìm bandwidth tối ưu bằng cách tạo SAT solver mới cho từng ngưỡng k."""

from __future__ import annotations

from time import perf_counter
from typing import Callable

from ..graph import Graph
from ..encodings.cardinality import CardinalityName
from ..verify import verify_solution
from .common import EncodingName, SearchResult, ThresholdTrial, build_encoding, decode_model, initial_upper_bound


def optimize_repeated(
    graph: Graph,
    encoding: EncodingName = "pairwise",
    on_trial: Callable[[ThresholdTrial, tuple[int, ...] | None], None] | None = None,
    *,
    cardinality: CardinalityName = "binomial",
) -> SearchResult:
    """Giảm k từ cận trên khả thi đến lần UNSAT đầu tiên.

    Mỗi k tạo CNF và một Solver mới. Nếu k SAT và k-1 UNSAT thì k là
    tối ưu. Với k=0 SAT, tính không âm của bandwidth đã chứng minh tối ưu.
    """
    try:
        from pysat.solvers import Solver
    except ImportError as exc:
        raise RuntimeError("cần cài python-sat: python -m pip install python-sat") from exc

    initial_k = initial_upper_bound(graph)
    trials: list[ThresholdTrial] = []
    best_positions: tuple[int, ...] | None = None
    best_k: int | None = None

    for k in range(initial_k, -1, -1):
        build_start = perf_counter()
        decision = build_encoding(graph, k, encoding, cardinality)
        with Solver(name="g3", bootstrap_with=decision.clauses) as solver:
            build_seconds = perf_counter() - build_start
            solve_start = perf_counter()
            satisfiable = solver.solve()
            solve_seconds = perf_counter() - solve_start
            if satisfiable:
                model = solver.get_model()
                if model is None:
                    raise RuntimeError("SAT solver báo SAT nhưng không trả model")
                positions = decode_model(decision, model)
                bandwidth = verify_solution(graph, positions)
                best_positions, best_k = positions, k
            else:
                bandwidth = None

        trial = ThresholdTrial(
                k=k,
                satisfiable=satisfiable,
                bandwidth=bandwidth,
                num_variables=decision.num_vars,
                num_clauses=len(decision.clauses),
                build_seconds=build_seconds,
                solve_seconds=solve_seconds,
            )
        trials.append(trial)
        # Benchmark ghi tiến độ ngay; timeout vẫn giữ được nghiệm SAT gần nhất.
        if on_trial is not None:
            on_trial(trial, positions if satisfiable else None)
        if not satisfiable:
            break

    if best_positions is None or best_k is None:
        raise RuntimeError("cận trên ban đầu phải SAT nhưng solver không tìm được nghiệm")
    verify_solution(graph, best_positions, claimed_bandwidth=best_k)
    return SearchResult(encoding, "repeated", best_k, best_positions, initial_k, tuple(trials), cardinality)
