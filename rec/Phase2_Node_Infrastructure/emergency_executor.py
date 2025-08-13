"""
File 7: EmergencyExecutor - Emergency-Aware Job Execution
Phase 2: Node Infrastructure

Emergency-aware job executor with vector clock coordination
and prioritized execution during crisis situations.

Key Features:
- Emergency context propagation and handling
- Priority-based job scheduling during emergencies
- Vector clock synchronization for emergency operations
- Causal consistency preservation in emergency mode
- Resource reallocation for critical tasks

Based on UCP Executor with enhancements for:
- Emergency response coordination
- Vector clock-based operation ordering
- Crisis-aware resource management
"""

import time
import threading
import logging
from typing import Dict, Optional, List, Set, Any
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum
from queue import PriorityQueue, Empty
from abc import ABC, abstractmethod

# Import Phase 1 stuff
import sys
import os
phase1_path = os.path.join(os.path.dirname(__file__), '..', 'Phase1_Core_Foundation')
sys.path.insert(0, phase1_path)

from rec.Phase1_Core_Foundation.vector_clock import VectorClock, EmergencyContext, EmergencyLevel, create_emergency
from rec.Phase1_Core_Foundation.causal_message import CausalMessage, MessageHandler
from rec.Phase1_Core_Foundation.causal_consistency import CausalConsistencyManager

LOG = logging.getLogger(__name__)

class ExecutorStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    EMERGENCY = "emergency"
    MAINTENANCE = "maintenance"
    FAILED = "failed"

class JobPriority(Enum):
    EMERGENCY_CRITICAL = 0
    EMERGENCY_HIGH = 1
    EMERGENCY_NORMAL = 2
    NORMAL_HIGH = 3
    NORMAL_MEDIUM = 4
    NORMAL_LOW = 5

@dataclass
class ExecutorJob:
    job_id: UUID
    data: dict
    priority: JobPriority = JobPriority.NORMAL_MEDIUM
    capabilities: Set[str] = field(default_factory=set)
    emergency_context: Optional[EmergencyContext] = None
    vector_clock: Optional[dict] = None
    submitted_at: float = field(default_factory=time.time)
    causal_message: Optional[CausalMessage] = None

    def __lt__(self, other):
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.submitted_at < other.submitted_at

@dataclass
class ExecutorCapabilities:
    supported_languages: Set[str] = field(default_factory=lambda: {"python"})
    max_concurrent_jobs: int = 4
    emergency_capable: bool = True
    resource_allocation: Dict[str, float] = field(default_factory=dict)

    def is_capable(self, required_caps: Set[str]) -> bool:
        return required_caps.issubset(self.supported_languages)

class JobExecutionStrategy(ABC):
    @abstractmethod
    def should_execute_immediately(self, job: ExecutorJob, current_load: int) -> bool:
        pass

    @abstractmethod
    def allocate_resources(self, job: ExecutorJob) -> Dict[str, Any]:
        pass

class EmergencyExecutionStrategy(JobExecutionStrategy):
    def __init__(self, max_concurrent: int = 4):
        self.max_concurrent = max_concurrent

    def should_execute_immediately(self, job: ExecutorJob, current_load: int) -> bool:
        if job.emergency_context and job.emergency_context.is_critical():
            return True
        return current_load < self.max_concurrent

    def allocate_resources(self, job: ExecutorJob) -> Dict[str, Any]:
        res = {
            "cpu_cores": 1,
            "memory_mb": 512,
            "timeout_seconds": 300
        }

        if job.emergency_context:
            if job.emergency_context.level == EmergencyLevel.CRITICAL:
                res["cpu_cores"] = 2
                res["memory_mb"] = 1024
                res["timeout_seconds"] = 60
            elif job.emergency_context.level == EmergencyLevel.HIGH:
                res["memory_mb"] = 768
                res["timeout_seconds"] = 120

        return res

