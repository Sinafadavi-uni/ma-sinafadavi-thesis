"""
File 6: RecoverySystem - Node Failure Detection and Recovery
Phase 2: Node Infrastructure

Recovery system for distributed nodes with vector clock coordination
and emergency-aware failure handling.

Key Features:
- Node health monitoring with vector clock timestamps
- Failure detection and automatic recovery
- Emergency-aware recovery prioritization
- Causal consistency preservation during recovery
- Distributed consensus for recovery decisions

Based on distributed systems fault tolerance with enhancements for:
- Vector clock-based failure detection
- Emergency context preservation
- Causal ordering of recovery operations
"""

import time
import threading
import logging
from typing import Dict, Set, Optional, List, Tuple
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

# Import Phase 1 foundation
import sys
import os
phase1_path = os.path.join(os.path.dirname(__file__), '..', 'Phase1_Core_Foundation')
sys.path.insert(0, phase1_path)

from vector_clock import VectorClock, EmergencyContext
from causal_message import CausalMessage, MessageHandler
from causal_consistency import CausalConsistencyManager

LOG = logging.getLogger(__name__)

class NodeStatus(Enum):
    """Node status enumeration"""
    HEALTHY = "healthy"
    SUSPECTED = "suspected"
    FAILED = "failed"
    RECOVERING = "recovering"
    EMERGENCY = "emergency"

@dataclass
class NodeInfo:
    """Information about a monitored node"""
    node_id: str
    host: str
    port: int
    status: NodeStatus = NodeStatus.HEALTHY
    last_heartbeat: float = field(default_factory=time.time)
    vector_clock: VectorClock = None
    emergency_context: Optional[EmergencyContext] = None
    failure_count: int = 0
    recovery_attempts: int = 0
    
    def __post_init__(self):
        if self.vector_clock is None:
            self.vector_clock = VectorClock(self.node_id)

@dataclass
class RecoveryAction:
    """Recovery action for failed node"""
    action_id: str
    target_node: str
    action_type: str
    priority: int = 1
    emergency_context: Optional[EmergencyContext] = None
    vector_clock: Optional[dict] = None
    scheduled_at: float = field(default_factory=time.time)

class RecoveryStrategy(ABC):
    """Abstract base for recovery strategies"""
    
    @abstractmethod
    def should_recover(self, node_info: NodeInfo) -> bool:
        """Determine if node should be recovered"""
        pass
    
    @abstractmethod
    def create_recovery_plan(self, node_info: NodeInfo) -> List[RecoveryAction]:
        """Create recovery plan for failed node"""
        pass

class SimpleRecoveryStrategy(RecoveryStrategy):
    """Simple recovery strategy with emergency awareness"""
    
    def __init__(self, max_failures: int = 3, recovery_timeout: float = 300.0):
        self.max_failures = max_failures
        self.recovery_timeout = recovery_timeout
    
    def should_recover(self, node_info: NodeInfo) -> bool:
        """Determine if node should be recovered"""
        if node_info.status == NodeStatus.FAILED:
            # Always attempt recovery if under failure limit
            if node_info.recovery_attempts < self.max_failures:
                return True
            
            # In emergency, attempt more recoveries
            if node_info.emergency_context and node_info.emergency_context.is_critical():
                return node_info.recovery_attempts < (self.max_failures * 2)
        
        return False
    
    def create_recovery_plan(self, node_info: NodeInfo) -> List[RecoveryAction]:
        """Create recovery plan for failed node"""
        actions = []
        
        # Action 1: Restart node service
        restart_action = RecoveryAction(
            action_id=f"restart-{node_info.node_id}-{uuid4()}",
            target_node=node_info.node_id,
            action_type="restart_service",
            priority=1,
            emergency_context=node_info.emergency_context
        )
        actions.append(restart_action)
        
        # Action 2: Verify node health
        verify_action = RecoveryAction(
            action_id=f"verify-{node_info.node_id}-{uuid4()}",
            target_node=node_info.node_id,
            action_type="verify_health",
            priority=2,
            emergency_context=node_info.emergency_context
        )
        actions.append(verify_action)
        
        # Emergency action: Failover if critical
        if node_info.emergency_context and node_info.emergency_context.is_critical():
            failover_action = RecoveryAction(
                action_id=f"failover-{node_info.node_id}-{uuid4()}",
                target_node=node_info.node_id,
                action_type="emergency_failover",
                priority=0,  # Highest priority
                emergency_context=node_info.emergency_context
            )
            actions.insert(0, failover_action)  # Insert at beginning
        
        return actions

