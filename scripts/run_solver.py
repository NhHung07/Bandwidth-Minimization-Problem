"""Chạy một solver đối chiếu trên một file BMP để kiểm tra thủ công."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


# Khi chạy trực tiếp file scripts/run_solver.py, cần thêm gốc dự án cho import.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Đổi dòng này nếu muốn nút Run Python File chạy một instance thật khác.
DEFAULT_INSTANCE = "data/hb_33/pores_1.mtx.rnd"

from src.graph import load_graph
from src.solvers.cplex_cp import solve_cplex_cp
from src.solvers.cplex_mip import solve_cplex_mip
from src.solvers.cpsat import solve_cpsat
from src.solvers.gurobi import solve_gurobi


SOLVERS = {
    "cpsat": solve_cpsat,
    "cplex_cp": solve_cplex_cp,
    "cplex_mip": solve_cplex_mip,
    "gurobi": solve_gurobi,
}


def main(argv: list[str] | None = None) -> int:
    """Chọn solver, đọc đồ thị, chạy và in kết quả đã được verify."""
    parser = argparse.ArgumentParser(description="Solve one BMP instance with a CP/MIP solver.")
    parser.add_argument("method", nargs="?", choices=SOLVERS, default="cpsat")
    parser.add_argument("instance", nargs="?", default=DEFAULT_INSTANCE)
    parser.add_argument("--time-limit", type=float, default=100.0, help="Solver time limit in seconds (default: 100)")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args(argv)
    path = Path(args.instance)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        parser.error(f"data file not found: {path}")

    graph = load_graph(path)
    result = SOLVERS[args.method](graph, time_limit=args.time_limit, workers=args.workers)
    # Dùng chữ ASCII khi in vì terminal Windows có thể dùng bảng mã cp1258.
    print(f"Data: {path} (n={graph.n}, m={graph.m})")
    print(f"Method: {result.method}; status: {result.status}")
    print(f"Bandwidth: {result.bandwidth}; lower bound: {result.lower_bound}")
    print(f"Vertex positions (1..n): {result.positions}")
    print(f"Build: {result.build_seconds:.3f}s; solve: {result.solve_seconds:.3f}s; total: {result.total_seconds:.3f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
