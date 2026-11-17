"""Worker cho một cấu hình SAT Nhóm 1, ghi tiến độ từng ngưỡng k."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.graph import load_graph
from src.search.incremental import optimize_incremental
from src.search.repeated import optimize_repeated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("instance", type=Path)
    parser.add_argument("encoding", choices=("pairwise", "order"))
    parser.add_argument("method", choices=("repeated", "incremental"))
    parser.add_argument("cardinality", choices=("product", "binomial"))
    parser.add_argument("events", type=Path)
    args = parser.parse_args()
    if args.encoding == "order" and args.cardinality != "binomial":
        parser.error("Order không dùng AMO Product")

    with args.events.open("a", encoding="utf-8", buffering=1) as stream:
        def emit(event: dict) -> None:
            event["at"] = perf_counter()
            stream.write(json.dumps(event, allow_nan=False) + "\n")
            stream.flush()

        def on_phase(phase: str, k: int, seconds: float, variables: int | None, clauses: int | None) -> None:
            emit({"type": "phase", "phase": phase, "k": k, "seconds": seconds,
                  "num_vars": variables, "num_clauses": clauses})

        def on_trial(trial, positions) -> None:
            emit({"type": "trial", "k": trial.k, "sat": trial.satisfiable,
                  "bandwidth": trial.bandwidth, "positions": positions,
                  "solve_time": trial.solve_seconds})

        try:
            graph = load_graph(args.instance)
            optimize = {"repeated": optimize_repeated,
                        "incremental": optimize_incremental}[args.method]
            result = optimize(graph, args.encoding, on_trial=on_trial,
                              cardinality=args.cardinality, on_phase=on_phase)
            emit({"type": "result", "bandwidth": result.bandwidth,
                  "positions": result.positions, "build_time": result.build_seconds,
                  "solve_time": result.solve_seconds, "sat_calls": result.sat_calls,
                  "num_vars": result.trials[-1].num_variables,
                  "num_clauses": result.trials[-1].num_clauses})
        except Exception as exc:
            emit({"type": "error", "message": f"{type(exc).__name__}: {exc}"})
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
