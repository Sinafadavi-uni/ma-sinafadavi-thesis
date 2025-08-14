"""
Multi-Broker Metadata Sync Demo

Shows periodic metadata sync between two VectorClockBrokers within one
cluster so metadata created on B1 becomes discoverable on B2 (and vice versa).

Run:
  PYTHONPATH=. python3 rec/scenario/multi_broker_metadata_sync_demo.py
"""
from __future__ import annotations

import time
from uuid import uuid4

from rec.Phase3_Core_Implementation.vector_clock_broker import VectorClockBroker
from rec.Phase4_UCP_Integration.multi_broker_coordinator import MultiBrokerCoordinator
from rec.Phase2_Node_Infrastructure.executorbroker import JobInfo


def main():
    # Set up two brokers and coordinator
    b1 = VectorClockBroker("broker_A")
    b2 = VectorClockBroker("broker_B")
    b1.register_peer_broker("broker_B", b2)
    b2.register_peer_broker("broker_A", b1)
    b1.start(); b2.start()

    coord = MultiBrokerCoordinator("coord_sync")
    coord.register_broker_cluster("cluster1", b1, additional_brokers=[b2])
    coord.start()

    # Submit job on B1 only
    job_id = uuid4()
    job = JobInfo(job_id=job_id, data={"task": "index"})
    b1.submit_distributed_job(job)

    # Wait beyond broker sync interval (3s) to allow background metadata sync
    time.sleep(4.0)

    # Simple observability via broker internal registries
    discoverable_on_b2 = job_id in b2.completed_jobs or job_id in b2.distributed_jobs
    print("B1 -> B2 discoverable:", bool(discoverable_on_b2))

    # Now B2 creates a job and sync back
    job2_id = uuid4()
    job2 = JobInfo(job_id=job2_id, data={"task": "agg"})
    b2.submit_distributed_job(job2)
    time.sleep(4.0)

    discoverable_on_b1 = job2_id in b1.completed_jobs or job2_id in b1.distributed_jobs
    print("B2 -> B1 discoverable:", bool(discoverable_on_b1))

    coord.stop(); b1.stop(); b2.stop()


if __name__ == "__main__":
    main()
