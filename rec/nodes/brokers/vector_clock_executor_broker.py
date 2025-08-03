# Broker w/ Vector Clock & Emergency Jobs!
# Student-built variant of UCP executor broker — hope this doesn't break stuff

from typing import Dict, List, Optional, Callable
from uuid import UUID
import time
import threading
from queue import Queue

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from readerwriterlock.rwlock import RWLockWrite

from rec.model import Capabilities, JobInfo
from rec.nodes.node import Node
from rec.nodetypes.executor import Executor
from rec.util.log import LOG

from rec.replication.core.vector_clock import VectorClock, CapabilityAwareVectorClock, EmergencyContext
from rec.replication.core.causal_message import CausalMessage, MessageHandler


# Slightly adjusted job model with emergency stuff + clocks
class EnhancedQueuedJob(BaseModel):
    job_id: UUID
    job_info: JobInfo
    wait_for: set[UUID]
    vector_clock: Dict[str, int] = {}  # string keys to avoid annoying Pydantic UUID parsing
    is_emergency: bool = False
    emergency_type: str = "none"
    priority_score: float = 1.0  # kinda rough, might revisit


class VectorClockExecutorBroker:
    """
    Trying to bolt vector clock logic onto the executor broker
    without completely rewriting it...
    """

    def __init__(self, on_job_started: Callable[[UUID, JobInfo], None]):
        self.executors: dict[UUID, Executor] = {}
        self.executor_lock = RWLockWrite()
        self.queued_jobs = Queue()
        self.completed_jobs = set()
        self.cj_lock = threading.Lock()
        self.should_exit = False
        self.__on_job_started = on_job_started
        
        import uuid
        self.node_id = uuid.uuid4()
        self.vector_clock = VectorClock(self.node_id)
        self.message_handler = MessageHandler(self.node_id, self._get_caps())

        self.emergency_context = EmergencyContext("none", "normal")
        self.emergency_jobs = set()

        LOG.info(f"Started broker with ID {self.node_id}")

    def _get_caps(self):
        # Just some standard numbers — hardcoded for now
        return Capabilities(cpu_cores=4, memory=8192, power=100.0)

    def _detect_emergency_job(self, job_info: JobInfo) -> tuple[bool, str]:
        # basic pattern match on keywords
        keywords = {
            'fire': 'fire',
            'medical': 'medical',
            'ambulance': 'medical',
            'emergency': 'general',
            'urgent': 'general',
            'critical': 'critical',
            'disaster': 'disaster'
        }
        job_str = str(job_info.model_dump()).lower()
        for word, category in keywords.items():
            if word in job_str:
                LOG.info(f"Emergency keyword '{word}' found — tagging as {category}")
                return True, category
        return False, "none"

    def _calculate_job_priority(self, job_info: JobInfo, is_emergency: bool, emergency_type: str) -> float:
        base = 1.0
        if is_emergency:
            boost = {
                'critical': 10.0,
                'medical': 8.0,
                'fire': 7.0,
                'disaster': 6.0,
                'general': 5.0
            }
            return base * boost.get(emergency_type, 5.0)
        return base

    def add_endpoints(self, app: FastAPI):
        @app.put("/executors/register")
        def reg_executor(hosts: list[str], executor: Executor, request: Request):
            LOG.debug(f"Registering exec {executor.id}")
            self.vector_clock.tick()
            with self.executor_lock.gen_wlock():
                self.executors[executor.id] = executor
            LOG.info(f"Executor {executor.id} is in!")

        @app.put("/executors/heartbeat/{exec_id}")
        def heartbeat(exec_id: UUID, capabilities: Capabilities):
            LOG.debug(f"Heartbeat from {exec_id}")
            self.vector_clock.tick()

            with self.executor_lock.gen_wlock():
                exec_ref = self.executors.get(exec_id)
                if not exec_ref:
                    raise HTTPException(404, "Executor not found")
                exec_ref.cur_caps = capabilities
                exec_ref.last_update = time.time()
                # Note: not syncing clocks here, maybe later

        @app.get("/executors/count")
        def count_execs():
            self.prune_executor_list()
            return len(self.executors)

        @app.put("/job/submit/{job_id}")
        def submit(job_info: JobInfo, job_id: UUID, request: Request, wait_for: Optional[set[UUID]] = None):
            self.vector_clock.tick()
            if job_info.result_addr.host == "this":
                job_info.result_addr.host = request.client.host

            is_emergency, type_ = self._detect_emergency_job(job_info)
            score = self._calculate_job_priority(job_info, is_emergency, type_)

            if wait_for is None:
                exec_ = self.capable_executor(job_info.capabilities)
                if not exec_:
                    raise HTTPException(503, "No executor available")
                if exec_.submit_job(job_id, job_info):
                    self.__on_job_started(job_id, job_info)
                    if is_emergency:
                        self.emergency_jobs.add(job_id)
                    return job_id
                raise HTTPException(503, "Executor rejected job")
            else:
                self.queue_job_enhanced(job_id, job_info, wait_for, is_emergency, type_, score)
                return job_id

        @app.put("/job/done/{job_id}")
        def mark_done(job_id: UUID):
            self.vector_clock.tick()
            with self.cj_lock:
                self.completed_jobs.add(job_id)
                self.emergency_jobs.discard(job_id)

    def capable_executor(self, req_caps: Capabilities) -> Optional[Executor]:
        self.prune_executor_list()
        with self.executor_lock.gen_rlock():
            for ex in self.executors.values():
                if (ex.cur_caps.memory >= req_caps.memory and
                    ex.cur_caps.disk >= req_caps.disk and
                    ex.cur_caps.cpu_cores >= req_caps.cpu_cores):
                    return ex
        return None

    def prune_executor_list(self):
        now = time.time()
        with self.executor_lock.gen_wlock():
            for ex_id in list(self.executors):
                if now - self.executors[ex_id].last_update > 300:
                    del self.executors[ex_id]
                    LOG.warning(f"Executor {ex_id} removed due to timeout")

    def queue_job_enhanced(self, job_id, job_info, wait_for, is_emergency, emergency_type, priority_score):
        if wait_for is None:
            wait_for = set()

        job = EnhancedQueuedJob(
            job_id=job_id,
            job_info=job_info,
            wait_for=wait_for,
            vector_clock={str(k): v for k, v in self.vector_clock.clock.items()},
            is_emergency=is_emergency,
            emergency_type=emergency_type,
            priority_score=priority_score
        )
        self.queued_jobs.put(job)

    def delete_job_from_executor(self, job_id: UUID) -> bool:
        with self.executor_lock.gen_rlock():
            for exec in self.executors.values():
                if exec.job_delete(job_id):
                    return True
        return False

    def start(self):
        threading.Thread(target=self.job_scheduler, daemon=True).start()

    def stop(self):
        self.should_exit = True

    def job_scheduler(self):
        while not self.should_exit:
            try:
                job = self.queued_jobs.get(timeout=1)

                while not job.wait_for.issubset(self.completed_jobs):
                    time.sleep(1)

                exec_ = self.capable_executor(job.job_info.capabilities)
                if exec_ and exec_.submit_job(job.job_id, job.job_info):
                    self.__on_job_started(job.job_id, job.job_info)
                    if job.is_emergency:
                        self.emergency_jobs.add(job.job_id)
                else:
                    time.sleep(5 if not job.is_emergency else 2)

            except Exception as e:
                if "Empty" not in str(e):
                    LOG.error(f"Job scheduler error: {e}")


def create_vector_clock_broker(on_job_started: Callable[[UUID, JobInfo], None]) -> VectorClockExecutorBroker:
    return VectorClockExecutorBroker(on_job_started)
