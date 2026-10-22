"""Read the project's ``.mtx.rnd`` edge lists as simple undirected graphs.

Vertex identifiers stay 1-based so they match the source files and paper.
The original graph size is retained, including isolated vertices and every
connected component. Self-loops do not affect bandwidth and are removed;
repeated or reversed copies of an edge are collapsed into one edge.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class GraphFormatError(ValueError):
    """The content of a ``.mtx.rnd`` file does not match its declared format."""


@dataclass(frozen=True, slots=True)
class Graph:
    """A normalized simple undirected graph from one benchmark instance.

    ``raw_edge_count`` is the number declared in the file. ``m`` is the number
    of distinct non-loop edges passed to every solver. The three counts obey
    ``raw_edge_count == m + duplicate_edge_count + self_loop_count``.
    """

    name: str
    n: int
    edges: tuple[tuple[int, int], ...]
    source_path: Path
    raw_edge_count: int
    duplicate_edge_count: int
    self_loop_count: int

    @property
    def m(self) -> int:
        """Number of edges after normalization."""
        return len(self.edges)


def list_instance_paths(data_dir: str | Path | None = None) -> tuple[Path, ...]:
    """Return all ``.mtx.rnd`` files under ``data_dir`` in stable order.

    Without an argument, the repository's ``data/`` directory is used.
    """
    root = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parents[1] / "data"
    if not root.is_dir():
        raise FileNotFoundError(f"Dataset directory does not exist: {root}")
    return tuple(sorted(root.rglob("*.mtx.rnd")))


def load_graph(path: str | Path) -> Graph:
    """Parse a ``.mtx.rnd`` file and normalize its edges.

    Expected lines: ``Nombre del problema: <filename>``, ``n n m``, then
    exactly ``m`` lines with two 1-based vertex identifiers. Malformed input
    raises :class:`GraphFormatError` with a filename and line number.
    """
    source = Path(path).resolve()

    def invalid(line_number: int, message: str) -> GraphFormatError:
        return GraphFormatError(f"{source}:{line_number}: {message}")

    with source.open("r", encoding="utf-8-sig") as stream:
        first_line = stream.readline().strip()
        prefix = "Nombre del problema:"
        if not first_line.startswith(prefix):
            raise invalid(1, f"expected '{prefix} <filename>'")
        declared_filename = first_line[len(prefix) :].strip()
        if declared_filename != source.name:
            raise invalid(1, f"declared filename {declared_filename!r} differs from {source.name!r}")

        header = stream.readline().split()
        if len(header) != 3:
            raise invalid(2, "expected three integers: n n m")
        try:
            rows, columns, raw_edge_count = (int(value) for value in header)
        except ValueError as exc:
            raise invalid(2, "n, n and m must be integers") from exc
        if rows < 1 or columns != rows or raw_edge_count < 0:
            raise invalid(2, "expected a positive square graph size and a nonnegative edge count")

        edges: set[tuple[int, int]] = set()
        seen_lines = duplicate_edge_count = self_loop_count = 0
        for line_number, line in enumerate(stream, start=3):
            seen_lines += 1
            if seen_lines > raw_edge_count:
                raise invalid(line_number, f"more than {raw_edge_count} edge lines")
            parts = line.split()
            if len(parts) != 2:
                raise invalid(line_number, "expected two vertex identifiers")
            try:
                u, v = (int(value) for value in parts)
            except ValueError as exc:
                raise invalid(line_number, "vertex identifiers must be integers") from exc
            if not (1 <= u <= rows and 1 <= v <= rows):
                raise invalid(line_number, f"vertices must be in 1..{rows}")
            if u == v:
                self_loop_count += 1
                continue
            edge = (min(u, v), max(u, v))
            if edge in edges:
                duplicate_edge_count += 1
            else:
                edges.add(edge)

        if seen_lines != raw_edge_count:
            raise invalid(seen_lines + 3, f"expected {raw_edge_count} edge lines, found {seen_lines}")

    return Graph(
        name=source.name.removesuffix(".mtx.rnd"),
        n=rows,
        edges=tuple(sorted(edges)),
        source_path=source,
        raw_edge_count=raw_edge_count,
        duplicate_edge_count=duplicate_edge_count,
        self_loop_count=self_loop_count,
    )
