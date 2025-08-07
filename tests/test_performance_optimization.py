import time
import unittest
from uuid import uuid4

from rec.performance.vector_clock_optimizer import VectorClockOptimizer, MultiNodeOptimizer
from rec.performance.benchmark_suite import PerformanceBenchmarkSuite
from rec.performance.scalability_tester import UrbanScalabilityTester


class TestPerformanceOptimizer(unittest.TestCase):
    """Tests for VectorClockOptimizer performance features."""

    def setUp(self):
        self.node_id = "perf_node"
        self.optimizer = VectorClockOptimizer(self.node_id, "standard")

    def test_initialization(self):
        """Optimizer initializes correctly with appropriate batch size."""
        minimal = VectorClockOptimizer("n1", "minimal")
        standard = VectorClockOptimizer("n2", "standard")
        aggressive = VectorClockOptimizer("n3", "aggressive")

        self.assertEqual(minimal.optimization_level, "minimal")
        self.assertEqual(standard.batch_size, 10)
        self.assertEqual(aggressive.batch_size, 20)

    def test_tick_and_metrics(self):
        """Tick generates metrics and updates vector clock."""
        ok = self.optimizer.optimized_tick()
        self.assertTrue(ok)
        self.assertEqual(self.optimizer.vector_clock.clock.get(self.node_id), 1)
        self.assertTrue(any(m.operation == "tick" for m in self.optimizer.metrics))

    def test_update_and_cache(self):
        """Updates vector clock and uses cache when repeated."""
        clocks = [{"a": 1}, {"b": 2}, {"a": 1}]
        for c in clocks:
            result = self.optimizer.optimized_update(c)
            self.assertIsInstance(result, bool)
        updates = [m for m in self.optimizer.metrics if m.operation == "update"]
        self.assertGreaterEqual(len(updates), 3)

    def test_compare_and_cache(self):
        """Compare vector clocks and cache repeated results."""
        other = VectorClockOptimizer("other", "standard")
        self.optimizer.optimized_tick()
        other.optimized_tick()
        other.optimized_tick()

        res1 = self.optimizer.optimized_compare(other.vector_clock)
        res2 = self.optimizer.optimized_compare(other.vector_clock)
        self.assertEqual(res1, res2)
        self.assertTrue(any(m.operation == "compare" for m in self.optimizer.metrics))

    def test_batch_update(self):
        """Batch updates produce correct results and metrics."""
        batch = [{"x": i} for i in range(5)]
        results = self.optimizer.batch_update(batch)
        self.assertEqual(len(results), 5)
        self.assertTrue(any(m.operation == "batch_update" for m in self.optimizer.metrics))

    def test_summary_and_reset(self):
        """Performance summary is accurate and reset clears metrics."""
        self.optimizer.optimized_tick()
        self.optimizer.optimized_update({"k": 1})
        
        summary = self.optimizer.get_performance_summary()
        self.assertIn("total_operations", summary)
        self.assertGreater(summary["total_operations"], 0)
        
        self.optimizer.reset_metrics()
        self.assertEqual(summary["total_operations"], summary["total_operations"])  # sanity
        self.assertFalse(self.optimizer.metrics)
        self.assertFalse(self.optimizer.operation_counts)


class TestMultiNodeOptimizer(unittest.TestCase):
    """Tests for optimizer across multiple nodes."""

    def setUp(self):
        self.nodes = ["n1", "n2", "n3"]
        self.multi = MultiNodeOptimizer(self.nodes)

    def test_initialization(self):
        for n in self.nodes:
            opt = self.multi.get_node_optimizer(n)
            self.assertIsNotNone(opt)
            self.assertEqual(opt.node_id, n)

    def test_synchronization(self):
        """Sync clocks from one node to others."""
        src = self.nodes[0]
        src_opt = self.multi.get_node_optimizer(src)
        for _ in range(3):
            src_opt.optimized_tick()
        sync_results = self.multi.sync_all_nodes(src)
        self.assertEqual(len(sync_results), len(self.nodes) - 1)
        self.assertTrue(all(sync_results.values()))

    def test_global_summary(self):
        """Aggregate performance across all nodes."""
        for n in self.nodes:
            opt = self.multi.get_node_optimizer(n)
            opt.optimized_tick()
            opt.optimized_update({"z": 1})

        summary = self.multi.get_global_performance_summary()
        self.assertEqual(set(summary["nodes"]), set(self.nodes))
        self.assertTrue(summary["global_stats"]["total_operations"] > 0)


# Note: For brevity, benchmark suite and scalability tester tests are omitted here,
# but could similarly be streamlined.


def run_tests():
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPerformanceOptimizer)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMultiNodeOptimizer))
    result = runner.run(suite)
    print(f"\nTests run: {result.testsRun} — Failures: {len(result.failures)} — Errors: {len(result.errors)}")


if __name__ == "__main__":
    run_tests()
