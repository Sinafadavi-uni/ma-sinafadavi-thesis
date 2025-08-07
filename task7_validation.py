# 🛡️ Task 7 Comprehensive Validation - Integration Test

import time
import random
from uuid import uuid4


def test_task7_basic_fault_detection():
    """Test basic fault detection functionality"""
    print("🧪 Testing Task 7: Basic Fault Detection")
    
    try:
        from task7_standalone_demo import SimpleTask7FaultTolerance
        
        system = SimpleTask7FaultTolerance("test_system")
        
        # Register nodes
        test_nodes = ["test_A", "test_B", "test_C"]
        for node in test_nodes:
            system.register_node(node)
        
        assert len(system.node_health) == 3, "Should have 3 registered nodes"
        assert len(system.trusted_nodes) == 3, "All nodes should start as trusted"
        
        # Send heartbeats
        for node in test_nodes:
            system.receive_heartbeat(node, {
                'status': 'healthy',
                'response_time': 0.1,
                'load': 0.5
            })
        
        health = system.perform_health_check()
        assert health['healthy_nodes'] == 3, "All nodes should be healthy"
        assert health['failed_nodes'] == 0, "No nodes should be failed"
        
        print("✅ Basic fault detection working")
        return True
        
    except Exception as e:
        print(f"❌ Basic fault detection failed: {e}")
        return False


def test_task7_byzantine_detection():
    """Test Byzantine behavior detection"""
    print("🧪 Testing Task 7: Byzantine Detection")
    
    try:
        from task7_standalone_demo import SimpleTask7FaultTolerance
        
        system = SimpleTask7FaultTolerance("byzantine_test")
        
        # Register good and bad nodes
        system.register_node("good_node")
        system.register_node("bad_node")
        
        # Good node sends valid data
        system.receive_heartbeat("good_node", {
            'status': 'healthy',
            'response_time': 0.1,
            'load': 0.5,
            'vector_clock': {'good_node': 1}
        })
        
        # Bad node sends invalid data
        system.receive_heartbeat("bad_node", {
            'status': 'healthy',
            'response_time': -1.0,  # Invalid
            'load': 2.0,  # Invalid  
            'vector_clock': {'bad_node': -5}  # Invalid
        })
        
        assert "good_node" in system.trusted_nodes, "Good node should be trusted"
        assert "bad_node" in system.suspicious_nodes, "Bad node should be suspicious"
        
        print("✅ Byzantine detection working")
        return True
        
    except Exception as e:
        print(f"❌ Byzantine detection failed: {e}")
        return False


def test_task7_emergency_protocols():
    """Test emergency protocol activation"""
    print("🧪 Testing Task 7: Emergency Protocols")
    
    try:
        from task7_standalone_demo import SimpleTask7FaultTolerance
        
        system = SimpleTask7FaultTolerance("emergency_test")
        
        # Register minimal nodes
        system.register_node("node1")
        
        # Activate emergency (less than 2 healthy nodes)
        health = system.perform_health_check()
        
        # Should activate emergency with only 1 node
        assert system.emergency_active, "Emergency should be active with only 1 node"
        
        # Add more nodes to stabilize
        system.register_node("node2")
        system.register_node("node3")
        
        # Send heartbeats
        for node in ["node1", "node2", "node3"]:
            system.receive_heartbeat(node, {
                'status': 'healthy',
                'response_time': 0.1,
                'load': 0.3
            })
        
        health = system.perform_health_check()
        
        # Should deactivate emergency with 3 healthy nodes
        assert not system.emergency_active, "Emergency should deactivate with 3 healthy nodes"
        
        print("✅ Emergency protocols working")
        return True
        
    except Exception as e:
        print(f"❌ Emergency protocols failed: {e}")
        return False


def test_task7_critical_job_handling():
    """Test critical job handling"""
    print("🧪 Testing Task 7: Critical Job Handling")
    
    try:
        from task7_standalone_demo import SimpleTask7FaultTolerance
        
        system = SimpleTask7FaultTolerance("job_test")
        
        # Register nodes
        for i in range(3):
            system.register_node(f"worker_{i}")
        
        # Submit critical jobs
        job_ids = ["critical_1", "critical_2", "emergency_3"]
        for job_id in job_ids:
            system.submit_critical_job(job_id)
        
        assert len(system.critical_jobs) == 3, "Should have 3 critical jobs"
        
        status = system.get_status()
        assert status['critical_jobs'] == 3, "Status should show 3 critical jobs"
        
        print("✅ Critical job handling working")
        return True
        
    except Exception as e:
        print(f"❌ Critical job handling failed: {e}")
        return False


