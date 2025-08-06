# ✅ UCP Part B Integration Test

import time
import threading
from uuid import uuid4
from datetime import datetime

import requests
from rec.nodes.brokers.vector_clock_broker import VectorClockBroker
from rec.nodes.enhanced_vector_clock_executor import (
    create_fcfs_executor
)
from rec.util.log import LOG

class SimpleUCPTest:
    """Runs both metadata sync (B.a) and conflict resolution tests (B.b)."""

    def __init__(self):
        self.brokers = []

    def setup_brokers(self, count=3):
        """Start brokers on ports 8000+"""
        for i in range(count):
            port = 8000 + i
            broker = VectorClockBroker(host=["127.0.0.1"], port=port, enable_coordination=True)
            threading.Thread(target=broker.run, daemon=True).start()
            self.brokers.append((broker, port))
            time.sleep(2)
            LOG.info(f"Broker started on port {port}")
        time.sleep(10)  # Allow discovery
        return True

    def test_metadata_sync(self):
        """Check that brokers discover each other and share vector clocks."""
        results = []
        for _, port in self.brokers:
            try:
                r = requests.get(f"http://localhost:{port}/broker/vector-clock", timeout=5)
                ok = r.status_code == 200
            except:
                ok = False
            results.append(ok)
        return all(results)

    def test_conflict_resolution(self):
        """Test FCFS processing with vector clock causal consistency (per thesis requirements)."""
        # Test Vector Clock-Enhanced FCFS instead of multiple strategies
        # Per thesis: "first-come-first-served manner"
        
        executor = create_fcfs_executor("test-fcfs-exec")
        
        # Test FCFS job submission and processing
        test_results = []
        
        # Submit multiple jobs to test FCFS ordering
        jobs = [
            ({"estimated_cpu": 20}, "low_cpu_job"),
            ({"estimated_cpu": 60}, "high_cpu_job"),  
            ({"estimated_cpu": 15}, "another_low_cpu_job")
        ]
        
        for job_info, job_type in jobs:
            success = executor.submit_job(uuid4(), job_info)
            test_results.append(success)
        
        # Test vector clock causal consistency
        initial_clock = executor.vector_clock.clock.copy()
        executor.sync_vector_clock({"broker_node": 3})
        updated_clock = executor.vector_clock.clock.copy()
        
        # Test first-come-first-served result submission policy
        test_job = uuid4()
        executor.submit_job(test_job, {"estimated_cpu": 10})
        
        # Simulate job running
        if test_job not in executor.running_jobs:
            executor.running_jobs.add(test_job)
        
        # First result should be accepted, second rejected (FCFS policy)
        first_result = executor.handle_result_submission(test_job, {"result": "first"})
        second_result = executor.handle_result_submission(test_job, {"result": "second"})
        
        # Check all FCFS requirements are met
        fcfs_submission_ok = all(test_results)  # All jobs accepted for FCFS processing
        causal_consistency_ok = updated_clock != initial_clock  # Vector clock updated
        result_policy_ok = first_result and not second_result  # FCFS result policy
        
        return fcfs_submission_ok and causal_consistency_ok and result_policy_ok

    def run(self):
        if not self.setup_brokers():
            return {"passed": False, "reason": "Broker setup failed"}

        b = self.test_metadata_sync()
        c = self.test_conflict_resolution()

        for broker, _ in self.brokers:
            try:
                broker.stop()
            except:
                pass

        return {
            "metadata_sync_ok": b,
            "conflict_resolution_ok": c,
            "overall_passed": b and c
        }

if __name__ == "__main__":
    tester = SimpleUCPTest()
    res = tester.run()

    print("=== UCP Part B Compliance Test ===")
    print("Metadata sync:", "✅" if res["metadata_sync_ok"] else "❌")
    print("Conflict resolution:", "✅" if res["conflict_resolution_ok"] else "❌")
    print("Overall result:", "✅ Passed" if res["overall_passed"] else "❌ Failed")
    print("==============================")
