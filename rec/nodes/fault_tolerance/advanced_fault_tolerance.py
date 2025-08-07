# 🛡️ Task 7: Advanced Fault Tolerance - Simple Student Implementation

import time
import random
from typing import Dict, List, Set
from uuid import uuid4, UUID
from dataclasses import dataclass

from rec.replication.core.vector_clock import VectorClock, EmergencyLevel
from rec.nodes.recovery_system import SimpleRecoveryManager
from rec.util.log import LOG


@dataclass
class NodeHealth:
    """Simple health tracking for a node"""
    node_id: str
    last_heartbeat: float
    failure_count: int
    is_healthy: bool
    response_time: float


@dataclass
class NetworkPartition:
    """Simple representation of network partition"""
    partition_id: str
    nodes: Set[str]
    created_at: float
    is_isolated: bool


class SimpleFaultDetector:
    """Easy fault detection - detects when nodes go down"""
    
    def __init__(self, detector_id: str = None):
        self.detector_id = detector_id or f"detector_{uuid4().hex[:5]}"
        self.clock = VectorClock(self.detector_id)
        
        # Simple settings - student can easily understand
        self.heartbeat_timeout = 10.0  # seconds
        self.max_failures = 3  # failures before marking as dead
        
        # Keep track of all nodes we know about
        self.node_health: Dict[str, NodeHealth] = {}
        self.suspected_failed: Set[str] = set()
        self.confirmed_failed: Set[str] = set()
        
        LOG.info(f"[FaultDetector] {self.detector_id} started")
    
    def register_node(self, node_id: str):
        """Add a new node to monitor"""
        self.clock.tick()
        
        self.node_health[node_id] = NodeHealth(
            node_id=node_id,
            last_heartbeat=time.time(),
            failure_count=0,
            is_healthy=True,
            response_time=0.1  # default 100ms
        )
        
        LOG.info(f"[FaultDetector] Now monitoring {node_id}")
    
    def receive_heartbeat(self, node_id: str, response_time: float = 0.1):
        """Node sent us a heartbeat - it's alive!"""
        current_time = time.time()
        
        if node_id not in self.node_health:
            self.register_node(node_id)
        
        health = self.node_health[node_id]
        health.last_heartbeat = current_time
        health.response_time = response_time
        health.failure_count = 0  # reset failure count
        health.is_healthy = True
        
        # Remove from suspected/failed lists
        self.suspected_failed.discard(node_id)
        self.confirmed_failed.discard(node_id)
        
        self.clock.tick()
    
    def check_for_failures(self) -> List[str]:
        """Check if any nodes have failed - returns list of failed nodes"""
        current_time = time.time()
        newly_failed = []
        
        for node_id, health in self.node_health.items():
            time_since_heartbeat = current_time - health.last_heartbeat
            
            # Node is taking too long to respond
            if time_since_heartbeat > self.heartbeat_timeout:
                health.failure_count += 1
                
                # First failure - just suspect it
                if health.failure_count == 1:
                    self.suspected_failed.add(node_id)
                    LOG.warning(f"[FaultDetector] {node_id} suspected failed (no heartbeat for {time_since_heartbeat:.1f}s)")
                
                # Too many failures - declare it dead
                elif health.failure_count >= self.max_failures:
                    if node_id not in self.confirmed_failed:
                        self.confirmed_failed.add(node_id)
                        health.is_healthy = False
                        newly_failed.append(node_id)
                        LOG.error(f"[FaultDetector] {node_id} CONFIRMED FAILED after {health.failure_count} failures")
        
        return newly_failed
    
    def get_healthy_nodes(self) -> List[str]:
        """Get list of all healthy nodes"""
        return [node_id for node_id, health in self.node_health.items() 
                if health.is_healthy and node_id not in self.confirmed_failed]
    
    def get_failed_nodes(self) -> List[str]:
        """Get list of all failed nodes"""
        return list(self.confirmed_failed)
    
    def get_status(self) -> Dict:
        """Get simple status report"""
        return {
            "detector_id": self.detector_id,
            "total_nodes": len(self.node_health),
            "healthy_nodes": len(self.get_healthy_nodes()),
            "suspected_failed": len(self.suspected_failed),
            "confirmed_failed": len(self.confirmed_failed),
            "vector_clock": self.clock.clock
        }


