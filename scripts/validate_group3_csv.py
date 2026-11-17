"""Kiểm tra cấu trúc và tính nhất quán của CSV nghiệm thu Nhóm 3."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.benchmark_group3 import FIELDS, METHODS
from src.graph import list_instance_paths, load_graph
from src.graph_bounds import compute_graph_bounds


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", nargs="?", type=Path,
                        default=ROOT / "results" / "data" / "group3_120s.csv")
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--check-graph-bound", action="store_true",
                        help="Kiểm tra cận dưới đã bao gồm cận đồ thị của benchmark mới")
    args = parser.parse_args()

    graphs = {graph.name: graph for graph in map(load_graph, list_instance_paths())}
    known_methods = {name for name, _ in METHODS}
    with args.csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError("CSV phải có đúng 12 cột Nhóm 3 theo đúng thứ tự")
        rows = list(reader)

    seen = set()
    for line, row in enumerate(rows, start=2):
        key = row["instance"], row["method"]
        if key in seen or key[0] not in graphs or key[1] not in known_methods:
            raise ValueError(f"Dòng {line}: instance/phương pháp lạ hoặc trùng")
        seen.add(key)
        graph = graphs[key[0]]
        if (int(row["n"]), int(row["m"])) != (graph.n, graph.m):
            raise ValueError(f"Dòng {line}: n,m không khớp dữ liệu")
        if row["status"] not in {"OPTIMAL", "FEASIBLE", "TIMEOUT", "ERROR"}:
            raise ValueError(f"Dòng {line}: trạng thái không hợp lệ")

        bandwidth = int(row["bandwidth"]) if row["bandwidth"] != "" else None
        bound = float(row["lower_bound"]) if row["lower_bound"] != "" else None
        if args.check_graph_bound and (bound is None or bound + 1e-5 < compute_graph_bounds(graph).strongest):
            raise ValueError(f"Dòng {line}: cận dưới thấp hơn cận đồ thị")
        gap = float(row["gap"]) if row["gap"] != "" else None
        if bandwidth is not None and not 0 <= bandwidth < graph.n:
            raise ValueError(f"Dòng {line}: bandwidth ngoài khoảng 0..n-1")
        if row["status"] in {"OPTIMAL", "FEASIBLE"} and bandwidth is None:
            raise ValueError(f"Dòng {line}: có nghiệm nhưng thiếu bandwidth")
        if row["status"] == "TIMEOUT" and bandwidth is not None:
            raise ValueError(f"Dòng {line}: TIMEOUT nhưng có nghiệm")
        if row["status"] == "OPTIMAL" and (bound is None or abs(bound - bandwidth) > 1e-5):
            raise ValueError(f"Dòng {line}: OPTIMAL nhưng không có cận dưới bằng bandwidth")
        if (bandwidth is None or bound is None) != (gap is None):
            raise ValueError(f"Dòng {line}: gap không khớp dữ liệu")
        if gap is not None and (bound > bandwidth + 1e-5 or abs(gap - (bandwidth - bound)) > 1e-5):
            raise ValueError(f"Dòng {line}: cận dưới hoặc gap không hợp lệ")
        for field in ("total_time", "build_time", "solve_time", "peak_ram_mb"):
            value = float(row[field])
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"Dòng {line}: {field} không hợp lệ")
        if float(row["build_time"]) + float(row["solve_time"]) > float(row["total_time"]) + 1:
            raise ValueError(f"Dòng {line}: tổng build/solve lớn hơn thời gian thực")

    expected = len(graphs) * len(METHODS)
    if not args.allow_partial and len(rows) != expected:
        raise ValueError(f"Cần {expected} dòng, hiện có {len(rows)}")
    print(f"Valid: {len(rows)}/{expected} rows; statuses: {dict(Counter(row['status'] for row in rows))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
