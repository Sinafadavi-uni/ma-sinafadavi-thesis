"""
extended_executorbroker.py
==========================

This module contains a demonstration implementation of an extended broker for
the Urban Compute Platform (UCP) that adds two key features missing from the
baseline code:

1. **Job redeployment on executor failure.**  When an executor node fails
   (e.g. because heartbeats stop), the broker reassigns any running jobs from
   the failed executor back into the queue so they can be picked up by a
   healthy executor.  This ensures that work is not lost if a node
   disappears.

2. **Metadata replication.**  The broker owns a ``MetadataStore`` (from
   ``metadata_store.py``) and periodically synchronises its contents with
   peer brokers.  This mechanism prevents metadata (e.g. job definitions or
   data descriptors) from becoming undiscoverable—a requirement of the UCP
   data replication specification.  In a production system the list of peer
   brokers would be discovered through service discovery or configuration;
   here it is provided explicitly.

The implementation below is deliberately self‑contained and does not depend
on the original UCP source tree.  It is intended as a conceptual starting
point rather than a drop‑in replacement.  You can integrate the ideas into
your existing classes by adapting the redeployment and metadata sync logic
shown here.
"""

import threading
import time
import uuid
from queue import Queue, Empty
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, Any, List

from .metadata_store import MetadataStore
try:
    # Import replication policy support if available.  The broker forwards
    # this to the metadata store so that operators can customise which
    # keys are synchronised and how frequently.
    from .replication_policy import ReplicationPolicyManager  # type: ignore
except ImportError:
    class ReplicationPolicyManager:
        pass


@dataclass
class JobInfo:
    """A simple representation of a job submitted to the broker."""
    job_id: str
    data: Dict[str, Any]
    result: Optional[Any] = None
    assigned_executor: Optional[str] = None
    vector_clock_snapshot: Optional[Dict[str, int]] = None


