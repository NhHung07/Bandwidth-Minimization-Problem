"""Nghiệm thu năm phương pháp Nhóm 3 trên 113 đồ thị, 120 giây mỗi lượt."""

from __future__ import annotations

import argparse
import csv
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from results.benchmark.benchmark_sat import read_events, stop_tree, tree_rss
from src.graph import list_instance_paths, load_graph
from src.graph_bounds import compute_graph_bounds
from src.verify import verify_solution


FIELDS = ("instance", "n", "m", "method", "status", "bandwidth", "lower_bound",
          "gap", "total_time", "build_time", "solve_time", "peak_ram_mb")
METHODS = (("Pairwise + Product + Incremental", "sat"), ("CP", "cp"),
           ("MIP", "mip"), ("CP-SAT", "cp_sat"), ("Gurobi", "gurobi"))


def run_case(path: Path, method: tuple[str, str], time_limit: float,
             memory_limit_gb: float) -> tuple[dict, str | None]:
    """Chạy worker độc lập, kiểm nghiệm nghiệm và đo thời gian/RAM thực."""
    graph = load_graph(path)
    label, key = method
    row = dict.fromkeys(FIELDS, "")
    row.update(instance=graph.name, n=graph.n, m=graph.m, method=label,
               status="TIMEOUT", total_time=0.0, build_time=0.0,
               solve_time=0.0, peak_ram_mb=0.0)

    with tempfile.TemporaryDirectory(prefix="bmp-group3-", ignore_cleanup_errors=True) as folder:
        events_path = Path(folder) / "events.jsonl"
        started_at = perf_counter()
        deadline = started_at + time_limit
        command = [sys.executable, str(ROOT / "results" / "benchmark" / "benchmark_group3_worker.py"),
                   str(path), key, str(deadline), str(events_path)]
        process = subprocess.Popen(
            command, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            start_new_session=os.name != "nt",
        )
        timed_out = memory_error = False
        peak_bytes = tree_rss(process.pid)
        while process.poll() is None:
            remaining = deadline - perf_counter()
            if remaining <= 0:
                timed_out = True
                stop_tree(process)
                break
            try:
                process.wait(timeout=min(0.25, remaining))
            except subprocess.TimeoutExpired:
                rss = tree_rss(process.pid)
                peak_bytes = max(peak_bytes, rss)
                if rss > memory_limit_gb * 1024**3:
                    memory_error = True
                    stop_tree(process)
                    break
        stopped_at = perf_counter()
        row["total_time"] = round(stopped_at - started_at, 6)
        row["peak_ram_mb"] = round(peak_bytes / 1024**2, 2)
        events = read_events(events_path, deadline)

    reason = None
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
                    active_phase = None
                elif phase == "solve_start":
                    active_phase = ("solve_time", event["at"])
            elif kind == "bounds":
                row["lower_bound"] = int(event["lower_bound"])
            elif kind == "trial":
                row["solve_time"] += event["solve_time"]
                active_phase = None
                if event["sat"]:
                    saw_sat = True
                    actual = verify_solution(graph, tuple(event["positions"]), event["bandwidth"])
                    row["bandwidth"] = (min(row["bandwidth"], actual)
                                        if row["bandwidth"] != "" else actual)
                    if actual == row["lower_bound"]:
                        proved_optimal = True
                elif row["bandwidth"] != "" and row["bandwidth"] == event["k"] + 1:
                    proved_optimal = True
                    row["lower_bound"] = row["bandwidth"]
            elif kind == "result":
                positions = event["positions"]
                if positions is not None:
                    row["bandwidth"] = verify_solution(
                        graph, tuple(positions), event["bandwidth"])
                elif event["bandwidth"] is not None:
                    raise ValueError("Có bandwidth nhưng không có hoán vị")
                if event["lower_bound"] is not None:
                    row["lower_bound"] = max(float(row["lower_bound"] or 0), float(event["lower_bound"]))
                row["build_time"] = event["build_time"]
                row["solve_time"] = event["solve_time"]
                row["status"] = event["status"]
                got_result = True
                active_phase = None
            elif kind == "error":
                raise RuntimeError(event.get("message", "worker error"))

        if active_phase is not None and (timed_out or memory_error):
            field, phase_start = active_phase
            row[field] += max(0.0, min(deadline, stopped_at) - phase_start)
        if not got_result:
            row["status"] = "OPTIMAL" if proved_optimal else "FEASIBLE" if saw_sat else "TIMEOUT"
            if proved_optimal:
                row["lower_bound"] = row["bandwidth"]
        if row["lower_bound"] == "":
            # Worker có thể bị dừng ngay khi đang tính cận; vẫn ghi cận hợp lệ.
            row["lower_bound"] = compute_graph_bounds(graph).strongest
        else:
            graph_bound = compute_graph_bounds(graph).strongest
            if row["lower_bound"] < graph_bound:
                raise ValueError("Cận dưới worker thấp hơn cận đồ thị")
        if row["bandwidth"] != "" and row["bandwidth"] == row["lower_bound"]:
            row["status"] = "OPTIMAL"
        if memory_error:
            row["status"] = "ERROR"
            reason = f"Worker vượt {memory_limit_gb:g} GiB RAM"
        elif not got_result and not timed_out:
            row["status"] = "ERROR"
            reason = f"Worker dừng không có kết quả (exit {process.returncode})"
        if row["bandwidth"] != "" and row["lower_bound"] != "":
            gap = row["bandwidth"] - float(row["lower_bound"])
            if gap < -1e-5:
                raise ValueError("Cận dưới lớn hơn bandwidth")
            row["gap"] = round(max(0.0, gap), 6)
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        row["status"] = "ERROR"
        reason = f"Kết quả không hợp lệ: {type(exc).__name__}: {exc}"

    row["build_time"] = round(row["build_time"], 6)
    row["solve_time"] = round(row["solve_time"], 6)
    return row, reason