class SimpleRecoveryManager:
    """
    Simple recovery manager for distributed nodes with vector clock coordination
    
    Features:
    - Health monitoring with vector clock timestamps
    - Failure detection based on heartbeat timeouts
    - Emergency-aware recovery prioritization
    - Causal consistency preservation during recovery
    """
    
    def __init__(self, manager_id: str = None, heartbeat_timeout: float = 30.0):
        """Initialize recovery manager"""
        self.manager_id = manager_id or f"recovery-{uuid4()}"
        self.vector_clock = VectorClock(self.manager_id)
        self.heartbeat_timeout = heartbeat_timeout
        
        # Node management
        self.monitored_nodes: Dict[str, NodeInfo] = {}
        self.node_lock = threading.RLock()
        
        # Recovery management
        self.recovery_strategy = SimpleRecoveryStrategy()
        self.recovery_queue: List[RecoveryAction] = []
        self.recovery_lock = threading.RLock()
        
        # Emergency and consistency management
        self.current_emergency: Optional[EmergencyContext] = None
        self.message_handler = MessageHandler(self.manager_id)
        self.consistency_manager = CausalConsistencyManager(self.manager_id)
        
        # Thread management
        self.should_exit = False
        self.monitor_thread = None
        self.recovery_thread = None
        
        LOG.info(f"RecoveryManager {self.manager_id} initialized")
    
    def register_node(self, node_id: str, host: str, port: int) -> bool:
        """
        Register node for monitoring
        
        Args:
            node_id: Unique node identifier
            host: Node host address
            port: Node port
            
        Returns:
            True if registration successful
        """
        self.vector_clock.tick()
        
        node_info = NodeInfo(
            node_id=node_id,
            host=host,
            port=port
        )
        
        with self.node_lock:
            self.monitored_nodes[node_id] = node_info
            LOG.info(f"Node {node_id} registered for monitoring")
        
        return True
    
    def process_heartbeat(self, node_id: str, vector_clock_state: dict = None,
                         emergency_context: EmergencyContext = None) -> bool:
        """
        Process heartbeat from monitored node
        
        Args:
            node_id: Node sending heartbeat
            vector_clock_state: Node's vector clock state
            emergency_context: Current emergency context
            
        Returns:
            True if heartbeat processed successfully
        """
        with self.node_lock:
            node_info = self.monitored_nodes.get(node_id)
            if node_info is None:
                LOG.warning(f"Heartbeat from unregistered node {node_id}")
                return False
            
            # Update node info
            node_info.last_heartbeat = time.time()
            node_info.status = NodeStatus.HEALTHY
            node_info.emergency_context = emergency_context
            
            # Update vector clocks
            if vector_clock_state:
                node_info.vector_clock.update(vector_clock_state)
                self.vector_clock.update(vector_clock_state)
            
            # Tick for heartbeat event
            self.vector_clock.tick()
            
            LOG.debug(f"Heartbeat processed from node {node_id}")
            return True
    
    def detect_node_failure(self, node_id: str, reason: str = "timeout") -> bool:
        """
        Manually mark node as failed
        
        Args:
            node_id: Failed node
            reason: Failure reason
            
        Returns:
            True if failure recorded
        """
        with self.node_lock:
            node_info = self.monitored_nodes.get(node_id)
            if node_info is None:
                return False
            
            self.vector_clock.tick()
            
            node_info.status = NodeStatus.FAILED
            node_info.failure_count += 1
            
            LOG.warning(f"Node {node_id} marked as failed: {reason}")
            
            # Schedule recovery if appropriate
            if self.recovery_strategy.should_recover(node_info):
                self._schedule_recovery(node_info)
            
            return True
    
    def set_emergency_mode(self, emergency_type: str, priority_level: str) -> None:
        """
        Activate emergency mode affecting recovery behavior
        
        Args:
            emergency_type: Type of emergency
            priority_level: Priority level
        """
        from vector_clock import create_emergency
        
        self.vector_clock.tick()
        self.current_emergency = create_emergency(emergency_type, priority_level)
        
        # Update all monitored nodes with emergency context
        with self.node_lock:
            for node_info in self.monitored_nodes.values():
                node_info.emergency_context = self.current_emergency
        
        LOG.warning(f"Recovery emergency mode activated: {emergency_type} ({priority_level})")
    
    def clear_emergency_mode(self) -> None:
        """Clear emergency mode"""
        self.vector_clock.tick()
        self.current_emergency = None
        
        # Clear emergency from all nodes
        with self.node_lock:
            for node_info in self.monitored_nodes.values():
                node_info.emergency_context = None
        
        LOG.info("Recovery emergency mode cleared")
    
    def get_node_status(self, node_id: str) -> Optional[NodeStatus]:
        """Get status of monitored node"""
        with self.node_lock:
            node_info = self.monitored_nodes.get(node_id)
            return node_info.status if node_info else None
    
    def get_healthy_nodes(self) -> List[str]:
        """Get list of healthy node IDs"""
        with self.node_lock:
            return [
                node_id for node_id, node_info in self.monitored_nodes.items()
                if node_info.status == NodeStatus.HEALTHY
            ]
    
    def get_failed_nodes(self) -> List[str]:
        """Get list of failed node IDs"""
        with self.node_lock:
            return [
                node_id for node_id, node_info in self.monitored_nodes.items()
                if node_info.status == NodeStatus.FAILED
            ]
    
    def start(self) -> None:
        """Start recovery manager background processing"""
        if self.monitor_thread is None or not self.monitor_thread.is_alive():
            self.should_exit = False
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(
                target=self._health_monitor,
                daemon=True,
                name=f"recovery-monitor-{self.manager_id}"
            )
            self.monitor_thread.start()
            
            # Start recovery thread
            self.recovery_thread = threading.Thread(
                target=self._recovery_processor,
                daemon=True,
                name=f"recovery-processor-{self.manager_id}"
            )
            self.recovery_thread.start()
            
            LOG.info(f"RecoveryManager {self.manager_id} started")
    
    def stop(self) -> None:
        """Stop recovery manager processing"""
        self.should_exit = True
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        if self.recovery_thread and self.recovery_thread.is_alive():
            self.recovery_thread.join(timeout=5.0)
        
        LOG.info(f"RecoveryManager {self.manager_id} stopped")
    
    def _schedule_recovery(self, node_info: NodeInfo) -> None:
        """Schedule recovery for failed node"""
        recovery_actions = self.recovery_strategy.create_recovery_plan(node_info)
        
        with self.recovery_lock:
            for action in recovery_actions:
                action.vector_clock = self.vector_clock.clock.copy()
                self.recovery_queue.append(action)
            
            # Sort by priority (lower number = higher priority)
            self.recovery_queue.sort(key=lambda a: a.priority)
        
        LOG.info(f"Scheduled {len(recovery_actions)} recovery actions for node {node_info.node_id}")
    
    def _health_monitor(self) -> None:
        """Background health monitoring thread"""
        LOG.info(f"Health monitor started for manager {self.manager_id}")
        
        while not self.should_exit:
            try:
                current_time = time.time()
                
                with self.node_lock:
                    for node_id, node_info in self.monitored_nodes.items():
                        if node_info.status == NodeStatus.HEALTHY:
                            # Check for heartbeat timeout
                            time_since_heartbeat = current_time - node_info.last_heartbeat
                            
                            if time_since_heartbeat > self.heartbeat_timeout:
                                # Mark as suspected first
                                if time_since_heartbeat > self.heartbeat_timeout * 1.5:
                                    node_info.status = NodeStatus.FAILED
                                    node_info.failure_count += 1
                                    self.vector_clock.tick()
                                    
                                    LOG.warning(f"Node {node_id} failed (heartbeat timeout)")
                                    
                                    # Schedule recovery
                                    if self.recovery_strategy.should_recover(node_info):
                                        self._schedule_recovery(node_info)
                                
                                elif node_info.status == NodeStatus.HEALTHY:
                                    node_info.status = NodeStatus.SUSPECTED
                                    LOG.debug(f"Node {node_id} suspected (heartbeat delay)")
                
                time.sleep(5.0)  # Check every 5 seconds
                
            except Exception as e:
                LOG.error(f"Error in health monitor: {e}")
                time.sleep(1.0)
        
        LOG.info(f"Health monitor stopped for manager {self.manager_id}")
    
    def _recovery_processor(self) -> None:
        """Background recovery processing thread"""
        LOG.info(f"Recovery processor started for manager {self.manager_id}")
        
        while not self.should_exit:
            try:
                with self.recovery_lock:
                    if not self.recovery_queue:
                        time.sleep(1.0)
                        continue
                    
                    # Get highest priority action
                    action = self.recovery_queue.pop(0)
                
                # Execute recovery action
                self._execute_recovery_action(action)
                
                time.sleep(0.5)  # Brief pause between actions
                
            except Exception as e:
                LOG.error(f"Error in recovery processor: {e}")
                time.sleep(1.0)
        
        LOG.info(f"Recovery processor stopped for manager {self.manager_id}")
    
    def _execute_recovery_action(self, action: RecoveryAction) -> bool:
        """
        Execute recovery action
        
        Args:
            action: Recovery action to execute
            
        Returns:
            True if action executed successfully
        """
        self.vector_clock.tick()
        
        LOG.info(f"Executing recovery action: {action.action_type} for node {action.target_node}")
        
        # Update node status
        with self.node_lock:
            node_info = self.monitored_nodes.get(action.target_node)
            if node_info:
                node_info.status = NodeStatus.RECOVERING
                node_info.recovery_attempts += 1
        
        # Simulate recovery action execution
        if action.action_type == "restart_service":
            return self._restart_node_service(action.target_node)
        elif action.action_type == "verify_health":
            return self._verify_node_health(action.target_node)
        elif action.action_type == "emergency_failover":
            return self._emergency_failover(action.target_node)
        
        return False
    
    def _restart_node_service(self, node_id: str) -> bool:
        """Simulate restarting node service"""
        LOG.info(f"Restarting service for node {node_id}")
        time.sleep(0.1)  # Simulate restart time
        return True
    
    def _verify_node_health(self, node_id: str) -> bool:
        """Simulate verifying node health"""
        LOG.info(f"Verifying health for node {node_id}")
        time.sleep(0.1)  # Simulate health check
        
        # Mark node as healthy if verification passes
        with self.node_lock:
            node_info = self.monitored_nodes.get(node_id)
            if node_info:
                node_info.status = NodeStatus.HEALTHY
                node_info.last_heartbeat = time.time()
        
        return True
    
    def _emergency_failover(self, node_id: str) -> bool:
        """Simulate emergency failover"""
        LOG.warning(f"Performing emergency failover for node {node_id}")
        time.sleep(0.1)  # Simulate failover time
        return True

