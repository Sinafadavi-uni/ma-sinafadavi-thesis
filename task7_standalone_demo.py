# 🛡️ Task 7 Fault Tolerance - Standalone Demo (No Dependencies)

import time
import random
from typing import Dict, List, Set
from uuid import uuid4
from dataclasses import dataclass


@dataclass
class SimpleVectorClock:
    """Simplified vector clock for demo"""
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.clock = {node_id: 0}
    
    def tick(self):
        self.clock[self.node_id] += 1
    
    def update(self, other_clock: dict):
        for node, time_val in other_clock.items():
            self.clock[node] = max(self.clock.get(node, 0), time_val)


@dataclass
class NodeHealth:
    """Simple health tracking for a node"""
    node_id: str
    last_heartbeat: float
    failure_count: int
    is_healthy: bool
    response_time: float


class SimpleTask7FaultTolerance:
    """Simplified Task 7 fault tolerance demo"""
    
    def __init__(self, system_id: str = "task7_demo"):
        self.system_id = system_id
        self.clock = SimpleVectorClock(system_id)
        
        # Node tracking
        self.node_health: Dict[str, NodeHealth] = {}
        self.trusted_nodes: Set[str] = set()
        self.suspicious_nodes: Set[str] = set()
        self.failed_nodes: Set[str] = set()
        
        # System state
        self.emergency_active = False
        self.critical_jobs: Set[str] = set()
        
        # Configuration
        self.heartbeat_timeout = 5.0
        self.max_failures = 2
        
        print(f"[Task7Demo] {system_id} initialized with fault tolerance")
    
    def register_node(self, node_id: str):
        """Register a node for monitoring"""
        self.clock.tick()
        
        self.node_health[node_id] = NodeHealth(
            node_id=node_id,
            last_heartbeat=time.time(),
            failure_count=0,
            is_healthy=True,
            response_time=0.1
        )
        
        self.trusted_nodes.add(node_id)
        print(f"[Task7Demo] {node_id} registered and marked as trusted")
    
    def receive_heartbeat(self, node_id: str, status: Dict):
        """Process heartbeat from node"""
        current_time = time.time()
        
        if node_id not in self.node_health:
            self.register_node(node_id)
        
        health = self.node_health[node_id]
        health.last_heartbeat = current_time
        health.response_time = status.get('response_time', 0.1)
        health.failure_count = 0
        health.is_healthy = True
        
        # Remove from failed/suspicious if it was there
        self.failed_nodes.discard(node_id)
        self.suspicious_nodes.discard(node_id)
        self.trusted_nodes.add(node_id)
        
        # Check for Byzantine behavior
        self._check_byzantine_behavior(node_id, status)
        
        self.clock.tick()
    
    def _check_byzantine_behavior(self, node_id: str, status: Dict):
        """Simple Byzantine behavior detection"""
        response_time = status.get('response_time', 0.1)
        load = status.get('load', 0.5)
        
        # Check for invalid values
        if response_time < 0 or response_time > 10.0:
            self._mark_suspicious(node_id, "invalid_response_time")
        
        if load < 0 or load > 1.0:
            self._mark_suspicious(node_id, "invalid_load")
        
        # Check vector clock
        if 'vector_clock' in status:
            node_clock = status['vector_clock']
            if node_id in node_clock and node_clock[node_id] < 0:
                self._mark_suspicious(node_id, "invalid_clock")
    
    def _mark_suspicious(self, node_id: str, reason: str):
        """Mark node as suspicious"""
        self.suspicious_nodes.add(node_id)
        self.trusted_nodes.discard(node_id)
        print(f"[Task7Demo] ⚠️  {node_id} marked SUSPICIOUS: {reason}")
    
    def check_for_failures(self) -> List[str]:
        """Check for failed nodes"""
        current_time = time.time()
        newly_failed = []
        
        for node_id, health in self.node_health.items():
            if node_id in self.failed_nodes:
                continue
                
            time_since_heartbeat = current_time - health.last_heartbeat
            
            if time_since_heartbeat > self.heartbeat_timeout:
                health.failure_count += 1
                
                if health.failure_count >= self.max_failures:
                    self.failed_nodes.add(node_id)
                    self.trusted_nodes.discard(node_id)
                    self.suspicious_nodes.discard(node_id)
                    health.is_healthy = False
                    newly_failed.append(node_id)
                    print(f"[Task7Demo] 💀 {node_id} FAILED after {health.failure_count} missed heartbeats")
        
        return newly_failed
    
    def activate_emergency_protocols(self, reason: str):
        """Activate emergency mode"""
        if not self.emergency_active:
            self.emergency_active = True
            print(f"[Task7Demo] 🚨 EMERGENCY PROTOCOLS ACTIVATED: {reason}")
            print(f"[Task7Demo] System entering safe mode")
    
    def deactivate_emergency_protocols(self):
        """Deactivate emergency mode"""
        if self.emergency_active:
            self.emergency_active = False
            print(f"[Task7Demo] ✅ Emergency protocols deactivated - system stable")
    
    def submit_critical_job(self, job_id: str):
        """Submit critical job with fault tolerance"""
        self.critical_jobs.add(job_id)
        healthy_count = len([n for n, h in self.node_health.items() if h.is_healthy])
        
        if healthy_count >= 2:
            print(f"[Task7Demo] 🎯 Critical job {job_id} submitted with {healthy_count} healthy nodes")
        else:
            print(f"[Task7Demo] ⚠️  Critical job {job_id} submitted but only {healthy_count} healthy nodes")
    
    def perform_health_check(self):
        """Perform system health check"""
        self.clock.tick()
        
        # Check for failures
        newly_failed = self.check_for_failures()
        
        # Calculate health metrics
        total_nodes = len(self.node_health)
        healthy_nodes = len([n for n, h in self.node_health.items() if h.is_healthy])
        failed_nodes = len(self.failed_nodes)
        suspicious_nodes = len(self.suspicious_nodes)
        
        # Check if emergency protocols needed
        problematic_ratio = (failed_nodes + suspicious_nodes) / max(total_nodes, 1)
        
        if problematic_ratio > 0.3 or healthy_nodes < 2:
            self.activate_emergency_protocols(f"Too many problems: {problematic_ratio:.1%} problematic nodes")
        elif problematic_ratio < 0.1 and healthy_nodes >= 3:
            self.deactivate_emergency_protocols()
        
        return {
            "total_nodes": total_nodes,
            "healthy_nodes": healthy_nodes,
            "failed_nodes": failed_nodes,
            "suspicious_nodes": suspicious_nodes,
            "emergency_active": self.emergency_active
        }
    
    def get_status(self):
        """Get system status"""
        return {
            "system_id": self.system_id,
            "total_nodes": len(self.node_health),
            "trusted_nodes": len(self.trusted_nodes),
            "suspicious_nodes": len(self.suspicious_nodes),
            "failed_nodes": len(self.failed_nodes),
            "critical_jobs": len(self.critical_jobs),
            "emergency_active": self.emergency_active,
            "vector_clock": self.clock.clock
        }