def code_hash() -> str:
    digest = hashlib.sha256()
    sources = sorted((ROOT / "src").rglob("*.py"))
    sources += [ROOT / "results" / "benchmark" / name for name in
                ("benchmark_sat.py", "benchmark_group3.py", "benchmark_group3_worker.py")]
    for path in sources:
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def manifest_for(paths: tuple[Path, ...], time_limit: float, memory_limit_gb: float) -> dict:
    return {
        "time_limit_seconds": time_limit, "memory_limit_gb": memory_limit_gb,
        "workers_per_solver": 1, "methods": [name for name, _ in METHODS],
        "graph_bound": "max(degree, neighborhood_radius_1_to_3, greedy_clique)",
        "mip_parameters": {"gurobi_MIPFocus": 3, "cplex_MIPEMphasis_BESTBOUND": 3},
        "python": platform.python_version(),
        "packages": {name: version(name) for name in ("python-sat", "ortools", "docplex", "cplex", "gurobipy")},
        "code_sha256": code_hash(),
        "data_sha256": {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in paths},
        "cpu": platform.processor(), "logical_cpus": os.cpu_count(),
    }


def completed_keys(output: Path) -> set[tuple[str, str]]:
    if not output.is_file() or output.stat().st_size == 0:
        return set()
    with output.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError("CSV có cấu trúc cột khác Nhóm 3")
        rows = list(reader)
    keys = [(row["instance"], row["method"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("CSV có cặp instance/phương pháp trùng")
    return set(keys)


def append_row(output: Path, row: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    new_file = not output.is_file() or output.stat().st_size == 0
    with output.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)
        stream.flush()
        os.fsync(stream.fileno())


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark 5 phương pháp Nhóm 3 trên 113 đồ thị")
    parser.add_argument("--instances", nargs="+", type=Path,
                        help="Chạy một số file được chọn; mặc định đủ 113")
    parser.add_argument("--time-limit", type=float, default=120.0)
    parser.add_argument("--memory-limit-gb", type=float, default=8.0)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "data" / "group3_official_strong_lb_120s.csv")
    parser.add_argument("--max-cases", type=int, help="Dừng sau N ca mới để kiểm tra rồi tiếp tục")
    args = parser.parse_args()
    if not (0 < args.time_limit < float("inf")) or not (0 < args.memory_limit_gb < float("inf")):
        parser.error("time-limit và memory-limit-gb phải dương và hữu hạn")
    selected = args.instances or list_instance_paths()
    paths = tuple((ROOT / path).resolve() if not path.is_absolute() else path.resolve()
                  for path in selected)
    if len(paths) != len(set(paths)) or any(not path.is_file() for path in paths):
        parser.error("instance bị lặp hoặc không tồn tại")
    output = (ROOT / args.output).resolve() if not args.output.is_absolute() else args.output.resolve()
    historical = (ROOT / "results" / "data" / "group3_120s.csv").resolve()
    if output == historical:
        parser.error("Giữ nguyên CSV lịch sử group3_120s.csv; hãy chọn file output mới")
    manifest_path = output.with_suffix(".meta.json")
    manifest = manifest_for(paths, args.time_limit, args.memory_limit_gb)
    if manifest_path.is_file():
        if json.loads(manifest_path.read_text(encoding="utf-8")) != manifest:
            parser.error(f"Điều kiện chạy khác manifest: {manifest_path}")
    elif output.is_file() and output.stat().st_size:
        parser.error(f"CSV có sẵn nhưng thiếu manifest: {manifest_path}")
    else:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    done = completed_keys(output)
    expected = len(paths) * len(METHODS)
    print(f"Start: {len(paths)} instances, {expected} cases, existing {len(done)} rows; CSV {output}", flush=True)
    new_count = 0
    for path in paths:
        for method in METHODS:
            if (path.name.removesuffix(".mtx.rnd"), method[0]) in done:
                continue
            if code_hash() != manifest["code_sha256"]:
                raise RuntimeError("Mã nguồn thay đổi trong lúc benchmark")
            row, reason = run_case(path, method, args.time_limit, args.memory_limit_gb)
            append_row(output, row)
            if reason:
                error_path = output.with_suffix(".errors.jsonl")
                with error_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps({"instance": row["instance"], "method": row["method"],
                                             "reason": reason}, ensure_ascii=False) + "\n")
                print(f"ERROR {row['instance']} / {row['method']}: {reason}", file=sys.stderr, flush=True)
            done.add((row["instance"], row["method"]))
            new_count += 1
            print(f"{len(done)}/{expected} {row['instance']} | {row['method']} | {row['status']} | "
                  f"B={row['bandwidth'] or '-'} | {row['total_time']:.2f}s | "
                  f"RAM={row['peak_ram_mb']:.0f} MiB", flush=True)
            if args.max_cases is not None and new_count >= args.max_cases:
                return 0
    print(f"Done: {len(done)}/{expected} rows in {output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