class SimplePartitionDetector:
    """Detects when network gets split into parts"""
    
    def __init__(self, detector_id: str = None):
        self.detector_id = detector_id or f"partition_{uuid4().hex[:5]}"
        self.clock = VectorClock(self.detector_id)
        
        # Simple partition tracking
        self.known_nodes: Set[str] = set()
        self.reachable_nodes: Set[str] = set()
        self.partitions: Dict[str, NetworkPartition] = {}
        self.current_partition_id = None
        
        LOG.info(f"[PartitionDetector] {self.detector_id} started")
    
    def add_known_node(self, node_id: str):
        """Add a node we should be able to reach"""
        self.known_nodes.add(node_id)
        self.reachable_nodes.add(node_id)
        LOG.info(f"[PartitionDetector] Added {node_id} to known nodes")
    
    def update_reachable_nodes(self, reachable: List[str]):
        """Update which nodes we can currently reach"""
        self.clock.tick()
        self.reachable_nodes = set(reachable)
        
        # Check if we're in a partition
        unreachable = self.known_nodes - self.reachable_nodes
        
        if unreachable:
            self._detect_partition(unreachable)
        else:
            self._clear_partition()
    
    def _detect_partition(self, unreachable_nodes: Set[str]):
        """We found a network partition!"""
        if not self.current_partition_id:
            self.current_partition_id = f"partition_{uuid4().hex[:5]}"
            
            partition = NetworkPartition(
                partition_id=self.current_partition_id,
                nodes=self.reachable_nodes.copy(),
                created_at=time.time(),
                is_isolated=len(self.reachable_nodes) < len(self.known_nodes) / 2
            )
            
            self.partitions[self.current_partition_id] = partition
            
            LOG.warning(f"[PartitionDetector] NETWORK PARTITION detected!")
            LOG.warning(f"[PartitionDetector] Reachable: {self.reachable_nodes}")
            LOG.warning(f"[PartitionDetector] Unreachable: {unreachable_nodes}")
    
    def _clear_partition(self):
        """Network is healed - all nodes reachable"""
        if self.current_partition_id:
            LOG.info(f"[PartitionDetector] Network partition HEALED")
            self.current_partition_id = None
    
    def is_partitioned(self) -> bool:
        """Are we currently in a network partition?"""
        return self.current_partition_id is not None
    
    def get_partition_info(self) -> Dict:
        """Get info about current partition state"""
        return {
            "detector_id": self.detector_id,
            "is_partitioned": self.is_partitioned(),
            "current_partition": self.current_partition_id,
            "known_nodes": len(self.known_nodes),
            "reachable_nodes": len(self.reachable_nodes),
            "unreachable_nodes": len(self.known_nodes - self.reachable_nodes),
            "vector_clock": self.clock.clock
        }


class AdvancedRecoveryManager:
    """Enhanced recovery with better fault tolerance"""
    
    def __init__(self, manager_id: str = None):
        self.manager_id = manager_id or f"advanced_recovery_{uuid4().hex[:5]}"
        self.clock = VectorClock(self.manager_id)
        
        # Use the simple recovery as base
        self.basic_recovery = SimpleRecoveryManager(f"basic_{uuid4().hex[:5]}")
        
        # Add advanced fault tolerance
        self.fault_detector = SimpleFaultDetector(f"fault_{uuid4().hex[:5]}")
        self.partition_detector = SimplePartitionDetector(f"part_{uuid4().hex[:5]}")
        
        # Simple job tracking
        self.critical_jobs: Set[str] = set()
        self.job_backup_copies: Dict[str, List[str]] = {}  # job_id -> [executor_ids]
        
        LOG.info(f"[AdvancedRecovery] {self.manager_id} started with enhanced fault tolerance")
    
    def register_executor(self, executor_id: str):
        """Register executor with advanced monitoring"""
        self.clock.tick()
        
        # Register with basic recovery
        self.basic_recovery.register_executor(executor_id)
        
        # Add to fault detector
        self.fault_detector.register_node(executor_id)
        self.partition_detector.add_known_node(executor_id)
        
        LOG.info(f"[AdvancedRecovery] {executor_id} registered with enhanced monitoring")
    
    def executor_heartbeat(self, executor_id: str, status: Dict):
        """Receive heartbeat with advanced processing"""
        # Update basic recovery
        self.basic_recovery.executor_heartbeat(executor_id, status)
        
        # Update fault detector
        response_time = status.get('response_time', 0.1)
        self.fault_detector.receive_heartbeat(executor_id, response_time)
        
        self.clock.tick()
    
    def check_system_health(self):
        """Check for failures and partitions"""
        # Check for failed nodes
        newly_failed = self.fault_detector.check_for_failures()
        
        for failed_node in newly_failed:
            LOG.warning(f"[AdvancedRecovery] Handling failure of {failed_node}")
            self._handle_node_failure(failed_node)
        
        # Update partition detector with current reachable nodes
        healthy_nodes = self.fault_detector.get_healthy_nodes()
        self.partition_detector.update_reachable_nodes(healthy_nodes)
        
        # Handle partition if detected
        if self.partition_detector.is_partitioned():
            self._handle_network_partition()
    
    def _handle_node_failure(self, failed_node: str):
        """Handle when a node fails"""
        # Mark as failed in basic recovery
        failed_jobs = self.job_backup_copies.get(failed_node, [])
        self.basic_recovery.mark_executor_failed(failed_node, failed_jobs)
        
        # Find critical jobs that need immediate backup
        for job_id in self.critical_jobs:
            if failed_node in self.job_backup_copies.get(job_id, []):
                self._create_job_backup(job_id)
    
    def _handle_network_partition(self):
        """Handle network partition situation"""
        partition_info = self.partition_detector.get_partition_info()
        
        LOG.warning(f"[AdvancedRecovery] Operating in network partition")
        LOG.warning(f"[AdvancedRecovery] Reachable nodes: {partition_info['reachable_nodes']}")
        
        # In partition mode - be more conservative
        # Only assign critical jobs to ensure they complete
        healthy_nodes = self.fault_detector.get_healthy_nodes()
        if len(healthy_nodes) >= 2:  # Need at least 2 nodes for backup
            LOG.info(f"[AdvancedRecovery] Continuing with {len(healthy_nodes)} healthy nodes")
        else:
            LOG.warning(f"[AdvancedRecovery] Too few healthy nodes ({len(healthy_nodes)}) - entering safe mode")
    
    def mark_job_critical(self, job_id: str):
        """Mark a job as critical - needs extra protection"""
        self.critical_jobs.add(job_id)
        self._create_job_backup(job_id)
        LOG.info(f"[AdvancedRecovery] Job {job_id} marked as CRITICAL")
    
    def _create_job_backup(self, job_id: str):
        """Create backup copies of critical job"""
        healthy_nodes = self.fault_detector.get_healthy_nodes()
        
        if len(healthy_nodes) >= 2:
            # Pick 2 random healthy nodes for backup
            backup_nodes = random.sample(healthy_nodes, min(2, len(healthy_nodes)))
            self.job_backup_copies[job_id] = backup_nodes
            LOG.info(f"[AdvancedRecovery] Created backup for job {job_id} on {backup_nodes}")
    
    def get_detailed_status(self) -> Dict:
        """Get comprehensive status of advanced recovery system"""
        return {
            "manager_id": self.manager_id,
            "vector_clock": self.clock.clock,
            "basic_recovery": self.basic_recovery.get_status(),
            "fault_detection": self.fault_detector.get_status(),
            "partition_detection": self.partition_detector.get_partition_info(),
            "critical_jobs": len(self.critical_jobs),
            "job_backups": len(self.job_backup_copies)
        }


