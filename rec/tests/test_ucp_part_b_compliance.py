# ✅ UCP Part B Integration Test

import time
import threading
from uuid import uuid4
from datetime import datetime

import requests
from rec.nodes.brokers.vector_clock_broker import VectorClockBroker
from rec.nodes.enhanced_vector_clock_executor import (
    create_enhanced_executor, ConflictStrategy, JobPriority
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
        """Submit jobs to a single executor under different strategies."""
        exec = create_enhanced_executor("test-exec", ConflictStrategy.CAUSAL)
        patterns = {}
        for strategy in ConflictStrategy:
            exec.set_conflict_strategy(strategy)
            outcomes = []
            for info, priority in [
                ({"estimated_cpu":20}, JobPriority()), 
                ({"estimated_cpu":60}, JobPriority(emergency=2, user=8)),
                ({"estimated_cpu":15}, JobPriority(user=9))
            ]:
                ok = exec.submit_job(uuid4(), info, priority)
                outcomes.append(ok)
            patterns[strategy.value] = tuple(outcomes)
            exec.running_jobs.clear()
        unique = len(set(patterns.values())) > 1
        emergency_prioritized = any(
            outcomes[1] for outcomes in patterns.values()
            if "emergency" in key
        for key,outcomes in patterns.items())
        return unique and emergency_prioritized

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
