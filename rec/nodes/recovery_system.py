# Simple Recovery System for Task 3
# Helps executors recover from failures and coordinate during emergencies
# Written in a simple, student-friendly way

import time
from typing import Dict, List, Set
from uuid import UUID, uuid4

from rec.replication.core.vector_clock import VectorClock, EmergencyLevel
from rec.util.log import LOG


class SimpleRecoveryManager:
    """
    A simple system to help executors recover from failures.
    Keeps track of which executors are alive and helps redistribute jobs.
    """
    
    def __init__(self, manager_id: str = None):
        self.manager_id = manager_id or f"recovery_{uuid4().hex[:8]}"
        self.vector_clock = VectorClock(self.manager_id)
        
        # Track executors
        self.healthy_executors = set()    # Executors that are working fine
        self.failed_executors = set()     # Executors that have failed
        self.emergency_executors = set()  # Executors in emergency mode
        
        # Keep track of jobs that need to be reassigned
        self.orphaned_jobs = []  # Jobs from failed executors
        
        # Emergency state
        self.system_emergency_level = EmergencyLevel.LOW
        self.emergency_active = False
        
        LOG.info(f"Recovery manager {self.manager_id} started")
    
    def register_executor(self, executor_id: str):
        """
        Register a new executor with the recovery system.
        """
        self.vector_clock.tick()
        self.healthy_executors.add(executor_id)
        self.failed_executors.discard(executor_id)  # Remove from failed if it was there
        
        LOG.info(f"Executor {executor_id} registered as healthy")
    
    def mark_executor_failed(self, executor_id: str, failed_jobs: List[UUID] = None):
        """
        Mark an executor as failed and handle its jobs.
        """
        self.vector_clock.tick()
        
        if executor_id in self.healthy_executors:
            self.healthy_executors.remove(executor_id)
            self.failed_executors.add(executor_id)
            
            # Add any jobs from the failed executor to our orphaned list
            if failed_jobs:
                self.orphaned_jobs.extend(failed_jobs)
                LOG.warning(f"Executor {executor_id} failed with {len(failed_jobs)} jobs")
            else:
                LOG.warning(f"Executor {executor_id} marked as failed")
            
            # Try to reassign orphaned jobs
            self._try_reassign_jobs()
    
    def executor_heartbeat(self, executor_id: str, status: Dict):
        """
        Receive a heartbeat from an executor.
        This tells us the executor is still alive and gives us its status.
        """
        # Update our vector clock with the executor's clock
        if 'vector_clock' in status:
            self.vector_clock.update(status['vector_clock'])
        
        # Make sure the executor is marked as healthy
        if executor_id not in self.healthy_executors:
            self.register_executor(executor_id)
        
        # Check if executor is in emergency mode
        if status.get('in_emergency_mode', False):
            self.emergency_executors.add(executor_id)
        else:
            self.emergency_executors.discard(executor_id)
    
    def declare_system_emergency(self, emergency_type: str, level: str):
        """
        Declare a system-wide emergency.
        This will tell all executors to switch to emergency mode.
        """
        self.vector_clock.tick()
        self.emergency_active = True
        
        # Convert string to emergency level
        if level.lower() == "low":
            self.system_emergency_level = EmergencyLevel.LOW
        elif level.lower() == "medium":
            self.system_emergency_level = EmergencyLevel.MEDIUM
        elif level.lower() == "high":
            self.system_emergency_level = EmergencyLevel.HIGH
        elif level.lower() == "critical":
            self.system_emergency_level = EmergencyLevel.CRITICAL
        
        LOG.warning(f"SYSTEM EMERGENCY DECLARED: {emergency_type} - {level}")
        
        # In a real system, we would notify all executors here
        # For simplicity, we'll just log it
        LOG.info(f"Would notify {len(self.healthy_executors)} executors of emergency")
    
    def clear_system_emergency(self):
        """
        Clear the system emergency and return to normal operation.
        """
        self.vector_clock.tick()
        self.emergency_active = False
        self.system_emergency_level = EmergencyLevel.LOW
        self.emergency_executors.clear()
        
        LOG.info("System emergency cleared - returning to normal operation")
    
    def _try_reassign_jobs(self):
        """
        Try to reassign orphaned jobs to healthy executors.
        Simple round-robin assignment.
        """
        if not self.orphaned_jobs or not self.healthy_executors:
            return  # Nothing to assign or no healthy executors
        
        healthy_list = list(self.healthy_executors)
        
        while self.orphaned_jobs and healthy_list:
            job_id = self.orphaned_jobs.pop(0)
            # In a real system, we would actually send the job to an executor
            # For demo, we'll just log which executor would get it
            executor_id = healthy_list[len(self.orphaned_jobs) % len(healthy_list)]
            LOG.info(f"Would reassign job {job_id} to executor {executor_id}")
    
    def get_system_status(self) -> Dict:
        """
        Get overall system status.
        """
        return {
            "manager_id": self.manager_id,
            "vector_clock": self.vector_clock.to_dict(),
            "emergency_active": self.emergency_active,
            "emergency_level": self.system_emergency_level.name,
            "executors": {
                "healthy": len(self.healthy_executors),
                "failed": len(self.failed_executors),
                "in_emergency_mode": len(self.emergency_executors),
                "healthy_list": list(self.healthy_executors),
                "failed_list": list(self.failed_executors)
            },
            "orphaned_jobs": len(self.orphaned_jobs)
        }
    
    def find_best_executor_for_emergency(self, job_type: str = "general") -> str:
        """
        Simple function to find the best executor for an emergency job.
        For now, just returns any healthy executor.
        """
        if not self.healthy_executors:
            return None
        
        # Simple strategy: return the first healthy executor
        # In a real system, this could consider capabilities, load, etc.
        return list(self.healthy_executors)[0]