def demo_advanced_fault_tolerance():
    """Simple demo of advanced fault tolerance"""
    print("🛡️ DEMO: Advanced Fault Tolerance System")
    print("=" * 50)
    
    # Create advanced recovery manager
    recovery = AdvancedRecoveryManager("demo_recovery")
    
    # Register some executors
    executors = ["exec_1", "exec_2", "exec_3", "exec_4"]
    for exec_id in executors:
        recovery.register_executor(exec_id)
    
    print("\n1. Initial system status:")
    status = recovery.get_detailed_status()
    print(f"   Healthy nodes: {status['fault_detection']['healthy_nodes']}")
    print(f"   Partitioned: {status['partition_detection']['is_partitioned']}")
    
    # Simulate heartbeats
    print("\n2. Sending heartbeats...")
    for exec_id in executors:
        recovery.executor_heartbeat(exec_id, {
            'status': 'healthy',
            'response_time': random.uniform(0.05, 0.2),
            'vector_clock': {exec_id: 1}
        })
    
    # Mark some jobs as critical
    print("\n3. Marking critical jobs...")
    recovery.mark_job_critical("critical_job_1")
    recovery.mark_job_critical("emergency_job_2")
    
    # Check system health
    recovery.check_system_health()
    
    print("\n4. Simulating node failure...")
    # Simulate exec_1 going down (stop sending heartbeats)
    time.sleep(1)  # Wait a bit
    
    # Only send heartbeats from remaining nodes
    for exec_id in ["exec_2", "exec_3", "exec_4"]:
        recovery.executor_heartbeat(exec_id, {
            'status': 'healthy',
            'response_time': random.uniform(0.05, 0.2),
            'vector_clock': {exec_id: 2}
        })
    
    # Check for failures
    recovery.check_system_health()
    
    print("\n5. Final system status:")
    final_status = recovery.get_detailed_status()
    print(f"   Healthy nodes: {final_status['fault_detection']['healthy_nodes']}")
    print(f"   Failed nodes: {final_status['fault_detection']['confirmed_failed']}")
    print(f"   Critical jobs protected: {final_status['critical_jobs']}")
    print(f"   Job backups created: {final_status['job_backups']}")
    
    print("\n🎉 Advanced fault tolerance demo complete!")


if __name__ == "__main__":
    demo_advanced_fault_tolerance()
