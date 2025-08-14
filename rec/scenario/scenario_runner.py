"""
Operational Scenario Runner: End-to-End example across all 4 phases

This scenario creates a realistic, single-process operational environment that
instantiates and exercises core components from each phase, showing exactly what
happens at runtime with vector clocks, causal ordering, FCFS policy, emergency
handling, and production integration surfaces.

How this maps to phases:
- Phase 1 (Core Foundation): VectorClock, causal messaging, FCFS policy
- Phase 2 (Node Infrastructure): ExecutorBroker + emergency-aware execution
- Phase 3 (Core Implementation): EnhancedVectorClockExecutor + VectorClockBroker
- Phase 4 (UCP Integration): ProductionVectorClockExecutor + MultiBrokerCoordinator

This file is intentionally compact and runnable without external services.
"""
from __future__ import annotations

import time
import logging
from uuid import uuid4

# Phase 1 imports
from rec.Phase1_Core_Foundation.vector_clock import (
    VectorClock,
    create_emergency,
    EmergencyLevel,
)
from rec.Phase1_Core_Foundation.causal_message import MessageHandler
from rec.Phase1_Core_Foundation.causal_consistency import FCFSConsistencyPolicy

# Phase 2 imports
from rec.Phase2_Node_Infrastructure.executorbroker import ExecutorBroker, JobInfo
from rec.Phase2_Node_Infrastructure.emergency_executor import (
    SimpleEmergencyExecutor,
    ExecutorCapabilities,
)

# Phase 3 imports
from rec.Phase3_Core_Implementation.enhanced_vector_clock_executor import (
    EnhancedVectorClockExecutor,
)
from rec.Phase3_Core_Implementation.vector_clock_broker import VectorClockBroker

# Phase 4 imports
from rec.Phase4_UCP_Integration.production_vector_clock_executor import (
    ProductionVectorClockExecutor,
    ProductionMode,
)
from rec.Phase4_UCP_Integration.multi_broker_coordinator import MultiBrokerCoordinator


logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("scenario")


def show(title: str, payload):
    print("\n===" , title, "===")
    print(payload)


def run_phase1_foundation():
    print("\n[Phase 1] Core Foundation")
    # Vector clocks
    c1 = VectorClock("node_A")
    c2 = VectorClock("node_B")
    c1.tick(); c2.tick(); c1.update(c2.clock)
    show("VectorClock state (A after B)", {"A": c1.clock, "B": c2.clock})

    # Causal messaging (minimal send/receive without networking)
    mh_a = MessageHandler("node_A")
    mh_b = MessageHandler("node_B")
    msg = mh_a.send_message({"msg": "hello"}, "node_B", is_emergency=False)
    mh_b.receive_message(msg)
    show("CausalMessage stats", mh_b.get_message_stats())

    # FCFS policy
    fcfs = FCFSConsistencyPolicy()
    job_id = str(uuid4())
    # Create a causal operation for job submission
    job_submit = {
        'operation_id': 'op-job-'+job_id,
        'operation_type': 'job_submission',
        'vector_clock': c1.clock.copy(),
        'job_id': job_id,
        'submitter_id': 'node_A',
    }
    job_ok = fcfs.apply_policy(job_submit, context={})
    # First result
    res1 = {
        'operation_id': 'op-res1-'+job_id,
        'operation_type': 'result_submission',
        'vector_clock': c1.clock.copy(),
        'job_id': job_id,
        'result': {'r': 1},
        'executor_id': 'node_A'
    }
    first = fcfs.apply_policy(res1, context={})
    # Second result (should be rejected by FCFS)
    res2 = {
        'operation_id': 'op-res2-'+job_id,
        'operation_type': 'result_submission',
        'vector_clock': c1.clock.copy(),
        'job_id': job_id,
        'result': {'r': 2},
        'executor_id': 'node_B'
    }
    second = fcfs.apply_policy(res2, context={})
    show("FCFS result acceptance", {"job_submission": job_ok, "first": first, "second_rejected": not second})


