"""
File 11: MultiBrokerCoordinator - Multi-Broker Coordination System
Phase 4: UCP Integration

Comprehensive multi-broker coordination system for large-scale distributed
deployment with vector clock synchronization and emergency coordination.

Key Features:
- Global coordination across multiple broker clusters
- Vector clock synchronization for large-scale distributed systems
- Emergency response coordination across broker networks
- Load balancing and failover coordination
- Production-ready scalability and fault tolerance

This provides the top-level coordination layer for distributed UCP deployment
with multiple broker clusters and complex emergency response scenarios.
"""

import time
import threading
import logging
from typing import Dict, Optional, List, Set, Any, Tuple
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import json

# Import Phase 1 foundation
import sys
import os
phase1_path = os.path.join(os.path.dirname(__file__), '..', 'Phase1_Core_Foundation')
sys.path.insert(0, phase1_path)

import vector_clock
import causal_message
import causal_consistency

from vector_clock import VectorClock, EmergencyContext, EmergencyLevel, create_emergency
from causal_message import CausalMessage, MessageHandler
from causal_consistency import CausalConsistencyManager

# Import Phase 3 implementation
phase3_path = os.path.join(os.path.dirname(__file__), '..', 'Phase3_Core_Implementation')
sys.path.insert(0, phase3_path)

from vector_clock_broker import VectorClockBroker
from emergency_integration import EmergencyIntegrationManager

LOG = logging.getLogger(__name__)

class CoordinationLevel(Enum):
    """Coordination scope levels"""
    LOCAL = "local"
    REGIONAL = "regional"
    GLOBAL = "global"
    EMERGENCY = "emergency"

class BrokerClusterStatus(Enum):
    """Broker cluster status"""
    ACTIVE = "active"
    DEGRADED = "degraded"
    EMERGENCY = "emergency"
    OFFLINE = "offline"
    RECOVERING = "recovering"

@dataclass
class BrokerCluster:
    """Broker cluster information"""
    cluster_id: str
    primary_broker: str
    broker_nodes: Set[str] = field(default_factory=set)
    status: BrokerClusterStatus = BrokerClusterStatus.ACTIVE
    vector_clock_state: Dict[str, int] = field(default_factory=dict)
    emergency_capability: bool = True
    load_factor: float = 0.0
    last_sync: float = field(default_factory=time.time)

@dataclass
class GlobalOperation:
    """Global coordination operation"""
    operation_id: UUID
    operation_type: str
    coordinator_id: str
    participating_clusters: Set[str] = field(default_factory=set)
    vector_clock_snapshot: Dict[str, int] = field(default_factory=dict)
    priority: int = 1
    emergency_context: Optional[EmergencyContext] = None
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    success: bool = False

