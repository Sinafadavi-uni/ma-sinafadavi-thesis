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
from typing import Dict, Optional, List, Set, Any, Tuple
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum
from queue import PriorityQueue, Empty
from collections import defaultdict

# Import Phase 1 foundation
import sys
import os
phase1_path = os.path.join(os.path.dirname(__file__), '..', 'Phase1_Core_Foundation')
sys.path.insert(0, phase1_path)

import vector_clock
import causal_message
import causal_consistency

from vector_clock import VectorClock, EmergencyContext, EmergencyLevel, create_emergency
from causal_message import CausalMessage, MessageHandler
from causal_consistency import CausalConsistencyManager, FCFSConsistencyPolicy

# Import Phase 2 infrastructure
phase2_path = os.path.join(os.path.dirname(__file__), '..', 'Phase2_Node_Infrastructure')
sys.path.insert(0, phase2_path)

from emergency_executor import SimpleEmergencyExecutor, ExecutorJob, JobPriority, ExecutorCapabilities

LOG = logging.getLogger(__name__)

class CausalJobState(Enum):
    """Job state in causal execution"""
    PENDING = "pending"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

@dataclass
class CausalJob:
    """Job with causal dependency tracking"""
    job_id: UUID
    data: dict
    vector_clock_snapshot: Dict[str, int]
    dependencies: Set[UUID] = field(default_factory=set)
    causal_predecessors: List[UUID] = field(default_factory=list)
    state: CausalJobState = CausalJobState.PENDING
    submitted_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    priority: JobPriority = JobPriority.NORMAL_MEDIUM
    emergency_context: Optional[EmergencyContext] = None
    
    def is_ready_for_execution(self, completed_jobs: Set[UUID]) -> bool:
        """Check if all causal dependencies are satisfied"""
        return all(dep_id in completed_jobs for dep_id in self.dependencies)

@dataclass 
class ExecutionCoordination:
    """Coordination state for distributed execution"""
    node_vector_clocks: Dict[str, Dict[str, int]] = field(default_factory=dict)
    global_job_order: List[UUID] = field(default_factory=list)
    fcfs_timestamps: Dict[UUID, float] = field(default_factory=dict)
    emergency_priorities: Dict[UUID, int] = field(default_factory=dict)

