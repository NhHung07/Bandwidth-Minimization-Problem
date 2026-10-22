"""Checks for the shared BMP data loader and independent solution verifier."""

import tempfile
import unittest
from pathlib import Path

from src.graph import GraphFormatError, list_instance_paths, load_graph
from src.verify import compute_bandwidth, validate_positions, verify_solution


class GraphLoaderTests(unittest.TestCase):
    def test_all_benchmark_instances_load_and_keep_declared_counts(self):
        paths = list_instance_paths()
        self.assertEqual(len(paths), 113)
        self.assertEqual(sum("hb_33" in path.parts for path in paths), 33)
        self.assertEqual(sum("hb_80" in path.parts for path in paths), 80)

        for path in paths:
            with self.subTest(instance=path.name):
                graph = load_graph(path)
                self.assertGreater(graph.n, 0)
                self.assertEqual(graph.source_path, path.resolve())
                self.assertEqual(
                    graph.raw_edge_count,
                    graph.m + graph.duplicate_edge_count + graph.self_loop_count,
                )
                self.assertEqual(graph.edges, tuple(sorted(set(graph.edges))))
                self.assertTrue(all(1 <= u < v <= graph.n for u, v in graph.edges))
                self.assertIsInstance(verify_solution(graph, range(1, graph.n + 1)), int)

        example = load_graph(next(path for path in paths if path.name == "bcspwr01.mtx.rnd"))
        self.assertEqual((example.n, example.raw_edge_count, example.m), (39, 46, 46))

    def test_normalizes_reversed_duplicates_and_loops_but_keeps_isolates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.mtx.rnd"
            path.write_text(
                "Nombre del problema: sample.mtx.rnd\n"
                "5 5 5\n"
                "2 1\n"
                "1 2\n"
                "2 2\n"
                "3 1\n"
                "4 3\n",
                encoding="utf-8",
            )
            graph = load_graph(path)

        self.assertEqual(graph.n, 5)  # Vertex 5 is isolated, but retained.
        self.assertEqual(graph.edges, ((1, 2), (1, 3), (3, 4)))
        self.assertEqual((graph.raw_edge_count, graph.m), (5, 3))
        self.assertEqual((graph.duplicate_edge_count, graph.self_loop_count), (1, 1))

    def test_rejects_malformed_headers_edges_and_counts(self):
        malformed = (
            ("wrong title\n2 2 0\n", "expected"),
            ("Nombre del problema: wrong.mtx.rnd\n2 2 0\n", "differs"),
            ("Nombre del problema: sample.mtx.rnd\n2 3 0\n", "square"),
            ("Nombre del problema: sample.mtx.rnd\n2 2 1\n", "expected 1 edge lines"),
            ("Nombre del problema: sample.mtx.rnd\n2 2 0\n1 2\n", "more than 0"),
            ("Nombre del problema: sample.mtx.rnd\n2 2 1\n1 3\n", "1..2"),
            ("Nombre del problema: sample.mtx.rnd\n2 2 1\na b\n", "integers"),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.mtx.rnd"
            for content, expected_message in malformed:
                with self.subTest(expected_message=expected_message, content=content):
                    path.write_text(content, encoding="utf-8")
                    with self.assertRaisesRegex(GraphFormatError, expected_message):
                        load_graph(path)


class VerifyTests(unittest.TestCase):
    def test_bandwidth_of_known_path_permutations(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "path.mtx.rnd"
            path.write_text(
                "Nombre del problema: path.mtx.rnd\n4 4 3\n1 2\n2 3\n3 4\n",
                encoding="utf-8",
            )
            graph = load_graph(path)

        self.assertEqual(verify_solution(graph, (1, 2, 3, 4), claimed_bandwidth=1), 1)
        self.assertEqual(compute_bandwidth(graph, (1, 3, 2, 4)), 2)
        self.assertEqual(compute_bandwidth(graph, {1: 1, 2: 3, 3: 2, 4: 4}), 2)
        self.assertEqual(validate_positions(graph, (1, 3, 2, 4)), (1, 3, 2, 4))
        with self.assertRaisesRegex(ValueError, "differs"):
            verify_solution(graph, (1, 3, 2, 4), claimed_bandwidth=1)

    def test_edgeless_graph_has_zero_bandwidth_but_still_needs_a_permutation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.mtx.rnd"
            path.write_text("Nombre del problema: empty.mtx.rnd\n3 3 0\n", encoding="utf-8")
            graph = load_graph(path)

        self.assertEqual(verify_solution(graph, (3, 1, 2), claimed_bandwidth=0), 0)
        with self.assertRaises(ValueError):
            verify_solution(graph, (1, 1, 2))

    def test_rejects_missing_duplicate_or_noninteger_positions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tiny.mtx.rnd"
            path.write_text("Nombre del problema: tiny.mtx.rnd\n3 3 1\n1 2\n", encoding="utf-8")
            graph = load_graph(path)

        for invalid in ((1, 2), (1, 1, 3), (1, 2, 4), (True, 2, 3), {1: 1, 3: 2, 4: 3}):
            with self.subTest(positions=invalid), self.assertRaises(ValueError):
                verify_solution(graph, invalid)
        with self.assertRaises(ValueError):
            verify_solution(graph, (1, 2, 3), claimed_bandwidth=True)


if __name__ == "__main__":
    unittest.main()