class SimpleCoordinator:
    """
    Coordinates between recovery manager and executors.
    Makes it easy to manage the whole system.
    """
    
    def __init__(self):
        self.recovery_manager = SimpleRecoveryManager()
        self.executors = {}  # Will store executor references if needed
        
    def add_executor(self, executor):
        """
        Add an executor to the coordination system.
        """
        executor_id = executor.executor_id
        self.executors[executor_id] = executor
        self.recovery_manager.register_executor(executor_id)
        
        # Sync vector clocks
        executor.sync_vector_clock(self.recovery_manager.vector_clock.to_dict())
        
        LOG.info(f"Executor {executor_id} added to coordination system")
    
    def simulate_executor_failure(self, executor_id: str):
        """
        Simulate an executor failure for testing.
        """
        if executor_id in self.executors:
            executor = self.executors[executor_id]
            failed_jobs = list(executor.running_jobs)  # Jobs that were running
            
            self.recovery_manager.mark_executor_failed(executor_id, failed_jobs)
            LOG.warning(f"Simulated failure of executor {executor_id}")
    
    def send_heartbeats(self):
        """
        Simulate sending heartbeats from all executors.
        """
        for executor_id, executor in self.executors.items():
            if executor_id in self.recovery_manager.healthy_executors:
                status = executor.get_status()
                self.recovery_manager.executor_heartbeat(executor_id, status)
    
    def get_full_system_status(self) -> Dict:
        """
        Get status of the entire coordinated system.
        """
        return {
            "recovery_manager": self.recovery_manager.get_system_status(),
            "executors": {exec_id: exec.get_status() 
                         for exec_id, exec in self.executors.items()}
        }


# Demo function showing the recovery system
def demo_recovery_system():
    """
    Simple demo of the recovery system working with executors.
    """
    print("=== Recovery System Demo ===")
    
    # Import here to avoid circular imports
    from rec.nodes.emergency_executor import create_emergency_executor
    
    # Create a coordinator
    coordinator = SimpleCoordinator()
    
    # Create some executors
    exec1 = create_emergency_executor("exec_1")
    exec2 = create_emergency_executor("exec_2")
    
    # Add them to the coordination system
    coordinator.add_executor(exec1)
    coordinator.add_executor(exec2)
    
    print("Initial system status:")
    print(coordinator.get_full_system_status())
    
    # Send some heartbeats
    coordinator.send_heartbeats()
    
    # Simulate an emergency
    coordinator.recovery_manager.declare_system_emergency("fire", "high")
    
    # Simulate a failure
    coordinator.simulate_executor_failure("exec_1")
    
    print("\nAfter emergency and failure:")
    print(coordinator.get_full_system_status())
    
    # Clear emergency
    coordinator.recovery_manager.clear_system_emergency()
    
    return coordinator


if __name__ == "__main__":
    # Run the demo if this file is executed directly
    demo_recovery_system()