class SimpleEmergencyExecutor:
    def __init__(self, node_id: str, capabilities: ExecutorCapabilities = None):
        self.node_id = node_id
        self.vector_clock = VectorClock(node_id)
        self.capabilities = capabilities or ExecutorCapabilities()

        self.status = ExecutorStatus.IDLE
        self.job_queue = PriorityQueue()
        self.active_jobs: Dict[UUID, ExecutorJob] = {}
        self.completed_jobs: Set[UUID] = set()
        self.job_lock = threading.RLock()

        self.emergency_mode = False
        self.current_emergency: Optional[EmergencyContext] = None
        self.execution_strategy = EmergencyExecutionStrategy(self.capabilities.max_concurrent_jobs)

        self.message_handler = MessageHandler(self.node_id)
        self.consistency_manager = CausalConsistencyManager(self.node_id)

        self.should_exit = False
        self.executor_thread = None
        self.last_heartbeat = time.time()

        LOG.info(f"EmergencyExecutor {node_id} initialized")

    def submit_job(self, job: ExecutorJob) -> bool:
        self.vector_clock.tick()
        job.vector_clock = self.vector_clock.clock.copy()

        if job.emergency_context:
            if job.emergency_context.level == EmergencyLevel.CRITICAL:
                job.priority = JobPriority.EMERGENCY_CRITICAL
            elif job.emergency_context.level == EmergencyLevel.HIGH:
                job.priority = JobPriority.EMERGENCY_HIGH
            else:
                job.priority = JobPriority.EMERGENCY_NORMAL

        job.causal_message = CausalMessage(
            content=job.data,
            sender_id="broker",
            vector_clock=job.vector_clock,
            message_type="emergency" if job.emergency_context and job.emergency_context.is_critical() else "normal",
            priority=10 if job.emergency_context and job.emergency_context.is_critical() else 1
        )

        if not self.capabilities.is_capable(job.capabilities):
            LOG.warning(f"Executor {self.node_id} cannot handle job {job.job_id} capabilities: {job.capabilities}")
            return False

        self.job_queue.put(job)
        LOG.info(f"Job {job.job_id} submitted to executor {self.node_id} with priority {job.priority.name}")
        return True

    def set_emergency_mode(self, emergency_type: str, priority_level: str) -> None:
        self.vector_clock.tick()
        self.emergency_mode = True
        self.current_emergency = create_emergency(emergency_type, priority_level)
        self.status = ExecutorStatus.EMERGENCY

        if self.current_emergency.is_critical():
            self._interrupt_non_emergency_jobs()

        LOG.warning(f"Executor {self.node_id} emergency mode activated: {emergency_type} ({priority_level})")

    def clear_emergency_mode(self) -> None:
        self.vector_clock.tick()
        self.emergency_mode = False
        self.current_emergency = None
        self.status = ExecutorStatus.IDLE if not self.active_jobs else ExecutorStatus.BUSY
        LOG.info(f"Executor {self.node_id} emergency mode cleared")

    @property
    def in_emergency_mode(self) -> bool:
        return self.emergency_mode

    def get_status(self) -> Dict[str, Any]:
        with self.job_lock:
            return {
                "node_id": self.node_id,
                "status": self.status.value,
                "emergency_mode": self.emergency_mode,
                "active_jobs": len(self.active_jobs),
                "queued_jobs": self.job_queue.qsize(),
                "completed_jobs": len(self.completed_jobs),
                "vector_clock": self.vector_clock.clock.copy(),
                "emergency_context": {
                    "type": self.current_emergency.emergency_type,
                    "level": self.current_emergency.level.name,
                    "location": self.current_emergency.location
                } if self.current_emergency else None,
                "last_heartbeat": self.last_heartbeat
            }

    def heartbeat(self) -> Dict[str, Any]:
        self.vector_clock.tick()
        self.last_heartbeat = time.time()
        return self.get_status()

    def cancel_job(self, job_id: UUID) -> bool:
        self.vector_clock.tick()
        with self.job_lock:
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
                LOG.info(f"Active job {job_id} cancelled on executor {self.node_id}")
                return True
        LOG.info(f"Job {job_id} marked for cancellation on executor {self.node_id}")
        return True

    def start(self) -> None:
        if self.executor_thread is None or not self.executor_thread.is_alive():
            self.should_exit = False
            self.executor_thread = threading.Thread(
                target=self._job_processor,
                daemon=True,
                name=f"executor-{self.node_id}"
            )
            self.executor_thread.start()
            LOG.info(f"EmergencyExecutor {self.node_id} started")

    def stop(self) -> None:
        self.should_exit = True
        if self.executor_thread and self.executor_thread.is_alive():
            self.executor_thread.join(timeout=5.0)
        LOG.info(f"EmergencyExecutor {self.node_id} stopped")

    def _interrupt_non_emergency_jobs(self) -> None:
        interrupted = []
        with self.job_lock:
            for job_id, job in list(self.active_jobs.items()):
                if job.emergency_context and job.emergency_context.is_critical():
                    continue
                del self.active_jobs[job_id]
                interrupted.append(job_id)
        if interrupted:
            LOG.warning(f"Interrupted {len(interrupted)} non-emergency jobs for critical emergency")

    def _job_processor(self) -> None:
        LOG.info(f"Job processor started for executor {self.node_id}")

        while not self.should_exit:
            try:
                job = self.job_queue.get(timeout=1.0)
                current_load = len(self.active_jobs)
                if not self.execution_strategy.should_execute_immediately(job, current_load):
                    self.job_queue.put(job)
                    time.sleep(0.5)
                    continue

                self._execute_job(job)

            except Empty:
                if not self.active_jobs:
                    self.status = ExecutorStatus.EMERGENCY if self.emergency_mode else ExecutorStatus.IDLE
                continue
            except Exception as e:
                LOG.error(f"Error in job processor: {e}")
                time.sleep(1.0)

        LOG.info(f"Job processor stopped for executor {self.node_id}")

    def _execute_job(self, job: ExecutorJob) -> bool:
        if job.vector_clock:
            self.vector_clock.update(job.vector_clock)
        self.vector_clock.tick()

        with self.job_lock:
            self.active_jobs[job.job_id] = job
            self.status = ExecutorStatus.EMERGENCY if self.emergency_mode else ExecutorStatus.BUSY

        resources = self.execution_strategy.allocate_resources(job)
        LOG.info(f"Executing job {job.job_id} on executor {self.node_id}")
        LOG.debug(f"Job resources: {resources}")

        try:
            exec_time = self._simulate_job_execution(job, resources)
            with self.job_lock:
                del self.active_jobs[job.job_id]
                self.completed_jobs.add(job.job_id)
            self.vector_clock.tick()
            LOG.info(f"Job {job.job_id} completed in {exec_time:.2f}s on executor {self.node_id}")
            return True
        except Exception as e:
            LOG.error(f"Job {job.job_id} failed on executor {self.node_id}: {e}")
            with self.job_lock:
                self.active_jobs.pop(job.job_id, None)
            return False

    def _simulate_job_execution(self, job: ExecutorJob, resources: Dict[str, Any]) -> float:
        base_time = 1.0
        if job.emergency_context:
            if job.emergency_context.level == EmergencyLevel.CRITICAL:
                base_time = 0.1
            elif job.emergency_context.level == EmergencyLevel.HIGH:
                base_time = 0.3
            else:
                base_time = 0.5

        cpu_factor = 1.0 / resources.get("cpu_cores", 1)
        exec_time = base_time * cpu_factor
        time.sleep(exec_time)
        return exec_time

