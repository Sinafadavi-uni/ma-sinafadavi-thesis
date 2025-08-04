# Simple Emergency Executor for Task 3
# This handles emergency jobs with vector clock coordination
# Written to be simple and easy to understand for students

import time
from typing import Dict, List
from uuid import UUID, uuid4

from rec.model import JobInfo, Capabilities
from rec.replication.core.vector_clock import VectorClock, EmergencyLevel, create_emergency
from rec.util.log import LOG


class SimpleEmergencyExecutor:
    """
    A simple executor that can handle both normal and emergency jobs.
    Emergency jobs get higher priority and are processed first.
    """
    
    def __init__(self, executor_id: str = None):
        # Basic setup
        self.executor_id = executor_id or f"executor_{uuid4().hex[:8]}"
        self.vector_clock = VectorClock(self.executor_id)
        
        # Job tracking - using simple lists and sets
        self.normal_jobs = []       # Regular jobs waiting to run
        self.emergency_jobs = []    # Emergency jobs (higher priority)
        self.running_jobs = set()   # Jobs currently being executed
        self.completed_jobs = set() # Jobs that are done
        
        # Emergency state
        self.emergency_level = EmergencyLevel.LOW
        self.in_emergency_mode = False
        
        # Simple capabilities
        self.max_concurrent_jobs = 3  # How many jobs we can run at once
        
        LOG.info(f"Emergency executor {self.executor_id} started")
    
    def receive_job(self, job_id: UUID, job_info: JobInfo, is_emergency: bool = False):
        """
        Add a new job to our queue.
        Emergency jobs go to the emergency queue, others to normal queue.
        """
        # Update our vector clock when we get a new job
        self.vector_clock.tick()
        
        if is_emergency:
            self.emergency_jobs.append((job_id, job_info))
            LOG.warning(f"Emergency job {job_id} received!")
        else:
            self.normal_jobs.append((job_id, job_info))
            LOG.info(f"Normal job {job_id} received")
        
        # Try to start jobs if we have capacity
        self._try_start_jobs()
    
    def set_emergency_mode(self, emergency_type: str, level: str):
        """
        Put the executor into emergency mode.
        In emergency mode, we only process emergency jobs.
        """
        self.vector_clock.tick()  # Update clock for this state change
        
        self.in_emergency_mode = True
        
        # Convert string level to enum
        if level.lower() == "low":
            self.emergency_level = EmergencyLevel.LOW
        elif level.lower() == "medium":
            self.emergency_level = EmergencyLevel.MEDIUM
        elif level.lower() == "high":
            self.emergency_level = EmergencyLevel.HIGH
        elif level.lower() == "critical":
            self.emergency_level = EmergencyLevel.CRITICAL
        
        LOG.warning(f"EMERGENCY MODE: {emergency_type} - {level}")
        
        # Emergency mode: stop accepting new normal jobs
        if self.emergency_level in [EmergencyLevel.HIGH, EmergencyLevel.CRITICAL]:
            LOG.warning("High/Critical emergency: pausing normal job processing")
    
    def clear_emergency_mode(self):
        """
        Exit emergency mode and return to normal operation.
        """
        self.vector_clock.tick()
        self.in_emergency_mode = False
        self.emergency_level = EmergencyLevel.LOW
        LOG.info("Emergency mode cleared - returning to normal operation")
        
        # Try to start any waiting jobs
        self._try_start_jobs()
    
    def _try_start_jobs(self):
        """
        Simple job scheduler. Emergency jobs always go first.
        """
        # Check if we have room for more jobs
        if len(self.running_jobs) >= self.max_concurrent_jobs:
            return  # Already at capacity
        
        # First, try to start emergency jobs
        while self.emergency_jobs and len(self.running_jobs) < self.max_concurrent_jobs:
            job_id, job_info = self.emergency_jobs.pop(0)  # Take first emergency job
            self._start_job(job_id, job_info, is_emergency=True)
        
        # Then, try normal jobs (but only if not in high/critical emergency)
        if not self.in_emergency_mode or self.emergency_level not in [EmergencyLevel.HIGH, EmergencyLevel.CRITICAL]:
            while self.normal_jobs and len(self.running_jobs) < self.max_concurrent_jobs:
                job_id, job_info = self.normal_jobs.pop(0)  # Take first normal job
                self._start_job(job_id, job_info, is_emergency=False)
    
    def _start_job(self, job_id: UUID, job_info: JobInfo, is_emergency: bool):
        """
        Actually start running a job.
        This is simplified - in reality it would execute WASM, etc.
        """
        self.vector_clock.tick()  # Update clock when starting job
        self.running_jobs.add(job_id)
        
        job_type = "EMERGENCY" if is_emergency else "normal"
        LOG.info(f"Starting {job_type} job {job_id}")
        
        # Simulate job execution (in real system, this would be more complex)
        # For demo, we'll just mark it as completed after a short delay
        self._simulate_job_completion(job_id)
    
    def _simulate_job_completion(self, job_id: UUID):
        """
        Simulate a job finishing.
        In a real system, this would be called when the job actually completes.
        """
        # Simulate some work time
        time.sleep(0.1)  # Very short for demo
        
        self.vector_clock.tick()  # Update clock when job completes
        self.running_jobs.discard(job_id)
        self.completed_jobs.add(job_id)
        
        LOG.info(f"Job {job_id} completed")
        
        # Try to start more jobs now that we have capacity
        self._try_start_jobs()
    
    def get_status(self) -> Dict:
        """
        Get current status of the executor.
        Simple dictionary with all the important info.
        """
        return {
            "executor_id": self.executor_id,
            "vector_clock": self.vector_clock.to_dict(),
            "in_emergency_mode": self.in_emergency_mode,
            "emergency_level": self.emergency_level.name if self.emergency_level else "NONE",
            "jobs": {
                "emergency_queue": len(self.emergency_jobs),
                "normal_queue": len(self.normal_jobs),
                "running": len(self.running_jobs),
                "completed": len(self.completed_jobs)
            },
            "capacity": {
                "max_concurrent": self.max_concurrent_jobs,
                "available_slots": self.max_concurrent_jobs - len(self.running_jobs)
            }
        }
    
    def sync_vector_clock(self, other_clock: Dict):
        """
        Synchronize our vector clock with another node's clock.
        This helps maintain distributed coordination.
        """
        self.vector_clock.update(other_clock)
        LOG.debug(f"Vector clock synchronized: {self.vector_clock.to_dict()}")


