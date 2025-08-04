# Simple Emergency Response Integration
# Brings together emergency executor, recovery system, and broker
# Written to be easy to understand and use

from typing import Dict, List
from uuid import UUID, uuid4

from rec.model import JobInfo
from rec.nodes.emergency_executor import SimpleEmergencyExecutor, create_emergency_executor
from rec.nodes.recovery_system import SimpleRecoveryManager, SimpleCoordinator
from rec.replication.core.vector_clock import VectorClock, create_emergency
from rec.util.log import LOG


class SimpleEmergencySystem:
    """
    Complete emergency response system that integrates:
    - Emergency-aware executors
    - Recovery management
    - Vector clock coordination
    
    This makes it easy to use all emergency response features together.
    """
    
    def __init__(self, system_name: str = "emergency_system"):
        self.system_name = system_name
        self.coordinator = SimpleCoordinator()
        self.system_clock = VectorClock(system_name)
        
        # Track different types of jobs
        self.emergency_job_count = 0
        self.normal_job_count = 0
        
        LOG.info(f"Emergency response system '{system_name}' initialized")
    
    def add_executor(self, executor_id: str = None) -> str:
        """
        Add a new emergency-capable executor to the system.
        Returns the executor ID.
        """
        executor = create_emergency_executor(executor_id)
        self.coordinator.add_executor(executor)
        
        # Sync system clock
        self.system_clock.tick()
        executor.sync_vector_clock(self.system_clock.to_dict())
        
        LOG.info(f"Added executor {executor.executor_id} to emergency response system")
        return executor.executor_id
    
    def submit_normal_job(self, job_info: JobInfo = None, target_executor: str = None) -> UUID:
        """
        Submit a normal (non-emergency) job to the system.
        """
        job_id = uuid4()
        # Create a simple default job if none provided
        if job_info is None:
            job_info = JobInfo(wasm_bin="default_task.wasm")
        
        self.system_clock.tick()
        self.normal_job_count += 1
        
        # Find an executor to handle the job
        if target_executor and target_executor in self.coordinator.executors:
            executor = self.coordinator.executors[target_executor]
        else:
            # Pick any healthy executor
            healthy_executors = list(self.coordinator.recovery_manager.healthy_executors)
            if not healthy_executors:
                LOG.error("No healthy executors available for normal job")
                return None
            
            executor_id = healthy_executors[0]
            executor = self.coordinator.executors[executor_id]
        
        # Submit the job
        executor.receive_job(job_id, job_info, is_emergency=False)
        LOG.info(f"Normal job {job_id} submitted to {executor.executor_id}")
        
        return job_id
    
    def submit_emergency_job(self, emergency_type: str, job_info: JobInfo = None) -> UUID:
        """
        Submit an emergency job to the system.
        Emergency jobs get priority treatment.
        """
        job_id = uuid4()
        # Create a simple default emergency job if none provided
        if job_info is None:
            job_info = JobInfo(wasm_bin=f"emergency_{emergency_type}.wasm")
        
        self.system_clock.tick()
        self.emergency_job_count += 1
        
        # Find the best executor for this emergency
        best_executor_id = self.coordinator.recovery_manager.find_best_executor_for_emergency(emergency_type)
        
        if not best_executor_id:
            LOG.error("No healthy executors available for emergency job")
            return None
        
        executor = self.coordinator.executors[best_executor_id]
        
        # Submit the emergency job
        executor.receive_job(job_id, job_info, is_emergency=True)
        LOG.warning(f"EMERGENCY job {job_id} ({emergency_type}) submitted to {best_executor_id}")
        
        return job_id
    
    def declare_system_emergency(self, emergency_type: str = "general", level: str = "medium"):
        """
        Declare a system-wide emergency.
        This affects how all executors handle jobs.
        """
        self.system_clock.tick()
        
        # Tell the recovery manager
        self.coordinator.recovery_manager.declare_system_emergency(emergency_type, level)
        
        # Tell all executors to enter emergency mode
        for executor_id, executor in self.coordinator.executors.items():
            if executor_id in self.coordinator.recovery_manager.healthy_executors:
                executor.set_emergency_mode(emergency_type, level)
        
        LOG.warning(f"SYSTEM-WIDE EMERGENCY: {emergency_type} ({level})")
    
    def clear_system_emergency(self):
        """
        Clear the system emergency and return to normal operation.
        """
        self.system_clock.tick()
        
        # Clear recovery manager emergency
        self.coordinator.recovery_manager.clear_system_emergency()
        
        # Tell all executors to exit emergency mode
        for executor_id, executor in self.coordinator.executors.items():
            if executor_id in self.coordinator.recovery_manager.healthy_executors:
                executor.clear_emergency_mode()
        
        LOG.info("System emergency cleared - all executors returning to normal")
    
    def simulate_executor_failure(self, executor_id: str):
        """
        Simulate an executor failure for testing recovery.
        """
        self.system_clock.tick()
        self.coordinator.simulate_executor_failure(executor_id)
        LOG.warning(f"Simulated failure of executor {executor_id}")
    
    def get_system_overview(self) -> Dict:
        """
        Get a simple overview of the entire emergency response system.
        """
        coordinator_status = self.coordinator.get_full_system_status()
        
        return {
            "system_name": self.system_name,
            "system_vector_clock": self.system_clock.to_dict(),
            "job_counts": {
                "emergency_jobs_submitted": self.emergency_job_count,
                "normal_jobs_submitted": self.normal_job_count
            },
            "emergency_status": {
                "active": coordinator_status["recovery_manager"]["emergency_active"],
                "level": coordinator_status["recovery_manager"]["emergency_level"]
            },
            "executor_summary": {
                "total_executors": len(self.coordinator.executors),
                "healthy_executors": coordinator_status["recovery_manager"]["executors"]["healthy"],
                "failed_executors": coordinator_status["recovery_manager"]["executors"]["failed"],
                "emergency_mode_executors": coordinator_status["recovery_manager"]["executors"]["in_emergency_mode"]
            },
            "detailed_status": coordinator_status
        }
    
    def run_heartbeat_cycle(self):
        """
        Run one cycle of heartbeats to keep the system updated.
        """
        self.coordinator.send_heartbeats()
        LOG.debug("Heartbeat cycle completed")


