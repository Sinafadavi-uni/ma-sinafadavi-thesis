"""
Full UCP All-Phases Scenario

This scenario starts the real UCP node services (Datastore, Broker, Executor)
from rec/nodes, and then sequentially exercises Phase 1–4 components to
showcase end-to-end behaviors in one run.

Run (from repo root):
  PYTHONPATH=. python3 rec/scenario/full_ucp_all_phases_demo.py
"""
from __future__ import annotations

import logging
import threading
import time
from uuid import uuid4
from typing import Tuple

import requests

# UCP node services (networked)
from rec.nodes.datastore import Datastore
from rec.nodes.broker import Broker
from rec.nodes.executor import Executor

# Phase 1
from rec.Phase1_Core_Foundation.vector_clock import (
    VectorClock,
    create_emergency,
    EmergencyLevel,
)
from rec.Phase1_Core_Foundation.causal_message import MessageHandler
from rec.Phase1_Core_Foundation.causal_consistency import FCFSConsistencyPolicy

# Phase 2
from rec.Phase2_Node_Infrastructure.executorbroker import ExecutorBroker, JobInfo
from rec.Phase2_Node_Infrastructure.emergency_executor import (
    SimpleEmergencyExecutor,
    ExecutorCapabilities,
)

# Phase 3
from rec.Phase3_Core_Implementation.enhanced_vector_clock_executor import (
    EnhancedVectorClockExecutor,
)
from rec.Phase3_Core_Implementation.vector_clock_broker import VectorClockBroker

# Phase 4
from rec.Phase4_UCP_Integration.production_vector_clock_executor import (
    ProductionVectorClockExecutor,
    ProductionMode,
)
from rec.Phase4_UCP_Integration.multi_broker_coordinator import MultiBrokerCoordinator
from rec.Phase4_UCP_Integration.datastore_replication import DatastoreReplicationManager
from rec.Phase4_UCP_Integration.system_integration import SystemIntegrationFramework


logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("full_ucp_demo")


def show(title: str, payload):
    print("\n===", title, "===")
    print(payload)


def wait_for_ping(host: str, port: int, timeout_s: float = 15.0) -> Tuple[bool, int]:
    url = f"http://{host}:{port}/ping"
    deadline = time.time() + timeout_s
    last_status = 0
    while time.time() < deadline:
        try:
            resp = requests.get(url, timeout=1.5)
            last_status = resp.status_code
            if resp.ok:
                return True, resp.status_code
        except Exception:
            pass
        time.sleep(0.3)
    return False, last_status


# --- UCP networked services boot ---

def start_ucp_nodes():
    host = ["127.0.0.1"]
    ds_port, br_port, ex_port = 8002, 8000, 8001
    ds_root = "/tmp/ucp_demo_datastore.d"
    ex_root = "/tmp/ucp_demo_executor.d"

    datastore = Datastore(host, ds_port, ds_root)
    broker = Broker(host, br_port)
    executor = Executor(host, ex_port, ex_root)

    t_ds = threading.Thread(target=datastore.run, daemon=True, name="datastore.run")
    t_br = threading.Thread(target=broker.run, daemon=True, name="broker.run")
    t_ex = threading.Thread(target=executor.run, daemon=True, name="executor.run")

    t_ds.start(); time.sleep(0.2)
    t_br.start(); time.sleep(0.2)
    t_ex.start()

    ok_ds, code_ds = wait_for_ping("127.0.0.1", ds_port)
    ok_br, code_br = wait_for_ping("127.0.0.1", br_port)
    ok_ex, code_ex = wait_for_ping("127.0.0.1", ex_port)

    show("UCP nodes up", {
        "datastore": {"port": ds_port, "ok": ok_ds, "status": code_ds},
        "broker": {"port": br_port, "ok": ok_br, "status": code_br},
        "executor": {"port": ex_port, "ok": ok_ex, "status": code_ex},
    })

    return (datastore, broker, executor, t_ds, t_br, t_ex)


def stop_ucp_nodes(datastore, broker, executor, t_ds, t_br, t_ex):
    try:
        executor.stop()
    except Exception:
        pass
    try:
        broker.stop()
    except Exception:
        pass
    try:
        datastore.stop()
    except Exception:
        pass
    t_ex.join(timeout=3.0)
    t_br.join(timeout=3.0)
    t_ds.join(timeout=3.0)


# --- Phase showcases ---

def run_phase1_showcase():
    print("\n[Phase 1] Core Foundation")
    c1 = VectorClock("A")
    c2 = VectorClock("B")
    c1.tick(); c2.tick(); c1.update(c2.clock)
    show("VectorClock state", {"A": c1.clock, "B": c2.clock})

    mh_a = MessageHandler("A"); mh_b = MessageHandler("B")
    msg = mh_a.send_message({"hello": 1}, "B", is_emergency=False)
    mh_b.receive_message(msg)
    show("CausalMessage stats", mh_b.get_message_stats())

    fcfs = FCFSConsistencyPolicy()
    job_id = str(uuid4())
    op_submit = {"operation_id": f"op-job-{job_id}", "operation_type": "job_submission", "vector_clock": c1.clock.copy(), "job_id": job_id}
    op_r1 = {"operation_id": f"op-r1-{job_id}", "operation_type": "result_submission", "vector_clock": c1.clock.copy(), "job_id": job_id}
    op_r2 = {"operation_id": f"op-r2-{job_id}", "operation_type": "result_submission", "vector_clock": c1.clock.copy(), "job_id": job_id}
    s1 = fcfs.apply_policy(op_submit, context={}); r1 = fcfs.apply_policy(op_r1, context={}); r2 = fcfs.apply_policy(op_r2, context={})
    show("FCFS results", {"submit": s1, "first": r1, "second_rejected": not r2})


