"""Chạy bốn cấu hình SAT trên 113 instance, mặc định 180 giây/cấu hình."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from importlib.metadata import version
from time import perf_counter

import psutil


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.graph import list_instance_paths, load_graph
from src.verify import verify_solution


FIELDS = ("instance", "n", "m", "configuration", "status", "bandwidth",
          "total_time", "build_time", "solve_time", "sat_calls", "num_vars", "num_clauses")
CONFIGURATIONS = (
    ("Pairwise + Binomial + Repeated", "pairwise", "repeated"),
    ("Pairwise + Binomial + Incremental", "pairwise", "incremental"),
    ("Order + Repeated", "order", "repeated"),
    ("Order + Incremental", "order", "incremental"),
)


def stop_tree(process: subprocess.Popen) -> None:
    """Dừng worker và mọi tiến trình con của nó khi hết thời gian hoặc RAM."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    process.wait()


def tree_rss(pid: int) -> int:
    """Tính RAM của worker và con/cháu, không tính Python điều phối."""
    try:
        parent = psutil.Process(pid)
        processes = [parent, *parent.children(recursive=True)]
        return sum(proc.memory_info().rss for proc in processes if proc.is_running())
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0


def read_events(path: Path, deadline: float) -> list[dict]:
    """Bỏ dòng JSON viết dở nếu worker bị dừng giữa lúc ghi."""
    if not path.is_file():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("at", float("inf")) <= deadline:
            events.append(event)
    return events


def run_case(path: Path, config: tuple[str, str, str], time_limit: float,
             memory_limit_gb: float) -> dict:
    """Chạy một cấu hình trong tiến trình riêng và kiểm lại mọi nghiệm SAT."""
    graph = load_graph(path)
    baseline_positions = tuple(range(1, graph.n + 1))
    baseline = verify_solution(graph, baseline_positions)
    label, encoding, method = config
    row = dict(zip(FIELDS, (graph.name, graph.n, graph.m, label, "TIMEOUT", baseline,
                            0.0, 0.0, 0.0, 0, 0, 0), strict=True))

    with tempfile.TemporaryDirectory(prefix="bmp-sat-", ignore_cleanup_errors=True) as folder:
        events_path = Path(folder) / "events.jsonl"
        command = [sys.executable, str(ROOT / "scripts" / "benchmark_sat_worker.py"),
                   str(path), method, encoding, str(events_path)]
        start = perf_counter()
        deadline = start + time_limit
        process = subprocess.Popen(
            command, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            start_new_session=os.name != "nt",
        )
        stopped_for_memory = False
        timed_out = False
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
        saw_sat = False
        proved_optimal = False
        got_result = False
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
                    positions = tuple(event["positions"])
                    actual = verify_solution(graph, positions, event["bandwidth"])
                    row["bandwidth"] = min(row["bandwidth"], actual)
                    if actual == 0:
                        proved_optimal = True
                elif row["bandwidth"] == event["k"] + 1:
                    # SAT ở k+1 và UNSAT ở k là chứng cứ tối ưu.
                    proved_optimal = True
            elif kind == "result":
                verified = verify_solution(graph, tuple(event["positions"]), event["bandwidth"])
                row["bandwidth"] = verified
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
            print(f"Memory limit {memory_limit_gb:g} GiB: {graph.name} / {label}", file=sys.stderr, flush=True)
        elif not got_result and not timed_out:
            row["status"] = "ERROR"
            print(f"Worker ended without result (exit {process.returncode}): {graph.name} / {label}",
                  file=sys.stderr, flush=True)
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        row["status"] = "ERROR"
        print(f"Invalid result: {graph.name} / {label}: {str(exc).encode('ascii', 'backslashreplace').decode()}",
              file=sys.stderr, flush=True)

    for name in ("build_time", "solve_time"):
        row[name] = round(row[name], 6)
    return row


