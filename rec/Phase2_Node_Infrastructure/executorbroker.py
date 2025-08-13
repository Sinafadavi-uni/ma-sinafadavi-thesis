"""
File 5: ExecutorBroker - Core Broker Functionality
Phase 2: Node Infrastructure

Core broker implementation for managing distributed executors with vector clock
coordination and emergency response capabilities.

Key Features:
- Executor registration and management
- Job scheduling with vector clock ordering
- Emergency-aware job prioritization
- Capability-based executor selection
- Heartbeat monitoring and health management

Based on UCP ExecutorBroker with enhancements for:
- Vector clock synchronization
- Emergency context propagation
- Causal job ordering
"""

import time
import threading
import random
from typing import Dict, Optional, Set
from uuid import UUID, uuid4
from queue import Queue, Empty
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging

# Phase 1 imports
import sys
import os
phase1_path = os.path.join(os.path.dirname(__file__), '..', 'Phase1_Core_Foundation')
sys.path.insert(0, phase1_path)

from rec.Phase1_Core_Foundation.vector_clock import VectorClock, EmergencyContext, create_emergency
from rec.Phase1_Core_Foundation.causal_message import CausalMessage, MessageHandler
from rec.Phase1_Core_Foundation.causal_consistency import CausalConsistencyManager

LOG = logging.getLogger(__name__)

@dataclass
class ExecutorInfo:
    id: UUID
    host: str
    port: int
    last_update: float = field(default_factory=time.time)
    capabilities: Set[str] = field(default_factory=set)
    vector_clock: VectorClock = None
    emergency_context: Optional[EmergencyContext] = None

    def __post_init__(self):
        if self.vector_clock is None:
            self.vector_clock = VectorClock(str(self.id))

@dataclass 
class JobInfo:
    job_id: UUID
    data: dict
    capabilities: Set[str] = field(default_factory=set)
    emergency_context: Optional[EmergencyContext] = None
    vector_clock: Optional[dict] = None
    result_addr: Optional[str] = None

@dataclass
class QueuedJob:
    job_info: JobInfo
    wait_for: Set[UUID] = field(default_factory=set)
    submitted_at: float = field(default_factory=time.time)
    causal_message: Optional[CausalMessage] = None