class EnhancedVectorClockExecutor(SimpleEmergencyExecutor):
    """
    Enhanced executor with full vector clock integration
    
    Extends SimpleEmergencyExecutor with:
    - Vector clock-based causal job ordering
    - Cross-node execution coordination
    - FCFS policy enforcement for job execution
    - Emergency-aware causal consistency
    - Distributed dependency resolution
    """
    
    def __init__(self, node_id: str, capabilities: ExecutorCapabilities = None):
        """Initialize enhanced vector clock executor"""
        super().__init__(node_id, capabilities)
        
        # Vector clock execution management
        self.causal_jobs: Dict[UUID, CausalJob] = {}
        self.job_dependencies: Dict[UUID, Set[UUID]] = defaultdict(set)
        self.dependency_graph: Dict[UUID, Set[UUID]] = defaultdict(set)
        self.causal_lock = threading.RLock()
        
        # Coordination management
        self.coordination = ExecutionCoordination()
        self.coordination_lock = threading.RLock()
        
        # FCFS policy integration
        self.fcfs_policy = FCFSConsistencyPolicy()
        self.global_job_counter = 0
        
        # Cross-node synchronization
        self.peer_executors: Dict[str, 'EnhancedVectorClockExecutor'] = {}
        self.sync_interval = 5.0  # Sync every 5 seconds
        self.sync_thread = None
        
        LOG.info(f"EnhancedVectorClockExecutor {node_id} initialized with vector clock coordination")
    
    def submit_causal_job(self, job_data: dict, dependencies: Set[UUID] = None,
                         emergency_context: EmergencyContext = None) -> UUID:
        """
        Submit job with causal dependency tracking
        
        Args:
            job_data: Job execution data
            dependencies: Set of job IDs this job depends on
            emergency_context: Emergency context if applicable
            
        Returns:
            UUID: Job identifier
        """
        # Tick vector clock for job submission
        self.vector_clock.tick()
        
        # Create causal job
        job_id = uuid4()
        causal_job = CausalJob(
            job_id=job_id,
            data=job_data,
            vector_clock_snapshot=self.vector_clock.clock.copy(),
            dependencies=dependencies or set(),
            emergency_context=emergency_context
        )
        
        # Determine priority based on emergency context and FCFS
        if emergency_context:
            if emergency_context.level == EmergencyLevel.CRITICAL:
                causal_job.priority = JobPriority.EMERGENCY_CRITICAL
            elif emergency_context.level == EmergencyLevel.HIGH:
                causal_job.priority = JobPriority.EMERGENCY_HIGH
            else:
                causal_job.priority = JobPriority.EMERGENCY_NORMAL
        
        # Apply FCFS policy for job ordering
        self.global_job_counter += 1
        fcfs_timestamp = time.time()
        
        with self.coordination_lock:
            self.coordination.fcfs_timestamps[job_id] = fcfs_timestamp
            self.coordination.global_job_order.append(job_id)
        
        # Track causal dependencies
        with self.causal_lock:
            self.causal_jobs[job_id] = causal_job
            if dependencies:
                self.job_dependencies[job_id] = dependencies
                # Build dependency graph
                for dep_id in dependencies:
                    self.dependency_graph[dep_id].add(job_id)
        
        # Check if job is ready for execution
        if causal_job.is_ready_for_execution(self.completed_jobs):
            causal_job.state = CausalJobState.READY
            self._schedule_causal_job(causal_job)
        else:
            causal_job.state = CausalJobState.BLOCKED
            LOG.info(f"Job {job_id} blocked waiting for dependencies: {dependencies}")
        
        LOG.info(f"Causal job {job_id} submitted with {len(dependencies or [])} dependencies")
        return job_id
    
    def get_vector_clock_state(self) -> Dict[str, int]:
        """Get current vector clock state for coordination"""
        return self.vector_clock.clock.copy()
    
    def sync_vector_clock(self, peer_clock: Dict[str, int], peer_node: str = None) -> None:
        """
        Synchronize vector clock with peer executor
        
        Args:
            peer_clock: Peer's vector clock state
            peer_node: Peer node identifier
        """
        self.vector_clock.update(peer_clock)
        
        if peer_node:
            with self.coordination_lock:
                self.coordination.node_vector_clocks[peer_node] = peer_clock.copy()
        
        # Check if any blocked jobs can now proceed
        self._check_blocked_jobs()
        
        LOG.debug(f"Vector clock synchronized with peer {peer_node}")
    
    def register_peer_executor(self, peer_node: str, peer_executor: 'EnhancedVectorClockExecutor') -> None:
        """Register peer executor for coordination"""
        self.peer_executors[peer_node] = peer_executor
        LOG.info(f"Registered peer executor: {peer_node}")
    
    def coordinate_job_execution(self, job_id: UUID) -> bool:
        """
        Coordinate job execution across distributed nodes using FCFS policy
        
        Args:
            job_id: Job to coordinate
            
        Returns:
            bool: True if this node should execute the job
        """
        with self.causal_lock:
            causal_job = self.causal_jobs.get(job_id)
            if not causal_job:
                return False
        
        # Apply FCFS policy for distributed coordination
        fcfs_timestamp = self.coordination.fcfs_timestamps.get(job_id, time.time())
        
        # Check if any peer has an earlier job
        earliest_node = self.node_id
        earliest_timestamp = fcfs_timestamp
        
        for peer_node, peer_executor in self.peer_executors.items():
            peer_timestamp = peer_executor.coordination.fcfs_timestamps.get(job_id)
            if peer_timestamp and peer_timestamp < earliest_timestamp:
                earliest_timestamp = peer_timestamp
                earliest_node = peer_node
        
        # This node executes if it has the earliest timestamp (FCFS)
        should_execute = (earliest_node == self.node_id)
        
        if should_execute:
            LOG.info(f"Node {self.node_id} executing job {job_id} via FCFS policy")
        else:
            LOG.info(f"Job {job_id} delegated to {earliest_node} via FCFS policy")
        
        return should_execute
    
    def handle_cross_node_dependency(self, job_id: UUID, completed_job_id: UUID, 
                                   completing_node: str) -> None:
        """
        Handle completion of dependency from another node
        
        Args:
            job_id: Job waiting for dependency
            completed_job_id: Completed dependency job
            completing_node: Node that completed the dependency
        """
        self.vector_clock.tick()
        
        with self.causal_lock:
            causal_job = self.causal_jobs.get(job_id)
            if causal_job and completed_job_id in causal_job.dependencies:
                causal_job.dependencies.remove(completed_job_id)
                
                # Check if job is now ready
                if causal_job.is_ready_for_execution(self.completed_jobs):
                    causal_job.state = CausalJobState.READY
                    self._schedule_causal_job(causal_job)
                    LOG.info(f"Job {job_id} unblocked by dependency {completed_job_id} from {completing_node}")
    
    def get_causal_execution_status(self) -> Dict[str, Any]:
        """Get detailed causal execution status"""
        with self.causal_lock:
            pending_jobs = [job_id for job_id, job in self.causal_jobs.items() 
                           if job.state == CausalJobState.PENDING]
            blocked_jobs = [job_id for job_id, job in self.causal_jobs.items() 
                           if job.state == CausalJobState.BLOCKED]
            executing_jobs = [job_id for job_id, job in self.causal_jobs.items() 
                             if job.state == CausalJobState.EXECUTING]
            
        with self.coordination_lock:
            coordination_state = {
                "peer_nodes": len(self.coordination.node_vector_clocks),
                "global_job_order": len(self.coordination.global_job_order),
                "fcfs_queue": len(self.coordination.fcfs_timestamps)
            }
        
        return {
            "node_id": self.node_id,
            "vector_clock": self.vector_clock.clock.copy(),
            "causal_jobs": {
                "pending": len(pending_jobs),
                "blocked": len(blocked_jobs), 
                "executing": len(executing_jobs),
                "completed": len(self.completed_jobs)
            },
            "coordination": coordination_state,
            "emergency_mode": self.emergency_mode,
            "peer_executors": list(self.peer_executors.keys())
        }
    
    def start(self) -> None:
        """Start enhanced executor with coordination"""
        super().start()
        
        # Start vector clock synchronization
        if self.sync_thread is None or not self.sync_thread.is_alive():
            self.sync_thread = threading.Thread(
                target=self._vector_clock_sync_worker,
                daemon=True,
                name=f"vc-sync-{self.node_id}"
            )
            self.sync_thread.start()
        
        LOG.info(f"EnhancedVectorClockExecutor {self.node_id} started with coordination")
    
    def stop(self) -> None:
        """Stop enhanced executor"""
        super().stop()
        
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=2.0)
        
        LOG.info(f"EnhancedVectorClockExecutor {self.node_id} stopped")
    
    def _schedule_causal_job(self, causal_job: CausalJob) -> None:
        """Schedule causal job for execution"""
        # Convert to ExecutorJob for base class
        executor_job = ExecutorJob(
            job_id=causal_job.job_id,
            data=causal_job.data,
            priority=causal_job.priority,
            emergency_context=causal_job.emergency_context,
            vector_clock=causal_job.vector_clock_snapshot
        )
        
        # Submit to base executor
        self.job_queue.put(executor_job)
        causal_job.state = CausalJobState.READY
        
        LOG.info(f"Causal job {causal_job.job_id} scheduled for execution")
    
    def _check_blocked_jobs(self) -> None:
        """Check if any blocked jobs can now proceed"""
        with self.causal_lock:
            unblocked_jobs = []
            
            for job_id, causal_job in self.causal_jobs.items():
                if (causal_job.state == CausalJobState.BLOCKED and 
                    causal_job.is_ready_for_execution(self.completed_jobs)):
                    unblocked_jobs.append(causal_job)
            
            for causal_job in unblocked_jobs:
                causal_job.state = CausalJobState.READY
                self._schedule_causal_job(causal_job)
        
        if unblocked_jobs:
            LOG.info(f"Unblocked {len(unblocked_jobs)} jobs after vector clock sync")
    
    def _vector_clock_sync_worker(self) -> None:
        """Background worker for vector clock synchronization"""
        LOG.info(f"Vector clock sync worker started for {self.node_id}")
        
        while not self.should_exit:
            try:
                # Synchronize with all peer executors
                for peer_node, peer_executor in self.peer_executors.items():
                    if not peer_executor.should_exit:
                        peer_clock = peer_executor.get_vector_clock_state()
                        self.sync_vector_clock(peer_clock, peer_node)
                
                time.sleep(self.sync_interval)
                
            except Exception as e:
                LOG.error(f"Error in vector clock sync: {e}")
                time.sleep(1.0)
        
        LOG.info(f"Vector clock sync worker stopped for {self.node_id}")
    
    def _execute_job(self, job: ExecutorJob) -> bool:
        """Override to handle causal job execution"""
        # Check if we should coordinate execution
        if self.peer_executors and not self.coordinate_job_execution(job.job_id):
            # Another node will handle this job
            return True
        
        # Update causal job state
        with self.causal_lock:
            causal_job = self.causal_jobs.get(job.job_id)
            if causal_job:
                causal_job.state = CausalJobState.EXECUTING
                causal_job.started_at = time.time()
        
        # Execute job using parent implementation
        result = super()._execute_job(job)
        
        # Update causal job state and notify peers
        with self.causal_lock:
            causal_job = self.causal_jobs.get(job.job_id)
            if causal_job:
                if result:
                    causal_job.state = CausalJobState.COMPLETED
                    causal_job.completed_at = time.time()
                    
                    # Notify dependent jobs on this node
                    for dependent_job_id in self.dependency_graph.get(job.job_id, set()):
                        self.handle_cross_node_dependency(dependent_job_id, job.job_id, self.node_id)
                    
                    # Notify peer executors
                    self._notify_job_completion(job.job_id)
                else:
                    causal_job.state = CausalJobState.FAILED
        
        return result
    
    def _notify_job_completion(self, job_id: UUID) -> None:
        """Notify peer executors of job completion"""
        for peer_node, peer_executor in self.peer_executors.items():
            # Check if peer has dependent jobs
            for dependent_job_id in peer_executor.dependency_graph.get(job_id, set()):
                peer_executor.handle_cross_node_dependency(dependent_job_id, job_id, self.node_id)

