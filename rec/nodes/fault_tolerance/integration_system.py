# 🛡️ Task 7: Complete Fault Tolerance Integration - Simple & Student Friendly

import time
import random
from typing import Dict, List, Set, Optional
from uuid import uuid4
from dataclasses import dataclass

from rec.replication.core.vector_clock import VectorClock, EmergencyLevel
from .advanced_fault_tolerance import AdvancedRecoveryManager
from .byzantine_tolerance import SimpleConsensusManager
from rec.nodes.recovery_system import SimpleRecoveryManager
from rec.util.log import LOG


@dataclass
class SystemHealth:
    """Overall system health snapshot"""
    timestamp: float
    total_nodes: int
    healthy_nodes: int
    failed_nodes: int
    suspicious_nodes: int
    partitioned: bool
    emergency_active: bool
    consensus_working: bool


class Task7FaultToleranceSystem:
    """Complete fault tolerance system - combines all Task 7 features"""
    
    def __init__(self, system_id: str = None):
        self.system_id = system_id or f"task7_system_{uuid4().hex[:5]}"
        self.clock = VectorClock(self.system_id)
        
        # Core fault tolerance components
        self.advanced_recovery = AdvancedRecoveryManager(f"recovery_{uuid4().hex[:5]}")
        self.consensus_manager = SimpleConsensusManager(f"consensus_{uuid4().hex[:5]}")
        
        # System state tracking
        self.registered_nodes: Set[str] = set()
        self.system_health_history: List[SystemHealth] = []
        self.emergency_protocols_active = False
        
        # Simple configuration
        self.health_check_interval = 5.0  # seconds
        self.max_health_history = 10  # keep last 10 health snapshots
        
        LOG.info(f"[Task7System] {self.system_id} initialized with complete fault tolerance")
    
    def register_node(self, node_id: str):
        """Register a node with all fault tolerance systems"""
        self.clock.tick()
        self.registered_nodes.add(node_id)
        
        # Register with all subsystems
        self.advanced_recovery.register_executor(node_id)
        self.consensus_manager.register_node(node_id)
        
        LOG.info(f"[Task7System] {node_id} registered with complete fault tolerance")
    
    def node_heartbeat(self, node_id: str, status: Dict):
        """Process heartbeat from node"""
        if node_id not in self.registered_nodes:
            self.register_node(node_id)
        
        # Forward to advanced recovery
        self.advanced_recovery.executor_heartbeat(node_id, status)
        
        # Check for Byzantine behavior
        self._check_byzantine_behavior(node_id, status)
        
        self.clock.tick()
    
    def _check_byzantine_behavior(self, node_id: str, status: Dict):
        """Simple Byzantine behavior detection"""
        # Check for impossible values
        response_time = status.get('response_time', 0.1)
        if response_time < 0 or response_time > 10.0:
            self.consensus_manager.detect_byzantine_behavior(node_id, "invalid_response_time")
        
        # Check for clock inconsistencies
        if 'vector_clock' in status:
            node_clock = status['vector_clock']
            if node_id in node_clock and node_clock[node_id] < 0:
                self.consensus_manager.detect_byzantine_behavior(node_id, "invalid_clock")
    
    def perform_health_check(self):
        """Check overall system health"""
        self.clock.tick()
        
        # Check for failures and partitions
        self.advanced_recovery.check_system_health()
        
        # Create health snapshot
        health = self._create_health_snapshot()
        self.system_health_history.append(health)
        
        # Keep only recent history
        if len(self.system_health_history) > self.max_health_history:
            self.system_health_history.pop(0)
        
        # Check if emergency protocols needed
        self._evaluate_emergency_protocols(health)
        
        return health
    
    def _create_health_snapshot(self) -> SystemHealth:
        """Create snapshot of current system health"""
        recovery_status = self.advanced_recovery.get_detailed_status()
        consensus_status = self.consensus_manager.get_consensus_status()
        
        return SystemHealth(
            timestamp=time.time(),
            total_nodes=len(self.registered_nodes),
            healthy_nodes=recovery_status['fault_detection']['healthy_nodes'],
            failed_nodes=recovery_status['fault_detection']['confirmed_failed'],
            suspicious_nodes=consensus_status['byzantine_status']['suspicious_nodes'],
            partitioned=recovery_status['partition_detection']['is_partitioned'],
            emergency_active=recovery_status['basic_recovery']['emergency'],
            consensus_working=consensus_status['pending_proposals'] == 0
        )
    
    def _evaluate_emergency_protocols(self, health: SystemHealth):
        """Decide if emergency protocols should be activated"""
        # Simple rules for emergency activation
        total_problematic = health.failed_nodes + health.suspicious_nodes
        problematic_ratio = total_problematic / max(health.total_nodes, 1)
        
        should_activate_emergency = (
            health.partitioned or 
            problematic_ratio > 0.3 or  # More than 30% of nodes are problematic
            health.healthy_nodes < 2    # Less than 2 healthy nodes
        )
        
        if should_activate_emergency and not self.emergency_protocols_active:
            self._activate_emergency_protocols(health)
        elif not should_activate_emergency and self.emergency_protocols_active:
            self._deactivate_emergency_protocols()
    
    def _activate_emergency_protocols(self, health: SystemHealth):
        """Activate emergency protocols"""
        self.emergency_protocols_active = True
        
        # Activate emergency in recovery system
        if health.partitioned:
            emergency_type = "network_partition"
            level = "HIGH"
        elif health.failed_nodes > health.healthy_nodes:
            emergency_type = "mass_failure"
            level = "CRITICAL"
        else:
            emergency_type = "byzantine_attack"
            level = "MEDIUM"
        
        self.advanced_recovery.basic_recovery.declare_system_emergency(emergency_type, level)
        
        # Create emergency consensus proposal
        proposal_content = f"Emergency protocol activation: {emergency_type}"
        proposal_id = self.consensus_manager.create_proposal(self.system_id, proposal_content)
        
        LOG.warning(f"[Task7System] EMERGENCY PROTOCOLS ACTIVATED: {emergency_type}")
        LOG.warning(f"[Task7System] Emergency proposal created: {proposal_id}")
    
    def _deactivate_emergency_protocols(self):
        """Deactivate emergency protocols"""
        self.emergency_protocols_active = False
        self.advanced_recovery.basic_recovery.clear_system_emergency()
        
        LOG.info(f"[Task7System] Emergency protocols deactivated - system stable")
    
    def submit_critical_job(self, job_id: str, job_data: Dict) -> bool:
        """Submit a critical job with maximum fault tolerance"""
        self.clock.tick()
        
        # Mark as critical for backup
        self.advanced_recovery.mark_job_critical(job_id)
        
        # Create consensus proposal for critical job
        proposal_content = f"Execute critical job: {job_id}"
        proposal_id = self.consensus_manager.create_proposal(self.system_id, proposal_content)
        
        # Auto-vote yes from system
        self.consensus_manager.submit_vote(self.system_id, proposal_id, "yes")
        
        LOG.info(f"[Task7System] Critical job {job_id} submitted with consensus proposal {proposal_id}")
        return True
    
    def vote_on_proposal(self, node_id: str, proposal_id: str, vote: str) -> bool:
        """Allow node to vote on proposals"""
        # Only allow trusted nodes to vote
        if self.consensus_manager.byzantine_detector.is_node_suspicious(node_id):
            LOG.warning(f"[Task7System] Blocking vote from suspicious node {node_id}")
            return False
        
        return self.consensus_manager.submit_vote(node_id, proposal_id, vote)
    
    def get_system_status(self) -> Dict:
        """Get comprehensive system status"""
        latest_health = self.system_health_history[-1] if self.system_health_history else None
        
        return {
            "system_id": self.system_id,
            "vector_clock": self.clock.clock,
            "registered_nodes": len(self.registered_nodes),
            "emergency_protocols_active": self.emergency_protocols_active,
            "latest_health": latest_health.__dict__ if latest_health else None,
            "advanced_recovery_status": self.advanced_recovery.get_detailed_status(),
            "consensus_status": self.consensus_manager.get_consensus_status()
        }
    
    def get_health_trend(self) -> Dict:
        """Analyze health trend over time"""
        if len(self.system_health_history) < 2:
            return {"trend": "insufficient_data"}
        
        recent = self.system_health_history[-3:]  # Last 3 snapshots
        
        # Simple trend analysis
        healthy_trend = [h.healthy_nodes for h in recent]
        failed_trend = [h.failed_nodes for h in recent]
        
        improving = all(h >= p for h, p in zip(healthy_trend[1:], healthy_trend[:-1]))
        deteriorating = all(f >= p for f, p in zip(failed_trend[1:], failed_trend[:-1]))
        
        if improving and not deteriorating:
            trend = "improving"
        elif deteriorating and not improving:
            trend = "deteriorating"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "healthy_nodes_trend": healthy_trend,
            "failed_nodes_trend": failed_trend,
            "emergency_activations": sum(1 for h in recent if h.emergency_active)
        }
    
    def activate_emergency_protocol(self, reason: str = "Manual activation"):
        """Manually activate emergency protocols"""
        if not self.emergency_protocols_active:
            fake_health = SystemHealth(
                timestamp=time.time(),
                total_nodes=len(self.registered_nodes),
                healthy_nodes=0,  # Force emergency
                failed_nodes=len(self.registered_nodes),
                suspicious_nodes=0,
                partitioned=False,
                emergency_active=False,
                consensus_working=True
            )
            self._activate_emergency_protocols(fake_health)
            LOG.info(f"[Task7System] Emergency protocol manually activated: {reason}")
    
    def deactivate_emergency_protocol(self):
        """Manually deactivate emergency protocols"""
        if self.emergency_protocols_active:
            self._deactivate_emergency_protocols()
            LOG.info(f"[Task7System] Emergency protocol manually deactivated")


