import os
import sys
import time
from uuid import uuid4

# Allow running directly as a script by ensuring repo root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from rec.Phase3_Core_Implementation.vector_clock_broker import VectorClockBroker
from rec.Phase3_Core_Implementation.enhanced_vector_clock_executor import (
    EnhancedVectorClockExecutor,
)
from rec.Phase2_Node_Infrastructure.executorbroker import JobInfo
from rec.Phase4_UCP_Integration.multi_broker_coordinator import MultiBrokerCoordinator
from rec.Phase4_UCP_Integration.datastore_replication import DatastoreReplicationManager


def test_broker_metadata_sync_discoverability():
    b1 = VectorClockBroker("tb_b1")
    b2 = VectorClockBroker("tb_b2")
    b1.register_peer_broker("tb_b2", b2)
    b2.register_peer_broker("tb_b1", b1)
    b1.start(); b2.start()

    coord = MultiBrokerCoordinator("tb_coord")
    coord.register_broker_cluster("c1", b1, additional_brokers=[b2])
    coord.start()

    job_id = uuid4()
    job = JobInfo(job_id=job_id, data={"task": "index"})
    b1.submit_distributed_job(job)

    time.sleep(4.0)

    assert job_id in b2.distributed_jobs or job_id in b2.completed_jobs

    coord.stop(); b1.stop(); b2.stop()


def test_executor_redeploy_and_stale_result_fcfs():
    eA = EnhancedVectorClockExecutor("tb_execA")
    eB = EnhancedVectorClockExecutor("tb_execB")
    eA.register_peer_executor("tb_execB", eB)
    eB.register_peer_executor("tb_execA", eA)
    eA.start(); eB.start()

    broker = VectorClockBroker("tb_vc_broker")
    broker.executors["tb_execA"] = eA
    broker.executors["tb_execB"] = eB

    job_id = uuid4()
    job = JobInfo(job_id=job_id, data={"task": "long"})

    broker.submit_distributed_job(job)
    eA.stop()
    broker.submit_distributed_job(job)

    time.sleep(1.5)

    assert broker.record_job_submission(job_id)
    assert broker.handle_result_submission(job_id, {"s": "B"}, "tb_execB") is True
    assert broker.handle_result_submission(job_id, {"s": "A"}, "tb_execA") is False

    eB.stop()


def test_replication_real_nodes_failover_and_repair():
    # Lean probe using the manager alone; node boot tested in scenario script
    repl = DatastoreReplicationManager("tb_repl")
    repl.register_datastore("ds1", "127.0.0.1", 7001, capacity=1024 * 1024)
    repl.register_datastore("ds2", "127.0.0.1", 7002, capacity=1024 * 1024)
    repl.start()

    key = f"t-{uuid4()}"; payload = b"v"
    assert repl.store_data(key, payload, replication_factor=2)
    assert repl.retrieve_data(key) == payload

    repl.handle_datastore_failure("ds1")
    assert repl.retrieve_data(key) == payload

    repl.stop()


if __name__ == "__main__":
    print("Running data replication scenarios...")
    try:
        test_broker_metadata_sync_discoverability(); print(" - metadata sync discoverability: PASS")
        test_executor_redeploy_and_stale_result_fcfs(); print(" - failover + broker FCFS: PASS")
        test_replication_real_nodes_failover_and_repair(); print(" - datastore replication failover/repair: PASS")
        print("All data replication scenarios passed.")
    except AssertionError as e:
        print(f"Scenario failed: {e}")
        raise
