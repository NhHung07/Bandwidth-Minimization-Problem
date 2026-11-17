"""Cận dưới hợp lệ của bandwidth: bậc, lân cận và clique."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .graph import Graph


@dataclass(frozen=True, slots=True)
class GraphBounds:
    """Ba cận dưới độc lập; cận mạnh nhất là giá trị lớn nhất."""

    degree: int
    neighborhood: int
    clique: int

    @property
    def strongest(self) -> int:
        return max(self.degree, self.neighborhood, self.clique)


@lru_cache(maxsize=1)
def compute_graph_bounds(graph: Graph, max_radius: int = 3) -> GraphBounds:
    """Tính cận bậc, quả cầu bán kính 1..3 và clique tham lam.

    Thứ tự chọn đỉnh và tiêu chí chọn clique giống bản thử CP; bitset chỉ
    thay cách biểu diễn tập ứng viên, không thay bất đẳng thức dùng làm cận.
    """
    if max_radius < 1:
        raise ValueError("max_radius phải >= 1")
    neighbors: list[set[int]] = [set() for _ in range(graph.n + 1)]
    masks = [0] * (graph.n + 1)
    for u, v in graph.edges:
        neighbors[u].add(v)
        neighbors[v].add(u)
        masks[u] |= 1 << v
        masks[v] |= 1 << u
    degrees = [len(neighbors[v]) for v in range(graph.n + 1)]
    degree_bound = (max(degrees, default=0) + 1) // 2

    neighborhood_bound = 0
    for start in range(1, graph.n + 1):
        visited = {start}
        frontier = {start}
        for radius in range(1, max_radius + 1):
            frontier = set().union(*(neighbors[v] for v in frontier)) - visited
            if not frontier:
                break
            visited.update(frontier)
            candidate = (len(visited) - 1 + 2 * radius - 1) // (2 * radius)
            neighborhood_bound = max(neighborhood_bound, candidate)

    clique_size = 1
    vertices = sorted(range(1, graph.n + 1), key=lambda v: (-degrees[v], v))
    for start in vertices:
        candidates = masks[start]
        size = 1
        while candidates:
            current = candidates
            best_vertex = 0
            best_key = (-1, -1, -graph.n - 1)
            while current:
                bit = current & -current
                vertex = bit.bit_length() - 1
                key = ((candidates & masks[vertex]).bit_count(), degrees[vertex], -vertex)
                if key > best_key:
                    best_key = key
                    best_vertex = vertex
                current ^= bit
            size += 1
            candidates &= masks[best_vertex]
        clique_size = max(clique_size, size)

    return GraphBounds(degree_bound, neighborhood_bound, clique_size - 1)