def run_phase2_showcase():
    print("\n[Phase 2] Node Infrastructure")
    broker = ExecutorBroker("demo_broker")
    caps = ExecutorCapabilities(emergency_capable=True, max_concurrent_jobs=1)
    ex = SimpleEmergencyExecutor("exec_p2", capabilities=caps)
    ex.start()
    broker.register_executor(ex.node_id, host="127.0.0.1", port=9000, capabilities={"python"})
    job = JobInfo(job_id=uuid4(), data={"task": "compute"})
    broker.submit_job(job)
    time.sleep(0.5)
    show("P2 status", {"executors": list(broker.executors.keys()), "completed_jobs": list(broker.completed_jobs)})
    ex.stop()


def run_phase3_showcase():
    print("\n[Phase 3] Core Implementation")
    caps = ExecutorCapabilities(emergency_capable=True, max_concurrent_jobs=2)
    e1 = EnhancedVectorClockExecutor("vc1", caps); e2 = EnhancedVectorClockExecutor("vc2", caps)
    e1.register_peer_executor("vc2", e2); e2.register_peer_executor("vc1", e1)
    e1.start(); e2.start()
    j1 = e1.submit_causal_job({"task": "pre"}); j2 = e1.submit_causal_job({"task": "an"}, dependencies={j1}); j3 = e2.submit_causal_job({"task": "rep"}, dependencies={j2})
    time.sleep(1.0)
    s1 = e1.get_causal_execution_status(); s2 = e2.get_causal_execution_status()
    show("Causal jobs", {"e1": list(s1["causal_jobs"].keys()), "e2": list(s2["causal_jobs"].keys())})
    b = VectorClockBroker("vc_broker")
    b.register_peer_broker(b.broker_id, b)
    job = JobInfo(job_id=uuid4(), data={"task": "agg"})
    b.submit_distributed_job(job)
    show("Broker clock", b.vector_clock.clock)
    e1.stop(); e2.stop()


def run_phase4_showcase():
    print("\n[Phase 4] UCP Integration")
    prod = ProductionVectorClockExecutor(host=["127.0.0.1"], port=9999, rootdir="/tmp", executor_id="prod_1", mode=ProductionMode.DEVELOPMENT)
    prod.start()
    job_id = uuid4(); first = prod.handle_result_submission(job_id, {"ok": True}); second = prod.handle_result_submission(job_id, {"ok": False})

    cluster_broker = VectorClockBroker("cluster_broker")
    coord = MultiBrokerCoordinator("coord_1"); coord.register_broker_cluster("A", cluster_broker)
    op_ok = coord.coordinate_global_operation({"operation": "sync", "priority": 1})

    repl = DatastoreReplicationManager("repl_1"); repl.register_datastore("ds1", "127.0.0.1", 7001, capacity=2 * 1024 * 1024); repl.register_datastore("ds2", "127.0.0.1", 7002, capacity=2 * 1024 * 1024)
    repl.start(); stored = repl.store_data("key", b"ucp-all-phases", replication_factor=2); fetched_ok = repl.retrieve_data("key") == b"ucp-all-phases"

    from rec.Phase3_Core_Implementation.emergency_integration import EmergencyIntegrationManager
    emergency_mgr = EmergencyIntegrationManager("emergency-coord_1")
    # Ensure emergency manager manages at least one node (compliance)
    emergency_mgr.register_node("prod_1", prod, {"execution", "emergency_response"})
    emergency_mgr.register_node("cluster_broker", cluster_broker, {"broker_coordination"})

    integ = SystemIntegrationFramework("system_all_phases")
    # Register missing components to raise compliance: executor + emergency manager
    integ.register_executor(prod)
    integ.register_emergency_manager(emergency_mgr)
    integ.register_coordinator(coord); integ.register_broker(cluster_broker); integ.register_datastore_replication(repl)
    integ.start_system(); compliant = integ.verify_ucp_compliance(); status = integ.get_system_status()

    # Normalize emergency context in prod status
    es = prod.get_status();
    if es.get("current_emergency") and not isinstance(es["current_emergency"], dict):
        ce = es["current_emergency"]; es["current_emergency"] = {"type": getattr(ce, "emergency_type", None), "level": getattr(getattr(ce, "level", None), "name", None)}

    show("Phase 4 status", {
        "prod": {"status": es, "fcfs_first": first, "fcfs_second_rejected": not second},
        "coord": {"op_ok": op_ok, "clusters": list(coord.get_global_status()["broker_clusters"].keys())},
        "repl": {"stored": stored, "fetched_ok": fetched_ok, "strategy": repl.get_replication_status()["strategy"]},
        "integration": {"compliant": compliant, "state": status["state"]},
    })

    # Stop components
    prod.stop(); repl.stop(); integ.stop_system(); coord.stop(); emergency_mgr.stop()


def main():
    print("Full UCP All-Phases Scenario")
    ds, br, ex, t_ds, t_br, t_ex = start_ucp_nodes()

    try:
        run_phase1_showcase()
        run_phase2_showcase()
        run_phase3_showcase()
        run_phase4_showcase()
    finally:
        stop_ucp_nodes(ds, br, ex, t_ds, t_br, t_ex)

    print("\nScenario complete.")


if __name__ == "__main__":
    main()
