"""Tìm bandwidth tối ưu bằng một SAT solver và các clause tăng dần."""

from __future__ import annotations

from time import perf_counter
from typing import Callable

from ..graph import Graph
from ..encodings.cardinality import CardinalityName
from ..verify import verify_solution
from .common import EncodingName, SearchResult, ThresholdTrial, build_encoding, decode_model, initial_upper_bound


def optimize_incremental(
    graph: Graph,
    encoding: EncodingName = "pairwise",
    on_trial: Callable[[ThresholdTrial, tuple[int, ...] | None], None] | None = None,
    *,
    cardinality: CardinalityName = "binomial",
) -> SearchResult:
    """Giữ một solver rồi siết k giảm dần đến lần UNSAT đầu tiên.

    Mỗi công thức ở k nhỏ hơn là điều kiện mạnh hơn về mặt logic. Chỉ nạp
    các clause chưa có; solver giữ các clause cũ và clause đã học.
    Với order, clause ở k cũ có thể khác chữ với clause ở k mới nhưng là
    hệ quả của ngưỡng chặt hơn, nên giữ lại vẫn đúng.
    """
    try:
        from pysat.solvers import Solver
    except ImportError as exc:
        raise RuntimeError("cần cài python-sat: python -m pip install python-sat") from exc

    initial_k = initial_upper_bound(graph)
    build_start = perf_counter()
    # Biến phụ của AMO có ID cố định theo thứ tự hàng/cột, độc lập với k.
    decision = build_encoding(graph, initial_k, encoding, cardinality)
    seen_clauses = set(decision.clauses)
    trials: list[ThresholdTrial] = []
    best_positions: tuple[int, ...] | None = None
    best_k: int | None = None

    with Solver(name="g3", bootstrap_with=decision.clauses) as solver:
        first_build_seconds = perf_counter() - build_start
        for k in range(initial_k, -1, -1):
            if k == initial_k:
                build_seconds = first_build_seconds
            else:
                build_start = perf_counter()
                decision = build_encoding(graph, k, encoding, cardinality)
                new_clauses = tuple(clause for clause in decision.clauses if clause not in seen_clauses)
                solver.append_formula(new_clauses)
                seen_clauses.update(new_clauses)
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
                    num_clauses=len(seen_clauses),
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
    return SearchResult(encoding, "incremental", best_k, best_positions, initial_k, tuple(trials), cardinality)
