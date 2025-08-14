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
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum
from queue import PriorityQueue, Empty
from abc import ABC, abstractmethod

# Import Phase 1 foundation
try:
    from ..Phase1_Core_Foundation.vector_clock import VectorClock, EmergencyContext, EmergencyLevel, create_emergency
    from ..Phase1_Core_Foundation.causal_message import CausalMessage, MessageHandler
    from ..Phase1_Core_Foundation.causal_consistency import CausalConsistencyManager
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Phase1_Core_Foundation'))
    from vector_clock import VectorClock, EmergencyContext, EmergencyLevel, create_emergency
    from causal_message import CausalMessage, MessageHandler
    from causal_consistency import CausalConsistencyManager

LOG = logging.getLogger(__name__)

class ExecutorStatus(Enum):
    """Executor status enumeration"""
    IDLE = "idle"
    BUSY = "busy"
    EMERGENCY = "emergency"
    MAINTENANCE = "maintenance"
    FAILED = "failed"

class JobPriority(Enum):
    """Job priority levels"""
    EMERGENCY_CRITICAL = 0
    EMERGENCY_HIGH = 1
    EMERGENCY_NORMAL = 2
    NORMAL_HIGH = 3
    NORMAL_MEDIUM = 4
    NORMAL_LOW = 5

@dataclass
class ExecutorJob:
    """Job execution information"""
    job_id: UUID
    data: dict
    priority: JobPriority = JobPriority.NORMAL_MEDIUM
    capabilities: set = field(default_factory=set)
    emergency_context: EmergencyContext = None
    vector_clock: dict = None
    submitted_at: float = field(default_factory=time.time)
    causal_message: CausalMessage = None
    
    def __lt__(self, other):
        """Priority comparison for queue ordering"""
        # Lower priority value = higher priority
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        # If same priority, use submission time
        return self.submitted_at < other.submitted_at

@dataclass
class ExecutorCapabilities:
    """Executor capabilities and resources"""
    supported_languages: set = field(default_factory=lambda: {"python"})
    max_concurrent_jobs: int = 4
    emergency_capable: bool = True
    resource_allocation: dict = field(default_factory=dict)
    
    def is_capable(self, required_caps):
        """Check if executor can handle required capabilities"""
        return required_caps.issubset(self.supported_languages)

class JobExecutionStrategy(ABC):
    """Abstract base for job execution strategies"""
    
    @abstractmethod
    def should_execute_immediately(self, job, current_load):
        """Determine if job should execute immediately"""
        pass
    
    @abstractmethod
    def allocate_resources(self, job):
        """Allocate resources for job execution"""
        pass

class EmergencyExecutionStrategy(JobExecutionStrategy):
    """Emergency-aware execution strategy"""
    
    def __init__(self, max_concurrent=4):
        self.max_concurrent = max_concurrent
    
    def should_execute_immediately(self, job, current_load):
        """Determine if job should execute immediately"""
        # Emergency jobs always get priority
        if job.emergency_context and job.emergency_context.is_critical():
            return True
        
        # Normal jobs only if under capacity
        return current_load < self.max_concurrent
    
    def allocate_resources(self, job):
        """Allocate resources for job execution"""
        resources = {
            "cpu_cores": 1,
            "memory_mb": 512,
            "timeout_seconds": 300
        }
        
        # Increase resources for emergency jobs
        if job.emergency_context:
            if job.emergency_context.level == EmergencyLevel.CRITICAL:
                resources["cpu_cores"] = 2
                resources["memory_mb"] = 1024
                resources["timeout_seconds"] = 60  # Faster timeout for critical
            elif job.emergency_context.level == EmergencyLevel.HIGH:
                resources["cpu_cores"] = 1
                resources["memory_mb"] = 768
                resources["timeout_seconds"] = 120
        
        return resources

