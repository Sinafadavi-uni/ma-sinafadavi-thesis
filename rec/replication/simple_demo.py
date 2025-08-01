# Simple Demo of Vector Clock Emergency System
# Shows how the system works with easy-to-understand examples

import uuid
from rec.model import Capabilities
from rec.replication.core.vector_clock import (
    CapabilityAwareVectorClock, EmergencyContext, EmergencyLevel, 
    CapabilityScorer, create_emergency
)
from rec.replication.core.causal_message import MessageHandler, send_emergency_alert


def demo_basic_vector_clock():
    """Demo 1: Basic vector clock operations"""
    print("=== Demo 1: Basic Vector Clock ===")
    
    # Create two nodes
    node1_id = uuid.uuid4()
    node2_id = uuid.uuid4()
    
    # Simple capabilities for testing
    caps1 = Capabilities(cpu_cores=4, memory=8192, power=85.0)
    caps2 = Capabilities(cpu_cores=2, memory=4096, power=60.0)
    
    # Create vector clocks
    clock1 = CapabilityAwareVectorClock(node1_id, caps1)
    clock2 = CapabilityAwareVectorClock(node2_id, caps2)
    
    print(f"Node 1 initial clock: {clock1.clock}")
    print(f"Node 2 initial clock: {clock2.clock}")
    
    # Node 1 does something (sends a message)
    clock1.tick()
    print(f"Node 1 after tick: {clock1.clock}")
    
    # Node 2 receives node 1's timestamp and updates
    clock2.update(clock1.clock)
    print(f"Node 2 after receiving from node 1: {clock2.clock}")
    
    # Compare the clocks
    relation = clock1.compare(clock2.clock)
    print(f"Clock 1 vs Clock 2: {relation}")
    
    print()


def demo_emergency_prioritization():
    """Demo 2: Emergency prioritization"""
    print("=== Demo 2: Emergency Prioritization ===")
    
    # Create nodes with different capabilities
    hospital_node = uuid.uuid4()
    regular_node = uuid.uuid4()
    
    hospital_caps = Capabilities(
        cpu_cores=8, 
        memory=16384, 
        power=95.0,
        has_medical_equipment=True  # this is the key difference
    )
    
    regular_caps = Capabilities(
        cpu_cores=4,
        memory=8192, 
        power=70.0,
        has_medical_equipment=False
    )
    
    hospital_clock = CapabilityAwareVectorClock(hospital_node, hospital_caps)
    regular_clock = CapabilityAwareVectorClock(regular_node, regular_caps)
    
    # Normal situation - basic scoring
    print("Normal situation:")
    hospital_score = hospital_clock.get_capability_score()
    regular_score = regular_clock.get_capability_score()
    print(f"Hospital node score: {hospital_score:.1f}")
    print(f"Regular node score: {regular_score:.1f}")
    
    # Emergency situation - medical emergency
    medical_emergency = create_emergency("medical", "critical")
    print(f"\nMedical emergency situation:")
    hospital_emergency_score = hospital_clock.get_capability_score(medical_emergency)
    regular_emergency_score = regular_clock.get_capability_score(medical_emergency)
    print(f"Hospital node emergency score: {hospital_emergency_score:.1f}")
    print(f"Regular node emergency score: {regular_emergency_score:.1f}")
    
    # Check who should handle the emergency
    should_hospital_handle = hospital_clock.should_handle_emergency(
        medical_emergency, [regular_emergency_score]
    )
    print(f"Should hospital handle emergency? {should_hospital_handle}")
    
    print()


def demo_message_ordering():
    """Demo 3: Message ordering with causal consistency"""
    print("=== Demo 3: Message Ordering ===")
    
    # Create three nodes
    node_ids = [uuid.uuid4() for _ in range(3)]
    capabilities = [
        Capabilities(cpu_cores=4, memory=8192, power=80.0),
        Capabilities(cpu_cores=2, memory=4096, power=60.0),
        Capabilities(cpu_cores=6, memory=12288, power=90.0)
    ]
    
    # Create message handlers for each node
    handlers = []
    for i in range(3):
        handler = MessageHandler(node_ids[i], capabilities[i])
        handlers.append(handler)
    
    print("Sending messages between nodes...")
    
    # Node 0 sends normal message to node 1
    msg1 = handlers[0].send_message("Hello from node 0", node_ids[1])
    print(f"Message 1: {msg1.content} (priority: {msg1.priority})")
    
    # Node 1 sends emergency message to node 2
    msg2 = handlers[1].send_message("EMERGENCY: Fire detected!", node_ids[2], is_emergency=True)
    print(f"Message 2: {msg2.content} (priority: {msg2.priority})")
    
    # Node 2 receives both messages
    print(f"\nNode 2 receiving messages...")
    handlers[2].receive_message(msg1)
    handlers[2].receive_message(msg2)
    
    print(f"Pending messages at node 2: {handlers[2].get_pending_count()}")
    print(f"Has emergency pending: {handlers[2].has_emergency_pending()}")
    
    print()


