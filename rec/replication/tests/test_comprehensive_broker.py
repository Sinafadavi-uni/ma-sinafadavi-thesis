# 🧪 Full Test Run: Broker + Vector Clock Integration
# Student-coded test suite for Task 2
# Gonna check everything... hopefully nothing breaks

import sys
import time
from uuid import uuid4

# Kind of a dirty path append — but works for now
sys.path.append('/home/sina/Desktop/Related Work/pr/ma-sinafadavi')

from rec.model import Capabilities, JobInfo, Address
from rec.nodes.brokers.vector_clock_executor_broker import VectorClockExecutorBroker, EnhancedQueuedJob
from rec.nodes.brokers.vector_clock_broker import VectorClockBroker
from rec.nodetypes.executor import Executor


def test_basic_startup():
    print("🔧 Broker Init Test")
    print("-" * 40)
    results = []
    try:
        broker = VectorClockExecutorBroker(lambda j, i: results.append((j, i)))
        print(f"✅ Broker ID: {broker.node_id}")
        print(f"✅ Clock: {broker.vector_clock.clock}")
        print(f"✅ Emergency context: {broker.emergency_context}")
        assert len(broker.executors) == 0
        return True
    except Exception as e:
        print(f"❌ Failed broker startup: {e}")
        return False


def test_emergency_keywords():
    print("\n🚨 Emergency Keywords Check")
    print("-" * 40)
    broker = VectorClockExecutorBroker(lambda *_: None)
    test_cases = [
        ("fire_drill.wasm", True, "fire"),
        ("ambulance_job.wasm", True, "medical"),
        ("nothing_special.wasm", False, "none"),
    ]
    correct = 0
    for wasm, should_flag, typ in test_cases:
        info = JobInfo(wasm_bin=wasm,
                       capabilities=Capabilities(1, 512, 5),
                       result_addr=Address("localhost", 9000))
        flagged, found_type = broker._detect_emergency_job(info)
        if flagged == should_flag and (not should_flag or found_type == typ):
            print(f"✅ Detected: {wasm} → {found_type}")
            correct += 1
        else:
            print(f"❌ Mismatch on {wasm} (expected {typ}, got {found_type})")
    return correct == len(test_cases)


def test_priority_scores():
    print("\n📊 Job Priority Score Test")
    print("-" * 40)
    broker = VectorClockExecutorBroker(lambda *_: None)
    base_info = JobInfo("sample.wasm", Capabilities(1, 512, 5), Address("localhost", 9000))
    results = []
    for level, mult in [("critical", 10.0), ("fire", 7.0), ("none", 1.0)]:
        score = broker._calculate_job_priority(base_info, level != "none", level)
        expected = 1.0 * mult
        ok = abs(score - expected) < 0.1
        print(f"{'✅' if ok else '❌'} {level.title()} → Score: {score}")
        results.append(ok)
    return all(results)


def test_clock_ticks_consistently():
    print("\n⏰ Vector Clock Tick Test")
    print("-" * 40)
    broker = VectorClockExecutorBroker(lambda *_: None)
    initial = broker.vector_clock.clock.get(broker.node_id, 0)
    for i in range(5):
        broker.vector_clock.tick()
        current = broker.vector_clock.clock.get(broker.node_id, 0)
        if current != initial + i + 1:
            print(f"❌ Tick failed at step {i}: {current} ≠ {initial + i + 1}")
            return False
    print("✅ Clock ticked forward cleanly")
    return True


def test_job_queue_logic():
    print("\n📦 Job Queue Test")
    print("-" * 40)
    broker = VectorClockExecutorBroker(lambda *_: None)
    reg = JobInfo("regular_task.wasm", Capabilities(1, 256, 10), Address("localhost", 9000))
    emg = JobInfo("emergency_fire.wasm", Capabilities(2, 1024, 20), Address("localhost", 9000))
    rid, eid = uuid4(), uuid4()
    r_flag, r_type = broker._detect_emergency_job(reg)
    e_flag, e_type = broker._detect_emergency_job(emg)
    r_score = broker._calculate_job_priority(reg, r_flag, r_type)
    e_score = broker._calculate_job_priority(emg, e_flag, e_type)
    broker.queue_job_enhanced(rid, reg, set(), r_flag, r_type, r_score)
    broker.queue_job_enhanced(eid, emg, set(), e_flag, e_type, e_score)
    size = broker.queued_jobs.qsize()
    print(f"📝 Queue size: {size} → Scores: R={r_score}, E={e_score}")
    return size == 2 and e_score > r_score


def test_executor_capabilities():
    print("\n🖥️ Executor Capability Test")
    print("-" * 40)
    broker = VectorClockExecutorBroker(lambda *_: None)
    mock_id = uuid4()

    class FakeExecutor:
        def __init__(self):
            self.id = mock_id
            self.cur_caps = Capabilities(4, 4096, 80)
            self.last_update = time.time()
            self.submit_job = lambda *_: True

    broker.executors[mock_id] = FakeExecutor()
    low = Capabilities(1, 512, 10)
    high = Capabilities(10, 16000, 200)
    result_low = broker.capable_executor(low)
    result_high = broker.capable_executor(high)
    print(f"✅ Found low-capable exec: {result_low is not None}")
    print(f"✅ Rejected high-capable exec: {result_high is None}")
    return result_low is not None and result_high is None


def test_final_object_creation():
    print("\n🧱 Final Job Object Creation")
    print("-" * 40)
    broker = VectorClockExecutorBroker(lambda *_: None)
    job_id = uuid4()
    info = JobInfo("end_check.wasm", Capabilities(1, 256, 5), Address("localhost", 9000))
    job = EnhancedQueuedJob(
        job_id=job_id,
        job_info=info,
        wait_for=set(),
        vector_clock={str(broker.node_id): 2},
        is_emergency=False,
        emergency_type="none",
        priority_score=1.0
    )
    print(f"✅ Created job: {job.job_id} w/ clock: {job.vector_clock}")
    return isinstance(job, EnhancedQueuedJob)


def run_all_tests():
    print("🏁 Starting Comprehensive Tests")
    print("=" * 60)

    tests = [
        test_basic_startup,
        test_emergency_keywords,
        test_priority_scores,
        test_clock_ticks_consistently,
        test_job_queue_logic,
        test_executor_capabilities,
        test_final_object_creation,
    ]

    pass_count = 0
    for t in tests:
        try:
            if t():
                pass_count += 1
            time.sleep(0.25)
        except Exception as e:
            print(f"💥 Test {t.__name__} crashed: {e}")

    print("\n📋 Test Summary")
    print("=" * 60)
    print(f"✅ {pass_count}/{len(tests)} tests passed")

    if pass_count == len(tests):
        print("🎉 Everything passed! Broker integration is solid.")
    elif pass_count >= len(tests) * 0.7:
        print("⚠️ Most tests passed, but double-check a few things.")
    else:
        print("❌ Multiple issues — needs serious debugging.")


if __name__ == "__main__":
    run_all_tests()