class ExecutorBroker:
    def __init__(self, broker_id: str = None):
        self.broker_id = broker_id or str(uuid4())
        self.vector_clock = VectorClock(self.broker_id)

        self.executors: Dict[UUID, ExecutorInfo] = {}
        self.executor_lock = threading.RLock()

        self.queued_jobs = Queue()
        self.completed_jobs: Set[UUID] = set()
        self.completed_lock = threading.RLock()

        self.current_emergency: Optional[EmergencyContext] = None
        self.message_handler = MessageHandler(self.broker_id)
        self.consistency_manager = CausalConsistencyManager(self.broker_id)

        self.should_exit = False
        self.scheduler_thread = None

        LOG.info(f"ExecutorBroker {self.broker_id} initialized")

    def register_executor(self, executor_id: UUID, host: str, port: int, capabilities: Set[str] = None) -> bool:
        self.vector_clock.tick()
        capabilities = capabilities or set()

        executor_info = ExecutorInfo(
            id=executor_id,
            host=host,
            port=port,
            capabilities=capabilities
        )

        with self.executor_lock:
            self.executors[executor_id] = executor_info
            LOG.info(f"Executor {executor_id} registered with capabilities: {capabilities}")

        self._synchronize_with_executor(executor_info)
        return True

    def heartbeat_executor(self, executor_id: UUID, capabilities: Set[str] = None,
                          vector_clock_state: dict = None, emergency_context: EmergencyContext = None) -> bool:
        with self.executor_lock:
            executor = self.executors.get(executor_id)
            if executor is None:
                LOG.warning(f"Heartbeat from unregistered executor {executor_id}")
                return False

            executor.last_update = time.time()
            if capabilities is not None:
                executor.capabilities = capabilities
            if emergency_context is not None:
                executor.emergency_context = emergency_context
            if vector_clock_state:
                executor.vector_clock.update(vector_clock_state)
                self.vector_clock.update(vector_clock_state)

            self.vector_clock.tick()
            LOG.debug(f"Heartbeat processed for executor {executor_id}")
            return True

    def submit_job(self, job_info: JobInfo, wait_for: Set[UUID] = None) -> UUID:
        self.vector_clock.tick()
        job_info.vector_clock = self.vector_clock.clock.copy()

        if self.current_emergency and self.current_emergency.is_critical():
            job_info.emergency_context = self.current_emergency
            LOG.info(f"Job {job_info.job_id} marked as emergency")

        causal_msg = CausalMessage(
            content=job_info.data,
            sender_id=self.broker_id,
            vector_clock=self.vector_clock.clock.copy(),
            message_type="emergency" if job_info.emergency_context and job_info.emergency_context.is_critical() else "normal",
            priority=10 if job_info.emergency_context and job_info.emergency_context.is_critical() else 1
        )

        queued_job = QueuedJob(
            job_info=job_info,
            wait_for=wait_for or set(),
            causal_message=causal_msg
        )

        if job_info.emergency_context and job_info.emergency_context.is_critical():
            executor = self._find_capable_executor(job_info.capabilities, emergency=True)
            if executor:
                return self._execute_job_on_executor(job_info, executor)

        self.queued_jobs.put(queued_job)
        LOG.debug(f"Job {job_info.job_id} queued")
        return job_info.job_id

    def set_emergency_mode(self, emergency_type: str, priority_level: str) -> None:
        self.vector_clock.tick()
        self.current_emergency = create_emergency(emergency_type, priority_level)

        with self.executor_lock:
            for executor in self.executors.values():
                executor.emergency_context = self.current_emergency

        LOG.warning(f"Emergency mode activated: {emergency_type} ({priority_level})")

    def clear_emergency_mode(self) -> None:
        self.vector_clock.tick()
        self.current_emergency = None

        with self.executor_lock:
            for executor in self.executors.values():
                executor.emergency_context = None

        LOG.info("Emergency mode cleared")

    def job_completed(self, job_id: UUID) -> None:
        self.vector_clock.tick()
        with self.completed_lock:
            self.completed_jobs.add(job_id)
        LOG.debug(f"Job {job_id} completed")

    def get_executor_count(self) -> int:
        self._prune_executor_list()
        with self.executor_lock:
            return len(self.executors)

    def start(self) -> None:
        if self.scheduler_thread is None or not self.scheduler_thread.is_alive():
            self.should_exit = False
            self.scheduler_thread = threading.Thread(
                target=self._job_scheduler,
                daemon=True,
                name=f"broker-scheduler-{self.broker_id}"
            )
            self.scheduler_thread.start()
            LOG.info(f"ExecutorBroker {self.broker_id} started")

    def stop(self) -> None:
        self.should_exit = True
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5.0)
        LOG.info(f"ExecutorBroker {self.broker_id} stopped")

    def _find_capable_executor(self, required_caps: Set[str], emergency: bool = False) -> Optional[ExecutorInfo]:
        self._prune_executor_list()
        with self.executor_lock:
            capable = [e for e in self.executors.values() if required_caps.issubset(e.capabilities)]

        if not capable:
            return None

        if emergency:
            non_emergency = [e for e in capable if e.emergency_context is None or not e.emergency_context.is_critical()]
            if non_emergency:
                capable = non_emergency

        return random.choice(capable)

    def _execute_job_on_executor(self, job_info: JobInfo, executor: ExecutorInfo) -> UUID:
        self.vector_clock.update(executor.vector_clock.clock)
        self.vector_clock.tick()

        msg = CausalMessage(
            content=job_info.data,
            sender_id=self.broker_id,
            vector_clock=self.vector_clock.clock.copy(),
            message_type="emergency" if job_info.emergency_context and job_info.emergency_context.is_critical() else "normal"
        )

        LOG.info(f"Executing job {job_info.job_id} on executor {executor.id}")
        return job_info.job_id

    def _synchronize_with_executor(self, executor: ExecutorInfo) -> None:
        self.vector_clock.update(executor.vector_clock.clock)
        executor.vector_clock.update(self.vector_clock.clock)

    def _prune_executor_list(self) -> None:
        now = time.time()
        timeout = 130
        to_remove = []

        with self.executor_lock:
            for eid, executor in self.executors.items():
                if (now - executor.last_update) > timeout:
                    to_remove.append(eid)

        for eid in to_remove:
            with self.executor_lock:
                self.executors.pop(eid, None)
                LOG.warning(f"Removed unresponsive executor {eid}")

    def _job_scheduler(self) -> None:
        LOG.info(f"Job scheduler started for broker {self.broker_id}")
        while not self.should_exit:
            try:
                job = self.queued_jobs.get(timeout=1.0)
                with self.completed_lock:
                    deps_ok = job.wait_for.issubset(self.completed_jobs)

                if not deps_ok:
                    self.queued_jobs.put(job)
                    time.sleep(1.0)
                    continue

                executor = self._find_capable_executor(job.job_info.capabilities,
                    emergency=bool(job.job_info.emergency_context))

                if executor:
                    self._execute_job_on_executor(job.job_info, executor)
                else:
                    self.queued_jobs.put(job)
                    time.sleep(5.0)

            except Empty:
                continue
            except Exception as e:
                LOG.error(f"Error in job scheduler: {e}")
                time.sleep(1.0)

        LOG.info(f"Job scheduler stopped for broker {self.broker_id}")

def demo_executorbroker():
    print("\n=== ExecutorBroker Demo ===")

    broker = ExecutorBroker("demo_broker")
    print(f"✅ Created broker: {broker.broker_id}")

    exec1_id = uuid4()
    exec2_id = uuid4()

    broker.register_executor(exec1_id, "127.0.0.1", 8001, {"python", "compute"})
    broker.register_executor(exec2_id, "127.0.0.1", 8002, {"python", "storage"})
    print(f"✅ Registered {broker.get_executor_count()} executors")

    broker.start()
    print("✅ Broker started")

    job1 = JobInfo(
        job_id=uuid4(),
        data={"task": "compute_pi", "precision": 1000},
        capabilities={"python", "compute"}
    )

    job_id = broker.submit_job(job1)
    print(f"✅ Submitted job: {job_id}")

    broker.set_emergency_mode("fire", "critical")
    print("✅ Emergency mode activated")

    emergency_job = JobInfo(
        job_id=uuid4(),
        data={"task": "emergency_evacuation", "zone": "A1"},
        capabilities={"python"}
    )

    emergency_id = broker.submit_job(emergency_job)
    print(f"✅ Emergency job submitted: {emergency_id}")

    time.sleep(0.1)
    broker.heartbeat_executor(exec1_id, {"python", "compute"})
    broker.heartbeat_executor(exec2_id, {"python", "storage"})
    print("✅ Heartbeats processed")

    broker.job_completed(job_id)
    broker.job_completed(emergency_id)
    print("✅ Jobs completed")

    broker.clear_emergency_mode()
    print("✅ Emergency mode cleared")

    broker.stop()
    print("✅ Broker stopped")

    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_executorbroker()