def test_task7_integration_with_existing():
    """Test integration with existing vector clock system"""
    print("🧪 Testing Task 7: Integration with Existing System")
    
    try:
        from task7_standalone_demo import SimpleTask7FaultTolerance, SimpleVectorClock
        
        # Test that vector clock integration works
        system = SimpleTask7FaultTolerance("integration_test")
        
        # Check vector clock functionality
        initial_clock = system.clock.clock.copy()
        system.register_node("test_node")
        
        # Clock should have advanced
        assert system.clock.clock[system.system_id] > initial_clock[system.system_id], "Vector clock should advance"
        
        # Test heartbeat with vector clock
        system.receive_heartbeat("test_node", {
            'status': 'healthy',
            'response_time': 0.1,
            'vector_clock': {'test_node': 5}
        })
        
        print("✅ Integration with existing system working")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False


def test_task7_comprehensive_scenario():
    """Test comprehensive fault tolerance scenario"""
    print("🧪 Testing Task 7: Comprehensive Scenario")
    
    try:
        from task7_standalone_demo import SimpleTask7FaultTolerance
        
        system = SimpleTask7FaultTolerance("comprehensive_test")
        
        # Phase 1: Normal operation
        nodes = ["alpha", "beta", "gamma", "delta", "epsilon"]
        for node in nodes:
            system.register_node(node)
        
        # Phase 2: Submit critical jobs
        for i in range(3):
            system.submit_critical_job(f"mission_critical_{i}")
        
        # Phase 3: Normal heartbeats
        for round_num in range(2):
            for node in nodes:
                system.receive_heartbeat(node, {
                    'status': 'healthy',
                    'response_time': random.uniform(0.05, 0.2),
                    'load': random.uniform(0.1, 0.8),
                    'vector_clock': {node: round_num + 1}
                })
            system.perform_health_check()
        
        # Phase 4: Byzantine attack
        system.receive_heartbeat("delta", {
            'status': 'healthy',
            'response_time': -1,  # Attack!
            'load': 5.0,  # Attack!
        })
        
        # Phase 5: Node failure (epsilon stops responding)
        # Skip epsilon in next round
        for node in ["alpha", "beta", "gamma"]:  # delta is Byzantine, epsilon is silent
            system.receive_heartbeat(node, {
                'status': 'healthy',
                'response_time': random.uniform(0.05, 0.2),
                'load': random.uniform(0.1, 0.8),
                'vector_clock': {node: 10}
            })
        
        # Phase 6: Health check and validation
        final_health = system.perform_health_check()
        final_status = system.get_status()
        
        # Validate results
        assert final_status['trusted_nodes'] >= 3, "Should have at least 3 trusted nodes"
        assert final_status['suspicious_nodes'] >= 1, "Should detect Byzantine node"
        assert final_status['critical_jobs'] == 3, "Should preserve critical jobs"
        
        print("✅ Comprehensive scenario working")
        return True
        
    except Exception as e:
        print(f"❌ Comprehensive scenario failed: {e}")
        return False


def run_task7_validation():
    """Run complete Task 7 validation"""
    print("🛡️ TASK 7 COMPREHENSIVE VALIDATION")
    print("=" * 45)
    
    tests = [
        test_task7_basic_fault_detection,
        test_task7_byzantine_detection,
        test_task7_emergency_protocols,
        test_task7_critical_job_handling,
        test_task7_integration_with_existing,
        test_task7_comprehensive_scenario
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            print()  # Add spacing
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
            print()
    
    print("📊 TASK 7 VALIDATION RESULTS:")
    print(f"   Passed: {passed}/{total}")
    print(f"   Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL TASK 7 TESTS PASSED!")
        print("\n✅ TASK 7 IMPLEMENTATION COMPLETE:")
        print("   • Advanced fault detection ✅")
        print("   • Byzantine fault tolerance ✅")
        print("   • Emergency protocols ✅")
        print("   • Critical job protection ✅")
        print("   • System integration ✅")
        print("   • Comprehensive validation ✅")
        print("\n🚀 Ready for Task 8: Academic Validation & Benchmarking")
    else:
        print(f"\n⚠️  {total - passed} tests failed - Task 7 needs attention")
    
    return passed == total


if __name__ == "__main__":
    success = run_task7_validation()
    exit(0 if success else 1)
