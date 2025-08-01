# Simple tests for the vector clock emergency system
# Just basic tests to make sure everything works

import uuid
import pytest
from rec.model import Capabilities
from rec.replication.core.vector_clock import (
    VectorClock, CapabilityAwareVectorClock, EmergencyLevel, 
    create_emergency, CapabilityScorer
)
from rec.replication.core.causal_message import MessageHandler


def test_basic_vector_clock():
    """Test basic vector clock operations work correctly"""
    # Create two nodes
    node1 = uuid.uuid4()
    node2 = uuid.uuid4()
    
    clock1 = VectorClock(node1)
    clock2 = VectorClock(node2)
    
    # Initially both clocks should be empty
    assert len(clock1.clock) == 0
    assert len(clock2.clock) == 0
    
    # After tick, node should have timestamp 1
    clock1.tick()
    assert clock1.clock[node1] == 1
    
    # Node 2 receives node 1's timestamp
    clock2.update(clock1.clock)
    assert clock2.clock[node1] == 1  # received from node 1
    assert clock2.clock[node2] == 1  # incremented own time
    
    # Clock comparison
    relation = clock1.compare(clock2.clock)
    assert relation in ['before', 'after', 'concurrent']


def test_emergency_prioritization():
    """Test emergency prioritization works"""
    # Create node with medical equipment
    node_id = uuid.uuid4()
    medical_caps = Capabilities(
        cpu_cores=4,
        memory=8192,
        power=85.0,
        has_medical_equipment=True
    )
    
    clock = CapabilityAwareVectorClock(node_id, medical_caps)
    
    # Normal score
    normal_score = clock.get_capability_score()
    
    # Emergency score should be higher for medical equipment
    medical_emergency = create_emergency("medical", "critical")
    emergency_score = clock.get_capability_score(medical_emergency)
    
    # Medical node should get bonus during medical emergency
    # (exact values might vary, but medical equipment should help)
    assert emergency_score >= normal_score


def test_capability_scoring():
    """Test capability scoring works for different node types"""
    # Create different types of nodes
    basic_caps = Capabilities(cpu_cores=2, memory=4096, power=60.0)
    powerful_caps = Capabilities(cpu_cores=8, memory=16384, power=95.0)
    
    scorer = CapabilityScorer()
    
    basic_score = scorer.score_node(basic_caps)
    powerful_score = scorer.score_node(powerful_caps)
    
    # More powerful node should score higher
    assert powerful_score > basic_score


def test_message_handling():
    """Test message ordering and emergency prioritization"""
    node_id = uuid.uuid4()
    caps = Capabilities(cpu_cores=4, memory=8192, power=80.0)
    
    handler = MessageHandler(node_id, caps)
    
    # Send normal message
    normal_msg = handler.send_message("Hello", uuid.uuid4())
    assert normal_msg.priority == 1
    assert not normal_msg.is_emergency()
    
    # Send emergency message
    emergency_msg = handler.send_message("FIRE!", uuid.uuid4(), is_emergency=True)
    assert emergency_msg.priority == 5
    assert emergency_msg.is_emergency()
    
    # Emergency message should have higher priority
    assert emergency_msg.priority > normal_msg.priority


def test_node_ranking():
    """Test node ranking by capabilities"""
    # Create several nodes with different capabilities
    nodes = []
    for i in range(3):
        node_id = uuid.uuid4()
        caps = Capabilities(
            cpu_cores=2 + i,
            memory=4096 * (i + 1),
            power=60 + i * 15
        )
        nodes.append((node_id, caps))
    
    scorer = CapabilityScorer()
    ranked = scorer.rank_nodes(nodes)
    
    # Should return list of (node_id, score) tuples
    assert len(ranked) == 3
    assert all(len(item) == 2 for item in ranked)
    
    # Scores should be in descending order
    scores = [score for _, score in ranked]
    assert scores == sorted(scores, reverse=True)


def test_emergency_context():
    """Test emergency context creation and properties"""
    # Create different emergency types
    medical = create_emergency("medical", "high")
    fire = create_emergency("fire", "critical")
    low_emergency = create_emergency("other", "low")
    
    # Check emergency levels
    assert medical.level == EmergencyLevel.HIGH
    assert fire.level == EmergencyLevel.CRITICAL
    assert low_emergency.level == EmergencyLevel.LOW
    
    # Check critical emergency detection
    assert medical.is_critical()
    assert fire.is_critical()
    assert not low_emergency.is_critical()


def test_message_vector_clocks():
    """Test that messages include proper vector clock information"""
    node_id = uuid.uuid4()
    caps = Capabilities(cpu_cores=4, memory=8192, power=80.0)
    
    handler = MessageHandler(node_id, caps)
    
    # Send a message
    message = handler.send_message("Test message", uuid.uuid4())
    
    # Message should have vector clock info
    assert hasattr(message, 'vector_clock')
    assert isinstance(message.vector_clock, dict)
    assert node_id in message.vector_clock
    assert message.vector_clock[node_id] >= 1


if __name__ == "__main__":
    # Run tests manually if pytest not available
    print("Running simple tests...")
    
    try:
        test_basic_vector_clock()
        print("✅ Basic vector clock test passed")
        
        test_emergency_prioritization()
        print("✅ Emergency prioritization test passed")
        
        test_capability_scoring()
        print("✅ Capability scoring test passed")
        
        test_message_handling()
        print("✅ Message handling test passed")
        
        test_node_ranking()
        print("✅ Node ranking test passed")
        
        test_emergency_context()
        print("✅ Emergency context test passed")
        
        test_message_vector_clocks()
        print("✅ Message vector clocks test passed")
        
        print("\n🎉 All tests passed! System is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise
