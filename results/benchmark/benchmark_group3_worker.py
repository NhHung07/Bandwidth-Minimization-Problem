"""Worker độc lập cho một phương pháp Nhóm 3; ghi sự kiện để giữ tiến độ."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.graph import load_graph
from src.graph_bounds import compute_graph_bounds
from src.search.incremental import optimize_incremental
from src.solvers.cplex_cp import solve_cplex_cp
from src.solvers.cplex_mip import solve_cplex_mip
from src.solvers.cpsat import solve_cpsat
from src.solvers.gurobi import solve_gurobi


SOLVERS = {"cp": solve_cplex_cp, "mip": solve_cplex_mip,
           "cp_sat": solve_cpsat, "gurobi": solve_gurobi}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("instance", type=Path)
    parser.add_argument("method", choices=("sat", *SOLVERS))
    parser.add_argument("deadline", type=float)
    parser.add_argument("events", type=Path)
    args = parser.parse_args()

    with args.events.open("a", encoding="utf-8", buffering=1) as stream:
        def emit(event: dict) -> None:
            event["at"] = perf_counter()
            stream.write(json.dumps(event, allow_nan=False) + "\n")
            stream.flush()

        try:
            graph = load_graph(args.instance)
            emit({"type": "phase", "phase": "build_start", "seconds": 0.0})
            bounds_start = perf_counter()
            bounds = compute_graph_bounds(graph)
            bounds_seconds = perf_counter() - bounds_start
            emit({"type": "bounds", "degree": bounds.degree,
                  "neighborhood": bounds.neighborhood, "clique": bounds.clique,
                  "lower_bound": bounds.strongest})
            emit({"type": "phase", "phase": "build_end", "seconds": bounds_seconds})
            if args.method == "sat":
                def on_phase(phase, k, seconds, variables, clauses) -> None:
                    emit({"type": "phase", "phase": phase, "seconds": seconds,
                          "num_vars": variables, "num_clauses": clauses})

                def on_trial(trial, positions) -> None:
                    emit({"type": "trial", "k": trial.k, "sat": trial.satisfiable,
                          "bandwidth": trial.bandwidth, "positions": positions,
                          "solve_time": trial.solve_seconds})

                result = optimize_incremental(graph, "pairwise", on_trial=on_trial,
                                              cardinality="product", on_phase=on_phase,
                                              min_k=bounds.strongest)
                emit({"type": "result", "status": "OPTIMAL", "bandwidth": result.bandwidth,
                      "lower_bound": result.bandwidth, "positions": result.positions,
                      "build_time": bounds_seconds + result.build_seconds,
                      "solve_time": result.solve_seconds})
            else:
                def on_phase(phase: str, seconds: float) -> None:
                    emit({"type": "phase", "phase": phase, "seconds": seconds})

                # Deadline do tiến trình cha đặt trước khi khởi động worker.
                # Trừ thời gian import và đọc dữ liệu để tổng lượt không quá hạn.
                remaining = max(0.001, args.deadline - perf_counter() - 1.0)
                emit({"type": "phase", "phase": "build_start", "seconds": 0.0})
                result = SOLVERS[args.method](graph, time_limit=remaining,
                                              workers=1, on_phase=on_phase)
                emit({"type": "result", "status": result.status,
                      "bandwidth": result.bandwidth, "lower_bound": result.lower_bound,
                      "native_lower_bound": result.native_lower_bound,
                      "positions": result.positions,
                      "build_time": bounds_seconds + result.build_seconds,
                      "solve_time": result.solve_seconds})
        except Exception as exc:
            emit({"type": "error", "message": f"{type(exc).__name__}: {exc}"})
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
