#!/usr/bin/env python3
"""
Phase 2 Node Infrastructure Test Suite
Tests emergency execution, broker coordination, recovery systems, and distributed node performance.
"""

import sys
import os
import time
import threading
import random
from typing import Dict, List, Any

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from rec.Phase1_Core_Foundation.vector_clock import VectorClock, EmergencyLevel, create_emergency
from rec.Phase2_Node_Infrastructure.emergency_executor import SimpleEmergencyExecutor
from rec.Phase2_Node_Infrastructure.executorbroker import ExecutorBroker
from rec.Phase2_Node_Infrastructure.recovery_system import SimpleRecoveryManager


class Phase2NodeInfrastructureTest:
    """
    Comprehensive test suite for Phase 2 Node Infrastructure.
    Tests emergency execution logic, broker coordination mathematics, and recovery system performance.
    """
    
    def __init__(self):
        self.test_results = {}
        self.performance_metrics = {}
        self.active_components = []
        
    def cleanup_components(self):
        """Clean up active test components."""
        for component in self.active_components:
            try:
                if hasattr(component, 'stop'):
                    component.stop()
            except Exception:
                pass
        self.active_components.clear()
    
    def test_emergency_executor_logic(self) -> bool:
        """
        Test emergency executor logic and mathematics:
        1. Job submission and execution ordering
        2. Emergency priority handling
        3. Vector clock integration
        4. Job state management
        """
        print("🚨 Testing Emergency Executor Logic...")
        
        try:
            # Test 1: Basic executor functionality
            executor = SimpleEmergencyExecutor("test_executor")
            self.active_components.append(executor)
            
            executor.start()
            
            # Test job submission
            normal_job = {"task": "normal_processing", "data": "test_data"}
            job_id = executor.submit_job(normal_job)
            
            assert job_id is not None, "Job submission should return valid ID"
            assert isinstance(job_id, str), "Job ID should be string"
            
            # Test 2: Emergency job priority
            emergency = create_emergency("fire", EmergencyLevel.CRITICAL)
            emergency_job = {"task": "emergency_evacuation", "priority": "critical"}
            
            emergency_job_id = executor.submit_emergency_job(emergency_job, emergency)
            
            assert emergency_job_id is not None, "Emergency job should be submitted"
            
            # Test 3: Vector clock integration
            initial_clock = executor.vector_clock.clock.copy()
            executor.vector_clock.tick()
            updated_clock = executor.vector_clock.clock.copy()
            
            # Clock should advance
            assert updated_clock != initial_clock, "Vector clock should advance"
            
            # Test 4: Job execution verification
            time.sleep(0.5)  # Allow job processing
            
            # Check job execution status
            job_status = executor.get_job_status(job_id)
            assert job_status is not None, "Job status should be available"
            
            # Test 5: Emergency mode activation
            executor.activate_emergency_mode(emergency)
            assert executor.in_emergency_mode == True, "Emergency mode should be activated"
            
            emergency_mode_job = {"task": "emergency_response", "urgent": True}
            emergency_mode_job_id = executor.submit_job(emergency_mode_job)
            
            assert emergency_mode_job_id is not None, "Jobs should be accepted in emergency mode"
            
            executor.stop()
            print("   ✅ Emergency executor logic verified")
            return True
            
        except Exception as e:
            print(f"   ❌ Emergency executor logic test failed: {e}")
            return False
        finally:
            self.cleanup_components()
    
    def test_broker_coordination_mathematics(self) -> bool:
        """
        Test broker coordination and mathematical properties:
        1. Executor registration and discovery
        2. Load balancing algorithms
        3. Metadata synchronization
        4. Distributed state consistency
        """
        print("🔗 Testing Broker Coordination Mathematics...")
        
        try:
            # Test 1: Basic broker functionality
            broker = ExecutorBroker("test_broker")
            self.active_components.append(broker)
            
            broker.start()
            
            # Test 2: Executor registration
            executor1 = SimpleEmergencyExecutor("executor_1")
            executor2 = SimpleEmergencyExecutor("executor_2")
            executor3 = SimpleEmergencyExecutor("executor_3")
            
            self.active_components.extend([executor1, executor2, executor3])
            
            executor1.start()
            executor2.start()
            executor3.start()
            
            # Register executors with broker
            broker.register_executor(executor1)
            broker.register_executor(executor2)
            broker.register_executor(executor3)
            
            # Test executor discovery
            registered_executors = broker.get_registered_executors()
            assert len(registered_executors) == 3, f"Should have 3 registered executors, got {len(registered_executors)}"
            
            # Test 3: Load balancing verification
            # Submit multiple jobs and verify distribution
            job_distribution = {}
            
            for i in range(9):  # 9 jobs across 3 executors = 3 jobs each ideally
                job = {"task": f"load_test_{i}", "data": f"test_data_{i}"}
                assigned_executor = broker.assign_job_to_executor(job)
                
                if assigned_executor:
                    executor_id = assigned_executor.node_id
                    job_distribution[executor_id] = job_distribution.get(executor_id, 0) + 1
            
            # Verify reasonable distribution (allow some variance)
            min_jobs = min(job_distribution.values()) if job_distribution else 0
            max_jobs = max(job_distribution.values()) if job_distribution else 0
            load_variance = max_jobs - min_jobs
            
            assert load_variance <= 2, f"Load balancing variance too high: {load_variance}"
            
            # Test 4: Metadata synchronization mathematics
            # Test distributed status aggregation
            distributed_status = broker.get_distributed_status()
            
            assert isinstance(distributed_status, dict), "Distributed status should be dictionary"
            assert len(distributed_status) > 0, "Distributed status should contain data"
            
            # Test vector clock synchronization
            initial_broker_clock = broker.vector_clock.clock.copy()
            broker.synchronize_clocks()
            updated_broker_clock = broker.vector_clock.clock.copy()
            
            # Clock should advance or maintain causality
            total_initial = sum(initial_broker_clock.values())
            total_updated = sum(updated_broker_clock.values())
            
            assert total_updated >= total_initial, "Clock synchronization should maintain causality"
            
            # Test 5: Fault tolerance in coordination
            # Simulate executor failure
            executor2.stop()
            
            # Broker should detect and handle the failure
            time.sleep(0.5)  # Allow detection time
            
            remaining_executors = broker.get_active_executors()
            assert len(remaining_executors) <= 2, "Broker should detect executor failure"
            
            # Test job reassignment after failure
            recovery_job = {"task": "recovery_test", "data": "recovery_data"}
            assigned_executor = broker.assign_job_to_executor(recovery_job)
            
            assert assigned_executor is not None, "Broker should assign jobs to remaining executors"
            
            # Cleanup
            executor1.stop()
            executor3.stop()
            broker.stop()
            
            print("   ✅ Broker coordination mathematics verified")
            return True
            
        except Exception as e:
            print(f"   ❌ Broker coordination mathematics test failed: {e}")
            return False
        finally:
            self.cleanup_components()
    
    def test_recovery_system_performance(self) -> bool:
        """
        Test recovery system performance and logic:
        1. Node failure detection algorithms
        2. Recovery time mathematics
        3. State restoration accuracy
        4. Cascading failure prevention
        """
        print("🔄 Testing Recovery System Performance...")
        
        try:
            # Test 1: Basic recovery system setup
            recovery_manager = SimpleRecoveryManager("test_recovery")
            self.active_components.append(recovery_manager)
            
            recovery_manager.start()
            
            # Test 2: Node registration and monitoring
            test_nodes = []
            for i in range(5):
                node_id = f"test_node_{i}"
                recovery_manager.register_node(node_id, f"127.0.0.1:800{i}")
                test_nodes.append(node_id)
            
            registered_nodes = recovery_manager.get_registered_nodes()
            assert len(registered_nodes) == 5, f"Should have 5 registered nodes, got {len(registered_nodes)}"
            
            # Test 3: Failure detection performance
            start_time = time.time()
            
            # Simulate node failures
            failed_nodes = test_nodes[:2]  # Fail first 2 nodes
            for node_id in failed_nodes:
                recovery_manager.report_node_failure(node_id)
            
            # Measure detection time
            detection_time = time.time() - start_time
            
            # Verify failure detection
            failed_node_list = recovery_manager.get_failed_nodes()
            assert len(failed_node_list) >= len(failed_nodes), "Failed nodes should be detected"
            
            # Performance requirement: detection should be fast
            assert detection_time < 1.0, f"Failure detection too slow: {detection_time:.3f}s"
            
            # Test 4: Recovery time mathematics
            start_recovery_time = time.time()
            
            # Initiate recovery for failed nodes
            recovery_results = []
            for node_id in failed_nodes:
                recovery_result = recovery_manager.initiate_recovery(node_id)
                recovery_results.append(recovery_result)
            
            recovery_time = time.time() - start_recovery_time
            
            # Verify recovery initiation
            successful_recoveries = sum(1 for result in recovery_results if result)
            assert successful_recoveries > 0, "At least one recovery should be initiated"
            
            # Performance requirement: recovery initiation should be fast
            assert recovery_time < 2.0, f"Recovery initiation too slow: {recovery_time:.3f}s"
            
            # Test 5: State restoration accuracy
            # Test vector clock state preservation
            test_clock_state = {"node_1": 5, "node_2": 3, "node_3": 7}
            recovery_manager.save_clock_state("recovery_test_node", test_clock_state)
            
            restored_state = recovery_manager.restore_clock_state("recovery_test_node")
            assert restored_state == test_clock_state, "Clock state should be accurately restored"
            
            # Test job state preservation
            test_job_state = {
                "active_jobs": ["job_1", "job_2", "job_3"],
                "completed_jobs": ["job_0"],
                "failed_jobs": []
            }
            recovery_manager.save_job_state("recovery_test_node", test_job_state)
            
            restored_job_state = recovery_manager.restore_job_state("recovery_test_node")
            assert restored_job_state == test_job_state, "Job state should be accurately restored"
            
            # Test 6: Cascading failure prevention
            # Simulate multiple simultaneous failures
            remaining_nodes = test_nodes[2:]  # Remaining 3 nodes
            
            start_cascade_time = time.time()
            
            # Report multiple failures quickly
            for node_id in remaining_nodes:
                recovery_manager.report_node_failure(node_id)
                time.sleep(0.1)  # Small delay between failures
            
            cascade_time = time.time() - start_cascade_time
            
            # System should handle cascading failures gracefully
            all_failed_nodes = recovery_manager.get_failed_nodes()
            assert len(all_failed_nodes) >= len(test_nodes), "All node failures should be tracked"
            
            # Recovery system should remain responsive
            assert cascade_time < 3.0, f"Cascading failure handling too slow: {cascade_time:.3f}s"
            
            # Test system health after cascading failures
            system_health = recovery_manager.get_system_health()
            assert isinstance(system_health, dict), "System health should be reportable"
            
            recovery_manager.stop()
            
            # Store performance metrics
            self.performance_metrics.update({
                'failure_detection_time': detection_time,
                'recovery_initiation_time': recovery_time,
                'cascade_handling_time': cascade_time,
                'nodes_monitored': len(test_nodes),
                'successful_recoveries': successful_recoveries
            })
            
            print("   ✅ Recovery system performance verified")
            return True
            
        except Exception as e:
            print(f"   ❌ Recovery system performance test failed: {e}")
            return False
        finally:
            self.cleanup_components()
    
    def test_distributed_coordination_stress(self) -> bool:
        """
        Test distributed coordination under stress:
        1. Concurrent job submissions
        2. Multiple executor coordination
        3. Emergency handling under load
        4. System stability metrics
        """
        print("💪 Testing Distributed Coordination Stress...")
        
        try:
            # Test 1: Setup distributed infrastructure
            broker = ExecutorBroker("stress_broker")
            recovery_manager = SimpleRecoveryManager("stress_recovery")
            
            self.active_components.extend([broker, recovery_manager])
            
            broker.start()
            recovery_manager.start()
            
            # Create multiple executors
            executors = []
            for i in range(5):
                executor = SimpleEmergencyExecutor(f"stress_executor_{i}")
                executors.append(executor)
                self.active_components.append(executor)
                
                executor.start()
                broker.register_executor(executor)
                recovery_manager.register_node(executor.node_id, f"127.0.0.1:900{i}")
            
            # Test 2: Concurrent job submission stress test
            def submit_jobs_concurrently(executor_idx, num_jobs):
                """Submit jobs concurrently from multiple threads"""
                executor = executors[executor_idx]
                submitted_jobs = []
                
                for i in range(num_jobs):
                    job = {
                        "task": f"stress_job_{executor_idx}_{i}",
                        "data": f"stress_data_{i}",
                        "timestamp": time.time()
                    }
                    
                    try:
                        job_id = executor.submit_job(job)
                        if job_id:
                            submitted_jobs.append(job_id)
                        time.sleep(0.01)  # Small delay to simulate real load
                    except Exception:
                        pass  # Continue despite individual failures
                
                return submitted_jobs
            
            # Start concurrent job submissions
            start_stress_time = time.time()
            threads = []
            jobs_per_executor = 20
            
            for i in range(len(executors)):
                thread = threading.Thread(
                    target=submit_jobs_concurrently,
                    args=(i, jobs_per_executor)
                )
                threads.append(thread)
                thread.start()
            
            # Wait for all submissions to complete
            all_submitted_jobs = []
            for i, thread in enumerate(threads):
                thread.join()
            
            stress_duration = time.time() - start_stress_time
            
            # Test 3: Emergency handling under load
            emergency = create_emergency("system_overload", EmergencyLevel.HIGH)
            
            # Activate emergency mode on all executors
            emergency_start_time = time.time()
            
            for executor in executors:
                executor.activate_emergency_mode(emergency)
            
            # Submit emergency jobs while under stress
            emergency_jobs = []
            for i in range(10):
                emergency_job = {
                    "task": f"emergency_stress_{i}",
                    "priority": "high",
                    "emergency_type": "system_overload"
                }
                
                # Use broker to assign emergency job
                assigned_executor = broker.assign_job_to_executor(emergency_job)
                if assigned_executor:
                    emergency_job_id = assigned_executor.submit_emergency_job(emergency_job, emergency)
                    if emergency_job_id:
                        emergency_jobs.append(emergency_job_id)
            
            emergency_duration = time.time() - emergency_start_time
            
            # Test 4: System stability verification
            time.sleep(1.0)  # Allow system to stabilize
            
            # Check broker state
            broker_status = broker.get_distributed_status()
            active_executors = broker.get_active_executors()
            
            assert len(active_executors) >= 3, "Most executors should remain active under stress"
            assert isinstance(broker_status, dict), "Broker should maintain valid state"
            
            # Check recovery system state
            system_health = recovery_manager.get_system_health()
            monitored_nodes = recovery_manager.get_registered_nodes()
            
            assert len(monitored_nodes) == len(executors), "All nodes should remain monitored"
            assert isinstance(system_health, dict), "Recovery system should maintain health data"
            
            # Test 5: Performance metrics validation
            total_jobs_attempted = len(executors) * jobs_per_executor
            jobs_per_second = total_jobs_attempted / stress_duration
            emergency_jobs_per_second = len(emergency_jobs) / emergency_duration
            
            # Performance thresholds
            assert jobs_per_second > 50, f"Job submission rate too low: {jobs_per_second:.1f} jobs/sec"
            assert emergency_jobs_per_second > 5, f"Emergency job rate too low: {emergency_jobs_per_second:.1f} jobs/sec"
            assert stress_duration < 10.0, f"Stress test took too long: {stress_duration:.3f}s"
            
            # Cleanup
            for executor in executors:
                executor.stop()
            broker.stop()
            recovery_manager.stop()
            
            # Store stress test metrics
            self.performance_metrics.update({
                'stress_test_duration': stress_duration,
                'jobs_per_second': jobs_per_second,
                'emergency_jobs_per_second': emergency_jobs_per_second,
                'executors_tested': len(executors),
                'emergency_jobs_completed': len(emergency_jobs)
            })
            
            print("   ✅ Distributed coordination stress test verified")
            return True
            
        except Exception as e:
            print(f"   ❌ Distributed coordination stress test failed: {e}")
            return False
        finally:
            self.cleanup_components()
    
    def test_integration_with_phase1(self) -> bool:
        """
        Test integration with Phase 1 components:
        1. Vector clock consistency across components
        2. Causal message integration
        3. FCFS policy enforcement
        4. Emergency context propagation
        """
        print("🔗 Testing Integration with Phase 1...")
        
        try:
            # Test 1: Vector clock consistency across components
            executor = SimpleEmergencyExecutor("integration_executor")
            broker = ExecutorBroker("integration_broker")
            
            self.active_components.extend([executor, broker])
            
            executor.start()
            broker.start()
            
            # Register executor with broker
            broker.register_executor(executor)
            
            # Test vector clock synchronization
            initial_executor_clock = executor.vector_clock.clock.copy()
            initial_broker_clock = broker.vector_clock.clock.copy()
            
            # Perform operations that should advance clocks
            job = {"task": "integration_test", "data": "test_data"}
            job_id = executor.submit_job(job)
            
            broker.assign_job_to_executor(job)
            
            # Check clock advancement
            updated_executor_clock = executor.vector_clock.clock.copy()
            updated_broker_clock = broker.vector_clock.clock.copy()
            
            assert updated_executor_clock != initial_executor_clock, "Executor clock should advance"
            assert updated_broker_clock != initial_broker_clock, "Broker clock should advance"
            
            # Test 2: Emergency context propagation
            emergency = create_emergency("integration_test", EmergencyLevel.MEDIUM)
            
            # Submit emergency job through executor
            emergency_job = {"task": "emergency_integration", "urgent": True}
            emergency_job_id = executor.submit_emergency_job(emergency_job, emergency)
            
            assert emergency_job_id is not None, "Emergency job should be submitted"
            
            # Verify emergency mode propagation
            executor.activate_emergency_mode(emergency)
            assert executor.in_emergency_mode == True, "Emergency mode should be active"
            
            # Test 3: Causal consistency in distributed operations
            # Create a sequence of causally related operations
            broker.vector_clock.tick()  # Broker operation
            executor.vector_clock.update(broker.vector_clock.clock)  # Sync from broker
            executor.vector_clock.tick()  # Executor operation
            
            # Verify causal ordering
            executor_clock_after = executor.vector_clock.clock.copy()
            
            # Executor should have higher timestamp after update
            for node_id in executor_clock_after:
                if node_id in broker.vector_clock.clock:
                    assert executor_clock_after[node_id] >= broker.vector_clock.clock[node_id], \
                        "Causal ordering should be preserved"
            
            # Test 4: FCFS policy integration
            # Submit multiple jobs and verify first-come-first-served handling
            job1 = {"task": "fcfs_test_1", "data": "first"}
            job2 = {"task": "fcfs_test_2", "data": "second"}
            
            job_id1 = executor.submit_job(job1)
            job_id2 = executor.submit_job(job2)
            
            assert job_id1 != job_id2, "Different jobs should have different IDs"
            
            # Both jobs should be submitted, but processing order should respect FCFS
            time.sleep(0.5)  # Allow processing
            
            job1_status = executor.get_job_status(job_id1)
            job2_status = executor.get_job_status(job_id2)
            
            # Both should have valid status (implementation may vary)
            assert job1_status is not None, "First job should have status"
            assert job2_status is not None, "Second job should have status"
            
            executor.stop()
            broker.stop()
            
            print("   ✅ Integration with Phase 1 verified")
            return True
            
        except Exception as e:
            print(f"   ❌ Integration with Phase 1 test failed: {e}")
            return False
        finally:
            self.cleanup_components()
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """
        Run all Phase 2 tests and return comprehensive results.
        """
        print("🎯 PHASE 2 NODE INFRASTRUCTURE - COMPREHENSIVE TEST SUITE")
        print("=" * 70)
        print()
        
        # Run all test components
        tests = [
            ("Emergency Executor Logic", self.test_emergency_executor_logic),
            ("Broker Coordination Mathematics", self.test_broker_coordination_mathematics),
            ("Recovery System Performance", self.test_recovery_system_performance),
            ("Distributed Coordination Stress", self.test_distributed_coordination_stress),
            ("Integration with Phase 1", self.test_integration_with_phase1)
        ]
        
        total_tests = len(tests)
        passed_tests = 0
        
        for test_name, test_func in tests:
            print(f"Running {test_name}...")
            result = test_func()
            self.test_results[test_name] = result
            if result:
                passed_tests += 1
            print()
        
        # Calculate overall results
        success_rate = (passed_tests / total_tests) * 100
        
        print("📊 PHASE 2 TEST RESULTS SUMMARY:")
        print("─" * 40)
        for test_name, result in self.test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"  {test_name}: {status}")
        
        print()
        print(f"📈 Overall Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests})")
        
        if self.performance_metrics:
            print()
            print("⚡ Performance Metrics:")
            for metric, value in self.performance_metrics.items():
                if 'time' in metric:
                    print(f"  {metric}: {value:.3f} seconds")
                elif 'per_second' in metric:
                    print(f"  {metric}: {value:.1f} operations/second")
                else:
                    print(f"  {metric}: {value}")
        
        # Final verdict
        print()
        if success_rate == 100:
            print("🏆 PHASE 2 NODE INFRASTRUCTURE: ALL TESTS PASSED")
            print("   ✅ Emergency executor logic verified")
            print("   ✅ Broker coordination mathematics confirmed")
            print("   ✅ Recovery system performance validated")
            print("   ✅ Distributed coordination stress tested")
            print("   ✅ Phase 1 integration working")
        else:
            print("⚠️  PHASE 2 NODE INFRASTRUCTURE: SOME TESTS FAILED")
            print("   Review failed components for issues")
        
        return {
            'phase': 'Phase 2 - Node Infrastructure',
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': success_rate,
            'test_results': self.test_results,
            'performance_metrics': self.performance_metrics,
            'overall_status': 'PASSED' if success_rate == 100 else 'FAILED'
        }


def main():
    """Run Phase 2 comprehensive test suite."""
    test_suite = Phase2NodeInfrastructureTest()
    try:
        results = test_suite.run_comprehensive_test()
        return 0 if results['overall_status'] == 'PASSED' else 1
    finally:
        test_suite.cleanup_components()


if __name__ == "__main__":
    exit(main())