def run_phase2_infrastructure():
    print("\n[Phase 2] Node Infrastructure")
    broker = ExecutorBroker("broker_demo")

    # Register a simple emergency-aware executor
    caps = ExecutorCapabilities(emergency_capable=True, max_concurrent_jobs=1)
    exec_node = SimpleEmergencyExecutor("exec_demo", capabilities=caps)
    exec_node.start()
    broker.register_executor(exec_node.node_id, host="127.0.0.1", port=9000, capabilities={"python"})

    # Submit a normal job
    normal_job = JobInfo(job_id=uuid4(), data={"task": "compute", "cost": 10})
    broker.submit_job(normal_job)

    # Trigger an emergency and submit an emergency job
    broker.set_emergency_mode("fire", "high")
    emergency_job = JobInfo(job_id=uuid4(), data={"task": "evacuate"})
    broker.submit_job(emergency_job)

    # Give the executor a tick to process
    time.sleep(0.5)
    status = {
        "executors": list(broker.executors.keys()),
        "broker_clock": broker.vector_clock.clock,
        "completed_jobs": list(broker.completed_jobs),
    }
    show("Broker + Emergency-aware execution", status)

    exec_node.stop()


def run_phase3_core():
    print("\n[Phase 3] Core Implementation")
    caps = ExecutorCapabilities(emergency_capable=True, max_concurrent_jobs=2)
    ex1 = EnhancedVectorClockExecutor("vc_exec_1", caps)
    ex2 = EnhancedVectorClockExecutor("vc_exec_2", caps)

    # Peer registration for vector clock sync
    ex1.register_peer_executor("vc_exec_2", ex2)
    ex2.register_peer_executor("vc_exec_1", ex1)

    ex1.start(); ex2.start()

    # Submit causal chain across nodes
    j1 = ex1.submit_causal_job({"task": "preprocess"})
    j2 = ex1.submit_causal_job({"task": "analyze"}, dependencies={j1})
    j3 = ex2.submit_causal_job({"task": "report"}, dependencies={j2})

    # Sync clocks and allow scheduling
    time.sleep(1.0)
    s1 = ex1.get_causal_execution_status()
    s2 = ex2.get_causal_execution_status()
    show("Causal execution status", {"exec1": s1["causal_jobs"], "exec2": s2["causal_jobs"]})

    # VectorClockBroker coordinating a distributed submission
    broker = VectorClockBroker("vc_broker_demo")
    # Minimal peer registration (self) to satisfy interfaces
    broker.register_peer_broker(broker.broker_id, broker)

    # Create a broker-level job mapped to Phase2.JobInfo
    job = JobInfo(job_id=uuid4(), data={"task": "city_aggregation"})
    broker.submit_distributed_job(job)
    show("VectorClockBroker state", {"broker_clock": broker.vector_clock.clock})

    ex1.stop(); ex2.stop()


def run_phase4_ucp_integration():
    print("\n[Phase 4] UCP Integration")
    # Start production-grade executor (no external server required)
    prod = ProductionVectorClockExecutor(
        host=["127.0.0.1"], port=9999, rootdir="/tmp", executor_id="prod_exec_1",
        mode=ProductionMode.DEVELOPMENT
    )
    prod.start()

    # Demonstrate FCFS result policy directly (first accepted, second rejected)
    prod.set_emergency_mode("power_outage", "high")
    job_id = uuid4()
    r1 = prod.handle_result_submission(job_id, {"status": "ok"})
    r2 = prod.handle_result_submission(job_id, {"status": "late"})

    # Multi-broker coordinator over a cluster with a VectorClockBroker
    cluster_broker = VectorClockBroker("cluster_broker_1")
    coord = MultiBrokerCoordinator("global_coord_1")
    coord.register_broker_cluster("cluster_A", cluster_broker)

    # Coordinate a global operation
    op_ok = coord.coordinate_global_operation({"operation": "sync-topology", "priority": 1})

    # Coordinate an emergency
    emg = coord.coordinate_emergency_response("medical", "high", ["cluster_A"]) 

    es = prod.get_status()
    # Normalize emergency context for display (EmergencyContext has no to_dict)
    if es.get("current_emergency") and not isinstance(es["current_emergency"], dict):
        ce = es["current_emergency"]
        es["current_emergency"] = {
            "type": getattr(ce, "emergency_type", None),
            "level": getattr(getattr(ce, "level", None), "name", None),
            "location": getattr(ce, "location", None),
        }

    status = {
        "executor_status": es,
        "fcfs_first": r1,
        "fcfs_second_rejected": not r2,
        "global_operation_success": op_ok,
        "emergency_coordination_keys": list(emg.keys()),
    }
    show("Production integration surfaces", status)

    prod.stop()


def main():
    print("Operational Scenario: 4-Phase End-to-End Example")
    run_phase1_foundation()
    run_phase2_infrastructure()
    run_phase3_core()
    run_phase4_ucp_integration()
    print("\nScenario complete.")


if __name__ == "__main__":
    main()
