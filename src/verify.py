"""Independently check BMP solutions returned by any SAT, CP, or MIP solver."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .graph import Graph


def validate_positions(graph: Graph, positions: Sequence[int] | Mapping[int, int]) -> tuple[int, ...]:
    """Validate a 1-based vertex-to-position permutation.

    For a sequence, element ``positions[v - 1]`` is the position of vertex
    ``v``. A mapping instead uses vertex IDs as keys. In both cases positions
    must be exactly ``1..graph.n`` with no repetitions. This is *not* a list
    of vertices in their left-to-right order.
    """
    if isinstance(positions, Mapping):
        expected_vertices = set(range(1, graph.n + 1))
        if any(type(vertex) is not int for vertex in positions) or set(positions) != expected_vertices:
            raise ValueError(f"vertex keys must be exactly 1..{graph.n}")
        permutation = tuple(positions[vertex] for vertex in range(1, graph.n + 1))
    else:
        if isinstance(positions, (str, bytes)):
            raise TypeError("positions must be a sequence of integers or a vertex-to-position mapping")
        permutation = tuple(positions)

    if len(permutation) != graph.n:
        raise ValueError(f"expected {graph.n} positions, found {len(permutation)}")
    if any(type(position) is not int for position in permutation):
        raise ValueError("all positions must be integers (Boolean values are not positions)")
    if set(permutation) != set(range(1, graph.n + 1)):
        raise ValueError(f"positions must be a permutation of 1..{graph.n}")
    return permutation


def compute_bandwidth(graph: Graph, positions: Sequence[int] | Mapping[int, int]) -> int:
    """Return ``max(abs(pos[u] - pos[v]))`` over all graph edges.

    An edgeless graph has bandwidth 0. The permutation is validated before
    any edge is evaluated, including when the graph has no edges.
    """
    permutation = validate_positions(graph, positions)
    return max((abs(permutation[u - 1] - permutation[v - 1]) for u, v in graph.edges), default=0)


def verify_solution(
    graph: Graph,
    positions: Sequence[int] | Mapping[int, int],
    claimed_bandwidth: int | None = None,
) -> int:
    """Check the permutation and optional solver claim; return actual bandwidth.

    Raises :class:`ValueError` for an invalid permutation or a claim that does
    not equal the independently computed bandwidth.
    """
    actual = compute_bandwidth(graph, positions)
    if claimed_bandwidth is not None:
        if type(claimed_bandwidth) is not int or claimed_bandwidth < 0:
            raise ValueError("claimed_bandwidth must be a nonnegative integer")
        if actual != claimed_bandwidth:
            raise ValueError(f"claimed bandwidth {claimed_bandwidth} differs from actual {actual}")
    return actual
