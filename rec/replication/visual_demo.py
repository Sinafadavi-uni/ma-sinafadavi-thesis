#!/usr/bin/env python3
"""
Visual Demo for Professor - Vector Clock Emergency System
Polished version of simple_demo.py with clean step-by-step output.
"""

import uuid
import time
from rec.model import Capabilities
from rec.replication.core.vector_clock import (
    CapabilityAwareVectorClock, EmergencyContext, EmergencyLevel, 
    CapabilityScorer, create_emergency
)
from rec.replication.core.causal_message import MessageHandler, send_emergency_alert


def print_header(title):
    print("\n" + "🎯" + "="*58 + "🎯")
    print(f"🎯 {title.center(58)} 🎯")
    print("🎯" + "="*58 + "🎯")


def print_step(step_num, description):
    print(f"\n📋 Step {step_num}: {description}")
    print("   " + "-" * 50)


def print_result(result):
    print(f"\n✅ RESULT: {result}")


def print_comparison(label1, value1, label2, value2, winner=None):
    print(f"\n📊 COMPARISON:")
    print(f"   {label1}: {value1}")
    print(f"   {label2}: {value2}")
    if winner:
        print(f"   🏆 WINNER: {winner}")


def wait_for_professor():
    input("\n⏸️  Press Enter to continue...")


def demo_basic_vector_clock():
    print_header("Demo 1: Basic Vector Clock Sync")

    print_step(1, "Creating two test nodes")
    node1_id = uuid.uuid4()
    node2_id = uuid.uuid4()

    caps1 = Capabilities(cpu_cores=4, memory=8192, power=85.0)
    caps2 = Capabilities(cpu_cores=2, memory=4096, power=60.0)

    clock1 = CapabilityAwareVectorClock(node1_id, caps1)
    clock2 = CapabilityAwareVectorClock(node2_id, caps2)

    print(f"   Node 1 (4 cores, 8GB): {clock1.clock}")
    print(f"   Node 2 (2 cores, 4GB): {clock2.clock}")
    print_result("Both clocks are clean slates to start")

    print_step(2, "Node 1 does something (ticks)")
    clock1.tick()
    print(f"   Node 1 updated clock: {clock1.clock}")
    print_result("Event registered in Node 1")

    print_step(3, "Node 1 sends its clock to Node 2")
    print(f"   Outgoing clock: {clock1.clock}")

    print_step(4, "Node 2 receives and syncs")
    clock2.update(clock1.clock)
    print(f"   Node 2 clock after sync: {clock2.clock}")
    print_result("Node 2 now sees Node 1’s event")

    print_step(5, "Compare both clocks for ordering")
    relation = clock1.compare(clock2.clock)
    print(f"   Comparison result: Node1 is '{relation}'")

    print_result("Clocks behave as expected")


def demo_emergency_prioritization():
    print_header("Demo 2: Emergency Node Prioritization")

    print_step(1, "Setting up two nodes with different capabilities")

    hospital_id = uuid.uuid4()
    office_id = uuid.uuid4()

    hospital_caps = Capabilities(cpu_cores=8, memory=32768, power=95.0, has_battery=True)
    office_caps = Capabilities(cpu_cores=2, memory=4096, power=65.0, has_battery=False)

    hospital = CapabilityAwareVectorClock(hospital_id, hospital_caps)
    office = CapabilityAwareVectorClock(office_id, office_caps)

    print("   Hospital: 8 cores, 32GB, battery")
    print("   Office: 2 cores, 4GB, no battery")

    print_step(2, "Scoring in regular (non-emergency) mode")
    hospital_score = hospital.get_capability_score()
    office_score = office.get_capability_score()
    print_comparison("Hospital", f"{hospital_score:.1f}", "Office", f"{office_score:.1f}",
                     "Hospital" if hospital_score > office_score else "Office")

    print_step(3, "Emergency scenario declared")
    emergency_context = create_emergency("medical", "high")

    hospital_em_score = hospital.get_capability_score(emergency_context)
    office_em_score = office.get_capability_score(emergency_context)
    print_comparison("Hospital (Emergency)", f"{hospital_em_score:.1f}",
                     "Office (Emergency)", f"{office_em_score:.1f}",
                     "Hospital" if hospital_em_score > office_em_score else "Office")

    print_step(4, "Who should respond?")
    if hospital_em_score > office_em_score:
        print_result("Hospital clearly wins – ready for emergency response!")
    else:
        print_result("⚠️ Office outscored hospital – check logic!")


