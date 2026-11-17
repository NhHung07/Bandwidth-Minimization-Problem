"""Kiểm tra 12 cột và đủ 4 × 113 dòng của benchmark SAT Nhóm 1."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from time import sleep

import psutil


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.benchmark_group1 import CONFIGURATIONS, FIELDS
from src.graph import list_instance_paths, load_graph


def validate(output: Path, partial: bool = False) -> dict:
    manifest = json.loads(output.with_suffix(".meta.json").read_text(encoding="utf-8"))
    with output.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError("CSV không có đúng 12 cột yêu cầu")
        rows = list(reader)

    paths = list_instance_paths()
    parsed = [load_graph(path) for path in paths]
    graphs = {graph.name: graph for graph in parsed}
    expected = {(name, label) for name in graphs for label, *_ in CONFIGURATIONS}
    seen = set()
    for index, row in enumerate(rows, start=2):
        key = (row["instance"], row["cardinality"])
        if key not in expected or key in seen:
            raise ValueError(f"Dòng {index}: instance/cấu hình lạ hoặc lặp: {key}")
        seen.add(key)
        graph = graphs[key[0]]
        if int(row["n"]) != graph.n or int(row["m"]) != graph.m:
            raise ValueError(f"Dòng {index}: n,m không khớp dữ liệu")
        if row["status"] not in ("OPTIMAL", "FEASIBLE", "TIMEOUT", "ERROR"):
            raise ValueError(f"Dòng {index}: trạng thái không hợp lệ")
        bandwidth = int(row["bandwidth"])
        if not 0 <= bandwidth < graph.n:
            raise ValueError(f"Dòng {index}: bandwidth ngoài miền")
        total = float(row["total_time"])
        build = float(row["build_time"])
        solve = float(row["solve_time"])
        if min(total, build, solve) < 0 or build + solve > total + 0.05:
            raise ValueError(f"Dòng {index}: thời gian không nhất quán")
        if min(int(row["num_vars"]), int(row["num_clauses"]), int(row["sat_calls"])) < 0:
            raise ValueError(f"Dòng {index}: số đếm âm")

    if manifest["time_limit_seconds"] != 120.0:
        raise ValueError("CSV không dùng thời hạn 120 giây")
    if manifest["configurations"] != [label for label, *_ in CONFIGURATIONS]:
        raise ValueError("Danh sách cấu hình trong metadata không khớp")
    for path in paths:
        source = path.relative_to(ROOT).as_posix()
        if manifest["data_sha256"].get(source) != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError(f"Dữ liệu thay đổi: {source}")
    missing = expected - seen
    if missing and not partial:
        raise ValueError(f"Còn thiếu {len(missing)} trong {len(expected)} lượt")
    return {"rows": len(rows), "expected": len(expected), "missing": len(missing),
            "statuses": dict(Counter(row["status"] for row in rows)),
            "time_limit_seconds": manifest["time_limit_seconds"],
            "memory_limit_gb": manifest["memory_limit_gb"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results" / "data" / "group1_product_120s.csv")
    parser.add_argument("--partial", action="store_true")
    parser.add_argument("--wait-pid", type=int, help="Chờ benchmark kết thúc")
    parser.add_argument("--summary", type=Path, help="Ghi báo cáo kiểm tra vào JSON")
    args = parser.parse_args()
    if args.wait_pid is not None:
        try:
            process = psutil.Process(args.wait_pid)
            born = process.create_time()
            while psutil.pid_exists(args.wait_pid) and psutil.Process(args.wait_pid).create_time() == born:
                sleep(15)
        except psutil.NoSuchProcess:
            pass
    summary = json.dumps(validate(args.output.resolve(), args.partial), ensure_ascii=True, indent=2)
    if args.summary is not None:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(summary + "\n", encoding="utf-8")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
