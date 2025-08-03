# 🚀 Vector Clock Broker Test Script
# Trying out Task 2 features without causing chaos

import sys
import time
from uuid import uuid4

# Just force-add the root to the path — yeah it's a bit hacky
sys.path.append('/home/sina/Desktop/Related Work/pr/ma-sinafadavi')

from rec.model import Capabilities, JobInfo, Address
from rec.nodes.brokers.vector_clock_executor_broker import VectorClockExecutorBroker


def test_vector_broker_basics():
    """
    Just a general test to make sure the new broker doesn't crash
    and actually does the clock/emergency stuff
    """
    print("🔬 Starting vector clock broker basic test")
    print("-" * 60)

    started = []

    def fake_start_callback(job_id, job_info):
        started.append((job_id, job_info))
        print(f"✅ Callback: Job {job_id} has started")

    print("🛠️  Creating broker...")
    broker = VectorClockExecutorBroker(fake_start_callback)
    print(f"   Node ID: {broker.node_id}")
    print(f"   Initial clock: {broker.vector_clock.clock}")

    print("\n⏱️  Testing vector clock tick")
    before = broker.vector_clock.clock.copy()
    broker.vector_clock.tick()
    after = broker.vector_clock.clock.copy()

    print(f"   Clock before tick: {before}")
    print(f"   Clock after tick : {after}")

    if before != after:
        print("   ✅ Tick works as expected")
    else:
        print("   ❌ Clock didn’t change!")

    print("\n🚨 Checking emergency detection logic")

    reg_job = JobInfo(
        wasm_bin="normal_job.wasm",
        capabilities=Capabilities(cpu_cores=1, memory=512, power=10),
        result_addr=Address(host="localhost", port=5000)
    )

    emg_job = JobInfo(
        wasm_bin="emergency_handler.wasm",
        capabilities=Capabilities(cpu_cores=2, memory=2048, power=90),
        result_addr=Address(host="localhost", port=5000)
    )

    reg_emg, reg_type = broker._detect_emergency_job(reg_job)
    emg_emg, emg_type = broker._detect_emergency_job(emg_job)

    print(f"   Regular job: {reg_emg} (type: {reg_type})")
    print(f"   Emergency job: {emg_emg} (type: {emg_type})")

    print("\n📊 Testing priority scoring")

    reg_score = broker._calculate_job_priority(reg_job, reg_emg, reg_type)
    emg_score = broker._calculate_job_priority(emg_job, emg_emg, emg_type)

    print(f"   Score for regular: {reg_score}")
    print(f"   Score for emergency: {emg_score}")

    if emg_score > reg_score:
        print("   ✅ Emergency job gets a bigger score")
    else:
        print("   ❌ Something's off with scoring logic")

    print("\n📦 Queuing jobs manually")

    job1_id = uuid4()
    job2_id = uuid4()

    broker.queue_job_enhanced(job1_id, reg_job, set(), reg_emg, reg_type, reg_score)
    broker.queue_job_enhanced(job2_id, emg_job, set(), emg_emg, emg_type, emg_score)

    print(f"   Added job {job1_id} (regular)")
    print(f"   Added job {job2_id} (emergency)")
    print(f"   Queue size now: {broker.queued_jobs.qsize()}")

    if broker.queued_jobs.qsize() == 2:
        print("   ✅ Queuing logic works")
    else:
        print("   ❌ Jobs not getting queued properly")

    print("\n🎉 Basic test complete!")
    return True


def test_clock_progression():
    """
    Sanity check to make sure the vector clock actually increments across steps
    """
    print("\n🔄 Starting clock sync test")
    print("-" * 50)

    def noop_cb(job_id, job_info): pass

    broker = VectorClockExecutorBroker(noop_cb)
    start_val = broker.vector_clock.clock.get(broker.node_id, 0)

    print(f"   Initial clock value: {start_val}")

    operations = ["tick_heartbeat", "tick_submit", "tick_done", "tick_emergency"]

    for idx, label in enumerate(operations):
        broker.vector_clock.tick()
        new_val = broker.vector_clock.clock.get(broker.node_id, 0)
        print(f"   After {label}: {new_val}")

        if new_val != start_val + idx + 1:
            print(f"   ❌ Clock sync failed on {label}")
            return False

    print("   ✅ Clock progression looks good!")
    return True


if __name__ == "__main__":
    print("🧪 Student-Level Integration Test: Vector Clock Broker")
    print("=" * 60)

    try:
        if test_vector_broker_basics():
            if test_clock_progression():
                print("\n🏁 All checks passed — time to try integration with services!")
            else:
                print("\n💥 Clock test failed")
        else:
            print("\n💥 Basic broker test failed")

    except Exception as err:
        print(f"\n😵 Test crashed: {err}")
        print("   Check your code, probably broke something")