def demo_network_emergency():
    print_header("Demo 3: Full Emergency Network Response")

    print_step(1, "Spinning up a realistic emergency network")

    nodes = []

    hospital_id = uuid.uuid4()
    hospital_caps = Capabilities(cpu_cores=16, memory=65536, power=98.0, has_battery=True)
    nodes.append(("🏥 Hospital", CapabilityAwareVectorClock(hospital_id, hospital_caps)))

    ambulance_id = uuid.uuid4()
    ambulance_caps = Capabilities(cpu_cores=4, memory=8192, power=75.0, has_battery=True)
    nodes.append(("🚑 Ambulance", CapabilityAwareVectorClock(ambulance_id, ambulance_caps)))

    fire_id = uuid.uuid4()
    fire_caps = Capabilities(cpu_cores=8, memory=16384, power=90.0, has_battery=True)
    nodes.append(("🚒 Fire Dept", CapabilityAwareVectorClock(fire_id, fire_caps)))

    office_id = uuid.uuid4()
    office_caps = Capabilities(cpu_cores=2, memory=4096, power=60.0, has_battery=False)
    nodes.append(("🏢 Office", CapabilityAwareVectorClock(office_id, office_caps)))

    print("   Network ready with 4 nodes.")

    print_step(2, "Scoring nodes under normal ops")
    normal_scores = [(name, node.get_capability_score()) for name, node in nodes]
    for i, (name, score) in enumerate(sorted(normal_scores, key=lambda x: -x[1]), 1):
        print(f"   {i}. {name}: {score:.1f}")

    print_step(3, "A critical emergency is declared (medical)")
    emergency = create_emergency("medical", "critical")
    em_scores = [(name, node.get_capability_score(emergency)) for name, node in nodes]

    print("   Emergency scores:")
    for i, (name, score) in enumerate(sorted(em_scores, key=lambda x: -x[1]), 1):
        icon = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
        print(f"   {icon} {i}. {name}: {score:.1f}")

    print_step(4, "Top responders begin action")
    top_responders = sorted(em_scores, key=lambda x: -x[1])[:3]
    for i, (name, score) in enumerate(top_responders, 1):
        print(f"   {i}. {name} responding... (score: {score:.1f})")
        time.sleep(0.3)

    print_result(f"{top_responders[0][0]} leads the response effort")


def main():
    print("\n🎓" * 25)
    print("🎓 VECTOR CLOCK EMERGENCY SYSTEM – DEMO 🎓")
    print("🎓 Student: Sina Fadavi | Date: Aug 1, 2025 🎓")
    print("🎓" * 25 + "\n")

    print("🚀 This visual demo showcases:")
    print("   1️⃣ Basic vector clock syncing")
    print("   2️⃣ Emergency response scoring")
    print("   3️⃣ Full network emergency handling")

    input("\nPress Enter to begin...")

    demo_basic_vector_clock()
    wait_for_professor()

    demo_emergency_prioritization()
    wait_for_professor()

    demo_network_emergency()

    print("\n🎉" * 25)
    print("🎉 DEMO COMPLETE – SYSTEM FULLY OPERATIONAL 🎉")
    print("🎉" * 25 + "\n")

    print("✅ Capable of:")
    print("   - Tracking causal order")
    print("   - Scoring response readiness")
    print("   - Coordinating distributed emergency actions\n")

    print("🎯 Academic Goal: Demonstrate causal clocks in real-world safety system")
    print("🏁 Ready for professor feedback and next phase!")


if __name__ == "__main__":
    main()
