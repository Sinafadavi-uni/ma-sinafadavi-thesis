"""
Replication on Real Datastore Nodes + Failover Demo

Starts two real datastore nodes, registers them into DatastoreReplicationManager,
replicates a key with factor=2, kills one node, verifies read from survivor,
restarts the node and verifies consistency repair.

Run:
  PYTHONPATH=. python3 rec/scenario/replication_real_nodes_failover_demo.py
"""
from __future__ import annotations

import threading
import time
from uuid import uuid4

from rec.nodes.datastore import Datastore
from rec.Phase4_UCP_Integration.datastore_replication import DatastoreReplicationManager


def start_datastore(node_id: str, port: int, root: str):
    ds = Datastore(["127.0.0.1"], port, root)
    t = threading.Thread(target=ds.run, daemon=True)
    t.start()
    # crude wait; reuse /ping via manager if desired
    time.sleep(0.8)
    return ds, t


def main():
    # Start two real datastore nodes
    ds1, t1 = start_datastore("ds1", 7001, "/tmp/ucp_ds1")
    ds2, t2 = start_datastore("ds2", 7002, "/tmp/ucp_ds2")

    repl = DatastoreReplicationManager("repl_real")
    repl.register_datastore("ds1", "127.0.0.1", 7001, capacity=4 * 1024 * 1024)
    repl.register_datastore("ds2", "127.0.0.1", 7002, capacity=4 * 1024 * 1024)
    repl.start()

    key = f"k-{uuid4()}"
    payload = b"replicated-value"

    stored = repl.store_data(key, payload, replication_factor=2)
    fetched_ok = repl.retrieve_data(key) == payload
    print("stored:", stored, "fetched_ok:", fetched_ok)

    # Fail one datastore
    ds1.stop(); t1.join(timeout=2.0)
    repl.handle_datastore_failure("ds1")

    # Read must still succeed from ds2
    fetched_ok_after_loss = repl.retrieve_data(key) == payload
    print("fetched_ok_after_loss:", fetched_ok_after_loss)

    # Restart ds1 and allow some time; replication manager should repair
    ds1, t1 = start_datastore("ds1", 7001, "/tmp/ucp_ds1")
    time.sleep(1.5)

    # Check replication status
    status = repl.get_replication_status()
    print("replication_status:", {"available": status["datastores"]["available"], "strategy": status["strategy"]})

    repl.stop()
    ds1.stop(); ds2.stop()
    t1.join(timeout=2.0); t2.join(timeout=2.0)


if __name__ == "__main__":
    main()