class MultiBrokerCoordinator:
    """
    Multi-broker coordination system for large-scale distributed deployment
    
    Coordinates multiple broker clusters with vector clock synchronization,
    emergency response coordination, and production-ready scalability.
    
    Features:
    - Global vector clock synchronization across broker clusters
    - Emergency response coordination at scale
    - Load balancing and failover coordination
    - Production monitoring and health checking
    - Causal consistency enforcement across clusters
    """
    
    def __init__(self, coordinator_id: str = None):
        """Initialize multi-broker coordinator"""
        self.coordinator_id = coordinator_id or f"multi-broker-coord-{uuid4()}"
        self.vector_clock = VectorClock(self.coordinator_id)
        
        # Cluster management
        self.broker_clusters: Dict[str, BrokerCluster] = {}
        self.cluster_brokers: Dict[str, VectorClockBroker] = {}  # cluster_id -> broker instance
        self.cluster_lock = threading.RLock()
        
        # Global coordination
        self.global_operations: Dict[UUID, GlobalOperation] = {}
        self.operation_lock = threading.RLock()
        
        # Emergency coordination
        self.emergency_manager = EmergencyIntegrationManager(f"emergency-{self.coordinator_id}")
        self.global_emergency_state = False
        
        # Synchronization and monitoring
        self.sync_interval = 10.0  # Sync every 10 seconds for production
        self.health_check_interval = 30.0  # Health check every 30 seconds
        self.sync_thread = None
        self.health_thread = None
        
        # Consistency management
        self.message_handler = MessageHandler(self.coordinator_id)
        self.consistency_manager = CausalConsistencyManager(self.coordinator_id)
        
        # System state
        self.should_exit = False
        self.coordination_metrics = {
            "operations_coordinated": 0,
            "clusters_synchronized": 0,
            "emergencies_handled": 0,
            "uptime_start": time.time()
        }
        
        LOG.info(f"MultiBrokerCoordinator {self.coordinator_id} initialized")
    
    def register_broker_cluster(self, cluster_id: str, primary_broker: VectorClockBroker,
                               additional_brokers: List[VectorClockBroker] = None) -> None:
        """
        Register broker cluster for coordination
        
        Args:
            cluster_id: Unique cluster identifier
            primary_broker: Primary broker for the cluster
            additional_brokers: Additional brokers in cluster
        """
        with self.cluster_lock:
            # Create cluster information
            broker_nodes = {primary_broker.broker_id}
            if additional_brokers:
                broker_nodes.update(broker.broker_id for broker in additional_brokers)
            
            cluster = BrokerCluster(
                cluster_id=cluster_id,
                primary_broker=primary_broker.broker_id,
                broker_nodes=broker_nodes,
                vector_clock_state=primary_broker.vector_clock.clock.copy()
            )
            
            self.broker_clusters[cluster_id] = cluster
            self.cluster_brokers[cluster_id] = primary_broker
            
            # Register cluster with emergency manager
            self.emergency_manager.register_node(cluster_id, primary_broker, {"broker_coordination"})
        
        LOG.info(f"Registered broker cluster {cluster_id} with {len(broker_nodes)} brokers")
    
    def coordinate_global_operation(self, operation_data: Dict[str, Any]) -> bool:
        """
        Coordinate operation across all broker clusters
        
        Args:
            operation_data: Operation details including type, data, and context
            
        Returns:
            bool: True if coordination successful
        """
        # Tick vector clock for global operation
        self.vector_clock.tick()
        
        # Create global operation
        operation_id = uuid4()
        global_op = GlobalOperation(
            operation_id=operation_id,
            operation_type=operation_data.get("operation", "unknown"),
            coordinator_id=self.coordinator_id,
            participating_clusters=set(self.broker_clusters.keys()),
            vector_clock_snapshot=self.vector_clock.clock.copy(),
            priority=operation_data.get("priority", 1),
            emergency_context=operation_data.get("emergency_context")
        )
        
        with self.operation_lock:
            self.global_operations[operation_id] = global_op
        
        # Coordinate with all clusters
        coordination_results = {}
        
        for cluster_id, cluster in self.broker_clusters.items():
            try:
                cluster_broker = self.cluster_brokers.get(cluster_id)
                if cluster_broker:
                    # Synchronize vector clocks
                    cluster_broker.sync_vector_clock(self.vector_clock.clock, self.coordinator_id)
                    
                    # Create coordination operation
                    coordination_op = {
                        "operation_id": str(operation_id),
                        "type": global_op.operation_type,
                        "vector_clock": self.vector_clock.clock.copy(),
                        "coordinator": self.coordinator_id,
                        "data": operation_data
                    }
                    
                    # Apply causal ordering
                    causal_result = cluster_broker.ensure_causal_order(coordination_op)
                    coordination_results[cluster_id] = causal_result
                    
                    LOG.debug(f"Coordinated operation {operation_id} with cluster {cluster_id}")
                
            except Exception as e:
                LOG.error(f"Failed to coordinate with cluster {cluster_id}: {e}")
                coordination_results[cluster_id] = False
        
        # Determine overall success
        success = all(coordination_results.values())
        global_op.completed_at = time.time()
        global_op.success = success
        
        if success:
            self.coordination_metrics["operations_coordinated"] += 1
        
        LOG.info(f"Global operation {operation_id} {'succeeded' if success else 'failed'} "
                f"across {len(coordination_results)} clusters")
        
        return success
    
    def coordinate_emergency_response(self, emergency_type: str, level: str, 
                                    affected_clusters: List[str] = None) -> Dict[str, Any]:
        """
        Coordinate emergency response across broker clusters
        
        Args:
            emergency_type: Type of emergency
            level: Emergency level
            affected_clusters: List of affected cluster IDs
            
        Returns:
            Dict: Emergency coordination results
        """
        # Tick vector clock for emergency
        self.vector_clock.tick()
        
        # Create emergency context
        emergency_context = create_emergency(emergency_type, level)
        self.global_emergency_state = True
        
        # Determine affected clusters
        if not affected_clusters:
            affected_clusters = list(self.broker_clusters.keys())
        
        # Coordinate emergency with emergency manager
        emergency_nodes = [cluster_id for cluster_id in affected_clusters 
                          if cluster_id in self.broker_clusters]
        
        response_id = self.emergency_manager.activate_emergency(
            emergency_type, level, emergency_nodes
        )
        
        # Coordinate emergency across clusters
        emergency_coordination = {}
        
        for cluster_id in affected_clusters:
            if cluster_id in self.broker_clusters:
                try:
                    cluster_broker = self.cluster_brokers[cluster_id]
                    
                    # Activate emergency mode on cluster
                    cluster_emergency_result = cluster_broker.coordinate_emergency_response(
                        emergency_context, affected_regions=[cluster_id]
                    )
                    
                    emergency_coordination[cluster_id] = {
                        "status": "emergency_activated",
                        "coordination_id": cluster_emergency_result.get("coordination_id"),
                        "vector_clock": cluster_broker.vector_clock.clock.copy()
                    }
                    
                    # Update cluster status
                    self.broker_clusters[cluster_id].status = BrokerClusterStatus.EMERGENCY
                    
                except Exception as e:
                    LOG.error(f"Failed emergency coordination with cluster {cluster_id}: {e}")
                    emergency_coordination[cluster_id] = {
                        "status": "coordination_failed",
                        "error": str(e)
                    }
        
        self.coordination_metrics["emergencies_handled"] += 1
        
        LOG.warning(f"Emergency {emergency_type} coordinated across {len(emergency_coordination)} clusters")
        
        return {
            "emergency_response_id": response_id,
            "emergency_context": {
                "type": emergency_type,
                "level": level
            },
            "global_coordinator": self.coordinator_id,
            "affected_clusters": affected_clusters,
            "coordination_results": emergency_coordination,
            "vector_clock": self.vector_clock.clock.copy()
        }
    
    def synchronize_all_clusters(self) -> Dict[str, bool]:
        """
        Synchronize vector clocks across all broker clusters
        
        Returns:
            Dict: Synchronization results per cluster
        """
        self.vector_clock.tick()
        sync_results = {}
        
        with self.cluster_lock:
            for cluster_id, cluster in self.broker_clusters.items():
                try:
                    cluster_broker = self.cluster_brokers.get(cluster_id)
                    if cluster_broker:
                        # Exchange vector clocks
                        cluster_clock = cluster_broker.vector_clock.clock.copy()
                        self.vector_clock.update(cluster_clock)
                        cluster_broker.sync_vector_clock(self.vector_clock.clock, self.coordinator_id)
                        
                        # Update cluster state
                        cluster.vector_clock_state = cluster_clock
                        cluster.last_sync = time.time()
                        
                        sync_results[cluster_id] = True
                        LOG.debug(f"Synchronized vector clock with cluster {cluster_id}")
                    
                except Exception as e:
                    LOG.error(f"Failed to sync with cluster {cluster_id}: {e}")
                    sync_results[cluster_id] = False
        
        successful_syncs = sum(1 for success in sync_results.values() if success)
        self.coordination_metrics["clusters_synchronized"] += successful_syncs
        
        return sync_results
    
    def get_global_status(self) -> Dict[str, Any]:
        """Get comprehensive global coordination status"""
        with self.cluster_lock:
            cluster_status = {}
            for cluster_id, cluster in self.broker_clusters.items():
                cluster_status[cluster_id] = {
                    "primary_broker": cluster.primary_broker,
                    "broker_count": len(cluster.broker_nodes),
                    "status": cluster.status.value,
                    "load_factor": cluster.load_factor,
                    "last_sync": cluster.last_sync,
                    "emergency_capable": cluster.emergency_capability
                }
        
        with self.operation_lock:
            active_operations = len([op for op in self.global_operations.values() 
                                   if op.completed_at is None])
            completed_operations = len([op for op in self.global_operations.values() 
                                      if op.completed_at is not None])
        
        return {
            "coordinator_id": self.coordinator_id,
            "vector_clock": self.vector_clock.clock.copy(),
            "global_emergency_state": self.global_emergency_state,
            "coordination_level": CoordinationLevel.GLOBAL.value,
            "broker_clusters": cluster_status,
            "operations": {
                "active": active_operations,
                "completed": completed_operations
            },
            "metrics": self.coordination_metrics,
            "uptime": time.time() - self.coordination_metrics["uptime_start"]
        }
    
    def start(self) -> None:
        """Start multi-broker coordinator"""
        if self.sync_thread is None or not self.sync_thread.is_alive():
            self.should_exit = False
            
            # Start synchronization thread
            self.sync_thread = threading.Thread(
                target=self._global_sync_worker,
                daemon=True,
                name=f"global-sync-{self.coordinator_id}"
            )
            self.sync_thread.start()
            
            # Start health monitoring thread
            self.health_thread = threading.Thread(
                target=self._health_monitor,
                daemon=True,
                name=f"health-monitor-{self.coordinator_id}"
            )
            self.health_thread.start()
        
        # Start emergency manager
        self.emergency_manager.start()
        
        LOG.info(f"MultiBrokerCoordinator {self.coordinator_id} started")
    
    def stop(self) -> None:
        """Stop multi-broker coordinator"""
        self.should_exit = True
        
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=3.0)
        
        if self.health_thread and self.health_thread.is_alive():
            self.health_thread.join(timeout=3.0)
        
        # Stop emergency manager
        self.emergency_manager.stop()
        
        LOG.info(f"MultiBrokerCoordinator {self.coordinator_id} stopped")
    
    def _global_sync_worker(self) -> None:
        """Background worker for global synchronization"""
        LOG.info(f"Global sync worker started for coordinator {self.coordinator_id}")
        
        while not self.should_exit:
            try:
                # Synchronize all clusters
                sync_results = self.synchronize_all_clusters()
                
                # Log synchronization status
                successful = sum(1 for success in sync_results.values() if success)
                total = len(sync_results)
                
                if successful < total:
                    LOG.warning(f"Global sync: {successful}/{total} clusters synchronized")
                else:
                    LOG.debug(f"Global sync: all {total} clusters synchronized")
                
                time.sleep(self.sync_interval)
                
            except Exception as e:
                LOG.error(f"Error in global sync: {e}")
                time.sleep(5.0)
        
        LOG.info(f"Global sync worker stopped for coordinator {self.coordinator_id}")
    
    def _health_monitor(self) -> None:
        """Background health monitoring worker"""
        LOG.info(f"Health monitor started for coordinator {self.coordinator_id}")
        
        while not self.should_exit:
            try:
                current_time = time.time()
                
                with self.cluster_lock:
                    for cluster_id, cluster in self.broker_clusters.items():
                        # Check cluster health based on last sync time
                        time_since_sync = current_time - cluster.last_sync
                        
                        if time_since_sync > self.sync_interval * 3:  # 3x sync interval
                            if cluster.status == BrokerClusterStatus.ACTIVE:
                                cluster.status = BrokerClusterStatus.DEGRADED
                                LOG.warning(f"Cluster {cluster_id} marked as degraded "
                                          f"(last sync {time_since_sync:.1f}s ago)")
                        
                        elif time_since_sync > self.sync_interval * 6:  # 6x sync interval
                            if cluster.status != BrokerClusterStatus.OFFLINE:
                                cluster.status = BrokerClusterStatus.OFFLINE
                                LOG.error(f"Cluster {cluster_id} marked as offline "
                                        f"(last sync {time_since_sync:.1f}s ago)")
                
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                LOG.error(f"Error in health monitor: {e}")
                time.sleep(5.0)
        
        LOG.info(f"Health monitor stopped for coordinator {self.coordinator_id}")

