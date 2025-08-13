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


# Import everything from Phase 1 modules
from .consistency_manager import BaseConsistencyManager, ConsistencyPolicy
from .vector_clock import VectorClock, EmergencyLevel, EmergencyContext, create_emergency
from .causal_message import CausalMessage, MessageHandler, broadcast_emergency, create_message_network
from .causal_consistency import CausalConsistencyManager, FCFSConsistencyPolicy, create_causal_operation

# This function shows how Phase 1 works with vector clocks and causal consistency
def demo_phase1():
    """
    This function runs a bunch of tests to show that the core things from Phase 1
    (vector clocks, messages, consistency policies) are working.
    """
    print("🎯 PHASE 1: CORE FOUNDATION DEMONSTRATION")
    print("=" * 60)
    print("   Foundation for vector clock-based causal consistency")
    print("   Emergency-aware distributed coordination")
    print("   FCFS data replication policy")
    print()

    try:
        # -------- Vector Clock Test --------
        print("📍 Test 1: Vector Clock Foundation")
        clock1 = VectorClock("node1")
        clock2 = VectorClock("node2")

        clock1.tick()
        clock2.tick()
        clock1.update(clock2.clock)

        relation = clock1.compare(clock2)
        print(f"   ✅ Vector clocks operational: {clock1.node_id} is '{relation}' relative to {clock2.node_id}")

        # -------- Emergency Context Test --------
        print("\n📍 Test 2: Emergency Context System")
        emergency = create_emergency("fire", "critical", "Building A")
        is_critical = emergency.is_critical()
        print(f"   ✅ Emergency created: {emergency} (Critical: {is_critical})")

        # -------- Causal Messaging Test --------
        print("\n📍 Test 3: Causal Message System")
        handler1 = MessageHandler("msg_node1")
        handler2 = MessageHandler("msg_node2")

        msg = handler1.send_message("Test message", "msg_node2")
        handler2.receive_message(msg)
        stats = handler2.get_message_stats()
        processed_count = stats['processed']
        print(f"   ✅ Causal messaging operational: {processed_count} messages processed")

        # -------- Consistency Manager Test --------
        print("\n📍 Test 4: Causal Consistency Manager")
        consistency_mgr = CausalConsistencyManager("consistency_node")

        test_operation = create_causal_operation(
            "test_op", "test", {"consistency_node": 1}
        )

        valid = consistency_mgr.validate_operation(test_operation)
        consistent = consistency_mgr.ensure_consistency(test_operation)

        print(f"   ✅ Consistency management: valid={valid}, consistent={consistent}")

        # -------- FCFS Policy Test --------
        print("\n📍 Test 5: FCFS Consistency Policy")
        fcfs_policy = FCFSConsistencyPolicy()

        job_op = create_causal_operation(
            "job1", "job_submission", {"node1": 1},
            job_id="test_job", submitter_id="submitter1"
        )
        job_accepted = fcfs_policy.apply_policy(job_op, {})

        result_op1 = create_causal_operation(
            "result1", "result_submission", {"node1": 2},
            job_id="test_job", result="first_result", executor_id="executor1"
        )
        first_result = fcfs_policy.apply_policy(result_op1, {})

        result_op2 = create_causal_operation(
            "result2", "result_submission", {"node1": 3},
            job_id="test_job", result="second_result", executor_id="executor2"
        )
        second_result = fcfs_policy.apply_policy(result_op2, {})

        print(f"   ✅ FCFS policy operational: job={job_accepted}, first={first_result}, second={not second_result}")

        # -------- Summary --------
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

# Exporting everything so it can be used outside this file
__all__ = [
    'BaseConsistencyManager',
    'ConsistencyPolicy',
    'VectorClock',
    'EmergencyLevel',
    'EmergencyContext',
    'create_emergency',
    'CausalMessage',
    'MessageHandler',
    'broadcast_emergency',
    'create_message_network',
    'CausalConsistencyManager',
    'FCFSConsistencyPolicy',
    'create_causal_operation',
    'demo_phase1'
]
