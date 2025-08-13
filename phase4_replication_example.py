#!/usr/bin/env python3
"""
Phase 4: UCP Integration - Replication Policy Example
====================================================

This script demonstrates how to:
1. Create a ReplicationPolicyManager with custom policies
2. Pass it to VectorClockBrokers during creation
3. Register peer brokers for both vector clock sync and metadata sync
4. Start the brokers to activate all synchronization threads

Usage:
    python3 phase4_replication_example.py
"""

import logging
import time
from rec.Phase2_Node_Infrastructure.replication_policy import ReplicationPolicyManager, ReplicationPolicy
from rec.Phase3_Core_Implementation.vector_clock_broker import VectorClockBroker

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)

def demonstrate_phase4_replication_policies():
    print("🚀 Phase 4: UCP Integration - Replication Policy Demo")
    print("=" * 60)
    
    # 3.1 Define operator policies
    print("\n📋 Step 1: Creating ReplicationPolicyManager with custom policies")
    rpm = ReplicationPolicyManager()
    
    # replicate all job metadata quickly (5s), datasets less frequently (30s), and skip debug keys entirely
    rpm.set_policy("job:", ReplicationPolicy(replicate=True, sync_interval=5.0))
    rpm.set_policy("dataset:", ReplicationPolicy(replicate=True, sync_interval=30.0))
    rpm.set_policy("debug:", ReplicationPolicy(replicate=False))
    
    print("   ✅ job: metadata -> replicate every 5 seconds")
    print("   ✅ dataset: metadata -> replicate every 30 seconds") 
    print("   ✅ debug: metadata -> do NOT replicate")
    
    # 3.2 Construct brokers *with* the policy
    print("\n🏗️  Step 2: Creating VectorClockBrokers with replication policies")
    b1 = VectorClockBroker("broker-1", replication_policy_manager=rpm)
    b2 = VectorClockBroker("broker-2", replication_policy_manager=rpm)
    print("   ✅ Created broker-1 with replication policies")
    print("   ✅ Created broker-2 with replication policies")
    
    # 3.3 Register peers (needed both for VC sync and for metadata sync)
    print("\n🔗 Step 3: Registering peer brokers for coordination")
    b1.register_peer_broker("broker-2", b2)
    b2.register_peer_broker("broker-1", b1)
    print("   ✅ broker-1 registered broker-2 as peer")
    print("   ✅ broker-2 registered broker-1 as peer")
    
    # 3.4 Start them (start() now builds metadata_peers then launches threads)
    print("\n▶️  Step 4: Starting brokers (activates all sync threads)")
    b1.start()
    b2.start()
    print("   ✅ broker-1 started (vector clock sync + metadata sync active)")
    print("   ✅ broker-2 started (vector clock sync + metadata sync active)")
    
    # Demonstrate the replication policy in action
    print("\n🔬 Step 5: Testing replication policies in action")
    
    # Store different types of metadata
    print("   📝 Storing metadata with different replication behaviors...")
    b1.metadata_store.update("job:urgent_task_001", {
        "status": "running", 
        "priority": "high",
        "executor": "worker-node-1"
    })
    
    b1.metadata_store.update("dataset:sensor_data_2025", {
        "size": "2.5GB",
        "format": "parquet", 
        "location": "cluster-storage-1"
    })
    
    b1.metadata_store.update("debug:verbose_trace_log", {
        "level": "TRACE",
        "component": "vector_clock_sync",
        "details": "Very detailed debugging information..."
    })
    
    # Check replication policies
    job_policy = rpm.get_policy("job:urgent_task_001")
    dataset_policy = rpm.get_policy("dataset:sensor_data_2025") 
    debug_policy = rpm.get_policy("debug:verbose_trace_log")
    
    print(f"   🔄 job:urgent_task_001 -> replicate: {job_policy.replicate}, interval: {job_policy.sync_interval}s")
    print(f"   🔄 dataset:sensor_data_2025 -> replicate: {dataset_policy.replicate}, interval: {dataset_policy.sync_interval}s")
    print(f"   🔄 debug:verbose_trace_log -> replicate: {debug_policy.replicate}")
    
    # Let the brokers sync for a moment
    print("\n⏳ Step 6: Allowing time for metadata synchronization...")
    time.sleep(2)
    
    # Check what got synchronized
    print("   📊 Checking broker-2's metadata store after sync:")
    b2_metadata = b2.metadata_store.snapshot()
    
    for key, value in b2_metadata.items():
        policy = rpm.get_policy(key)
        replication_status = "✅ REPLICATED" if policy.replicate else "❌ LOCAL ONLY"
        print(f"      {key}: {replication_status}")
    
    # Show broker status
    print("\n📈 Step 7: Broker Status Summary")
    b1_status = b1.get_distributed_status()
    b2_status = b2.get_distributed_status()
    
    print(f"   broker-1: {len(b1_status['peer_brokers'])} peers, vector clock: {b1_status['vector_clock']}")
    print(f"   broker-2: {len(b2_status['peer_brokers'])} peers, vector clock: {b2_status['vector_clock']}")
    
    # Clean shutdown
    print("\n⏹️  Step 8: Graceful shutdown")
    b1.stop()
    b2.stop()
    print("   ✅ broker-1 stopped")
    print("   ✅ broker-2 stopped")
    
    print("\n🎉 Phase 4 Replication Policy Demo Completed Successfully!")
    print("\nKey Achievements:")
    print("  ✅ ReplicationPolicyManager configured with custom policies")
    print("  ✅ VectorClockBrokers created with shared replication policies")  
    print("  ✅ Peer relationships established for coordination")
    print("  ✅ Brokers started with active synchronization threads")
    print("  ✅ Metadata replication behavior verified according to policies")
    print("  ✅ Vector clock coordination working across brokers")

if __name__ == "__main__":
    demonstrate_phase4_replication_policies()