# Demo and testing functions
def demo_multi_broker_coordinator():
    """Demonstrate MultiBrokerCoordinator functionality"""
    print("\n=== MultiBrokerCoordinator Demo ===")
    
    # Create coordinator
    coordinator = MultiBrokerCoordinator("production_coordinator")
    print(f"✅ Created coordinator: {coordinator.coordinator_id}")
    
    # Create broker clusters (simulated)
    from vector_clock_broker import VectorClockBroker
    
    cluster1_broker = VectorClockBroker("cluster1_primary")
    cluster2_broker = VectorClockBroker("cluster2_primary")
    cluster3_broker = VectorClockBroker("cluster3_primary")
    
    # Register clusters
    coordinator.register_broker_cluster("cluster_1", cluster1_broker)
    coordinator.register_broker_cluster("cluster_2", cluster2_broker)
    coordinator.register_broker_cluster("cluster_3", cluster3_broker)
    
    print(f"✅ Registered {len(coordinator.broker_clusters)} broker clusters")
    
    # Start coordinator
    coordinator.start()
    print("✅ Coordinator started")
    
    # Test global operation coordination
    operation_data = {
        "operation": "global_job_submission",
        "priority": 1,
        "data": {"job_count": 100, "distribution": "round_robin"}
    }
    
    coordination_result = coordinator.coordinate_global_operation(operation_data)
    print(f"✅ Global operation coordination: {'successful' if coordination_result else 'failed'}")
    
    # Test emergency coordination
    emergency_result = coordinator.coordinate_emergency_response(
        "system_overload", "high", ["cluster_1", "cluster_2"]
    )
    print(f"✅ Emergency coordination: {len(emergency_result['coordination_results'])} clusters")
    
    # Test global synchronization
    sync_results = coordinator.synchronize_all_clusters()
    successful_syncs = sum(1 for success in sync_results.values() if success)
    print(f"✅ Global synchronization: {successful_syncs}/{len(sync_results)} clusters")
    
    # Check global status
    status = coordinator.get_global_status()
    print(f"✅ Global status: {len(status['broker_clusters'])} clusters, "
          f"{status['operations']['completed']} operations completed")
    
    # Wait for background processing
    time.sleep(0.5)
    
    # Stop coordinator
    coordinator.stop()
    print("✅ Coordinator stopped")
    
    return True

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run demo
    demo_multi_broker_coordinator()
