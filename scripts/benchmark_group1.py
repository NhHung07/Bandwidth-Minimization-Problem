"""Benchmark bốn cấu hình SAT Nhóm 1 trên đủ 113 đồ thị BMP."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.benchmark_amo import FIELDS, append_row, check_manifest, load_completed
from scripts.benchmark_sat import read_events, stop_tree, tree_rss
from src.graph import list_instance_paths, load_graph
from src.verify import verify_solution


# Theo yêu cầu CSV chỉ có 12 cột, cột "cardinality" ghi tên đầy đủ của cấu
# hình; nếu chỉ ghi Product/Binomial thì không phân biệt được Repeated/Incremental.
CONFIGURATIONS = (
    ("Pairwise + Product + Repeated", "pairwise", "repeated", "product"),
    ("Pairwise + Product + Incremental", "pairwise", "incremental", "product"),
    ("Order + Repeated", "order", "repeated", "binomial"),
    ("Order + Incremental", "order", "incremental", "binomial"),
)


def run_case(path: Path, config: tuple[str, str, str, str], time_limit: float,
             memory_limit_gb: float) -> dict:
    """Chạy một cấu hình trong worker riêng, kiểm lại nghiệm trước khi ghi CSV."""
    graph = load_graph(path)
    baseline = verify_solution(graph, tuple(range(1, graph.n + 1)))
    label, encoding, method, cardinality = config
    row = dict(zip(FIELDS, (graph.name, graph.n, graph.m, label, "TIMEOUT", baseline,
                            0.0, 0.0, 0.0, 0, 0, 0), strict=True))

    with tempfile.TemporaryDirectory(prefix="bmp-group1-", ignore_cleanup_errors=True) as folder:
        events_path = Path(folder) / "events.jsonl"
        command = [sys.executable, str(ROOT / "scripts" / "benchmark_group1_worker.py"),
                   str(path), encoding, method, cardinality, str(events_path)]
        start = perf_counter()
        deadline = start + time_limit
        process = subprocess.Popen(
            command, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            start_new_session=os.name != "nt",
        )
        timed_out = stopped_for_memory = False
        while process.poll() is None:
            remaining = deadline - perf_counter()
            if remaining <= 0:
                timed_out = True
                stop_tree(process)
                break
            try:
                process.wait(timeout=min(0.25, remaining))
            except subprocess.TimeoutExpired:
                if tree_rss(process.pid) > memory_limit_gb * 1024**3:
                    stopped_for_memory = True
                    stop_tree(process)
                    break
        stopped_at = perf_counter()
        row["total_time"] = round(stopped_at - start, 6)
        events = read_events(events_path, deadline)

    try:
        active_phase = None
        saw_sat = proved_optimal = got_result = False
        for event in events:
            kind = event.get("type")
            if kind == "phase":
                phase = event["phase"]
                if phase == "build_start":
                    active_phase = ("build_time", event["at"])
                elif phase == "build_end":
                    row["build_time"] += event["seconds"]
                    row["num_vars"] = event["num_vars"]
                    row["num_clauses"] = event["num_clauses"]
                    active_phase = None
                elif phase == "solve_start":
                    row["sat_calls"] += 1
                    active_phase = ("solve_time", event["at"])
            elif kind == "trial":
                row["solve_time"] += event["solve_time"]
                active_phase = None
                if event["sat"]:
                    saw_sat = True
                    candidate = tuple(event["positions"])
                    actual = verify_solution(graph, candidate, event["bandwidth"])
                    row["bandwidth"] = min(row["bandwidth"], actual)
                    if actual == 0:
                        proved_optimal = True
                elif row["bandwidth"] == event["k"] + 1:
                    proved_optimal = True
            elif kind == "result":
                actual = verify_solution(graph, tuple(event["positions"]), event["bandwidth"])
                row["bandwidth"] = actual
                row["build_time"] = event["build_time"]
                row["solve_time"] = event["solve_time"]
                row["sat_calls"] = event["sat_calls"]
                row["num_vars"] = event["num_vars"]
                row["num_clauses"] = event["num_clauses"]
                active_phase = None
                got_result = proved_optimal = True
            elif kind == "error":
                raise RuntimeError(event.get("message", "worker lỗi"))

        if active_phase is not None and (timed_out or stopped_for_memory):
            field, phase_start = active_phase
            row[field] += max(0.0, min(deadline, stopped_at) - phase_start)
        row["status"] = "OPTIMAL" if proved_optimal else "FEASIBLE" if saw_sat else "TIMEOUT"
        if stopped_for_memory:
            row["status"] = "ERROR"
            print(f"Memory limit {memory_limit_gb:g} GiB: {graph.name} / {label}",
                  file=sys.stderr, flush=True)
        elif not got_result and not timed_out:
            row["status"] = "ERROR"
            print(f"Worker ended without result (exit {process.returncode}): {graph.name} / {label}",
                  file=sys.stderr, flush=True)
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        row["status"] = "ERROR"
        reason = str(exc).encode("ascii", "backslashreplace").decode()
        print(f"Invalid result: {graph.name} / {label}: {reason}", file=sys.stderr, flush=True)

    row["build_time"] = round(row["build_time"], 6)
    row["solve_time"] = round(row["solve_time"], 6)
    return row


def code_hash() -> str:
    """Băm thuật toán và mọi file thực thi mà lượt đo phụ thuộc."""
    digest = hashlib.sha256()
    sources = sorted((ROOT / "src").rglob("*.py"))
    sources += [ROOT / "scripts" / name for name in
                ("benchmark_sat.py", "benchmark_amo.py", "benchmark_group1.py",
                 "benchmark_group1_worker.py")]
    for path in sources:
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def manifest_for(paths: tuple[Path, ...], time_limit: float, memory_limit_gb: float) -> dict:
    data = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}
    return {"time_limit_seconds": time_limit, "memory_limit_gb": memory_limit_gb,
            "configurations": [label for label, *_ in CONFIGURATIONS],
            "python": platform.python_version(), "python_sat": version("python-sat"),
            "code_sha256": code_hash(), "data_sha256": data,
            "cpu": platform.processor(), "logical_cpus": os.cpu_count()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark Nhóm 1 trên 113 đồ thị BMP")
    parser.add_argument("--instances", nargs="+", type=Path, help="Chỉ chạy các file được chọn; mặc định đủ 113")
    parser.add_argument("--time-limit", type=float, default=120.0,
                        help="Giây cho mỗi cấu hình trên mỗi instance")
    parser.add_argument("--memory-limit-gb", type=float, default=8.0,
                        help="RAM tối đa cho worker; vượt hạn là ERROR")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results" / "data" / "group1_product_120s.csv")
    args = parser.parse_args(argv)
    if not (0 < args.time_limit < float("inf")) or not (0 < args.memory_limit_gb < float("inf")):
        parser.error("time-limit và memory-limit-gb phải dương, hữu hạn")
    selected = args.instances or list_instance_paths()
    paths = tuple((ROOT / path).resolve() if not path.is_absolute() else path.resolve()
                  for path in selected)
    if len(paths) != len(set(paths)) or any(not path.is_file() for path in paths):
        parser.error("instance bị lặp hoặc không tồn tại")
    output = (ROOT / args.output).resolve() if not args.output.is_absolute() else args.output.resolve()
    manifest = manifest_for(paths, args.time_limit, args.memory_limit_gb)
    check_manifest(output, manifest)
    done = load_completed(output)
    expected = len(paths) * len(CONFIGURATIONS)
    print(f"Start: {len(paths)} instances, {expected} cases; existing: {len(done)} rows; CSV: {output}",
          flush=True)
    for path in paths:
        for config in CONFIGURATIONS:
            if code_hash() != manifest["code_sha256"]:
                raise RuntimeError("Mã nguồn thay đổi trong lúc benchmark; dừng để tránh trộn kết quả")
            key = (path.name.removesuffix(".mtx.rnd"), config[0])
            if key in done:
                continue
            row = run_case(path, config, args.time_limit, args.memory_limit_gb)
            append_row(output, row)
            done.add((row["instance"], row["cardinality"]))
            print(f"{len(done)}/{expected} {row['instance']} | {row['cardinality']} | "
                  f"{row['status']} | B={row['bandwidth']} | {row['total_time']:.2f}s", flush=True)
    print(f"Done: {len(done)}/{expected} rows in {output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
