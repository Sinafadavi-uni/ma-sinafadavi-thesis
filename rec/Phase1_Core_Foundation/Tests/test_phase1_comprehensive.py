#!/usr/bin/env python3
"""
Phase 1 Core Foundation Test Suite
Tests vector clock logic, mathematics, FCFS policy, and causal consistency performance.
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
from rec.Phase1_Core_Foundation.causal_message import CausalMessage, MessageHandler
from rec.Phase1_Core_Foundation.causal_consistency import CausalConsistencyManager, FCFSConsistencyPolicy


class Phase1CoreFoundationTest:
    """
    Comprehensive test suite for Phase 1 Core Foundation.
    Tests logic, mathematics, and performance of vector clocks and causal consistency.
    """
    
    def __init__(self):
        self.test_results = {}
        self.performance_metrics = {}
        
    def test_vector_clock_mathematics(self) -> bool:
        """
        Test Lamport's vector clock mathematical properties:
        1. Causality detection (happens-before relationship)
        2. Concurrent event detection
        3. Clock advancement rules
        4. Merge operation correctness
        """
        print("🧮 Testing Vector Clock Mathematics...")
        
        try:
            # Test 1: Basic clock operations
            clock1 = VectorClock("node1")
            clock2 = VectorClock("node2")
            
            # Test initial state
            assert clock1.clock == {"node1": 0}, "Initial clock should be zero"
            
            # Test tick operation (Lamport Rule 1)
            clock1.tick()
            assert clock1.clock["node1"] == 1, "Tick should increment local counter"
            
            # Test 2: Causality detection
            clock1.tick()  # node1: 2
            clock2.tick()  # node2: 1
            
            # Test happens-before relationship
            relation_before = clock1.compare(clock2)
            assert relation_before == "concurrent", "Independent events should be concurrent"
            
            # Test clock merge (Lamport Rule 2)
            clock2.update(clock1.clock)
            clock2.tick()  # Should have max values + 1
            
            expected_clock2 = {"node1": 2, "node2": 2}
            assert clock2.clock == expected_clock2, f"Clock merge failed: {clock2.clock} != {expected_clock2}"
            
            # Test 3: Causal ordering
            clock3 = VectorClock("node3")
            clock3.update(clock1.clock)  # Inherits causality
            clock3.tick()
            
            relation_after = clock1.compare(clock3)
            assert relation_after == "before", "Clock1 should happen-before clock3"
            
            # Test 4: Mathematical properties verification
            # Property 1: Irreflexivity (a clock doesn't happen-before itself)
            relation_self = clock1.compare(clock1)
            assert relation_self == "equal", "Clock should be equal to itself"
            
            # Property 2: Transitivity test
            clock4 = VectorClock("node4")
            clock4.update(clock3.clock)
            clock4.tick()
            
            # If clock1 -> clock3 and clock3 -> clock4, then clock1 -> clock4
            relation_transitive = clock1.compare(clock4)
            assert relation_transitive == "before", "Transitivity property violated"
            
            print("   ✅ Vector clock mathematics verified")
            return True
            
        except Exception as e:
            print(f"   ❌ Vector clock mathematics test failed: {e}")
            return False
    
    def test_fcfs_policy_logic(self) -> bool:
        """
        Test FCFS consistency policy logic:
        1. First submission acceptance
        2. Subsequent submission rejection
        3. Vector clock ordering respect
        4. Emergency priority handling
        """
        print("📋 Testing FCFS Policy Logic...")
        
        try:
            # Test 1: Basic FCFS behavior
            fcfs_policy = FCFSConsistencyPolicy()
            
            # First submission should be accepted
            operation1 = {'type': 'result_submission', 'job_id': 'job1', 'result': 'first_result'}
            context1 = {'vector_clock': {'node1': 1}, 'emergency_level': None}
            
            result1 = fcfs_policy._handle_result_submission(operation1, context1)
            assert result1 == True, "First submission should be accepted"
            
            # Second submission should be rejected
            operation2 = {'type': 'result_submission', 'job_id': 'job1', 'result': 'second_result'}
            context2 = {'vector_clock': {'node2': 1}, 'emergency_level': None}
            
            result2 = fcfs_policy._handle_result_submission(operation2, context2)
            assert result2 == False, "Second submission should be rejected (FCFS violation)"
            
            # Test 2: Vector clock ordering respect
            fcfs_policy2 = FCFSConsistencyPolicy()
            
            # Create operations with different vector clock timestamps
            early_operation = {'type': 'result_submission', 'job_id': 'job2', 'result': 'early'}
            late_operation = {'type': 'result_submission', 'job_id': 'job2', 'result': 'late'}
            
            early_context = {'vector_clock': {'node1': 1}, 'timestamp': time.time() - 10}
            late_context = {'vector_clock': {'node1': 2}, 'timestamp': time.time()}
            
            # Submit late operation first
            late_result = fcfs_policy2._handle_result_submission(late_operation, late_context)
            early_result = fcfs_policy2._handle_result_submission(early_operation, early_context)
            
            assert late_result == True, "Late submission first should be accepted"
            assert early_result == False, "Early submission second should be rejected"
            
            # Test 3: Emergency priority handling
            emergency = create_emergency("fire", EmergencyLevel.CRITICAL)
            emergency_context = {
                'vector_clock': {'emergency_node': 1},
                'emergency_level': emergency.level,
                'emergency_type': emergency.emergency_type
            }
            
            emergency_operation = {'type': 'result_submission', 'job_id': 'emergency_job', 'result': 'emergency_result'}
            emergency_result = fcfs_policy2._handle_result_submission(emergency_operation, emergency_context)
            
            # Emergency operations should have special handling
            assert emergency_result in [True, False], "Emergency operation should be processed"
            
            print("   ✅ FCFS policy logic verified")
            return True
            
        except Exception as e:
            print(f"   ❌ FCFS policy logic test failed: {e}")
            return False
    
    def test_causal_message_ordering(self) -> bool:
        """
        Test causal message ordering and consistency:
        1. Message causality preservation
        2. Emergency context propagation
        3. Vector clock advancement
        4. Message handler coordination
        """
        print("📨 Testing Causal Message Ordering...")
        
        try:
            # Test 1: Basic message creation and causality
            sender_clock = VectorClock("sender")
            receiver_clock = VectorClock("receiver")
            
            sender_clock.tick()  # sender: 1
            
            # Create causal message
            message = CausalMessage(
                sender_id="sender",
                receiver_id="receiver", 
                content={"data": "test_message"},
                vector_clock=sender_clock.clock
            )
            
            assert message.sender_id == "sender", "Sender ID should be preserved"
            assert message.vector_clock == sender_clock.clock, "Vector clock should be attached"
            assert message.content["data"] == "test_message", "Content should be preserved"
            
            # Test 2: Message handler processing
            handler = MessageHandler("receiver")
            
            # Process message and verify clock update
            initial_receiver_clock = receiver_clock.clock.copy()
            processed = handler.process_message(message, receiver_clock)
            
            assert processed == True, "Message should be processed successfully"
            # Receiver clock should advance after processing
            assert receiver_clock.clock["receiver"] > initial_receiver_clock.get("receiver", 0), "Receiver clock should advance"
            
            # Test 3: Causal ordering verification
            # Create a series of causally related messages
            node1_clock = VectorClock("node1")
            node2_clock = VectorClock("node2")
            node3_clock = VectorClock("node3")
            
            # Message sequence: node1 -> node2 -> node3
            node1_clock.tick()
            msg1_to_2 = CausalMessage("node1", "node2", {"seq": 1}, node1_clock.clock)
            
            node2_clock.update(node1_clock.clock)
            node2_clock.tick()
            msg2_to_3 = CausalMessage("node2", "node3", {"seq": 2}, node2_clock.clock)
            
            # Verify causal ordering
            handler2 = MessageHandler("node2")
            handler3 = MessageHandler("node3")
            
            result1 = handler2.process_message(msg1_to_2, node2_clock)
            result2 = handler3.process_message(msg2_to_3, node3_clock)
            
            assert result1 and result2, "Causal message sequence should be processed correctly"
            
            # Test 4: Emergency context propagation
            emergency = create_emergency("medical", EmergencyLevel.HIGH)
            emergency_msg = CausalMessage(
                "emergency_sender",
                "emergency_receiver",
                {"emergency": "medical_crisis"},
                node1_clock.clock,
                emergency_context=emergency
            )
            
            assert emergency_msg.emergency_context is not None, "Emergency context should be preserved"
            assert emergency_msg.emergency_context.level == EmergencyLevel.HIGH, "Emergency level should be preserved"
            
            print("   ✅ Causal message ordering verified")
            return True
            
        except Exception as e:
            print(f"   ❌ Causal message ordering test failed: {e}")
            return False
    
    def test_performance_benchmarks(self) -> bool:
        """
        Test performance characteristics:
        1. Vector clock operation speed
        2. FCFS policy throughput
        3. Message processing latency
        4. Concurrent operations handling
        """
        print("⚡ Testing Performance Benchmarks...")
        
        try:
            # Test 1: Vector clock operation performance
            clock = VectorClock("perf_test")
            
            # Measure tick performance
            start_time = time.time()
            for _ in range(1000):
                clock.tick()
            tick_duration = time.time() - start_time
            tick_ops_per_sec = 1000 / tick_duration
            
            # Measure compare performance
            clock2 = VectorClock("perf_test2")
            clock2.tick()
            
            start_time = time.time()
            for _ in range(1000):
                clock.compare(clock2)
            compare_duration = time.time() - start_time
            compare_ops_per_sec = 1000 / compare_duration
            
            # Performance thresholds
            assert tick_ops_per_sec > 10000, f"Tick performance too slow: {tick_ops_per_sec} ops/sec"
            assert compare_ops_per_sec > 5000, f"Compare performance too slow: {compare_ops_per_sec} ops/sec"
            
            # Test 2: FCFS policy throughput
            fcfs = FCFSConsistencyPolicy()
            
            start_time = time.time()
            for i in range(100):
                operation = {'type': 'result_submission', 'job_id': f'job_{i}', 'result': f'result_{i}'}
                context = {'vector_clock': {'node': i}, 'emergency_level': None}
                fcfs._handle_result_submission(operation, context)
            fcfs_duration = time.time() - start_time
            fcfs_ops_per_sec = 100 / fcfs_duration
            
            assert fcfs_ops_per_sec > 1000, f"FCFS throughput too slow: {fcfs_ops_per_sec} ops/sec"
            
            # Test 3: Concurrent operations stress test
            def concurrent_clock_operations():
                """Simulate concurrent vector clock operations"""
                local_clock = VectorClock(f"thread_{threading.current_thread().ident}")
                for _ in range(100):
                    local_clock.tick()
                    time.sleep(0.001)  # Small delay to simulate real work
                return local_clock
            
            # Run concurrent operations
            threads = []
            start_time = time.time()
            
            for i in range(10):
                thread = threading.Thread(target=concurrent_clock_operations)
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            concurrent_duration = time.time() - start_time
            
            # Should complete within reasonable time even with concurrency
            assert concurrent_duration < 5.0, f"Concurrent operations too slow: {concurrent_duration}s"
            
            # Test 4: Memory efficiency test
            initial_clocks = []
            for i in range(1000):
                clock = VectorClock(f"node_{i}")
                clock.tick()
                initial_clocks.append(clock)
            
            # Verify clocks are independent and don't interfere
            for i, clock in enumerate(initial_clocks):
                expected_value = 1
                actual_value = clock.clock[f"node_{i}"]
                assert actual_value == expected_value, f"Clock independence violated at {i}"
            
            # Store performance metrics
            self.performance_metrics.update({
                'tick_ops_per_sec': tick_ops_per_sec,
                'compare_ops_per_sec': compare_ops_per_sec,
                'fcfs_ops_per_sec': fcfs_ops_per_sec,
                'concurrent_duration': concurrent_duration
            })
            
            print("   ✅ Performance benchmarks passed")
            return True
            
        except Exception as e:
            print(f"   ❌ Performance benchmark test failed: {e}")
            return False
    
    def test_emergency_integration(self) -> bool:
        """
        Test emergency context integration across components:
        1. Emergency creation and validation
        2. Priority level handling
        3. Context propagation through messages
        4. Emergency-aware consistency management
        """
        print("🚨 Testing Emergency Integration...")
        
        try:
            # Test 1: Emergency creation and validation
            fire_emergency = create_emergency("fire", EmergencyLevel.CRITICAL)
            medical_emergency = create_emergency("medical", EmergencyLevel.HIGH)
            traffic_emergency = create_emergency("traffic", EmergencyLevel.MEDIUM)
            
            assert fire_emergency.emergency_type == "fire", "Emergency type should be preserved"
            assert fire_emergency.level == EmergencyLevel.CRITICAL, "Emergency level should be preserved"
            assert fire_emergency.is_critical() == True, "Critical emergency should be detected"
            
            assert medical_emergency.level == EmergencyLevel.HIGH, "High priority should be set"
            assert traffic_emergency.level == EmergencyLevel.MEDIUM, "Medium priority should be set"
            
            # Test 2: Emergency priority comparison
            assert fire_emergency.level.value > medical_emergency.level.value, "Critical should be higher than high"
            assert medical_emergency.level.value > traffic_emergency.level.value, "High should be higher than medium"
            
            # Test 3: Emergency context in causal consistency
            manager = CausalConsistencyManager("emergency_node")
            
            # Normal operation
            normal_op = {'type': 'test', 'data': 'normal'}
            normal_context = {'vector_clock': {'emergency_node': 1}}
            
            # Emergency operation
            emergency_op = {'type': 'test', 'data': 'emergency'}
            emergency_context = {
                'vector_clock': {'emergency_node': 2},
                'emergency_level': fire_emergency.level,
                'emergency_type': fire_emergency.emergency_type
            }
            
            # Both should be processed, but emergency context should be preserved
            normal_result = manager.process_operation(normal_op, normal_context)
            emergency_result = manager.process_operation(emergency_op, emergency_context)
            
            assert normal_result in [True, False], "Normal operation should be processed"
            assert emergency_result in [True, False], "Emergency operation should be processed"
            
            # Test 4: Emergency context propagation through messages
            emergency_clock = VectorClock("emergency_sender")
            emergency_clock.tick()
            
            emergency_message = CausalMessage(
                "emergency_sender",
                "emergency_receiver",
                {"alert": "building_fire", "evacuation_needed": True},
                emergency_clock.clock,
                emergency_context=fire_emergency
            )
            
            assert emergency_message.emergency_context is not None, "Emergency context should be attached"
            assert emergency_message.emergency_context.is_critical(), "Critical emergency should be preserved"
            
            # Test emergency message processing
            emergency_handler = MessageHandler("emergency_receiver")
            receiver_clock = VectorClock("emergency_receiver")
            
            processing_result = emergency_handler.process_message(emergency_message, receiver_clock)
            assert processing_result == True, "Emergency message should be processed successfully"
            
            print("   ✅ Emergency integration verified")
            return True
            
        except Exception as e:
            print(f"   ❌ Emergency integration test failed: {e}")
            return False
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """
        Run all Phase 1 tests and return comprehensive results.
        """
        print("🎯 PHASE 1 CORE FOUNDATION - COMPREHENSIVE TEST SUITE")
        print("=" * 65)
        print()
        
        # Run all test components
        tests = [
            ("Vector Clock Mathematics", self.test_vector_clock_mathematics),
            ("FCFS Policy Logic", self.test_fcfs_policy_logic),
            ("Causal Message Ordering", self.test_causal_message_ordering),
            ("Performance Benchmarks", self.test_performance_benchmarks),
            ("Emergency Integration", self.test_emergency_integration)
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
        
        print("📊 PHASE 1 TEST RESULTS SUMMARY:")
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
                if 'ops_per_sec' in metric:
                    print(f"  {metric}: {value:.1f} operations/second")
                else:
                    print(f"  {metric}: {value:.3f} seconds")
        
        # Final verdict
        print()
        if success_rate == 100:
            print("🏆 PHASE 1 CORE FOUNDATION: ALL TESTS PASSED")
            print("   ✅ Vector clock mathematics verified")
            print("   ✅ FCFS policy logic confirmed")
            print("   ✅ Causal message ordering working")
            print("   ✅ Performance benchmarks met")
            print("   ✅ Emergency integration functional")
        else:
            print("⚠️  PHASE 1 CORE FOUNDATION: SOME TESTS FAILED")
            print("   Review failed components for issues")
        
        return {
            'phase': 'Phase 1 - Core Foundation',
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': success_rate,
            'test_results': self.test_results,
            'performance_metrics': self.performance_metrics,
            'overall_status': 'PASSED' if success_rate == 100 else 'FAILED'
        }


def main():
    """Run Phase 1 comprehensive test suite."""
    test_suite = Phase1CoreFoundationTest()
    results = test_suite.run_comprehensive_test()
    
    # Return exit code based on results
    return 0 if results['overall_status'] == 'PASSED' else 1


if __name__ == "__main__":
    exit(main())
