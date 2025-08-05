
# Processes normal and emergency jobs using a simple vector clock

import time
from typing import Dict
from uuid import UUID, uuid4

from rec.model import JobInfo
from rec.replication.core.vector_clock import VectorClock, EmergencyLevel
from rec.util.log import LOG


class SimpleEmergencyExecutor:
    """
    A straightforward executor that handles both normal and emergency jobs.
    Emergency jobs always start first and are limited by capacity.
    """

    def __init__(self, executor_id: str = None):
        self.executor_id = executor_id or f"exec_{uuid4().hex[:6]}"
        self.vclock = VectorClock(self.executor_id)

        self.normal_jobs = []       # list of (job_id, JobInfo)
        self.emergency_jobs = []    # list of emergency jobs
        self.running = set()        # job_ids currently executing
        self.done = set()           # finished job_ids

        self.emergency_level = EmergencyLevel.LOW
        self.in_emergency = False

        self.max_running = 3        # max jobs that run at the same time

        LOG.info(f"{self.executor_id} started")

    def receive_job(self, job_id: UUID, job_info: JobInfo, is_emergency: bool = False):
        self.vclock.tick()

        if is_emergency:
            self.emergency_jobs.append((job_id, job_info))
            LOG.warning(f"➕ Emergency job {job_id} received")
        else:
            self.normal_jobs.append((job_id, job_info))
            LOG.info(f"➕ Normal job {job_id} received")

        self._try_start()

    def set_emergency_mode(self, emergency_type: str, level: str):
        self.vclock.tick()
        self.in_emergency = True
        try:
            self.emergency_level = EmergencyLevel[level.upper()]
        except KeyError:
            self.emergency_level = EmergencyLevel.LOW
        LOG.warning(f"🚨 Entering emergency: {emergency_type} / {level}")

        if self.emergency_level in (EmergencyLevel.HIGH, EmergencyLevel.CRITICAL):
            LOG.warning("High/critical mode – pausing normal jobs")

    def clear_emergency_mode(self):
        self.vclock.tick()
        self.in_emergency = False
        self.emergency_level = EmergencyLevel.LOW
        LOG.info("✅ Emergency cleared – back to normal")
        self._try_start()

    def _try_start(self):
        # Start emergency jobs first
        while self.emergency_jobs and len(self.running) < self.max_running:
            jid, jinfo = self.emergency_jobs.pop(0)
            self._start_job(jid, jinfo, emergency=True)

        # Start normal jobs only if not in high emergency
        if not self.in_emergency or self.emergency_level not in (EmergencyLevel.HIGH, EmergencyLevel.CRITICAL):
            while self.normal_jobs and len(self.running) < self.max_running:
                jid, jinfo = self.normal_jobs.pop(0)
                self._start_job(jid, jinfo, emergency=False)

    def _start_job(self, job_id: UUID, job_info: JobInfo, emergency: bool):
        self.vclock.tick()
        self.running.add(job_id)
        LOG.info(f"👷 Starting {'EMERGENCY' if emergency else 'normal'} job {job_id}")

        # Simulate execution with a short delay
        time.sleep(0.1)
        self._complete_job(job_id)

    def _complete_job(self, job_id: UUID):
        self.vclock.tick()
        self.running.remove(job_id)
        self.done.add(job_id)
        LOG.info(f"✅ Job {job_id} completed")
        self._try_start()

    def get_status(self) -> Dict:
        return {
            "executor": self.executor_id,
            "vector_clock": self.vclock.clock,
            "emergency_mode": self.in_emergency,
            "emergency_level": self.emergency_level.name,
            "queues": {
                "emergency": len(self.emergency_jobs),
                "normal": len(self.normal_jobs)
            },
            "running": len(self.running),
            "completed": len(self.done),
            "slots_left": self.max_running - len(self.running),
        }

    def sync_vector_clock(self, other_clock: Dict[str, int]):
        self.vclock.update(other_clock)
        LOG.debug(f"✅ Clock synced: {self.vclock.clock}")


def create_emergency_executor(executor_id: str = None) -> SimpleEmergencyExecutor:
    """Factory function to create emergency executor"""
    return SimpleEmergencyExecutor(executor_id)


def demo_executor():
    print("=== Demo: Emergency Executor ===")
    execu = SimpleEmergencyExecutor("demoExec")
    j1 = uuid4(); j2 = uuid4(); j3 = uuid4()

    execu.receive_job(j1, JobInfo(wasm_bin="n1.wasm"), is_emergency=False)
    execu.receive_job(j2, JobInfo(wasm_bin="n2.wasm"), is_emergency=False)
    print("Status:", execu.get_status())

    execu.set_emergency_mode("fire", "high")
    execu.receive_job(j3, JobInfo(wasm_bin="e1.wasm"), is_emergency=True)
    print("Status during emergency:", execu.get_status())

    time.sleep(0.3)
    print("Final status:", execu.get_status())

    execu.clear_emergency_mode()
    print("After clearing emergency:", execu.get_status())

if __name__ == "__main__":
    demo_executor()