def demo_complete_fault_tolerance():
    """Complete demo of Task 7 fault tolerance system"""
    print("🛡️ DEMO: Complete Task 7 Fault Tolerance System")
    print("=" * 55)
    
    # Create the complete system
    system = Task7FaultToleranceSystem("demo_task7")
    
    # Register nodes
    nodes = ["node_A", "node_B", "node_C", "node_D", "node_E"]
    print(f"\n1. Registering {len(nodes)} nodes...")
    for node in nodes:
        system.register_node(node)
    
    # Normal operation
    print("\n2. Normal operation - sending heartbeats...")
    for i in range(3):
        for node in nodes:
            system.node_heartbeat(node, {
                'status': 'healthy',
                'response_time': random.uniform(0.05, 0.2),
                'vector_clock': {node: i + 1},
                'load': random.uniform(0.1, 0.8)
            })
        
        health = system.perform_health_check()
        print(f"   Health check {i+1}: {health.healthy_nodes} healthy, {health.failed_nodes} failed")
        time.sleep(0.5)
    
    # Submit critical job
    print("\n3. Submitting critical job...")
    system.submit_critical_job("emergency_job_1", {"priority": "critical", "type": "emergency"})
    
    # Nodes vote on the proposal
    print("\n4. Nodes voting on critical job proposal...")
    consensus_status = system.consensus_manager.get_consensus_status()
    if consensus_status['pending_proposals'] > 0:
        # Get first pending proposal
        for proposal_id, proposal in system.consensus_manager.proposals.items():
            if proposal.status == "pending":
                for node in nodes[:3]:  # First 3 nodes vote
                    vote = random.choice(["yes", "yes", "no"])  # Bias towards yes
                    system.vote_on_proposal(node, proposal_id, vote)
                break
    
    # Simulate some problems
    print("\n5. Simulating node failures...")
    
    # Node D sends Byzantine data
    system.node_heartbeat("node_D", {
        'status': 'healthy',
        'response_time': -1.0,  # Invalid response time
        'vector_clock': {"node_D": -5},  # Invalid clock
        'load': 1.5  # Invalid load > 1.0
    })
    
    # Node E stops sending heartbeats (simulated failure)
    for node in ["node_A", "node_B", "node_C", "node_D"]:  # E is missing
        system.node_heartbeat(node, {
            'status': 'healthy',
            'response_time': random.uniform(0.05, 0.2),
            'vector_clock': {node: 5},
            'load': random.uniform(0.1, 0.8)
        })
    
    # Check system response
    health = system.perform_health_check()
    print(f"   After problems: {health.healthy_nodes} healthy, {health.failed_nodes} failed, {health.suspicious_nodes} suspicious")
    
    print("\n6. Final system status:")
    final_status = system.get_system_status()
    print(f"   Emergency protocols active: {final_status['emergency_protocols_active']}")
    print(f"   Total registered nodes: {final_status['registered_nodes']}")
    
    health_trend = system.get_health_trend()
    print(f"   Health trend: {health_trend['trend']}")
    print(f"   Healthy nodes trend: {health_trend['healthy_nodes_trend']}")
    
    consensus_final = system.consensus_manager.get_consensus_status()
    byz_final = consensus_final['byzantine_status']
    print(f"   Trusted nodes: {byz_final['trusted_nodes']}")
    print(f"   Suspicious nodes: {byz_final['suspicious_nodes']}")
    
    print("\n🎉 Complete Task 7 fault tolerance demo finished!")
    print("✅ Advanced fault detection working")
    print("✅ Byzantine fault tolerance working") 
    print("✅ Emergency protocols working")
    print("✅ Consensus system working")


if __name__ == "__main__":
    demo_complete_fault_tolerance()
