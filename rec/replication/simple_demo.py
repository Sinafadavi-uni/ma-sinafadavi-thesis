# Vector Clock Emergency System - Demo Suite
# Written as a simple walkthrough for testing core concepts interactively

import uuid
from rec.model import Capabilities
from rec.replication.core.vector_clock import (
    CapabilityAwareVectorClock, EmergencyContext, EmergencyLevel, 
    CapabilityScorer, create_emergency
)
from rec.replication.core.causal_message import MessageHandler, send_emergency_alert


def demo_basic_vector_clock():
    print("=== Demo 1: Vector Clock Basics ===")

    node1_id = uuid.uuid4()
    node2_id = uuid.uuid4()

    caps1 = Capabilities(cpu_cores=4, memory=8192, power=85.0)
    caps2 = Capabilities(cpu_cores=2, memory=4096, power=60.0)

    vc1 = CapabilityAwareVectorClock(node1_id, caps1)
    vc2 = CapabilityAwareVectorClock(node2_id, caps2)

    print("Initial state:")
    print("Node 1 clock:", vc1.clock)
    print("Node 2 clock:", vc2.clock)

    # Node 1 sends something
    vc1.tick()
    print("Node 1 after tick:", vc1.clock)

    # Node 2 receives and merges
    vc2.update(vc1.clock)
    print("Node 2 after receiving Node 1:", vc2.clock)

    # Compare ordering
    relation = vc1.compare(vc2.clock)
    print(f"Clock comparison result: Node1 is '{relation}' relative to Node2\n")


def demo_emergency_prioritization():
    print("=== Demo 2: Emergency Prioritization ===")

    hospital_id = uuid.uuid4()
    regular_id = uuid.uuid4()

    hospital_caps = Capabilities(
        cpu_cores=8,
        memory=16384,
        power=95.0,
        has_medical_equipment=True
    )
    regular_caps = Capabilities(
        cpu_cores=4,
        memory=8192,
        power=70.0,
        has_medical_equipment=False
    )

    hospital = CapabilityAwareVectorClock(hospital_id, hospital_caps)
    regular = CapabilityAwareVectorClock(regular_id, regular_caps)

    print("→ Normal context:")
    print(f"Hospital score: {hospital.get_capability_score():.1f}")
    print(f"Regular node score: {regular.get_capability_score():.1f}")

    emergency = create_emergency("medical", "critical")
    print("\n→ Emergency context (medical):")
    print(f"Hospital score: {hospital.get_capability_score(emergency):.1f}")
    print(f"Regular node score: {regular.get_capability_score(emergency):.1f}")

    decision = hospital.should_handle_emergency(emergency, [regular.get_capability_score(emergency)])
    print(f"Should hospital handle it? {'Yes' if decision else 'No'}\n")


def demo_message_ordering():
    print("=== Demo 3: Message Ordering ===")

    node_ids = [uuid.uuid4() for _ in range(3)]
    caps = [
        Capabilities(cpu_cores=4, memory=8192, power=80.0),
        Capabilities(cpu_cores=2, memory=4096, power=60.0),
        Capabilities(cpu_cores=6, memory=12288, power=90.0)
    ]

    handlers = [MessageHandler(nid, cap) for nid, cap in zip(node_ids, caps)]

    msg1 = handlers[0].send_message("Hello from Node 0", node_ids[1])
    msg2 = handlers[1].send_message("🔥 EMERGENCY: Fire detected", node_ids[2], is_emergency=True)

    print(f"→ Sent Message 1 (priority {msg1.priority}): {msg1.content}")
    print(f"→ Sent Message 2 (priority {msg2.priority}): {msg2.content}")

    handlers[2].receive_message(msg1)
    handlers[2].receive_message(msg2)

    print("\n→ Node 2 state:")
    print("Pending messages:", handlers[2].get_pending_count())
    print("Has emergency:", handlers[2].has_emergency_pending())
    print()


def demo_node_ranking():
    print("=== Demo 4: Node Capability Ranking ===")

    nodes = []
    for i in range(4):
        nid = uuid.uuid4()
        cap = Capabilities(
            cpu_cores=2 + i,
            memory=4096 * (i + 1),
            power=50 + i * 15,
            has_medical_equipment=(i == 2)
        )
        nodes.append((nid, cap))

    scorer = CapabilityScorer()

    print("→ Basic scoring:")
    ranked = scorer.rank_nodes(nodes)
    for i, (nid, score) in enumerate(ranked, start=1):
        print(f"  {i}. Node {str(nid)[:8]} – Score: {score:.1f}")

    emergency = create_emergency("medical", "high")
    scorer.strategy = "emergency"

    print("\n→ Emergency scoring (medical):")
    ranked_emergency = scorer.rank_nodes(nodes, emergency)
    for i, (nid, score) in enumerate(ranked_emergency, start=1):
        print(f"  {i}. Node {str(nid)[:8]} – Score: {score:.1f}")
    print()


def demo_emergency_alert_system():
    print("=== Demo 5: Emergency Alert System ===")

    total_nodes = 5
    node_ids = [uuid.uuid4() for _ in range(total_nodes)]

    handlers = []
    for i in range(total_nodes):
        caps = Capabilities(
            cpu_cores=2 + (i % 3),
            memory=4096 + i * 2048,
            power=60 + i * 10,
            has_medical_equipment=(i in [1, 3])
        )
        handlers.append(MessageHandler(node_ids[i], caps))

    print(f"→ {total_nodes} nodes initialized.")
    print("Medical-capable nodes: 1, 3")

    print("\n→ Node 0 detects emergency...")
    location = "Building A, Floor 2"
    recipients = node_ids[1:]

    alerts = send_emergency_alert(handlers[0], "medical", location, recipients)
    print(f"→ Sent {len(alerts)} alerts")

    for i, msg in enumerate(alerts):
        handlers[i + 1].receive_message(msg)
        print(f"Node {i + 1} received alert.")

    print("\n→ Pending emergency states:")
    for i, h in enumerate(handlers):
        if h.has_emergency_pending():
            print(f"  Node {i}: {h.get_pending_count()} message(s), emergency present")
    print()


def run_all_demos():
    print("=== Running All Demos ===")
    print("Student Implementation of Vector Clock Emergency System\n")

    demo_basic_vector_clock()
    demo_emergency_prioritization()
    demo_message_ordering()
    demo_node_ranking()
    demo_emergency_alert_system()

    print("✓ All demos executed successfully.\n")


if __name__ == "__main__":
    run_all_demos()