# Easy-to-use demo function for students
def demo_complete_emergency():
    """
    Complete demonstration of emergency response functionality.
    Shows emergency handling, recovery, and coordination.
    """
    print("=== Complete Emergency Response Demo ===")
    
    # Create the emergency response system
    system = SimpleEmergencySystem("demo_system")
    
    # Add some executors
    exec1_id = system.add_executor("medical_executor")
    exec2_id = system.add_executor("fire_executor") 
    exec3_id = system.add_executor("general_executor")
    
    print(f"\nAdded 3 executors: {exec1_id}, {exec2_id}, {exec3_id}")
    
    # Submit some normal jobs
    job1 = system.submit_normal_job()
    job2 = system.submit_normal_job()
    
    print(f"Submitted normal jobs: {job1}, {job2}")
    
    # Check initial status
    print("\nInitial system status:")
    overview = system.get_system_overview()
    print(f"- Healthy executors: {overview['executor_summary']['healthy_executors']}")
    print(f"- Jobs submitted: {overview['job_counts']}")
    
    # Declare an emergency
    system.declare_system_emergency("fire", "high")
    
    # Submit emergency jobs
    emergency_job1 = system.submit_emergency_job("fire")
    emergency_job2 = system.submit_emergency_job("medical")
    
    print(f"\nSubmitted emergency jobs: {emergency_job1}, {emergency_job2}")
    
    # Run heartbeats
    system.run_heartbeat_cycle()
    
    # Simulate a failure
    system.simulate_executor_failure(exec2_id)
    
    print(f"\nSimulated failure of {exec2_id}")
    
    # Check final status
    print("\nFinal system status:")
    overview = system.get_system_overview()
    print(f"- Healthy executors: {overview['executor_summary']['healthy_executors']}")
    print(f"- Failed executors: {overview['executor_summary']['failed_executors']}")
    print(f"- Emergency active: {overview['emergency_status']['active']}")
    print(f"- Emergency level: {overview['emergency_status']['level']}")
    print(f"- Total jobs submitted: {overview['job_counts']}")
    
    # Clear emergency
    system.clear_system_emergency()
    print("\nEmergency cleared - system returning to normal")
    
    return system


# Simple helper function for students to get started
def create_emergency_system(name: str = "my_emergency_system") -> SimpleEmergencySystem:
    """
    Create a new emergency response system ready to use.
    This is the main entry point for students.
    """
    return SimpleEmergencySystem(name)


if __name__ == "__main__":
    # Run the complete demo
    demo_complete_emergency()
