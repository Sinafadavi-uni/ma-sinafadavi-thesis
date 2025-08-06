
# Handles job conflicts based on selected strategy (e.g. causal, priority)

import threading
import time
from uuid import UUID
from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime

from rec.replication.core.vector_clock import VectorClock
from rec.util.log import LOG

# Define available strategies
class ConflictStrategy(Enum):
    FCFS = "first_com‑first‑served"
    PRIORITY = "priority‑based"
    EMERGENCY = "emergency‑first"
    CAUSAL = "vector‑clock causal"

# Track minimal job priority
class JobPriority:
    def __init__(self, emergency=0, user=5):
        self.emergency = emergency
        self.user = user

class SimpleEnhancedExecutor:
    """
    Student‑level executor with basic conflict resolution:
    - Detect conflict if resource needs exceed threshold
    - Resolve based on strategy chosen
    """

    def __init__(self, node_id: str, strategy: ConflictStrategy = ConflictStrategy.CAUSAL):
        self.node_id = node_id
        self.vclock = VectorClock(node_id)
        self.strategy = strategy
        self.running_jobs = set()   # jobs currently running
        self.job_priorities: Dict[UUID, JobPriority] = {}
        self.lock = threading.Lock()

    def submit_job(self, job_id: UUID, job_info: dict, priority: Optional[JobPriority] = None) -> bool:
        with self.lock:
            self.vclock.tick()
            self.job_priorities[job_id] = priority or JobPriority()

            conflicts = self._find_conflicts(job_info)
            if conflicts:
                decision = self._resolve_conflict(job_id, conflicts)
                if decision:
                    self.running_jobs.add(job_id)
                    LOG.info(f"✅ Job {job_id} started (after conflict resolution)")
                    return True
                else:
                    LOG.info(f"⏸ Job {job_id} deferred due to conflict")
                    return False
            else:
                self.running_jobs.add(job_id)
                LOG.info(f"✅ Job {job_id} started (no conflict)")
                return True

    def _find_conflicts(self, job_info: dict) -> List[UUID]:
        # Simplified: detect conflict if CPU need > threshold
        cpu = job_info.get("estimated_cpu", 0)
        return list(self.running_jobs) if cpu > 50 else []

    def _resolve_conflict(self, job_id: UUID, conflicts: List[UUID]) -> bool:
        if self.strategy == ConflictStrategy.FCFS:
            return False

        jp = self.job_priorities[job_id]
        if self.strategy == ConflictStrategy.PRIORITY:
            inner_score = jp.user
            conflict_scores = [self.job_priorities[c].user for c in conflicts]
            return inner_score > max(conflict_scores, default=0)

        if self.strategy == ConflictStrategy.EMERGENCY:
            inner_e = jp.emergency
            conflict_es = [self.job_priorities[c].emergency for c in conflicts]
            return inner_e > max(conflict_es, default=0)

        if self.strategy == ConflictStrategy.CAUSAL:
            # Simplified: prefer newer clock values (demonstrative)
            return True

        return False

    def complete_job(self, job_id: UUID):
        with self.lock:
            if job_id in self.running_jobs:
                self.running_jobs.remove(job_id)
                self.vclock.tick()
                LOG.info(f"✅ Job {job_id} completed")

    def status(self) -> Dict:
        return {
            "node": self.node_id,
            "vclock": self.vclock.clock,
            "strategy": self.strategy.value,
            "running": list(self.running_jobs)
        }


def create_enhanced_executor(node_id="executor_1", strategy=ConflictStrategy.FCFS, **kwargs):
    """Factory function to create enhanced executor instances."""
    return SimpleEnhancedExecutor(strategy=strategy, node_id=node_id, **kwargs)
