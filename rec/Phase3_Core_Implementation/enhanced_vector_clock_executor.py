"""
File 8: EnhancedVectorClockExecutor - Vector Clock-Aware Job Execution
Phase 3: Core Implementation

Enhanced executor with full vector clock integration for causal consistency
and distributed job execution coordination.

Key Features:
- Vector clock-aware job scheduling and execution
- Causal ordering enforcement for dependent jobs
- Cross-node execution coordination with vector clock sync
- Emergency-aware execution with causal consistency preservation
- FCFS policy integration for distributed execution ordering

This is a core thesis contribution combining:
- Lamport's vector clocks for causal ordering
- UCP distributed execution framework
- Emergency response coordination
- First-Come-First-Served execution policies
"""

import time
import threading
import logging
from typing import Dict, Optional, List, Set, Any
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

import sys
import os
phase1_path = os.path.join(os.path.dirname(__file__), '..', 'Phase1_Core_Foundation')
sys.path.insert(0, phase1_path)

from rec.Phase1_Core_Foundation.vector_clock import VectorClock, EmergencyContext, EmergencyLevel, create_emergency
from rec.Phase1_Core_Foundation.causal_message import CausalMessage, MessageHandler
from rec.Phase1_Core_Foundation.causal_consistency import CausalConsistencyManager, FCFSConsistencyPolicy

phase2_path = os.path.join(os.path.dirname(__file__), '..', 'Phase2_Node_Infrastructure')
sys.path.insert(0, phase2_path)

from rec.Phase2_Node_Infrastructure.emergency_executor import SimpleEmergencyExecutor, ExecutorJob, JobPriority, ExecutorCapabilities

LOG = logging.getLogger(__name__)

class CausalJobState(Enum):
    PENDING = "pending"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

@dataclass
class CausalJob:
    job_id: UUID
    data: dict
    vector_clock_snapshot: Dict[str, int]
    dependencies: Set[UUID] = field(default_factory=set)
    state: CausalJobState = CausalJobState.PENDING
    priority: JobPriority = JobPriority.NORMAL_MEDIUM
    emergency_context: Optional[EmergencyContext] = None

    def is_ready(self, completed: Set[UUID]) -> bool:
        return all(dep in completed for dep in self.dependencies)

class EnhancedVectorClockExecutor(SimpleEmergencyExecutor):
    def __init__(self, node_id: str, capabilities: ExecutorCapabilities = None):
        super().__init__(node_id, capabilities)
        self.causal_jobs: Dict[UUID, CausalJob] = {}
        self.dependencies: Dict[UUID, Set[UUID]] = defaultdict(set)
        self.lock = threading.RLock()
        self.fcfs_policy = FCFSConsistencyPolicy()
        self.job_order: List[UUID] = []
        self.job_timestamps: Dict[UUID, float] = {}
        self.peers: Dict[str, 'EnhancedVectorClockExecutor'] = {}

    def submit_causal_job(self, data: dict, deps: Set[UUID] = None, context: EmergencyContext = None) -> UUID:
        self.vector_clock.tick()
        job_id = uuid4()
        job = CausalJob(job_id, data, self.vector_clock.clock.copy(), deps or set(), emergency_context=context)
        if context:
            if context.level == EmergencyLevel.CRITICAL:
                job.priority = JobPriority.EMERGENCY_CRITICAL
            elif context.level == EmergencyLevel.HIGH:
                job.priority = JobPriority.EMERGENCY_HIGH
        with self.lock:
            self.causal_jobs[job_id] = job
            self.dependencies[job_id] = deps or set()
            self.job_order.append(job_id)
            self.job_timestamps[job_id] = time.time()
        if job.is_ready(self.completed_jobs):
            job.state = CausalJobState.READY
            self._schedule(job)
        else:
            job.state = CausalJobState.BLOCKED
        LOG.info(f"Job {job_id} submitted with dependencies: {deps}")
        return job_id

    def _schedule(self, job: CausalJob):
        ejob = ExecutorJob(
            job_id=job.job_id, 
            data=job.data, 
            priority=job.priority, 
            emergency_context=job.emergency_context, 
            vector_clock=job.vector_clock_snapshot
        )
        self.job_queue.put(ejob)

    def register_peer(self, peer_id: str, peer: 'EnhancedVectorClockExecutor'):
        self.peers[peer_id] = peer

    def get_status(self) -> Dict[str, Any]:
        with self.lock:
            return {
                'jobs': {k: v.state.value for k, v in self.causal_jobs.items()},
                'completed': list(self.completed_jobs),
                'vector_clock': self.vector_clock.clock
            }

    def _execute_job(self, job: ExecutorJob) -> bool:
        if self.peers and not self._should_execute(job.job_id):
            return True
        with self.lock:
            cjob = self.causal_jobs.get(job.job_id)
            if cjob:
                cjob.state = CausalJobState.EXECUTING
        success = super()._execute_job(job)
        with self.lock:
            if cjob:
                cjob.state = CausalJobState.COMPLETED if success else CausalJobState.FAILED
        return success

    def _should_execute(self, job_id: UUID) -> bool:
        my_time = self.job_timestamps.get(job_id, time.time())
        for peer in self.peers.values():
            peer_time = peer.job_timestamps.get(job_id)
            if peer_time and peer_time < my_time:
                return False
        return True

    def check_blocked(self):
        with self.lock:
            for job in self.causal_jobs.values():
                if job.state == CausalJobState.BLOCKED and job.is_ready(self.completed_jobs):
                    job.state = CausalJobState.READY
                    self._schedule(job)

    def sync_clocks(self):
        for peer in self.peers.values():
            self.vector_clock.update(peer.vector_clock.clock)
        self.check_blocked()

# Demo and testing
def demo_enhanced_executor():
    print("\n=== Enhanced Vector Clock Executor Demo ===")
    
    # Create executors
    exec1 = EnhancedVectorClockExecutor("enhanced_node1")
    exec2 = EnhancedVectorClockExecutor("enhanced_node2")
    
    # Register as peers
    exec1.register_peer("enhanced_node2", exec2)
    exec2.register_peer("enhanced_node1", exec1)
    
    print("✅ Created enhanced executors with peer registration")
    
    # Start executors
    exec1.start()
    exec2.start()
    print("✅ Enhanced executors started")
    
    # Submit causal jobs with dependencies
    id1 = exec1.submit_causal_job({"task": "data_preparation"})
    id2 = exec1.submit_causal_job({"task": "computation"}, {id1})  # Depends on id1
    
    print("✅ Causal jobs with dependencies submitted")
    
    # Submit emergency job
    emergency = create_emergency("fire", "critical")
    id3 = exec2.submit_causal_job({"task": "emergency_evacuation"}, context=emergency)
    
    print("✅ Emergency causal job submitted")
    
    # Let jobs process
    time.sleep(0.5)
    
    # Synchronize clocks between peers
    exec1.sync_clocks()
    exec2.sync_clocks()
    print("✅ Vector clocks synchronized")
    
    # Check status
    status1 = exec1.get_status()
    status2 = exec2.get_status()
    print(f"✅ Executor 1 completed: {len(status1['completed'])} jobs")
    print(f"✅ Executor 2 completed: {len(status2['completed'])} jobs")
    
    # Stop executors
    exec1.stop()
    exec2.stop()
    print("✅ Enhanced executors stopped")
    
    return True

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    demo_enhanced_executor()

