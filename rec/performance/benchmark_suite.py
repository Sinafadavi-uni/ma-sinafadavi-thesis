# ===  Benchmark Suite for UCP Vector Clocks ===

import time
import os
import json
import psutil
from uuid import uuid4
from datetime import datetime
from dataclasses import dataclass, asdict
import statistics

from rec.replication.core.vector_clock import VectorClock
from rec.nodes.enhanced_vector_clock_executor import VectorClockFCFSExecutor
from rec.nodes.brokers.multi_broker_coordinator import BrokerMetadata

@dataclass
class BenchmarkResult:
    name: str
    duration: float
    memory_delta_mb: float
    cpu_percent: float

class SimpleBenchmarkSuite:
    """Lightweight benchmark suite to test vector clock and executor performance."""

    def __init__(self, output_dir="benchmark_results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.process = psutil.Process()
        self.base_memory = self.process.memory_info().rss / 1024 / 1024
        print(f"[INIT] Baseline memory: {self.base_memory:.2f} MB")

    def _snapshot_resources(self):
        mem_mb = self.process.memory_info().rss / 1024 / 1024
        cpu = self.process.cpu_percent(interval=0.1)
        return cpu, mem_mb

    def run_test(self, name, func):
        print(f"\n--- Running test: {name} ---")
        cpu0, mem0 = self._snapshot_resources()
        t0 = time.time()

        try:
            func()
        except Exception as e:
            print(f"[ERROR] {name}: {e}")

        duration = time.time() - t0
        cpu1, mem1 = self._snapshot_resources()
        mem_delta = mem1 - mem0

        print(f"[RESULT] {name}: {duration:.3f}s, CPU {cpu1:.1f}%, ΔMem {mem_delta:.2f} MB")
        return BenchmarkResult(name, duration, mem_delta, cpu1)

    def test_vector_clock_ops(self, iterations=1000):
        def tick_ops():
            vc = VectorClock("bench")
            for _ in range(iterations):
                vc.tick()
        return self.run_test("VectorClock Tick", tick_ops)

    def test_fcfs_executor(self, job_count=100):
        def submit_fcfs():
            exe = VectorClockFCFSExecutor(node_id="bench_exe")
            jobs = [uuid4() for _ in range(job_count)]
            for j in jobs:
                exe.submit_job(j, {"data": str(j)})
            for j in jobs:
                exe.handle_result_submission(j, {"result": "ok"})
                exe.handle_result_submission(j, {"result": "again"})
        return self.run_test(f"FCFS Executor {job_count} jobs", submit_fcfs)

    def test_metadata_update(self):
        def update_meta():
            bm = BrokerMetadata(
                broker_id="bench", vector_clock={}, executor_count=1,
                active_jobs=[], emergency_jobs=[], last_updated=datetime.now().isoformat(),
                capabilities={"demo": True}
            )
            for i in range(100):
                bm.active_jobs.append(f"job_{i}")
                bm.vector_clock[bm.broker_id] = i
        return self.run_test("Broker Metadata Update", update_meta)

    def run_all(self):
        results = {}
        results["vc_tick"] = asdict(self.test_vector_clock_ops())
        results["fcfs_50"] = asdict(self.test_fcfs_executor(50))
        results["fcfs_100"] = asdict(self.test_fcfs_executor(100))
        results["meta_update"] = asdict(self.test_metadata_update())

        output_file = os.path.join(self.output_dir, f"benchmark_{int(time.time())}.json")
        with open(output_file, "w") as f:
            json.dump({"results": results, "timestamp": time.time()}, f, indent=2)

        print(f"\n[SUMMARY] Results saved to {output_file}")
        return results

class PerformanceBenchmarkSuite:
    """Alias for compatibility"""
    def __init__(self, output_dir="benchmark_results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.process = psutil.Process()
        self.base_memory = self.process.memory_info().rss / 1024 / 1024
        print(f"[INIT] Baseline memory: {self.base_memory:.2f} MB")

    def _snapshot_resources(self):
        mem_mb = self.process.memory_info().rss / 1024 / 1024
        cpu = self.process.cpu_percent(interval=0.1)
        return cpu, mem_mb

    def run_test(self, name, func):
        print(f"\n--- Running test: {name} ---")
        cpu0, mem0 = self._snapshot_resources()
        t0 = time.time()

        try:
            func()
        except Exception as e:
            print(f"[ERROR] {name}: {e}")

        duration = time.time() - t0
        cpu1, mem1 = self._snapshot_resources()
        mem_delta = mem1 - mem0

        print(f"[RESULT] {name}: {duration:.3f}s, CPU {cpu1:.1f}%, ΔMem {mem_delta:.2f} MB")
        return BenchmarkResult(name, duration, mem_delta, cpu1)

    def run_vector_clock_benchmarks(self, iterations=1000):
        results = {}
        
        def tick_ops():
            vc = VectorClock("bench")
            for _ in range(iterations):
                vc.tick()
        results["tick"] = self.run_test("VectorClock Tick", tick_ops)
        
        def update_ops():
            vc = VectorClock("bench")
            for i in range(iterations):
                vc.update({"other": i})
        results["update"] = self.run_test("VectorClock Update", update_ops)
        
        return results

    def run_fcfs_benchmarks(self, job_counts=[50, 100]):
        results = {}
        for job_count in job_counts:
            def submit_fcfs():
                exe = VectorClockFCFSExecutor(node_id="bench_exe")
                jobs = [uuid4() for _ in range(job_count)]
                for j in jobs:
                    exe.submit_job(j, {"data": str(j)})
                for j in jobs:
                    exe.handle_result_submission(j, {"result": "ok"})
                    exe.handle_result_submission(j, {"result": "again"})
            results[f"fcfs_{job_count}"] = self.run_test(f"FCFS Executor {job_count} jobs", submit_fcfs)
        return results

    def run_broker_benchmarks(self):
        def update_meta():
            bm = BrokerMetadata(
                broker_id="bench", vector_clock={}, executor_count=1,
                active_jobs=[], emergency_jobs=[], last_updated=datetime.now().isoformat(),
                capabilities={"demo": True}
            )
            for i in range(100):
                bm.active_jobs.append(f"job_{i}")
                bm.vector_clock[bm.broker_id] = i
        return {"metadata_update": self.run_test("Broker Metadata Update", update_meta)}

    def run_all(self):
        """Run all benchmark tests and return summary"""
        results = self.run_comprehensive_benchmark()
        return results

    def run_comprehensive_benchmark(self):
        results = {
            "vector_clock": self.run_vector_clock_benchmarks(),
            "fcfs_executor": self.run_fcfs_benchmarks(),
            "broker": self.run_broker_benchmarks()
        }
        
        # Convert BenchmarkResult objects to dictionaries for JSON serialization
        def convert_results(data):
            if isinstance(data, dict):
                return {k: convert_results(v) for k, v in data.items()}
            elif isinstance(data, BenchmarkResult):
                return asdict(data)
            else:
                return data
        
        json_results = convert_results(results)
        
        output_file = os.path.join(self.output_dir, f"comprehensive_benchmark_{int(time.time())}.json")
        with open(output_file, "w") as f:
            json.dump({"results": json_results, "timestamp": time.time()}, f, indent=2)
        
        print(f"\n[SUMMARY] Results saved to {output_file}")
        return results

def run_quick_benchmark():
    """Quick benchmark function for compatibility"""
    suite = SimpleBenchmarkSuite()
    
    # Run basic tests
    vc_result = suite.test_vector_clock_ops(100)
    fcfs_result = suite.test_fcfs_executor(50)
    
    return {
        "vector_clock_performance": {
            "vector_clock_tick": {
                "operations_per_second": 100 / vc_result.duration if vc_result.duration > 0 else 0,
                "operations_per_second_overall": 100 / vc_result.duration if vc_result.duration > 0 else 0
            }
        },
        "fcfs_performance": {
            "duration": fcfs_result.duration,
            "operations_per_second": 50 / fcfs_result.duration if fcfs_result.duration > 0 else 0
        }
    }


if __name__ == "__main__":
    suite = SimpleBenchmarkSuite()
    summary = suite.run_all()
    print("\nAll benchmarks completed successfully!")
