"""So sánh năm AMO với Pairwise + Incremental trên hb_33 hoặc hb_80."""

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


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.benchmark_sat import read_events, stop_tree, tree_rss
from src.graph import list_instance_paths, load_graph
from src.verify import verify_solution


FIELDS = ("instance", "n", "m", "cardinality", "status", "bandwidth",
          "total_time", "build_time", "solve_time", "num_vars", "num_clauses", "sat_calls")
CARDINALITIES = (
    ("Binomial", "binomial"),
    ("Binary", "binary"),
    ("Commander", "commander"),
    ("Product", "product"),
    ("Sequential", "sequential"),
)


def run_case(path: Path, cardinality: tuple[str, str], time_limit: float,
             memory_limit_gb: float) -> dict:
    """Chạy một AMO trong tiến trình riêng và kiểm nghiệm mọi nghiệm nhận được."""
    graph = load_graph(path)
    baseline = verify_solution(graph, tuple(range(1, graph.n + 1)))
    label, key = cardinality
    row = dict(zip(FIELDS, (graph.name, graph.n, graph.m, label, "TIMEOUT", baseline,
                            0.0, 0.0, 0.0, 0, 0, 0), strict=True))

    with tempfile.TemporaryDirectory(prefix="bmp-amo-", ignore_cleanup_errors=True) as folder:
        events_path = Path(folder) / "events.jsonl"
        command = [sys.executable, str(ROOT / "scripts" / "benchmark_amo_worker.py"),
                   str(path), key, str(events_path)]
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
                    # UNSAT ở k chứng minh nghiệm tốt nhất k+1 là tối ưu.
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


def load_completed(output: Path) -> set[tuple[str, str]]:
    """Chỉ tiếp tục những cặp instance/AMO chưa có trong CSV."""
    if not output.is_file() or output.stat().st_size == 0:
        return set()
    with output.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError("CSV hiện có không đúng 12 cột AMO yêu cầu")
        rows = list(reader)
    keys = [(row["instance"], row["cardinality"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("CSV hiện có cặp instance/AMO bị lặp")
    return set(keys)


def append_row(output: Path, row: dict) -> None:
    """Ghi và đồng bộ từng dòng để không mất các ca đã hoàn thành."""
    output.parent.mkdir(parents=True, exist_ok=True)
    fresh = not output.is_file() or output.stat().st_size == 0
    with output.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        if fresh:
            writer.writeheader()
        writer.writerow(row)
        stream.flush()
        os.fsync(stream.fileno())


def code_hash() -> str:
    """Băm mọi mã nguồn mà lượt AMO phụ thuộc vào."""
    digest = hashlib.sha256()
    sources = sorted((ROOT / "src").rglob("*.py"))
    sources += [ROOT / "scripts" / name for name in
                ("benchmark_sat.py", "benchmark_amo.py", "benchmark_amo_worker.py")]
    for path in sources:
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def manifest_for(paths: tuple[Path, ...], time_limit: float, memory_limit_gb: float) -> dict:
    """Ghi điều kiện thí nghiệm để cấm trộn các lượt chạy khác nhau."""
    data = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}
    return {"time_limit_seconds": time_limit, "memory_limit_gb": memory_limit_gb,
            "cardinalities": [label for label, _ in CARDINALITIES],
            "method": "pairwise+incremental", "python": platform.python_version(),
            "python_sat": version("python-sat"), "code_sha256": code_hash(),
            "data_sha256": data, "cpu": platform.processor(),
            "logical_cpus": os.cpu_count()}


def check_manifest(output: Path, expected: dict) -> None:
    manifest = output.with_suffix(".meta.json")
    if manifest.is_file():
        actual = json.loads(manifest.read_text(encoding="utf-8"))
        # Manifest gộp có thêm lịch sử những đợt chạy trước; chỉ các điều kiện
        # thí nghiệm hiện tại phải trùng, lịch sử phải được giữ nguyên.
        if any(actual.get(key) != value for key, value in expected.items()):
            raise ValueError(f"Điều kiện chạy khác {manifest}; hãy chọn CSV mới")
    elif output.is_file() and output.stat().st_size:
        raise ValueError(f"CSV đã tồn tại nhưng thiếu metadata: {manifest}")
    else:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark năm AMO bằng Pairwise + Incremental SAT")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--instances", nargs="+", type=Path,
                           help="Chọn file cụ thể; mặc định nhóm hb_33")
    selection.add_argument("--all", action="store_true",
                           help="Chạy cả 113 file trong thí nghiệm riêng")
    selection.add_argument("--hb80", action="store_true",
                           help="Chạy đúng 80 instance hb_80")
    parser.add_argument("--time-limit", type=float, default=120.0,
                        help="Giây cho mỗi AMO trên mỗi instance")
    parser.add_argument("--memory-limit-gb", type=float, default=8.0,
                        help="RAM tối đa cho worker; vượt hạn là ERROR")
    parser.add_argument("--output", type=Path,
                        help="CSV đầu ra; mặc định amo_hb80_120s.csv khi dùng --hb80")
    parser.add_argument("--max-cases", type=int,
                        help="Dừng sau N ca mới; chạy lại cùng lệnh để tiếp tục")
    args = parser.parse_args(argv)
    if not (0 < args.time_limit < float("inf")) or not (0 < args.memory_limit_gb < float("inf")):
        parser.error("time-limit và memory-limit-gb phải dương, hữu hạn")
    if args.max_cases is not None and args.max_cases < 1:
        parser.error("max-cases phải là số nguyên dương")
    selected = (args.instances or list_instance_paths(
        ROOT / "data" if args.all else ROOT / "data" / "hb_80" if args.hb80
        else ROOT / "data" / "hb_33"))
    paths = tuple((ROOT / path).resolve() if not path.is_absolute() else path.resolve()
                  for path in selected)
    if len(paths) != len(set(paths)) or any(not path.is_file() for path in paths):
        parser.error("instance bị lặp hoặc không tồn tại")
    default_name = ("amo_hb80_120s.csv" if args.hb80 else
                    "amo_all_120s.csv" if args.all else "amo_120s.csv")
    chosen_output = args.output or ROOT / "results" / "data" / default_name
    output = (ROOT / chosen_output).resolve() if not chosen_output.is_absolute() else chosen_output.resolve()
    manifest = manifest_for(paths, args.time_limit, args.memory_limit_gb)
    check_manifest(output, manifest)
    done = load_completed(output)
    expected = len(paths) * len(CARDINALITIES)
    print(f"Start: {len(paths)} instances, {expected} cases; existing: {len(done)} rows; CSV: {output}",
          flush=True)
    new_count = 0
    for path in paths:
        for cardinality in CARDINALITIES:
            if code_hash() != manifest["code_sha256"]:
                raise RuntimeError("Mã nguồn thay đổi trong lúc benchmark; dừng để tránh trộn kết quả")
            key = (path.name.removesuffix(".mtx.rnd"), cardinality[0])
            if key in done:
                continue
            row = run_case(path, cardinality, args.time_limit, args.memory_limit_gb)
            append_row(output, row)
            done.add((row["instance"], row["cardinality"]))
            print(f"{len(done)}/{expected} {row['instance']} | {row['cardinality']} | "
                  f"{row['status']} | B={row['bandwidth']} | {row['total_time']:.2f}s", flush=True)
            new_count += 1
            if args.max_cases is not None and new_count >= args.max_cases:
                return 0
    print(f"Done: {len(done)}/{expected} rows in {output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