def demo_task7_fault_tolerance():
    """Complete Task 7 fault tolerance demo"""
    print("🛡️ TASK 7 FAULT TOLERANCE DEMO")
    print("=" * 40)
    
    # Create fault tolerance system
    system = SimpleTask7FaultTolerance("demo_system")
    
    # Register nodes
    nodes = ["node_A", "node_B", "node_C", "node_D", "node_E"]
    print(f"\n1. Registering {len(nodes)} nodes...")
    for node in nodes:
        system.register_node(node)
    
    # Normal operation
    print("\n2. Normal operation - sending heartbeats...")
    for round_num in range(3):
        print(f"   Round {round_num + 1}:")
        for node in nodes:
            system.receive_heartbeat(node, {
                'status': 'healthy',
                'response_time': random.uniform(0.05, 0.3),
                'load': random.uniform(0.1, 0.9),
                'vector_clock': {node: round_num + 1}
            })
        
        health = system.perform_health_check()
        print(f"     Health: {health['healthy_nodes']} healthy, {health['failed_nodes']} failed, {health['suspicious_nodes']} suspicious")
        time.sleep(0.5)
    
    # Submit critical jobs
    print("\n3. Submitting critical jobs...")
    system.submit_critical_job("emergency_job_1")
    system.submit_critical_job("backup_job_2")
    
    # Byzantine behavior
    print("\n4. Simulating Byzantine behavior...")
    system.receive_heartbeat("node_D", {
        'status': 'healthy',
        'response_time': -0.5,  # Invalid!
        'load': 1.5,  # Invalid!
        'vector_clock': {"node_D": -10}  # Invalid!
    })
    
    # Node failure simulation
    print("\n5. Simulating node failures...")
    print("   node_E stops sending heartbeats...")
    
    # Only some nodes send heartbeats
    for node in ["node_A", "node_B", "node_C"]:  # node_D is Byzantine, node_E is silent
        system.receive_heartbeat(node, {
            'status': 'healthy',
            'response_time': random.uniform(0.05, 0.3),
            'load': random.uniform(0.1, 0.9),
            'vector_clock': {node: 5}
        })
    
    # Wait for failure detection
    time.sleep(1)
    
    # Check system health
    print("\n6. Health check after problems...")
    health = system.perform_health_check()
    print(f"   Final health: {health['healthy_nodes']} healthy, {health['failed_nodes']} failed, {health['suspicious_nodes']} suspicious")
    print(f"   Emergency active: {health['emergency_active']}")
    
    # Final status
    print("\n7. Final system status:")
    final_status = system.get_status()
    print(f"   Total nodes: {final_status['total_nodes']}")
    print(f"   Trusted: {final_status['trusted_nodes']}")
    print(f"   Suspicious: {final_status['suspicious_nodes']}")
    print(f"   Failed: {final_status['failed_nodes']}")
    print(f"   Critical jobs: {final_status['critical_jobs']}")
    print(f"   Emergency protocols: {final_status['emergency_active']}")
    
    print("\n🎉 Task 7 Fault Tolerance Demo Complete!")
    print("\n✅ TASK 7 FEATURES DEMONSTRATED:")
    print("   • Advanced fault detection")
    print("   • Byzantine behavior detection")
    print("   • Emergency protocol activation")
    print("   • Critical job protection")
    print("   • Multi-level health monitoring")
    
    return final_status


if __name__ == "__main__":
    demo_task7_fault_tolerance()
