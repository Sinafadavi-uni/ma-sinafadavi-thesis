"""
UCP Networked Cluster Demo (no Phase1-4 libs):
- Starts real FastAPI/Uvicorn services for Datastore, Broker, and Executor from rec/nodes
- Verifies they listen on ports via /ping
- Shuts them down cleanly

Run (from repo root):
  PYTHONPATH=. python3 rec/scenario/ucp_network_cluster_demo.py
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Tuple

import requests

from rec.nodes.datastore import Datastore
from rec.nodes.broker import Broker
from rec.nodes.executor import Executor


logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("ucp_network_demo")


def wait_for_ping(host: str, port: int, timeout_s: float = 15.0) -> Tuple[bool, int]:
    """Poll /ping until success or timeout; returns (ok, http_status)."""
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


def main():
    host = ["127.0.0.1"]
    ds_port = 8002
    br_port = 8000
    ex_port = 8001
    ds_root = "/tmp/ucp_demo_datastore.d"
    ex_root = "/tmp/ucp_demo_executor.d"

    # Construct nodes
    datastore = Datastore(host, ds_port, ds_root)
    broker = Broker(host, br_port)
    executor = Executor(host, ex_port, ex_root)

    # Start nodes in background threads using their blocking run() methods
    t_ds = threading.Thread(target=datastore.run, daemon=True, name="datastore.run")
    t_br = threading.Thread(target=broker.run, daemon=True, name="broker.run")
    t_ex = threading.Thread(target=executor.run, daemon=True, name="executor.run")

    LOG.info("Starting Datastore, Broker, Executor...")
    t_ds.start(); time.sleep(0.2)
    t_br.start(); time.sleep(0.2)
    t_ex.start();

    # Verify ports are live via /ping
    ok_ds, code_ds = wait_for_ping("127.0.0.1", ds_port)
    ok_br, code_br = wait_for_ping("127.0.0.1", br_port)
    ok_ex, code_ex = wait_for_ping("127.0.0.1", ex_port)

    print("\n=== UCP Networked Services ===")
    print({
        "datastore": {"port": ds_port, "ok": ok_ds, "status": code_ds},
        "broker": {"port": br_port, "ok": ok_br, "status": code_br},
        "executor": {"port": ex_port, "ok": ok_ex, "status": code_ex},
    })

    # Let them run briefly (executor may attempt broker registration via zeroconf)
    time.sleep(1.5)

    # Stop services
    LOG.info("Stopping services...")
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

    # Join threads with timeouts
    t_ex.join(timeout=3.0)
    t_br.join(timeout=3.0)
    t_ds.join(timeout=3.0)

    print("Done.")


if __name__ == "__main__":
    main()
