
# For students: combines executors, recovery, and vector clock coordination

import time
from uuid import UUID, uuid4
from typing import Dict

from rec.model import JobInfo
from rec.replication.core.vector_clock import VectorClock
from rec.nodes.emergency_executor import create_emergency_executor
from rec.nodes.recovery_system import SimpleRecoveryManager, SimpleCoordinator
from rec.util.log import LOG


class SimpleEmergencySystem:
    """
    Manages executors, job submission, emergencies, and recovery.
    Designed to be clear and easy to extend.
    """

    def __init__(self, system_name: str = "emergency_system"):
        self.name = system_name
        self.coordinator = SimpleCoordinator()
        self.system_clock = VectorClock(system_name)

        self.normal_jobs = 0
        self.emergency_jobs = 0

        LOG.info(f"Emergency system '{self.name}' initialized")

    def add_executor(self, executor_id: str = None) -> str:
        exec = create_emergency_executor(executor_id)
        exec_id = exec.executor_id
        self.coordinator.add_executor(exec)
        self.system_clock.tick()
        LOG.info(f"Executor {exec_id} added")
        return exec_id

    def submit_normal_job(self, job_info: JobInfo = None) -> UUID:
        job_id = uuid4()
        if job_info is None:
            job_info = JobInfo(wasm_bin="normal_task.wasm")
        self.system_clock.tick()
        self.normal_jobs += 1

        # Pick first healthy executor
        healthy = list(self.coordinator.recovery.healthy)
        if not healthy:
            LOG.error("No healthy executors for normal job")
            return None
        eid = healthy[0]
        self.coordinator.executors[eid].receive_job(job_id, job_info, is_emergency=False)
        LOG.info(f"Normal job {job_id} sent to {eid}")
        return job_id

    def submit_emergency_job(self, emergency_type: str, job_info: JobInfo = None) -> UUID:
        job_id = uuid4()
        if job_info is None:
            job_info = JobInfo(wasm_bin=f"emergency_{emergency_type}.wasm")
        self.system_clock.tick()
        self.emergency_jobs += 1

        # Pick first healthy executor for emergency
        healthy = list(self.coordinator.recovery.healthy)
        if not healthy:
            LOG.error("No executor available for emergency")
            return None
        best = healthy[0]
        self.coordinator.executors[best].receive_job(job_id, job_info, is_emergency=True)
        LOG.warning(f"Emergency job {job_id} ({emergency_type}) sent to {best}")
        return job_id

    def declare_emergency(self, type: str = "general", level: str = "medium"):
        self.system_clock.tick()
        self.coordinator.recovery.declare_system_emergency(type, level)
        for exec in self.coordinator.executors.values():
            exec.set_emergency_mode(type, level)
        LOG.warning(f"System-wide emergency: {type}/{level}")

    def clear_emergency(self):
        self.system_clock.tick()
        self.coordinator.recovery.clear_system_emergency()
        for exec in self.coordinator.executors.values():
            exec.clear_emergency_mode()
        LOG.info("Cleared system-wide emergency")

    def simulate_failure(self, executor_id: str):
        self.system_clock.tick()
        self.coordinator.simulate_failure(executor_id)
        LOG.warning(f"Simulated failure: {executor_id}")

    def status(self) -> Dict:
        coord_status = self.coordinator.get_system_status()
        return {
            "system": self.name,
            "clock": self.system_clock.clock,
            "jobs": {"normal": self.normal_jobs, "emergency": self.emergency_jobs},
            "executors": {
                "total": len(self.coordinator.executors),
                "healthy": len(self.coordinator.recovery.healthy),
                "failed": len(self.coordinator.recovery.failed),
                "in_emergency": len(self.coordinator.recovery.emergency_nodes)
            },
            "detail": coord_status
        }


def create_emergency_system(system_name: str = "emergency_system") -> SimpleEmergencySystem:
    """Factory function to create emergency system"""
    return SimpleEmergencySystem(system_name)


def demo_complete_emergency():
    """Run a complete demo to show system behavior"""
    print("=== Demo: Emergency Response System ===")
    system = SimpleEmergencySystem("demo_system")

    # Add executors
    e1 = system.add_executor("exec1")
    e2 = system.add_executor("exec2")
    print(f"Added executors: {e1}, {e2}")

    # Submit normal jobs
    j1 = system.submit_normal_job()
    j2 = system.submit_normal_job()
    print(f"Submitted normal jobs: {j1}, {j2}")

    print("\nInitial system state:")
    print(system.status())

    # Trigger emergency and post emergency jobs
    system.declare_emergency("fire", "high")
    ej1 = system.submit_emergency_job("fire")
    ej2 = system.submit_emergency_job("medical")
    print(f"Submitted emergency jobs: {ej1}, {ej2}")

    system.simulate_failure(e2)
    print("\nState after failure:")
    print(system.status())

    system.clear_emergency()
    print("\nState after clearing emergency:")
    print(system.status())

    return system


if __name__ == "__main__":
    demo_complete_emergency()