# Simple helper function to create emergency executors
def create_emergency_executor(executor_id: str = None) -> SimpleEmergencyExecutor:
    """
    Factory function to create a new emergency executor.
    Makes it easy for students to create executors.
    """
    return SimpleEmergencyExecutor(executor_id)


# Demo function to show how it works
def demo_emergency_executor():
    """
    Simple demonstration of how the emergency executor works.
    Students can run this to see the system in action.
    """
    print("=== Emergency Executor Demo ===")
    
    # Create an executor
    executor = create_emergency_executor("demo_executor")
    
    # Add some normal jobs
    normal_job_1 = JobInfo(wasm_bin="demo_normal_1.wasm")
    normal_job_2 = JobInfo(wasm_bin="demo_normal_2.wasm")
    
    executor.receive_job(uuid4(), normal_job_1, is_emergency=False)
    executor.receive_job(uuid4(), normal_job_2, is_emergency=False)
    
    print("Status after adding normal jobs:")
    print(executor.get_status())
    
    # Declare an emergency
    executor.set_emergency_mode("fire", "high")
    
    # Add an emergency job
    emergency_job = JobInfo(wasm_bin="demo_emergency.wasm")
    executor.receive_job(uuid4(), emergency_job, is_emergency=True)
    
    print("\nStatus after emergency and emergency job:")
    print(executor.get_status())
    
    # Wait a bit for jobs to complete
    time.sleep(0.5)
    
    print("\nFinal status:")
    print(executor.get_status())
    
    # Clear emergency
    executor.clear_emergency_mode()
    
    return executor


if __name__ == "__main__":
    # Run the demo if this file is executed directly
    demo_emergency_executor()
