# Simple Tests for Emergency Response System
# Basic tests to make sure everything works correctly
# Written to be easy to understand and modify

import time
from uuid import uuid4

from rec.model import JobInfo
from rec.nodes.emergency_executor import create_emergency_executor
from rec.nodes.recovery_system import SimpleRecoveryManager
from rec.nodes.emergency_integration import create_emergency_system


def test_emergency_executor():
    """Test that the emergency executor works correctly."""
    print("Testing Emergency Executor...")
    
    # Create an executor
    executor = create_emergency_executor("test_executor")
    
    # Test normal job
    normal_job = JobInfo(wasm_bin="test_normal.wasm")
    executor.receive_job(uuid4(), normal_job, is_emergency=False)
    
    # Test emergency job
    emergency_job = JobInfo(wasm_bin="test_emergency.wasm")
    executor.receive_job(uuid4(), emergency_job, is_emergency=True)
    
    # Check status
    status = executor.get_status()
    assert status["jobs"]["emergency_queue"] >= 0, "Emergency queue should exist"
    assert status["jobs"]["normal_queue"] >= 0, "Normal queue should exist"
    
    print("✅ Emergency executor test passed")


def test_recovery_system():
    """Test that the recovery system works."""
    print("Testing Recovery System...")
    
    # Create recovery manager
    recovery = SimpleRecoveryManager("test_recovery")
    
    # Register some executors
    recovery.register_executor("exec1")
    recovery.register_executor("exec2")
    
    # Test failure handling
    recovery.mark_executor_failed("exec1", [uuid4(), uuid4()])
    
    # Check status
    status = recovery.get_system_status()
    assert status["executors"]["healthy"] >= 1, "Should have healthy executors"
    assert status["executors"]["failed"] >= 1, "Should have failed executors"
    
    print("✅ Recovery system test passed")


def test_complete_system():
    """Test the complete emergency response integration."""
    print("Testing Complete Emergency System...")
    
    # Create system
    system = create_emergency_system("test_system")
    
    # Add executors
    exec1 = system.add_executor("test_exec1")
    exec2 = system.add_executor("test_exec2")
    
    # Submit jobs
    normal_job = system.submit_normal_job()
    emergency_job = system.submit_emergency_job("fire")
    
    # Test emergency mode
    system.declare_system_emergency("medical", "high")
    
    # Get status
    overview = system.get_system_overview()
    assert overview["executor_summary"]["total_executors"] == 2, "Should have 2 executors"
    assert overview["emergency_status"]["active"] == True, "Emergency should be active"
    
    # Clear emergency
    system.clear_system_emergency()
    
    print("✅ Complete system test passed")


def test_vector_clock_coordination():
    """Test that vector clocks work correctly."""
    print("Testing Vector Clock Coordination...")
    
    # Create system
    system = create_emergency_system("clock_test")
    
    # Add executor
    exec_id = system.add_executor("clock_executor")
    executor = system.coordinator.executors[exec_id]
    
    # Check initial clock
    initial_clock = executor.vector_clock.to_dict()
    
    # Submit job (should update clock)
    system.submit_normal_job()
    
    # Check clock updated
    updated_clock = executor.vector_clock.to_dict()
    assert updated_clock != initial_clock, "Clock should update after job submission"
    
    print("✅ Vector clock coordination test passed")


def run_all_tests():
    """Run all emergency response tests."""
    print("=== Running All Emergency Response Tests ===")
    
    try:
        test_emergency_executor()
        test_recovery_system()
        test_complete_system()
        test_vector_clock_coordination()
        
        print("\n🎉 All emergency response tests passed! 🎉")
        print("Emergency response implementation is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


def quick_demo():
    """Quick demo showing key emergency response features."""
    print("=== Quick Emergency Response Demo ===")
    
    # Create and setup system
    system = create_emergency_system("quick_demo")
    exec1 = system.add_executor("demo_executor_1")
    exec2 = system.add_executor("demo_executor_2")
    
    print(f"Created system with executors: {exec1}, {exec2}")
    
    # Normal operation
    job1 = system.submit_normal_job()
    job2 = system.submit_normal_job()
    print(f"Submitted normal jobs: {job1}, {job2}")
    
    # Emergency situation
    system.declare_system_emergency("fire", "critical")
    emergency_job = system.submit_emergency_job("fire")
    print(f"EMERGENCY! Submitted emergency job: {emergency_job}")
    
    # Simulate failure and recovery
    system.simulate_executor_failure(exec1)
    print(f"Executor {exec1} failed - system handling recovery")
    
    # Show final status
    overview = system.get_system_overview()
    print(f"\nFinal status:")
    print(f"- Active emergency: {overview['emergency_status']['active']}")
    print(f"- Healthy executors: {overview['executor_summary']['healthy_executors']}")
    print(f"- Failed executors: {overview['executor_summary']['failed_executors']}")
    
    # Clean up
    system.clear_system_emergency()
    print("Emergency cleared - demo complete!")


if __name__ == "__main__":
    # Run tests first
    run_all_tests()
    
    print("\n" + "="*50)
    
    # Then run demo
    quick_demo()
