# 🚨 Simple Tests for Emergency Response System
# Written for clarity and ease-of-understanding

import time
from uuid import uuid4

from rec.model import JobInfo
from rec.nodes.emergency_executor import create_emergency_executor
from rec.nodes.recovery_system import SimpleRecoveryManager
from rec.nodes.emergency_integration import create_emergency_system


def test_executor_behavior():
    print("🔧 Testing Emergency Executor...")

    exec = create_emergency_executor("student_exec")

    # Send a regular job
    regular = JobInfo(wasm_bin="basic.wasm")
    exec.receive_job(uuid4(), regular, is_emergency=False)

    # Send an emergency job
    urgent = JobInfo(wasm_bin="urgent.wasm")
    exec.receive_job(uuid4(), urgent, is_emergency=True)

    status = exec.get_status()
    assert "emergency" in status["queues"]
    assert "normal" in status["queues"]

    print("✅ Executor basic behavior test passed")


def test_recovery_manager_behavior():
    print("🔧 Testing Recovery Manager...")

    recovery = SimpleRecoveryManager("student_recovery")
    recovery.register_executor("execA")
    recovery.register_executor("execB")

    failed_jobs = [uuid4() for _ in range(2)]
    recovery.mark_executor_failed("execA", failed_jobs)

    stats = recovery.get_status()
    assert len(stats["executors"]["healthy"]) > 0
    assert len(stats["executors"]["failed"]) > 0

    print("✅ Recovery manager test passed")


def test_emergency_system_flow():
    print("🔧 Testing Full Emergency System Flow...")

    system = create_emergency_system("test_flow")

    # Add executors
    e1 = system.add_executor("e1")
    e2 = system.add_executor("e2")

    # Submit a normal and emergency job
    job_n = system.submit_normal_job()
    job_e = system.submit_emergency_job("fire")

    # Trigger system-wide emergency
    system.declare_emergency("fire", "high")
    status = system.status()
    assert system.coordinator.recovery.emergency_active == True

    # Clear emergency and validate
    system.clear_emergency()
    assert system.coordinator.recovery.emergency_active == False

    print("✅ Full emergency system test passed")


def test_clock_behavior():
    print("🔧 Testing Vector Clock Updates...")

    system = create_emergency_system("clock_check")
    eid = system.add_executor("clock_exec")
    executor = system.coordinator.executors[eid]

    clock_before = executor.vclock.clock.copy()
    system.submit_normal_job()
    clock_after = executor.vclock.clock

    assert clock_before != clock_after, "Clock should advance after job"

    print("✅ Vector clock update test passed")


def run_all_tests():
    print("🔍 Running All Emergency System Tests")

    try:
        test_executor_behavior()
        test_recovery_manager_behavior()
        test_emergency_system_flow()
        test_clock_behavior()
        print("\n🎉 All tests passed successfully!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")


def quick_demo():
    print("\n🚨 Quick Emergency Response System Demo 🚨")

    system = create_emergency_system("demo_showcase")
    e1 = system.add_executor("alpha_exec")
    e2 = system.add_executor("beta_exec")

    system.submit_normal_job()
    system.submit_normal_job()

    system.declare_emergency("flood", "critical")
    system.submit_emergency_job("flood")

    system.simulate_failure(e1)

    print("System overview after simulation:")
    print(system.status())

    system.clear_emergency()
    print("✅ Emergency cleared, system back to normal.")


if __name__ == "__main__":
    run_all_tests()
    print("\n" + "=" * 40)
    quick_demo()
