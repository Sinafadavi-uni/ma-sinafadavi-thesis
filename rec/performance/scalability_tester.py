# ===  Urban Scalability Tester for UCP Vector Clocks ===

import time
import os
import json
import statistics
import random
from uuid import uuid4
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List

from rec.replication.core.vector_clock import EmergencyLevel
from rec.nodes.brokers.multi_broker_coordinator import BrokerMetadata
from rec.nodes.enhanced_vector_clock_executor import VectorClockFCFSExecutor

@dataclass
class ScenarioConfig:
    city_name: str
    zones: int
    brokers_per_zone: int
    executors_per_broker: int
    job_rate_per_second: float
    emergency_rate_per_hour: float

@dataclass
class ScenarioMetrics:
    city_name: str
    total_nodes: int
    jobs_processed: int
    duration: float
    avg_response_time: float
    throughput: float

class SimpleUrbanTester:
    """Simulates activity across city zones, jobs, and emergencies."""

    def __init__(self, output_dir="urban_test_results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.scenarios = self._load_scenarios()
        self.results: List[ScenarioMetrics] = []
        print(f"[INIT] Tester initialized with {len(self.scenarios)} scenarios")

    def _load_scenarios(self) -> List[ScenarioConfig]:
        return [
            ScenarioConfig("SmallTown", zones=3, brokers_per_zone=2, executors_per_broker=3, job_rate_per_second=5.0, emergency_rate_per_hour=2.0),
            ScenarioConfig("MediumCity", zones=5, brokers_per_zone=3, executors_per_broker=5, job_rate_per_second=15.0, emergency_rate_per_hour=5.0),
        ]

    def _simulate_job(self, executor, event_type: str) -> float:
        start = time.time()
        job_id = uuid4()
        executor.submit_job(job_id, {"type": event_type})
        executor.handle_result_submission(job_id, {"result": "ok"})
        return time.time() - start

    def run_scenario(self, scenario: ScenarioConfig, duration_sec: int = 60):
        print(f"\n[RUN] Scenario: {scenario.city_name}")
        total_nodes = scenario.zones * scenario.brokers_per_zone * scenario.executors_per_broker
        executors = [VectorClockFCFSExecutor(node_id=f"{scenario.city_name}_node_{i}") for i in range(total_nodes)]

        start_time = time.time()
        response_times = []
        job_count = 0

        while time.time() - start_time < duration_sec:
            for executor in executors:
                # Submit normal job
                if random.random() < scenario.job_rate_per_second * 0.1:
                    rt = self._simulate_job(executor, "normal")
                    response_times.append(rt)
                    job_count += 1

                # Submit emergency job
                if random.random() < scenario.emergency_rate_per_hour / 3600:
                    rt = self._simulate_job(executor, "emergency")
                    response_times.append(rt)
                    job_count += 1

        duration = time.time() - start_time
        avg_rt = statistics.mean(response_times) if response_times else 0
        throughput = job_count / duration if duration > 0 else 0

        metrics = ScenarioMetrics(
            city_name=scenario.city_name,
            total_nodes=total_nodes,
            jobs_processed=job_count,
            duration=duration,
            avg_response_time=avg_rt,
            throughput=throughput
        )
        self.results.append(metrics)
        print(f"[RESULT] {scenario.city_name}: {job_count} jobs, {avg_rt:.3f}s avg, {throughput:.2f} job/s")

        return metrics

    def run_all(self):
        summary = {}
        for sc in self.scenarios:
            metrics = self.run_scenario(sc)
            summary[sc.city_name] = asdict(metrics)

        out_file = os.path.join(self.output_dir, f"urban_summary_{int(time.time())}.json")
        with open(out_file, "w") as f:
            json.dump({"timestamp": time.time(), "results": summary}, f, indent=2)

        print(f"\n[SUMMARY] Results saved to {out_file}")
        return summary

class UrbanScalabilityTester:
    """Alias for compatibility"""
    def __init__(self, output_dir="urban_test_results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.scenarios = self._load_scenarios()
        self.results: List[ScenarioMetrics] = []
        print(f"[INIT] Tester initialized with {len(self.scenarios)} scenarios")

    def _load_scenarios(self) -> List[ScenarioConfig]:
        return [
            ScenarioConfig("SmallTown", zones=3, brokers_per_zone=2, executors_per_broker=3, job_rate_per_second=5.0, emergency_rate_per_hour=2.0),
            ScenarioConfig("MediumCity", zones=5, brokers_per_zone=3, executors_per_broker=5, job_rate_per_second=15.0, emergency_rate_per_hour=5.0),
            ScenarioConfig("Metropolis", zones=10, brokers_per_zone=5, executors_per_broker=8, job_rate_per_second=30.0, emergency_rate_per_hour=10.0),
        ]

    def _simulate_job(self, executor, event_type: str) -> float:
        start = time.time()
        job_id = uuid4()
        executor.submit_job(job_id, {"type": event_type})
        executor.handle_result_submission(job_id, {"result": "ok"})
        return time.time() - start

    def run_scenario(self, scenario: ScenarioConfig, duration_sec: int = 30):
        print(f"\n[RUN] Scenario: {scenario.city_name}")
        total_nodes = scenario.zones * scenario.brokers_per_zone * scenario.executors_per_broker
        executors = [VectorClockFCFSExecutor(node_id=f"{scenario.city_name}_node_{i}") for i in range(min(total_nodes, 10))]

        start_time = time.time()
        response_times = []
        job_count = 0

        while time.time() - start_time < duration_sec:
            for executor in executors:
                # Submit normal job
                if random.random() < scenario.job_rate_per_second * 0.1:
                    rt = self._simulate_job(executor, "normal")
                    response_times.append(rt)
                    job_count += 1

                # Submit emergency job
                if random.random() < scenario.emergency_rate_per_hour / 3600:
                    rt = self._simulate_job(executor, "emergency")
                    response_times.append(rt)
                    job_count += 1

        duration = time.time() - start_time
        avg_rt = statistics.mean(response_times) if response_times else 0
        throughput = job_count / duration if duration > 0 else 0

        metrics = ScenarioMetrics(
            city_name=scenario.city_name,
            total_nodes=len(executors),
            jobs_processed=job_count,
            duration=duration,
            avg_response_time=avg_rt,
            throughput=throughput
        )
        self.results.append(metrics)
        print(f"[RESULT] {scenario.city_name}: {job_count} jobs, {avg_rt:.3f}s avg, {throughput:.2f} job/s")

        return metrics

    def run_all(self):
        """Run all scalability tests and return summary"""
        summary = self.run_all_scenarios()
        return summary

    def run_all_scenarios(self):
        summary = {}
        for sc in self.scenarios:
            metrics = self.run_scenario(sc)
            summary[sc.city_name] = asdict(metrics)

        out_file = os.path.join(self.output_dir, f"urban_summary_{int(time.time())}.json")
        with open(out_file, "w") as f:
            json.dump({"timestamp": time.time(), "results": summary}, f, indent=2)

        print(f"\n[SUMMARY] Results saved to {out_file}")
        return summary

def run_quick_scalability_test():
    """Quick scalability test function for compatibility"""
    tester = SimpleUrbanTester()
    
    # Run a quick small town scenario
    scenario = ScenarioConfig("QuickTest", zones=2, brokers_per_zone=2, executors_per_broker=2, job_rate_per_second=10.0, emergency_rate_per_hour=1.0)
    metrics = tester.run_scenario(scenario, duration_sec=15)
    
    return {
        "scenario": "QuickTest",
        "metrics": asdict(metrics)
    }

    def _load_scenarios(self) -> List[ScenarioConfig]:
        return [
            ScenarioConfig("SmallTown", zones=3, brokers_per_zone=2, executors_per_broker=3, job_rate_per_second=5.0, emergency_rate_per_hour=2.0),
            ScenarioConfig("MediumCity", zones=5, brokers_per_zone=3, executors_per_broker=5, job_rate_per_second=15.0, emergency_rate_per_hour=5.0),
        ]

    def _simulate_job(self, executor, event_type: str) -> float:
        start = time.time()
        job_id = uuid4()
        executor.submit_job(job_id, {"type": event_type})
        executor.handle_result_submission(job_id, {"result": "ok"})
        return time.time() - start

    def run_scenario(self, scenario: ScenarioConfig, duration_sec: int = 60):
        print(f"\n[RUN] Scenario: {scenario.city_name}")
        total_nodes = scenario.zones * scenario.brokers_per_zone * scenario.executors_per_broker
        executors = [VectorClockFCFSExecutor(node_id=f"{scenario.city_name}_node_{i}") for i in range(total_nodes)]

        start_time = time.time()
        response_times = []
        job_count = 0

        while time.time() - start_time < duration_sec:
            for executor in executors:
                # Submit normal job
                if random.random() < scenario.job_rate_per_second * 0.1:
                    rt = self._simulate_job(executor, "normal")
                    response_times.append(rt)
                    job_count += 1

                # Submit emergency job
                if random.random() < scenario.emergency_rate_per_hour / 3600:
                    rt = self._simulate_job(executor, "emergency")
                    response_times.append(rt)
                    job_count += 1

        duration = time.time() - start_time
        avg_rt = statistics.mean(response_times) if response_times else 0
        throughput = job_count / duration if duration > 0 else 0

        metrics = ScenarioMetrics(
            city_name=scenario.city_name,
            total_nodes=total_nodes,
            jobs_processed=job_count,
            duration=duration,
            avg_response_time=avg_rt,
            throughput=throughput
        )
        self.results.append(metrics)
        print(f"[RESULT] {scenario.city_name}: {job_count} jobs, {avg_rt:.3f}s avg, {throughput:.2f} job/s")

        return metrics

    def run_all(self):
        summary = {}
        for sc in self.scenarios:
            metrics = self.run_scenario(sc)
            summary[sc.city_name] = asdict(metrics)

        out_file = os.path.join(self.output_dir, f"urban_summary_{int(time.time())}.json")
        with open(out_file, "w") as f:
            json.dump({"timestamp": time.time(), "results": summary}, f, indent=2)

        print(f"\n[SUMMARY] Results saved to {out_file}")
        return summary

if __name__ == "__main__":
    tester = SimpleUrbanTester()
    tester.run_all()
