# 👩‍🚒 Easy Recovery System – Handles Failing Executors + Emergencies

import time
from typing import Dict, List
from uuid import uuid4, UUID

from rec.replication.core.vector_clock import VectorClock, EmergencyLevel
from rec.util.log import LOG


class SimpleRecoveryManager:
    """Keeps track of healthy and failed executors and handles job recovery."""

    def __init__(self, manager_id=None):
        self.manager_id = manager_id or f"recovery_{uuid4().hex[:5]}"
        self.clock = VectorClock(self.manager_id)

        self.healthy = set()
        self.failed = set()
        self.emergency_nodes = set()
        self.orphaned_jobs = []

        self.emergency_active = False
        self.emergency_level = EmergencyLevel.LOW

        LOG.info(f"[Recovery] Manager {self.manager_id} online")

    def register_executor(self, executor_id):
        """Executor joins the system – mark as healthy."""
        self.clock.tick()
        self.healthy.add(executor_id)
        self.failed.discard(executor_id)
        LOG.info(f"[Recovery] {executor_id} is healthy")

    def mark_executor_failed(self, executor_id, failed_jobs=None):
        """An executor has gone down – reclaim its jobs."""
        self.clock.tick()
        if executor_id in self.healthy:
            self.healthy.remove(executor_id)
            self.failed.add(executor_id)

            if failed_jobs:
                self.orphaned_jobs.extend(failed_jobs)
                LOG.warning(f"[Recovery] {executor_id} failed with {len(failed_jobs)} jobs")
            else:
                LOG.warning(f"[Recovery] {executor_id} failed")

            self._redistribute_jobs()

    def executor_heartbeat(self, executor_id, status: Dict):
        """Executor sends a 'I'm alive' message and status."""
        if 'vector_clock' in status:
            self.clock.update(status['vector_clock'])

        if executor_id not in self.healthy:
            self.register_executor(executor_id)

        if status.get('in_emergency_mode'):
            self.emergency_nodes.add(executor_id)
        else:
            self.emergency_nodes.discard(executor_id)

    def declare_system_emergency(self, emergency_type, level_str):
        """Trigger system-wide emergency state."""
        self.clock.tick()
        self.emergency_active = True
        self.emergency_level = getattr(EmergencyLevel, level_str.upper(), EmergencyLevel.LOW)

        LOG.warning(f"[Emergency] SYSTEM EMERGENCY – {emergency_type.upper()} at level {level_str.upper()}")
        LOG.info(f"[Notify] Would alert {len(self.healthy)} healthy executors.")

    def clear_system_emergency(self):
        """All clear – return to normal."""
        self.clock.tick()
        self.emergency_active = False
        self.emergency_level = EmergencyLevel.LOW
        self.emergency_nodes.clear()
        LOG.info("[Emergency] All clear. Back to normal.")

    def _redistribute_jobs(self):
        """Simple round-robin recovery of orphaned jobs."""
        if not self.orphaned_jobs or not self.healthy:
            return

        healthy_list = list(self.healthy)

        for idx, job_id in enumerate(list(self.orphaned_jobs)):
            executor_id = healthy_list[idx % len(healthy_list)]
            LOG.info(f"[Recovery] Reassigning job {job_id} to {executor_id}")
            self.orphaned_jobs.remove(job_id)

    def get_status(self):
        return {
            "id": self.manager_id,
            "vector_clock": self.clock.clock,
            "emergency": self.emergency_active,
            "level": self.emergency_level.name,
            "executors": {
                "healthy": list(self.healthy),
                "failed": list(self.failed),
                "emergency_mode": list(self.emergency_nodes),
            },
            "orphaned_jobs": len(self.orphaned_jobs),
        }


class SimpleCoordinator:
    """Coordinates executors and recovery manager"""

    def __init__(self):
        self.recovery = SimpleRecoveryManager()
        self.executors = {}

    def add_executor(self, executor):
        """Add and sync executor"""
        exec_id = executor.executor_id
        self.executors[exec_id] = executor
        self.recovery.register_executor(exec_id)
        executor.sync_vector_clock(self.recovery.clock.clock)
        LOG.info(f"[Coordinator] {exec_id} added and synced")

    def simulate_failure(self, executor_id):
        """Pretend an executor crashed"""
        if executor_id in self.executors:
            exec = self.executors[executor_id]
            failed_jobs = list(exec.running)
            self.recovery.mark_executor_failed(executor_id, failed_jobs)
            LOG.warning(f"[Coordinator] Simulated failure of {executor_id}")

    def send_heartbeats(self):
        """Ping all alive executors"""
        for exec_id, exec in self.executors.items():
            if exec_id in self.recovery.healthy:
                self.recovery.executor_heartbeat(exec_id, exec.get_status())

    def get_system_status(self):
        """Get full system info"""
        return {
            "recovery": self.recovery.get_status(),
            "executors": {
                eid: e.get_status() for eid, e in self.executors.items()
            }
        }


def demo_recovery():
    print("== DEMO: RECOVERY SYSTEM ==")

    from rec.nodes.emergency_executor import create_emergency_executor

    coordinator = SimpleCoordinator()

    # Add two executors
    exec1 = create_emergency_executor("exec_1")
    exec2 = create_emergency_executor("exec_2")
    coordinator.add_executor(exec1)
    coordinator.add_executor(exec2)

    print("Initial system:")
    print(coordinator.get_system_status())

    # Heartbeats
    coordinator.send_heartbeats()

    # Declare emergency and simulate failure
    coordinator.recovery.declare_system_emergency("fire", "high")
    coordinator.simulate_failure("exec_1")

    print("\nAfter failure:")
    print(coordinator.get_system_status())

    coordinator.recovery.clear_system_emergency()

if __name__ == "__main__":
    demo_recovery()