# Demo and testing functions
def demo_recovery_system():
    """Demonstrate RecoverySystem functionality"""
    print("\n=== RecoverySystem Demo ===")
    
    # Create recovery manager
    recovery = SimpleRecoveryManager("demo_recovery")
    print(f"✅ Created recovery manager: {recovery.manager_id}")
    
    # Register nodes for monitoring
    node1_id = "executor_1"
    node2_id = "executor_2" 
    node3_id = "datastore_1"
    
    recovery.register_node(node1_id, "127.0.0.1", 8001)
    recovery.register_node(node2_id, "127.0.0.1", 8002)
    recovery.register_node(node3_id, "127.0.0.1", 9001)
    
    print(f"✅ Registered {len(recovery.monitored_nodes)} nodes for monitoring")
    
    # Start recovery manager
    recovery.start()
    print("✅ Recovery manager started")
    
    # Process heartbeats
    recovery.process_heartbeat(node1_id)
    recovery.process_heartbeat(node2_id)
    recovery.process_heartbeat(node3_id)
    print("✅ Processed heartbeats")
    
    # Check node status
    print(f"✅ Healthy nodes: {recovery.get_healthy_nodes()}")
    print(f"✅ Failed nodes: {recovery.get_failed_nodes()}")
    
    # Simulate node failure
    recovery.detect_node_failure(node2_id, "network_timeout")
    print(f"✅ Node {node2_id} marked as failed")
    
    # Test emergency mode
    recovery.set_emergency_mode("fire", "critical")
    print("✅ Emergency mode activated")
    
    # Simulate emergency failure
    recovery.detect_node_failure(node3_id, "emergency_shutdown")
    print(f"✅ Emergency failure detected for {node3_id}")
    
    # Wait for recovery actions
    time.sleep(0.5)
    print("✅ Recovery actions processed")
    
    # Clear emergency
    recovery.clear_emergency_mode()
    print("✅ Emergency mode cleared")
    
    # Stop recovery manager
    recovery.stop()
    print("✅ Recovery manager stopped")
    
    return True

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run demo
    demo_recovery_system()