def load_completed(output: Path) -> set[tuple[str, str]]:
    """Tiếp tục từ CSV cũ; không ghi trùng cặp instance/cấu hình."""
    if not output.is_file() or output.stat().st_size == 0:
        return set()
    with output.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError("CSV hiện có không đúng 12 cột yêu cầu")
        rows = list(reader)
    keys = [(row["instance"], row["configuration"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("CSV hiện có cặp instance/cấu hình bị lặp")
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


def code_hash() -> str:
    """Băm các file thuật toán và bộ chạy đang dùng."""
    code = hashlib.sha256()
    sources = sorted((ROOT / "src").rglob("*.py"))
    sources += [ROOT / "scripts" / "benchmark_sat.py", ROOT / "scripts" / "benchmark_sat_worker.py"]
    for path in sources:
        code.update(path.relative_to(ROOT).as_posix().encode())
        code.update(path.read_bytes())
    return code.hexdigest()


def manifest_for(paths: tuple[Path, ...], time_limit: float, memory_limit_gb: float) -> dict:
    """Khóa dữ liệu, mã nguồn và giới hạn để không trộn các lượt đo khác nhau."""
    data = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}
    return {"time_limit_seconds": time_limit, "memory_limit_gb": memory_limit_gb,
            "configurations": [config[0] for config in CONFIGURATIONS],
            "python": platform.python_version(), "python_sat": version("python-sat"),
            "code_sha256": code_hash(), "data_sha256": data,
            "cpu": platform.processor(), "logical_cpus": os.cpu_count()}


def check_manifest(output: Path, expected: dict) -> None:
    """Tạo metadata một lần; lượt chạy tiếp phải dùng cùng điều kiện."""
    manifest = output.with_suffix(".meta.json")
    if manifest.is_file():
        actual = json.loads(manifest.read_text(encoding="utf-8"))
        if actual != expected:
            raise ValueError(f"Điều kiện chạy khác {manifest}; hãy chọn CSV mới")
    elif output.is_file() and output.stat().st_size:
        raise ValueError(f"CSV đã tồn tại nhưng thiếu metadata: {manifest}")
    else:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark 4 cấu hình SAT trên bộ BMP Harwell–Boeing")
    parser.add_argument("--instances", nargs="+", type=Path, help="File dữ liệu cần chạy; mặc định đủ 113 file")
    parser.add_argument("--time-limit", type=float, default=180.0, help="Giây cho mỗi cấu hình/instance")
    parser.add_argument("--memory-limit-gb", type=float, default=8.0,
                        help="RAM tối đa của một worker; vượt hạn sẽ báo ERROR")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "data" / "sat_180s.csv")
    args = parser.parse_args(argv)
    if not (0 < args.time_limit < float("inf")) or not (0 < args.memory_limit_gb < float("inf")):
        parser.error("time-limit và memory-limit-gb phải dương, hữu hạn")
    paths = tuple((ROOT / path).resolve() if not path.is_absolute() else path.resolve()
                  for path in (args.instances or list_instance_paths()))
    if len(paths) != len(set(paths)) or any(not path.is_file() for path in paths):
        parser.error("instance bị lặp hoặc không tồn tại")
    output = (ROOT / args.output).resolve() if not args.output.is_absolute() else args.output.resolve()
    manifest = manifest_for(paths, args.time_limit, args.memory_limit_gb)
    check_manifest(output, manifest)
    done = load_completed(output)
    expected = len(paths) * len(CONFIGURATIONS)
    print(f"Start: {len(paths)} instances, {expected} cases; existing: {len(done)} rows; CSV: {output}", flush=True)
    for path in paths:
        for config in CONFIGURATIONS:
            if code_hash() != manifest["code_sha256"]:
                raise RuntimeError("Mã nguồn thay đổi trong lúc benchmark; đã dừng trước khi trộn kết quả")
            if (path.name.removesuffix(".mtx.rnd"), config[0]) in done:
                continue
            row = run_case(path, config, args.time_limit, args.memory_limit_gb)
            append_row(output, row)
            done.add((row["instance"], row["configuration"]))
            print(f"{len(done)}/{expected} {row['instance']} | {row['configuration']} | "
                  f"{row['status']} | B={row['bandwidth']} | {row['total_time']:.2f}s", flush=True)
    print(f"Done: {len(done)}/{expected} rows in {output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
