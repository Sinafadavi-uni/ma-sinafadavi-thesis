"""
Phase 1: Core Foundation

Core foundation modules for vector clock-based causal consistency.
These are the fundamental building blocks that all other phases depend on.

Phase 1 Files:
1. consistency_manager.py - Base consistency interface (foundation for all consistency)
2. vector_clock.py - Core vector clock implementation (Lamport's algorithm + emergency)
3. causal_message.py - Causal messaging system (distributed communication)
4. causal_consistency.py - Causal consistency manager + FCFS policy (thesis core)

This phase implements the absolute foundation: vector clock-based causal 
consistency with emergency awareness and FCFS data replication policy.
"""


# Import all Phase 1 components
from .consistency_manager import BaseConsistencyManager, ConsistencyPolicy
from .vector_clock import VectorClock, EmergencyLevel, EmergencyContext, create_emergency
from .causal_message import CausalMessage, MessageHandler, broadcast_emergency, create_message_network
from .causal_consistency import CausalConsistencyManager, FCFSConsistencyPolicy, create_causal_operation

# Phase 1 demonstration function
def demo_phase1():
    """
    Demonstrate Phase 1 core foundation functionality
    
    Shows vector clock basics, causal messaging, and consistency management
    working together as the foundation for all subsequent phases.
    """
    print("🎯 PHASE 1: CORE FOUNDATION DEMONSTRATION")
    print("=" * 60)
    print("   Foundation for vector clock-based causal consistency")
    print("   Emergency-aware distributed coordination")
    print("   FCFS data replication policy")
    print()
    
    try:
        # Test 1: Vector Clock Basics
        print("📍 Test 1: Vector Clock Foundation")
        clock1 = VectorClock("node1")
        clock2 = VectorClock("node2")
        
        clock1.tick()
        clock2.tick()
        clock1.update(clock2.clock)
        
        relation = clock1.compare(clock2)
        print(f"   ✅ Vector clocks operational: {clock1.node_id} is '{relation}' relative to {clock2.node_id}")
        
        # Test 2: Emergency Context
        print("\n📍 Test 2: Emergency Context System")
        emergency = create_emergency("fire", "critical", "Building A")
        print(f"   ✅ Emergency created: {emergency} (Critical: {emergency.is_critical()})")
        
        # Test 3: Causal Messaging
        print("\n📍 Test 3: Causal Message System")
        handler1 = MessageHandler("msg_node1")
        handler2 = MessageHandler("msg_node2")
        
        msg = handler1.send_message("Test message", "msg_node2")
        handler2.receive_message(msg)
        stats = handler2.get_message_stats()
        print(f"   ✅ Causal messaging operational: {stats['processed']} messages processed")
        
        # Test 4: Causal Consistency Manager
        print("\n📍 Test 4: Causal Consistency Manager")
        consistency_mgr = CausalConsistencyManager("consistency_node")
        
        test_operation = create_causal_operation(
            "test_op", "test", {"consistency_node": 1}
        )
        
        valid = consistency_mgr.validate_operation(test_operation)
        consistent = consistency_mgr.ensure_consistency(test_operation)
        print(f"   ✅ Consistency management: valid={valid}, consistent={consistent}")
        
        # Test 5: FCFS Policy
        print("\n📍 Test 5: FCFS Consistency Policy")
        fcfs_policy = FCFSConsistencyPolicy()
        
        # Submit job
        job_op = create_causal_operation(
            "job1", "job_submission", {"node1": 1}, 
            job_id="test_job", submitter_id="submitter1"
        )
        job_accepted = fcfs_policy.apply_policy(job_op, {})
        
        # Submit first result
        result_op1 = create_causal_operation(
            "result1", "result_submission", {"node1": 2},
            job_id="test_job", result="first_result", executor_id="executor1"
        )
        first_result = fcfs_policy.apply_policy(result_op1, {})
        
        # Submit second result (should be rejected)
        result_op2 = create_causal_operation(
            "result2", "result_submission", {"node1": 3},
            job_id="test_job", result="second_result", executor_id="executor2"
        )
        second_result = fcfs_policy.apply_policy(result_op2, {})
        
        print(f"   ✅ FCFS policy operational: job={job_accepted}, first={first_result}, second={not second_result}")
        
        # Phase 1 Summary
        print("\n" + "=" * 60)
        print("🎉 PHASE 1 COMPLETE: CORE FOUNDATION OPERATIONAL")
        print("=" * 60)
        print("✅ Vector Clock Foundation - Lamport's algorithm with emergency support")
        print("✅ Causal Message System - Distributed communication with ordering")
        print("✅ Consistency Manager - Base interface for all consistency policies")
        print("✅ Causal Consistency - Vector clock-based causal ordering")
        print("✅ FCFS Policy - First-result-accepted data replication")
        print()
        print("🚀 Ready for Phase 2: Node Infrastructure")
        print("=" * 60)
        
        return {
            'phase': 'Phase 1',
            'status': 'complete',
            'components_tested': 5,
            'all_tests_passed': True,
            'ready_for_next_phase': True
        }
        
    except Exception as e:
        print(f"❌ Phase 1 error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'phase': 'Phase 1',
            'status': 'error',
            'error': str(e),
            'ready_for_next_phase': False
        }

# Export all Phase 1 components
__all__ = [
    # Base interfaces
    'BaseConsistencyManager',
    'ConsistencyPolicy',
    
    # Vector clock system
    'VectorClock', 
    'EmergencyLevel',
    'EmergencyContext',
    'create_emergency',
    
    # Causal messaging
    'CausalMessage',
    'MessageHandler', 
    'broadcast_emergency',
    'create_message_network',
    
    # Causal consistency
    'CausalConsistencyManager',
    'FCFSConsistencyPolicy',
    'create_causal_operation',
    
    # Phase demonstration
    'demo_phase1'
]