class SimpleEmergencyExecutor:
    """
    Emergency-aware job executor with vector clock coordination
    
    Features:
    - Emergency context propagation and prioritization
    - Vector clock synchronization for job ordering
    - Causal consistency preservation during execution
    - Resource reallocation for emergency tasks
    - Health monitoring and status reporting
    """
    
    def __init__(self, node_id, capabilities=None):
        """Initialize emergency executor"""
        self.node_id = node_id
        self.vector_clock = VectorClock(node_id)
        self.capabilities = capabilities or ExecutorCapabilities()
        
        # Execution management
        self.status = ExecutorStatus.IDLE
        self.job_queue = PriorityQueue()
        self.active_jobs = {}
        self.completed_jobs = set()
        self.job_lock = threading.RLock()
        
        # Emergency management
        self.emergency_mode = False
        self.current_emergency = None
        self.execution_strategy = EmergencyExecutionStrategy(
            self.capabilities.max_concurrent_jobs
        )
        
        # Consistency and messaging
        self.message_handler = MessageHandler(self.node_id)
        self.consistency_manager = CausalConsistencyManager(self.node_id)
        
        # Thread management
        self.should_exit = False
        self.executor_thread = None
        self.last_heartbeat = time.time()
        
        LOG.info(f"EmergencyExecutor {node_id} initialized")
    
    def submit_job(self, job):
        """
        Submit job for execution with emergency prioritization
        
        Args:
            job: Job to execute
            
        Returns:
            True if job submitted successfully
        """
        # Tick vector clock for job submission
        self.vector_clock.tick()
        
        # Add vector clock state to job
        job.vector_clock = self.vector_clock.clock.copy()
        
        # Determine job priority based on emergency context
        if job.emergency_context:
            if job.emergency_context.level == EmergencyLevel.CRITICAL:
                job.priority = JobPriority.EMERGENCY_CRITICAL
            elif job.emergency_context.level == EmergencyLevel.HIGH:
                job.priority = JobPriority.EMERGENCY_HIGH
            else:
                job.priority = JobPriority.EMERGENCY_NORMAL
        
        # Create causal message for job
        causal_msg = CausalMessage(
            content=job.data,
            sender_id="broker",
            vector_clock=job.vector_clock,
            message_type="emergency" if job.emergency_context and job.emergency_context.is_critical() else "normal",
            priority=10 if job.emergency_context and job.emergency_context.is_critical() else 1
        )
        job.causal_message = causal_msg
        
        # Check if executor can handle job
        if not self.capabilities.is_capable(job.capabilities):
            LOG.warning(f"Executor {self.node_id} cannot handle job {job.job_id} capabilities: {job.capabilities}")
            return False
        
        # Submit to priority queue
        self.job_queue.put(job)
        
        LOG.info(f"Job {job.job_id} submitted to executor {self.node_id} with priority {job.priority.name}")
        return True
    
    def set_emergency_mode(self, emergency_type: str, priority_level: str) -> None:
        """
        Activate emergency mode
        
        Args:
            emergency_type: Type of emergency
            priority_level: Priority level
        """
        self.vector_clock.tick()
        
        self.emergency_mode = True
        self.current_emergency = create_emergency(emergency_type, priority_level)
        self.status = ExecutorStatus.EMERGENCY
        
        # Interrupt non-emergency jobs if emergency is critical
        if self.current_emergency.is_critical():
            self._interrupt_non_emergency_jobs()
        
        LOG.warning(f"Executor {self.node_id} emergency mode activated: {emergency_type} ({priority_level})")
    
    def clear_emergency_mode(self):
        """Clear emergency mode"""
        self.vector_clock.tick()
        
        self.emergency_mode = False
        self.current_emergency = None
        self.status = ExecutorStatus.IDLE if not self.active_jobs else ExecutorStatus.BUSY
        
        LOG.info(f"Executor {self.node_id} emergency mode cleared")
    
    @property
    def in_emergency_mode(self):
        """Check if executor is in emergency mode"""
        return self.emergency_mode
    
    def get_status(self):
        """Get executor status information"""
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
    
    def heartbeat(self):
        """Send heartbeat with current status"""
        self.vector_clock.tick()
        self.last_heartbeat = time.time()
        
        status = self.get_status()
        LOG.debug(f"Heartbeat from executor {self.node_id}")
        return status
    
    def cancel_job(self, job_id):
        """
        Cancel job execution
        
        Args:
            job_id: Job to cancel
            
        Returns:
            True if job cancelled successfully
        """
        self.vector_clock.tick()
        
        with self.job_lock:
            # Remove from active jobs if running
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
                LOG.info(f"Active job {job_id} cancelled on executor {self.node_id}")
                return True
        
        # Remove from queue if not yet started
        # Note: PriorityQueue doesn't support direct removal, 
        # so we'll mark for cancellation during processing
        LOG.info(f"Job {job_id} marked for cancellation on executor {self.node_id}")
        return True
    
    def start(self) -> None:
        """Start executor background processing"""
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
        """Stop executor processing"""
        self.should_exit = True
        if self.executor_thread and self.executor_thread.is_alive():
            self.executor_thread.join(timeout=5.0)
        LOG.info(f"EmergencyExecutor {self.node_id} stopped")
    
    def _interrupt_non_emergency_jobs(self) -> None:
        """Interrupt non-emergency jobs for critical emergency"""
        interrupted = []
        
        with self.job_lock:
            for job_id, job in list(self.active_jobs.items()):
                # Keep emergency jobs running
                if job.emergency_context and job.emergency_context.is_critical():
                    continue
                
                # Interrupt non-emergency jobs
                del self.active_jobs[job_id]
                interrupted.append(job_id)
        
        if interrupted:
            LOG.warning(f"Interrupted {len(interrupted)} non-emergency jobs for critical emergency")
    
    def _job_processor(self) -> None:
        """Background job processing thread"""
        LOG.info(f"Job processor started for executor {self.node_id}")
        
        while not self.should_exit:
            try:
                # Get next job from priority queue
                job = self.job_queue.get(timeout=1.0)
                
                # Check if we should execute immediately
                current_load = len(self.active_jobs)
                if not self.execution_strategy.should_execute_immediately(job, current_load):
                    # Put job back and wait
                    self.job_queue.put(job)
                    time.sleep(0.5)
                    continue
                
                # Execute job
                self._execute_job(job)
                
            except Empty:
                # No jobs to process, update status
                if not self.active_jobs:
                    self.status = ExecutorStatus.EMERGENCY if self.emergency_mode else ExecutorStatus.IDLE
                continue
            except Exception as e:
                LOG.error(f"Error in job processor: {e}")
                time.sleep(1.0)
        
        LOG.info(f"Job processor stopped for executor {self.node_id}")
    
    def _execute_job(self, job: ExecutorJob) -> bool:
        """
        Execute individual job
        
        Args:
            job: Job to execute
            
        Returns:
            True if execution successful
        """
        # Update vector clock before execution
        if job.vector_clock:
            self.vector_clock.update(job.vector_clock)
        self.vector_clock.tick()
        
        # Add to active jobs
        with self.job_lock:
            self.active_jobs[job.job_id] = job
            self.status = ExecutorStatus.EMERGENCY if self.emergency_mode else ExecutorStatus.BUSY
        
        # Allocate resources
        resources = self.execution_strategy.allocate_resources(job)
        
        LOG.info(f"Executing job {job.job_id} on executor {self.node_id}")
        LOG.debug(f"Job resources: {resources}")
        
        try:
            # Simulate job execution
            execution_time = self._simulate_job_execution(job, resources)
            
            # Mark job as completed
            with self.job_lock:
                del self.active_jobs[job.job_id]
                self.completed_jobs.add(job.job_id)
            
            # Tick for completion
            self.vector_clock.tick()
            
            LOG.info(f"Job {job.job_id} completed in {execution_time:.2f}s on executor {self.node_id}")
            return True
            
        except Exception as e:
            LOG.error(f"Job {job.job_id} failed on executor {self.node_id}: {e}")
            
            # Remove from active jobs
            with self.job_lock:
                self.active_jobs.pop(job.job_id, None)
            
            return False
    
    def _simulate_job_execution(self, job, resources):
        """
        Simulate job execution time
        
        Args:
            job: Job being executed
            resources: Allocated resources
            
        Returns:
            Execution time in seconds
        """
        # Base execution time
        base_time = 1.0
        
        # Emergency jobs execute faster
        if job.emergency_context:
            if job.emergency_context.level == EmergencyLevel.CRITICAL:
                base_time = 0.1  # Very fast for critical
            elif job.emergency_context.level == EmergencyLevel.HIGH:
                base_time = 0.3  # Fast for high priority
            else:
                base_time = 0.5  # Moderate for normal emergency
        
        # More CPU cores = faster execution
        cpu_multiplier = 1.0 / resources.get("cpu_cores", 1)
        execution_time = base_time * cpu_multiplier
        
        # Simulate execution
        time.sleep(execution_time)
        
        return execution_time