def demo_emergency_executor():
    print("\n=== EmergencyExecutor Demo ===")

    capabilities = ExecutorCapabilities(
        supported_languages={"python", "compute"},
        max_concurrent_jobs=2,
        emergency_capable=True
    )

    executor = SimpleEmergencyExecutor("demo_executor", capabilities)
    print(f"✅ Created executor: {executor.node_id}")

    executor.start()
    print("✅ Executor started")

    normal_job1 = ExecutorJob(
        job_id=uuid4(),
        data={"task": "compute_data", "size": 1000},
        capabilities={"python"}
    )

    normal_job2 = ExecutorJob(
        job_id=uuid4(),
        data={"task": "process_batch", "count": 50},
        capabilities={"compute"}
    )

    executor.submit_job(normal_job1)
    executor.submit_job(normal_job2)
    print("✅ Submitted normal jobs")

    status = executor.get_status()
    print(f"✅ Executor status: {status['status']}")
    print(f"✅ Active jobs: {status['active_jobs']}")
    print(f"✅ Queued jobs: {status['queued_jobs']}")

    executor.set_emergency_mode("fire", "critical")
    print("✅ Emergency mode activated")

    emergency_job = ExecutorJob(
        job_id=uuid4(),
        data={"task": "emergency_evacuation", "zone": "A1"},
        capabilities={"python"},
        emergency_context=create_emergency("fire", "critical")
    )

    executor.submit_job(emergency_job)
    print("✅ Emergency job submitted")

    time.sleep(0.5)
    print("✅ Jobs processed")

    hb = executor.heartbeat()
    print(f"✅ Heartbeat sent: emergency_mode={hb['emergency_mode']}")

    final = executor.get_status()
    print(f"✅ Completed jobs: {final['completed_jobs']}")

    executor.clear_emergency_mode()
    print("✅ Emergency mode cleared")

    executor.stop()
    print("✅ Executor stopped")

    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_emergency_executor()
