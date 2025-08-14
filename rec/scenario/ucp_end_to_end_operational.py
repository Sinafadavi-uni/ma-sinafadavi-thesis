"""
UCP End-to-End Operational Scenario (rec/ only, no Phase1–4)
- Starts Datastore(8002), Broker(8000), Executor(8001)
- Waits for /ping, registers executor with broker
- Uploads a tiny stdin and dummy wasm name (executor will handle per implementation)
- Submits a minimal JobInfo to /job/submit/{job_id}
- Waits briefly, then prints broker/executor counts and tries to list job ids
- Shuts down services cleanly

Run:
  PYTHONPATH=. python3 rec/scenario/ucp_end_to_end_operational.py
"""
from __future__ import annotations

import io
import logging
import threading
import time
from uuid import uuid4
from typing import Tuple

import requests

from rec.model import JobInfo, Capabilities, Address
from rec.nodes.datastore import Datastore
from rec.nodes.broker import Broker
from rec.nodes.executor import Executor

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("ucp_e2e")


def wait_for_ping(host: str, port: int, timeout_s: float = 20.0) -> Tuple[bool, int]:
    url = f"http://{host}:{port}/ping"
    deadline = time.time() + timeout_s
    last_status = 0
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=1.5)
            last_status = r.status_code
            if r.ok:
                return True, r.status_code
        except Exception:
            pass
        time.sleep(0.3)
    return False, last_status


def wait_until_executor_broker(executor: Executor, timeout_s: float = 20.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if getattr(executor, "broker", None) is not None:
            return True
        time.sleep(0.3)
    return False


def upload_inputs_via_broker(broker_host: str, broker_port: int) -> None:
    # Upload exec.wasm and stdin.txt through broker /data endpoint (multipart)
    url_base = f"http://{broker_host}:{broker_port}/data"
    files = {
        "data": ("exec.wasm", b"\x00asm minimal", "application/wasm"),
    }
    r = requests.put(f"{url_base}/exec.wasm", files=files)
    r.raise_for_status()

    files = {
        "data": ("stdin.txt", b"hello from ucp", "text/plain"),
    }
    r = requests.put(f"{url_base}/stdin.txt", files=files)
    r.raise_for_status()


def submit_simple_job(broker_host: str, broker_port: int) -> str:
    url = f"http://{broker_host}:{broker_port}/job/submit/{{job_id}}"
    job_id = str(uuid4())
    job = JobInfo(
        # Provide wasm_bin as a named tuple value so broker/executor pathing is valid
        wasm_bin=("exec.wasm", "exec.wasm"),
        wasm_bin_is_named=True,
        # Provide stdin as named tuple
        stdin=("stdin.txt", "stdin.txt"),
        stdin_is_named=True,
        args=[],
        env={},
        zip_results={"/": "/"},
        named_results={},
        capabilities=Capabilities(
            memory=0,
            disk=0,
            cpu_load=100.0,
            cpu_cores=1,
            cpu_freq=0.0,
            has_battery=True,
            power=0,
        ),
        result_addr=Address(host="", port=0),  # store in datastore
        delete=True,
    )
    # Wrap into {"job_info": {...}} so FastAPI binds the body parameter correctly
    r = requests.put(url.format(job_id=job_id), json={"job_info": job.model_dump()})
    if not r.ok:
        print("Submit error:", r.status_code, r.text)
        r.raise_for_status()
    return job_id


def main():
    host = ["127.0.0.1"]
    ds_port, br_port, ex_port = 8002, 8000, 8001
    ds_root = "/tmp/ucp_demo_datastore.d"
    ex_root = "/tmp/ucp_demo_executor.d"

    # Start services
    datastore = Datastore(host, ds_port, ds_root)
    broker = Broker(host, br_port)
    executor = Executor(host, ex_port, ex_root)

    t_ds = threading.Thread(target=datastore.run, daemon=True)
    t_br = threading.Thread(target=broker.run, daemon=True)
    t_ex = threading.Thread(target=executor.run, daemon=True)
    t_ds.start(); time.sleep(0.2); t_br.start(); time.sleep(0.2); t_ex.start()

    ok_ds, _ = wait_for_ping("127.0.0.1", ds_port)
    ok_br, _ = wait_for_ping("127.0.0.1", br_port)
    ok_ex, _ = wait_for_ping("127.0.0.1", ex_port)

    print("\n=== Boot ===", {"datastore": ok_ds, "broker": ok_br, "executor": ok_ex})

    # Ensure the executor registers with the broker (sets executor.broker)
    # Although Executor.run spawns registration thread, call explicitly and wait.
    executor.register_with_broker()
    if not wait_until_executor_broker(executor):
        print("Executor failed to register with broker in time")
        executor.stop(); broker.stop(); datastore.stop()
        t_ex.join(timeout=3.0); t_br.join(timeout=3.0); t_ds.join(timeout=3.0)
        return

    # Submit a simple job
    job_id = submit_simple_job("127.0.0.1", br_port)
    print("Submitted job:", job_id)

    # Give the system a short time to schedule
    time.sleep(2.0)

    # Quick sanity: ask broker executor count
    r = requests.get(f"http://127.0.0.1:{br_port}/executors/count")
    print("Executors registered:", r.json())

    # Attempt to list executor jobs
    r = requests.get(f"http://127.0.0.1:{ex_port}/job/list")
    print("Executor jobs:", r.json())

    # Stop
    executor.stop(); broker.stop(); datastore.stop()
    t_ex.join(timeout=3.0); t_br.join(timeout=3.0); t_ds.join(timeout=3.0)
    print("Done.")


if __name__ == "__main__":
    main()
