# ===  Performance Report Generator for UCP Vector Clocks ===

import os
import json
import time
from datetime import datetime
from dataclasses import dataclass, asdict
import matplotlib.pyplot as plt

from rec.performance.benchmark_suite import run_quick_benchmark
from rec.performance.scalability_tester import run_quick_scalability_test

@dataclass
class Insight:
    category: str
    message: str
    severity: str  # high, medium, low

class SimplePerformanceReport:
    """Generates a basic performance report with insights and charts."""

    def __init__(self, output_dir="perf_reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.insights = []
        print(f"[INIT] Reports will be saved to: {self.output_dir}")

    def run(self):
        start = time.time()

        print("\nRunning benchmarks...")
        bench = run_quick_benchmark()

        print("\nRunning scalability test...")
        scale = run_quick_scalability_test()

        duration = time.time() - start

        report = {
            "timestamp": datetime.now().isoformat(),
            "duration_sec": duration,
            "benchmark": bench,
            "scalability": scale
        }

        self._derive_insights(bench, scale)
        self._save_report(report)
        self._create_simple_chart(bench, scale)

        print(f"\n===== Summary =====")
        for i in self.insights:
            print(f"- [{i.severity.upper()}] {i.category}: {i.message}")

        print("\nReport generation complete.")
        return report

    def _derive_insights(self, bench, scale):
        vc_ops = bench["vector_clock_performance"]
        if vc_ops:
            key, data = next(iter(vc_ops.items()))
            msg = f"{key}: {data['vector_clock_performance'][key]['operations_per_second']:.1f} ops/sec"
            severity = "high" if data['vector_clock_performance'][key]['operations_per_second'] < 500 else "low"
            self.insights.append(Insight("Vector Clock", msg, severity))

        sc = scale["metrics"]
        msg = f"{sc['jobs_processed']} jobs in {sc['duration']:.1f}s → {sc['throughput']:.1f} job/s"
        severity = "high" if sc["throughput"] < 10 else "low"
        self.insights.append(Insight("Scalability", msg, severity))

    def _save_report(self, report):
        path = os.path.join(self.output_dir, "performance_report.json")
        with open(path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to {path}")

    def _create_simple_chart(self, bench, scale):
        fig, ax = plt.subplots()
        x_labels = ["Vector Clock Ops", "Scalability Throughput"]
        values = [
            next(iter(bench["vector_clock_performance"].values()))["vector_clock_performance"].get(
                list(bench["vector_clock_performance"].keys())[0], {}
            ).get("operations_per_second_overall", 0),
            scale["metrics"]["throughput"]
        ]

        ax.bar(x_labels, values, color=["blue", "green"])
        ax.set_ylabel("Operations per second")
        ax.set_title("Quick Performance Comparison")

        chart_path = os.path.join(self.output_dir, "perf_chart.png")
        plt.savefig(chart_path, dpi=200)
        plt.close()
        print(f"Chart saved to {chart_path}")
