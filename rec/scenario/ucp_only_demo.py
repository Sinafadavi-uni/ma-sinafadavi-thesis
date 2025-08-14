"""
UCP-Only Scenario: Minimal runnable example using Phase 4 components

This script demonstrates running the UCP integration layer alone, without
walking through the full 4-phase demo. It focuses on:
- ProductionVectorClockExecutor lifecycle and FCFS result handling
- DatastoreReplicationManager store/retrieve and failure handling

Run (from repo root):
  PYTHONPATH=. python3 rec/scenario/ucp_only_demo.py
"""
from __future__ import annotations

import logging
import time
from uuid import uuid4

from rec.Phase4_UCP_Integration.production_vector_clock_executor import (
    ProductionVectorClockExecutor,
    ProductionMode,
)
from rec.Phase4_UCP_Integration.datastore_replication import (
    DatastoreReplicationManager,
)


logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("ucp_only_demo")


def show(title: str, payload):
    print("\n===", title, "===")
    print(payload)


def run_ucp_executor_demo():
    print("\n[UCP] Production Executor Demo")

    # Start production-grade executor in DEVELOPMENT mode (no external services required)
    executor = ProductionVectorClockExecutor(
        host=["127.0.0.1"],
        port=9999,
        rootdir="/tmp",
        executor_id="ucp_prod_exec_1",
        mode=ProductionMode.DEVELOPMENT,
    )
    executor.start()

    # Demonstrate FCFS result policy (first accepted, second rejected)
    executor.set_emergency_mode("brownout", "high")
    job_id = uuid4()
    first_ok = executor.handle_result_submission(job_id, {"status": "ok"})
    second_rejected = not executor.handle_result_submission(job_id, {"status": "late"})

    # Query status
    status = executor.get_status()
    # Normalize emergency context for safe printing
    if status.get("current_emergency") and not isinstance(status["current_emergency"], dict):
        ce = status["current_emergency"]
        status["current_emergency"] = {
            "type": getattr(ce, "emergency_type", None),
            "level": getattr(getattr(ce, "level", None), "name", None),
            "location": getattr(ce, "location", None),
        }

    show(
        "Production Executor Status",
        {
            "status": status,
            "fcfs_first": first_ok,
            "fcfs_second_rejected": second_rejected,
        },
    )

    executor.stop()


def run_datastore_replication_demo():
    print("\n[UCP] Datastore Replication Demo")

    repl = DatastoreReplicationManager(manager_id="ucp_repl_demo")
    # Register two datastores (in-memory simulation)
    repl.register_datastore("ds1", "127.0.0.1", 7001, capacity=2 * 1024 * 1024)
    repl.register_datastore("ds2", "127.0.0.1", 7002, capacity=2 * 1024 * 1024)

    repl.start()

    # Store a small blob with replication factor 2
    key = "greeting"
    value = b"hello ucp"
    stored = repl.store_data(key, value, replication_factor=2)
    fetched = repl.retrieve_data(key)

    # Simulate a datastore failure and switch to emergency strategy
    repl.handle_datastore_failure("ds1")
    repl.set_emergency_mode(True)

    # Let background threads run briefly
    time.sleep(0.5)

    status = repl.get_replication_status()
    show(
        "Datastore Replication Status",
        {
            "stored": stored,
            "fetched_ok": fetched == value,
            "replication": status,
        },
    )

    repl.stop()


def main():
    print("UCP-Only Scenario (Phase 4 components only)")
    run_ucp_executor_demo()
    run_datastore_replication_demo()
    print("\nScenario complete.")


if __name__ == "__main__":
    main()