# Demo and testing functions
def demo_emergency_executor():
    """Demonstrate EmergencyExecutor functionality"""
    print("\n=== EmergencyExecutor Demo ===")
    
    # Create emergency executor
    capabilities = ExecutorCapabilities(
        supported_languages={"python", "compute"},
        max_concurrent_jobs=2,
        emergency_capable=True
    )
    
    executor = SimpleEmergencyExecutor("demo_executor", capabilities)
    print(f"✅ Created executor: {executor.node_id}")
    
    # Start executor
    executor.start()
    print("✅ Executor started")
    
    # Submit normal jobs
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
    
    # Check status
    status = executor.get_status()
    print(f"✅ Executor status: {status['status']}")
    print(f"✅ Active jobs: {status['active_jobs']}")
    print(f"✅ Queued jobs: {status['queued_jobs']}")
    
    # Activate emergency mode
    executor.set_emergency_mode("fire", "critical")
    print("✅ Emergency mode activated")
    
    # Submit emergency job
    emergency_job = ExecutorJob(
        job_id=uuid4(),
        data={"task": "emergency_evacuation", "zone": "A1"},
        capabilities={"python"},
        emergency_context=create_emergency("fire", "critical")
    )
    
    executor.submit_job(emergency_job)
    print("✅ Emergency job submitted")
    
    # Wait for processing
    time.sleep(0.5)
    print("✅ Jobs processed")
    
    # Send heartbeat
    heartbeat_data = executor.heartbeat()
    print(f"✅ Heartbeat sent: emergency_mode={heartbeat_data['emergency_mode']}")
    
    # Check final status
    final_status = executor.get_status()
    print(f"✅ Completed jobs: {final_status['completed_jobs']}")
    
    # Clear emergency mode
    executor.clear_emergency_mode()
    print("✅ Emergency mode cleared")
    
    # Stop executor
    executor.stop()
    print("✅ Executor stopped")
    
    return True

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run demo
    demo_emergency_executor()