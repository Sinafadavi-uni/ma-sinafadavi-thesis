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
from typing import Dict, Optional, Set, List
from uuid import UUID, uuid4
from queue import Queue, Empty
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from collections import defaultdict
import logging

# Import Phase 1 foundation
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
    """Information about a registered executor"""
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
    """Job submission information"""
    job_id: UUID
    data: dict
    capabilities: Set[str] = field(default_factory=set)
    emergency_context: Optional[EmergencyContext] = None
    vector_clock: Optional[dict] = None
    result_addr: Optional[str] = None

@dataclass
class QueuedJob:
    """Job waiting for execution"""
    job_info: JobInfo
    wait_for: Set[UUID] = field(default_factory=set)
    submitted_at: float = field(default_factory=time.time)
    causal_message: Optional[CausalMessage] = None

class ExecutorBroker:
    """
    Core broker for managing distributed executors with vector clock coordination
    
    Features:
    - Executor registration and health monitoring
    - Vector clock synchronization across nodes
    - Emergency-aware job scheduling
    - Causal consistency for job ordering
    """
    
    def __init__(self, broker_id: str = None):
        """Initialize ExecutorBroker with vector clock coordination"""
        self.broker_id = broker_id or str(uuid4())
        self.vector_clock = VectorClock(self.broker_id)
        
        # Executor management
        self.executors: Dict[UUID, ExecutorInfo] = {}
        self.executor_lock = threading.RLock()
        
        # Job management  
        self.queued_jobs = Queue()
        self.completed_jobs: Set[UUID] = set()
        self.completed_lock = threading.RLock()
        
        # Add job tracking
        self.job_to_executor: Dict[UUID, UUID] = {}  # job_id -> executor_id
        self.executor_to_jobs: Dict[UUID, Set[UUID]] = defaultdict(set)  # executor_id -> {job_ids}
        self.job_states: Dict[UUID, str] = {}  # job_id -> state
        
        # Emergency and consistency management
        self.current_emergency: Optional[EmergencyContext] = None
        self.message_handler = MessageHandler(self.broker_id)
        self.consistency_manager = CausalConsistencyManager(self.broker_id)
        
        # Thread management
        self.should_exit = False
        self.scheduler_thread = None
        
        LOG.info(f"ExecutorBroker {self.broker_id} initialized")
    
    def register_executor(self, executor_id: UUID, host: str, port: int, 
                         capabilities: Set[str] = None) -> bool:
        """
        Register executor with vector clock synchronization
        
        Args:
            executor_id: Unique executor identifier
            host: Executor host address
            port: Executor port
            capabilities: Executor capabilities
            
        Returns:
            True if registration successful
        """
        # Tick vector clock for registration event
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
        
        # Synchronize vector clocks
        self._synchronize_with_executor(executor_info)
        
        return True
    
    def heartbeat_executor(self, executor_id: UUID, capabilities: Set[str] = None,
                          vector_clock_state: dict = None, 
                          emergency_context: EmergencyContext = None) -> bool:
        """
        Process executor heartbeat with vector clock and emergency updates
        
        Args:
            executor_id: Executor sending heartbeat
            capabilities: Updated capabilities
            vector_clock_state: Executor's vector clock state
            emergency_context: Current emergency context
            
        Returns:
            True if heartbeat processed successfully
        """
        with self.executor_lock:
            executor = self.executors.get(executor_id)
            if executor is None:
                LOG.warning(f"Heartbeat from unregistered executor {executor_id}")
                return False
            
            # Update executor info
            executor.last_update = time.time()
            if capabilities is not None:
                executor.capabilities = capabilities
            if emergency_context is not None:
                executor.emergency_context = emergency_context
                
            # Update vector clocks
            if vector_clock_state:
                executor.vector_clock.update(vector_clock_state)
                self.vector_clock.update(vector_clock_state)
            
            # Tick for heartbeat event
            self.vector_clock.tick()
            
            LOG.debug(f"Heartbeat processed for executor {executor_id}")
            return True
    
    def submit_job(self, job_info: JobInfo, wait_for: Set[UUID] = None) -> UUID:
        """
        Submit job with vector clock ordering and emergency prioritization
        
        Args:
            job_info: Job information
            wait_for: Job dependencies
            
        Returns:
            Job ID if submission successful
        """
        # Tick vector clock for job submission
        self.vector_clock.tick()
        
        # Add vector clock state to job
        job_info.vector_clock = self.vector_clock.clock.copy()
        
        # Check for emergency context
        if self.current_emergency and self.current_emergency.is_critical():
            job_info.emergency_context = self.current_emergency
            LOG.info(f"Job {job_info.job_id} marked as emergency: {self.current_emergency.emergency_type}")
        
        # Create causal message for job
        causal_msg = CausalMessage(
            content=job_info.data,
            sender_id=self.broker_id,
            vector_clock=self.vector_clock.clock.copy(),
            message_type="emergency" if job_info.emergency_context and job_info.emergency_context.is_critical() else "normal",
            priority=10 if job_info.emergency_context and job_info.emergency_context.is_critical() else 1
        )
        
        # Create queued job
        queued_job = QueuedJob(
            job_info=job_info,
            wait_for=wait_for or set(),
            causal_message=causal_msg
        )
        
        # Emergency jobs get priority
        if job_info.emergency_context and job_info.emergency_context.is_critical():
            # Find suitable executor immediately for emergency
            executor = self._find_capable_executor(job_info.capabilities, emergency=True)
            if executor:
                return self._execute_job_on_executor(job_info, executor)
        
        # Queue normal job
        self.queued_jobs.put(queued_job)
        LOG.debug(f"Job {job_info.job_id} queued for execution")
        
        return job_info.job_id
    
    def set_emergency_mode(self, emergency_type: str, priority_level: str) -> None:
        """
        Activate emergency mode with vector clock coordination
        
        Args:
            emergency_type: Type of emergency
            priority_level: Priority level
        """
        # Tick for emergency activation
        self.vector_clock.tick()
        
        self.current_emergency = create_emergency(emergency_type, priority_level)
        
        # Propagate emergency to all executors
        with self.executor_lock:
            for executor in self.executors.values():
                executor.emergency_context = self.current_emergency
        
        LOG.warning(f"Emergency mode activated: {emergency_type} ({priority_level})")
    
    def clear_emergency_mode(self) -> None:
        """Clear emergency mode"""
        self.vector_clock.tick()
        self.current_emergency = None
        
        # Clear emergency from all executors
        with self.executor_lock:
            for executor in self.executors.values():
                executor.emergency_context = None
        
        LOG.info("Emergency mode cleared")
    
    def job_completed(self, job_id: UUID) -> None:
        """Mark job as completed with vector clock update"""
        self.vector_clock.tick()
        
        with self.completed_lock:
            self.completed_jobs.add(job_id)
        
        LOG.debug(f"Job {job_id} marked as completed")
    
    def get_executor_count(self) -> int:
        """Get number of active executors"""
        self._prune_executor_list()
        with self.executor_lock:
            return len(self.executors)
    
    def start(self) -> None:
        """Start broker background processing"""
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
        """Stop broker processing"""
        self.should_exit = True
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5.0)
        LOG.info(f"ExecutorBroker {self.broker_id} stopped")
    
    def _find_capable_executor(self, required_caps: Set[str], 
                              emergency: bool = False) -> Optional[ExecutorInfo]:
        """
        Find executor capable of handling job with given capabilities
        
        Args:
            required_caps: Required capabilities
            emergency: Whether this is an emergency job
            
        Returns:
            Suitable executor or None
        """
        self._prune_executor_list()
        
        with self.executor_lock:
            capable_executors = [
                executor for executor in self.executors.values()
                if required_caps.issubset(executor.capabilities)
            ]
        
        if not capable_executors:
            return None
        
        # For emergency jobs, prefer executors not in emergency mode
        if emergency:
            non_emergency_executors = [
                ex for ex in capable_executors 
                if ex.emergency_context is None or not ex.emergency_context.is_critical()
            ]
            if non_emergency_executors:
                capable_executors = non_emergency_executors
        
        # Select random capable executor
        return random.choice(capable_executors)
    
    def _execute_job_on_executor(self, job_info: JobInfo, executor: ExecutorInfo) -> UUID:
        """
        Enhanced job execution with tracking
        
        Args:
            job_info: Job to execute
            executor: Target executor
            
        Returns:
            Job ID if successful
        """
        # Synchronize vector clocks before execution
        self.vector_clock.update(executor.vector_clock.clock)
        self.vector_clock.tick()
        
        # Track job assignment
        with self.executor_lock:
            self.job_to_executor[job_info.job_id] = executor.id
            self.executor_to_jobs[executor.id].add(job_info.job_id)
            self.job_states[job_info.job_id] = "executing"
        
        LOG.info(f"Job {job_info.job_id} assigned to executor {executor.id}")
        
        # Create execution message
        execution_msg = CausalMessage(
            content=job_info.data,
            sender_id=self.broker_id,
            vector_clock=self.vector_clock.clock.copy(),
            message_type="emergency" if job_info.emergency_context and job_info.emergency_context.is_critical() else "normal"
        )
        
        LOG.info(f"Executing job {job_info.job_id} on executor {executor.id}")
        
        # In real implementation, would send to executor via network
        # For demo, just log the execution
        return job_info.job_id
    
    def _synchronize_with_executor(self, executor: ExecutorInfo) -> None:
        """Synchronize vector clocks with executor"""
        self.vector_clock.update(executor.vector_clock.clock)
        executor.vector_clock.update(self.vector_clock.clock)
    
    def _prune_executor_list(self) -> None:
        """Remove unresponsive executors"""
        current_time = time.time()
        timeout = 130  # 130 seconds timeout
        
        to_remove = []
        with self.executor_lock:
            for executor_id, executor in self.executors.items():
                if (current_time - executor.last_update) > timeout:
                    to_remove.append(executor_id)
        
        for executor_id in to_remove:
            with self.executor_lock:
                removed = self.executors.pop(executor_id, None)
                if removed:
                    LOG.warning(f"Removed unresponsive executor {executor_id}")
    
    def _job_scheduler(self) -> None:
        """Background job scheduler thread"""
        LOG.info(f"Job scheduler started for broker {self.broker_id}")
        
        while not self.should_exit:
            try:
                # Get next job from queue
                queued_job = self.queued_jobs.get(timeout=1.0)
                
                # Check if dependencies are satisfied
                with self.completed_lock:
                    dependencies_met = queued_job.wait_for.issubset(self.completed_jobs)
                
                if not dependencies_met:
                    # Put job back and wait
                    self.queued_jobs.put(queued_job)
                    time.sleep(1.0)
                    continue
                
                # Find capable executor
                executor = self._find_capable_executor(
                    queued_job.job_info.capabilities,
                    emergency=bool(queued_job.job_info.emergency_context)
                )
                
                if executor:
                    self._execute_job_on_executor(queued_job.job_info, executor)
                else:
                    # No capable executor, requeue and wait
                    self.queued_jobs.put(queued_job)
                    time.sleep(5.0)
                    
            except Empty:
                # No jobs to process, continue
                continue
            except Exception as e:
                LOG.error(f"Error in job scheduler: {e}")
                time.sleep(1.0)
        
        LOG.info(f"Job scheduler stopped for broker {self.broker_id}")

