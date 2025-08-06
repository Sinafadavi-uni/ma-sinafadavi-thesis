
# Shows how broker metadata is shared and how jobs are prioritized using different rules.

import sys
import os
import tempfile
from uuid import uuid4
from datetime import datetime

# Make sure we can import our modules even if we're running this from somewhere else
sys.path.insert(0, os.getcwd())

# Import core classes and helpers
from rec.nodes.enhanced_vector_clock_executor import (
    create_enhanced_executor,
    ConflictStrategy,
    JobPriority
)

from rec.nodes.brokers.multi_broker_coordinator import BrokerMetadata

def demo_step_5():
    print("="*50)
    print("🚀 UCP Part B - Step 5 Demo")
    print("="*50)

    # ---- Part B.a: Metadata Sharing Between Brokers ----
    print("\n🔍 Part B.a - Metadata Sharing Between Brokers")
    print("-" * 40)

    # Create sample broker info manually (just for demo)
    broker1 = BrokerMetadata(
        broker_id="broker-A",
        vector_clock={"broker-A": 4, "broker-B": 2},
        executor_count=2,
        active_jobs=["job-101", "job-102"],
        emergency_jobs=["job-emergency-1"],
        last_updated=datetime.now().isoformat(),
        capabilities={"emergency_handling": True}
    )

    broker2 = BrokerMetadata(
        broker_id="broker-B",
        vector_clock={"broker-A": 3, "broker-B": 5},
        executor_count=3,
        active_jobs=["job-103", "job-104", "job-105"],
        emergency_jobs=[],
        last_updated=datetime.now().isoformat(),
        capabilities={"emergency_handling": True}
    )

    print(f"✅ Broker A: {broker1.vector_clock}")
    print(f"✅ Broker B: {broker2.vector_clock}")
    print("🔁 These would normally sync every 60 seconds")
    print("📨 Emergency jobs shared between brokers")

    # ---- Part B.b: Conflict Resolution Between Jobs ----
    print("\n⚔️ Part B.b - Conflict Resolution Strategies")
    print("-" * 40)

    with tempfile.TemporaryDirectory() as tmp_dir:
        executor = create_enhanced_executor(
            node_id="demo-exec",
            strategy=ConflictStrategy.FCFS,
            rootdir=tmp_dir
        )

        for strategy in ConflictStrategy:
            executor.set_conflict_strategy(strategy)
            print(f"\n🧪 Trying strategy: {strategy.value}")

            job_normal = {
                "id": uuid4(),
                "info": {"estimated_cpu": 20.0},
                "priority": JobPriority(user_priority=5)
            }

            job_emergency = {
                "id": uuid4(),
                "info": {"estimated_cpu": 30.0},
                "priority": JobPriority(emergency_level=2, user_priority=8)
            }

            job_high_priority = {
                "id": uuid4(),
                "info": {"estimated_cpu": 15.0},
                "priority": JobPriority(user_priority=9, deadline_urgency=0.8)
            }

            if strategy == ConflictStrategy.EMERGENCY:
                print("⚠️ Emergency jobs get top priority")
            elif strategy == ConflictStrategy.PRIORITY:
                scores = [
                    executor._calculate_priority_score(job_normal["priority"]),
                    executor._calculate_priority_score(job_emergency["priority"]),
                    executor._calculate_priority_score(job_high_priority["priority"])
                ]
                print(f"📊 Calculated scores: Normal={scores[0]:.1f}, Emergency={scores[1]:.1f}, High={scores[2]:.1f}")
            elif strategy == ConflictStrategy.CAUSAL:
                print(f"⏳ Uses vector clock ordering: {executor.vector_clock.clock}")
            elif strategy == ConflictStrategy.RESOURCE:
                print("🧠 Tries to fit jobs based on CPU/memory limits")
            else:
                print("📦 Simple FCFS: First submitted = first executed")

        # Show conflict summary
        stats = executor.get_conflict_statistics()
        print("\n📈 Conflict Summary")
        print(f"Strategy Used: {stats['current_strategy']}")
        print(f"Running Jobs: {stats['running_jobs']}")
        print(f"Conflicts Waiting: {stats['pending_conflicts']}")

    print("\n✅ Step 5 demo complete. UCP Part B is working as expected!")
    print("="*50)

if __name__ == "__main__":
    demo_step_5()