class ExtendedExecutorBroker:
    """A broker that supports job redeployment and metadata replication."""

    def __init__(self, broker_id: str,
                 peer_brokers: Optional[List["ExtendedExecutorBroker"]] = None,
                 heartbeat_timeout: float = 60.0,
                 metadata_sync_interval: float = 10.0,
                 replication_policy_manager: Optional[ReplicationPolicyManager] = None) -> None:
        self.broker_id = broker_id
        self.heartbeat_timeout = heartbeat_timeout
        self.metadata_sync_interval = metadata_sync_interval

        # Executor state: maps executor_id -> last heartbeat time
        self.executors: Dict[str, float] = {}
        self.executor_lock = threading.RLock()

        # Job queues and mappings
        self.job_queue: "Queue[JobInfo]" = Queue()
        self.running_jobs: Dict[str, JobInfo] = {}  # job_id -> JobInfo
        self.executor_jobs: Dict[str, Set[str]] = {}  # executor_id -> set(job_id)

        # Track completed job results for FCFS deduplication
        self.completed_results: Dict[str, Any] = {}
        self.completed_lock = threading.RLock()

        # Metadata store.  If a replication policy manager is supplied,
        # pass it to the store so that only selected keys are synchronised.
        self.metadata_store = MetadataStore(policy_manager=replication_policy_manager)

        # Peer brokers for metadata sync
        self.peer_brokers: List[ExtendedExecutorBroker] = peer_brokers or []

        # Internal state
        self.should_exit = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.timeout_thread: Optional[threading.Thread] = None
        self.metadata_sync_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Executor management
    # ------------------------------------------------------------------
    def register_executor(self, executor_id: str) -> None:
        """Register a new executor with the broker."""
        with self.executor_lock:
            self.executors[executor_id] = time.time()
            self.executor_jobs.setdefault(executor_id, set())

    def heartbeat_executor(self, executor_id: str) -> None:
        """Record a heartbeat from an executor."""
        with self.executor_lock:
            if executor_id in self.executors:
                self.executors[executor_id] = time.time()

    def _check_executor_timeouts(self) -> None:
        """Background worker that removes timed‑out executors and redeploys jobs."""
        while not self.should_exit:
            now = time.time()
            to_remove: List[str] = []
            with self.executor_lock:
                for eid, last_seen in self.executors.items():
                    if now - last_seen > self.heartbeat_timeout:
                        to_remove.append(eid)
            for eid in to_remove:
                self._handle_executor_failure(eid)
            time.sleep(self.heartbeat_timeout / 3)

    def _handle_executor_failure(self, executor_id: str) -> None:
        """Handle executor failure by redeploying its jobs and removing it."""
        # Remove executor
        with self.executor_lock:
            self.executors.pop(executor_id, None)
        # Redeploy any running jobs
        job_ids = self.executor_jobs.pop(executor_id, set())
        for job_id in job_ids:
            job = self.running_jobs.pop(job_id, None)
            if job:
                job.assigned_executor = None
                self.job_queue.put(job)
        # Note: we deliberately keep completed_results untouched; results from
        # a resurrected executor will be checked against this set in
        # handle_result_submission.

    # ------------------------------------------------------------------
    # Job submission and scheduling
    # ------------------------------------------------------------------
    def submit_job(self, data: Dict[str, Any]) -> str:
        """Submit a new job to the broker.  Returns the job ID."""
        job_id = str(uuid.uuid4())
        job = JobInfo(job_id=job_id, data=data)
        self.job_queue.put(job)
        # Store metadata so that other brokers can discover this job
        self.metadata_store.update(f"job:{job_id}", {
            "broker": self.broker_id,
            "status": "queued",
            "data": data
        })
        return job_id

    def _scheduler_loop(self) -> None:
        """Background worker that assigns jobs to available executors."""
        while not self.should_exit:
            try:
                job = self.job_queue.get(timeout=1.0)
            except Empty:
                continue
            # pick any available executor
            executor_id = self._pick_executor()
            if executor_id:
                job.assigned_executor = executor_id
                # track running job
                self.running_jobs[job.job_id] = job
                self.executor_jobs.setdefault(executor_id, set()).add(job.job_id)
                # update metadata to show assignment
                self.metadata_store.update(f"job:{job.job_id}", {
                    "broker": self.broker_id,
                    "status": "running",
                    "executor": executor_id,
                    "data": job.data
                })
                # Simulate dispatch; in a real system this would send the job over
                # the network to the executor.
                # Here we just mark it as running.
            else:
                # no executor available, requeue after a short delay
                self.job_queue.put(job)
                time.sleep(1.0)

    def _pick_executor(self) -> Optional[str]:
        """Select an executor with the smallest number of running jobs."""
        with self.executor_lock:
            if not self.executors:
                return None
            # choose executor with fewest jobs
            return min(self.executors.keys(), key=lambda eid: len(self.executor_jobs.get(eid, set())))

    def handle_result_submission(self, job_id: str, result: Any) -> bool:
        """Record a job result.  Implements FCFS deduplication.

        Returns True if this is the first result received for the given job.
        Subsequent submissions are ignored and return False.
        """
        with self.completed_lock:
            if job_id in self.completed_results:
                # duplicate result; ignore
                return False
            self.completed_results[job_id] = result
        # cleanup running jobs mapping
        job = self.running_jobs.pop(job_id, None)
        if job and job.assigned_executor:
            exec_jobs = self.executor_jobs.get(job.assigned_executor)
            if exec_jobs:
                exec_jobs.discard(job_id)
        # update metadata
        self.metadata_store.update(f"job:{job_id}", {
            "broker": self.broker_id,
            "status": "completed",
            "result": result
        })
        return True

    # ------------------------------------------------------------------
    # Metadata synchronisation
    # ------------------------------------------------------------------
    def _metadata_sync_loop(self) -> None:
        """Periodically synchronise metadata with peer brokers."""
        while not self.should_exit:
            for peer in self.peer_brokers:
                # push our metadata to peer (simple merge)
                peer.metadata_store.sync_with_peer(self.metadata_store)
                # pull peer metadata into our store
                self.metadata_store.sync_with_peer(peer.metadata_store)
            time.sleep(self.metadata_sync_interval)

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start background worker threads."""
        self.should_exit = False
        if not self.scheduler_thread or not self.scheduler_thread.is_alive():
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()
        if not self.timeout_thread or not self.timeout_thread.is_alive():
            self.timeout_thread = threading.Thread(target=self._check_executor_timeouts, daemon=True)
            self.timeout_thread.start()
        if self.peer_brokers and (not self.metadata_sync_thread or not self.metadata_sync_thread.is_alive()):
            self.metadata_sync_thread = threading.Thread(target=self._metadata_sync_loop, daemon=True)
            self.metadata_sync_thread.start()

    def stop(self) -> None:
        """Signal worker threads to stop and wait for them to finish."""
        self.should_exit = True
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=2.0)
        if self.timeout_thread:
            self.timeout_thread.join(timeout=2.0)
        if self.metadata_sync_thread:
            self.metadata_sync_thread.join(timeout=2.0)

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------
    def get_job_status(self, job_id: str) -> Optional[str]:
        meta = self.metadata_store.get(f"job:{job_id}")
        if meta:
            return meta.get("status")
        return None

    def get_metadata_snapshot(self) -> Dict[str, Any]:
        return self.metadata_store.snapshot()