def demo_node_ranking():
    """Demo 4: Ranking nodes by capability"""
    print("=== Demo 4: Node Ranking ===")
    
    # Create several nodes with different capabilities
    nodes = []
    for i in range(4):
        node_id = uuid.uuid4()
        # Vary the capabilities
        caps = Capabilities(
            cpu_cores=2 + i,
            memory=4096 * (i + 1),
            power=50 + i * 15,
            has_medical_equipment=(i == 2)  # only node 2 has medical equipment
        )
        nodes.append((node_id, caps))
    
    # Create capability scorer
    scorer = CapabilityScorer()
    
    # Rank nodes in normal situation
    print("Normal situation ranking:")
    scorer.strategy = "basic"
    ranked_normal = scorer.rank_nodes(nodes)
    for i, (node_id, score) in enumerate(ranked_normal):
        print(f"  {i+1}. Node {str(node_id)[:8]}... Score: {score:.1f}")
    
    # Rank nodes in emergency situation
    print(f"\nMedical emergency ranking:")
    scorer.strategy = "emergency"
    medical_emergency = create_emergency("medical", "high")
    ranked_emergency = scorer.rank_nodes(nodes, medical_emergency)
    for i, (node_id, score) in enumerate(ranked_emergency):
        print(f"  {i+1}. Node {str(node_id)[:8]}... Score: {score:.1f}")
    
    print()


def demo_emergency_alert_system():
    """Demo 5: Complete emergency alert system"""
    print("=== Demo 5: Emergency Alert System ===")
    
    # Create a small network of nodes
    num_nodes = 5
    node_ids = [uuid.uuid4() for _ in range(num_nodes)]
    
    # Create handlers with different capabilities
    handlers = []
    for i in range(num_nodes):
        caps = Capabilities(
            cpu_cores=2 + (i % 3),
            memory=4096 + i * 2048,
            power=60 + i * 10,
            has_medical_equipment=(i in [1, 3])  # nodes 1 and 3 have medical equipment
        )
        handler = MessageHandler(node_ids[i], caps)
        handlers.append(handler)
    
    print(f"Created network with {num_nodes} nodes")
    print("Nodes with medical equipment: 1, 3")
    
    # Node 0 detects an emergency
    print(f"\nNode 0 detects medical emergency...")
    emergency_location = "Building A, Floor 2"
    recipient_ids = node_ids[1:]  # send to all other nodes
    
    alert_messages = send_emergency_alert(
        handlers[0], 
        "medical", 
        emergency_location, 
        recipient_ids
    )
    
    print(f"Sent {len(alert_messages)} emergency alerts")
    
    # Other nodes receive the alerts
    for i, message in enumerate(alert_messages):
        recipient_idx = i + 1  # nodes 1, 2, 3, 4
        handlers[recipient_idx].receive_message(message)
        print(f"Node {recipient_idx} received emergency alert")
    
    # Check which nodes have emergency messages pending
    print(f"\nEmergency message status:")
    for i, handler in enumerate(handlers):
        has_emergency = handler.has_emergency_pending()
        pending_count = handler.get_pending_count()
        if has_emergency:
            print(f"  Node {i}: {pending_count} pending ({has_emergency} emergency)")
    
    print()


def run_all_demos():
    """Run all the demos to show the system working"""
    print("Vector Clock Emergency System - Simple Student Implementation")
    print("=" * 60)
    print()
    
    demo_basic_vector_clock()
    demo_emergency_prioritization()
    demo_message_ordering()
    demo_node_ranking()
    demo_emergency_alert_system()
    
    print("All demos completed successfully!")
    print("The system can handle:")
    print("- Basic vector clock operations")
    print("- Emergency prioritization")
    print("- Message ordering")
    print("- Node capability ranking")
    print("- Emergency alert distribution")


if __name__ == "__main__":
    run_all_demos()