# Demo and testing functions
def demo_executorbroker():
    """Demonstrate ExecutorBroker functionality"""
    print("\n=== ExecutorBroker Demo ===")
    
    # Create broker
    broker = ExecutorBroker("demo_broker")
    print(f"✅ Created broker: {broker.broker_id}")
    
    # Register executors
    exec1_id = uuid4()
    exec2_id = uuid4()
    
    broker.register_executor(exec1_id, "127.0.0.1", 8001, {"python", "compute"})
    broker.register_executor(exec2_id, "127.0.0.1", 8002, {"python", "storage"})
    
    print(f"✅ Registered {broker.get_executor_count()} executors")
    
    # Start broker
    broker.start()
    print("✅ Broker started")
    
    # Submit jobs
    job1 = JobInfo(
        job_id=uuid4(),
        data={"task": "compute_pi", "precision": 1000},
        capabilities={"python", "compute"}
    )
    
    job_id = broker.submit_job(job1)
    print(f"✅ Submitted job: {job_id}")
    
    # Test emergency mode
    broker.set_emergency_mode("fire", "critical")
    print("✅ Emergency mode activated")
    
    # Submit emergency job
    emergency_job = JobInfo(
        job_id=uuid4(),
        data={"task": "emergency_evacuation", "zone": "A1"},
        capabilities={"python"}
    )
    
    emergency_id = broker.submit_job(emergency_job)
    print(f"✅ Emergency job submitted: {emergency_id}")
    
    # Test heartbeats
    time.sleep(0.1)
    broker.heartbeat_executor(exec1_id, {"python", "compute"})
    broker.heartbeat_executor(exec2_id, {"python", "storage"})
    print("✅ Heartbeats processed")
    
    # Complete jobs
    broker.job_completed(job_id)
    broker.job_completed(emergency_id)
    print("✅ Jobs completed")
    
    # Clear emergency
    broker.clear_emergency_mode()
    print("✅ Emergency mode cleared")
    
    # Stop broker
    broker.stop()
    print("✅ Broker stopped")
    
    return True

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run demo
    demo_executorbroker()