# Demo and testing functions
def demo_enhanced_vector_clock_executor():
    """Demonstrate EnhancedVectorClockExecutor functionality"""
    print("\n=== EnhancedVectorClockExecutor Demo ===")
    
    # Create two coordinated executors
    capabilities = ExecutorCapabilities(
        supported_languages={"python", "compute"},
        max_concurrent_jobs=2,
        emergency_capable=True
    )
    
    executor1 = EnhancedVectorClockExecutor("vc_executor_1", capabilities)
    executor2 = EnhancedVectorClockExecutor("vc_executor_2", capabilities)
    
    # Register as peers
    executor1.register_peer_executor("vc_executor_2", executor2)
    executor2.register_peer_executor("vc_executor_1", executor1)
    
    print(f"✅ Created coordinated executors: {executor1.node_id}, {executor2.node_id}")
    
    # Start executors
    executor1.start()
    executor2.start()
    print("✅ Executors started with coordination")
    
    # Submit jobs with causal dependencies
    job1_id = executor1.submit_causal_job(
        {"task": "preprocess_data", "data_size": 1000}
    )
    
    job2_id = executor1.submit_causal_job(
        {"task": "analyze_data", "model": "regression"},
        dependencies={job1_id}  # Job 2 depends on Job 1
    )
    
    job3_id = executor2.submit_causal_job(
        {"task": "generate_report", "format": "pdf"},
        dependencies={job2_id}  # Job 3 depends on Job 2
    )
    
    print(f"✅ Submitted causal jobs: {job1_id} -> {job2_id} -> {job3_id}")
    
    # Test emergency job
    emergency_job_id = executor1.submit_causal_job(
        {"task": "emergency_backup", "priority": "critical"},
        emergency_context=create_emergency("system_failure", "critical")
    )
    print(f"✅ Emergency job submitted: {emergency_job_id}")
    
    # Wait for processing
    time.sleep(1.0)
    
    # Check execution status
    status1 = executor1.get_causal_execution_status()
    status2 = executor2.get_causal_execution_status()
    
    print(f"✅ Executor 1 status: {status1['causal_jobs']}")
    print(f"✅ Executor 2 status: {status2['causal_jobs']}")
    print(f"✅ Vector clock sync: {len(status1['peer_executors'])} peers")
    
    # Stop executors
    executor1.stop()
    executor2.stop()
    print("✅ Executors stopped")
    
    return True

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run demo
    demo_enhanced_vector_clock_executor()
