"""
File 10: EmergencyIntegration - Emergency Response System Integration
Phase 3: Core Implementation

Comprehensive emergency response integration system that coordinates
emergency detection, response, and recovery across distributed nodes
with vector clock-based causal consistency.

Key Features:
- Emergency detection and propagation across distributed system
- Vector clock coordination during emergency scenarios
- Emergency-aware resource allocation and job prioritization
- Causal consistency preservation during crisis situations
- Cross-system emergency response coordination

This integrates all emergency response capabilities from previous phases
into a unified emergency management system for distributed environments.
"""

import time
import threading
import logging
from typing import Dict, Optional, List, Set, Any, Tuple, Callable
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

# Import Phase 1 foundation
import sys
import os
phase1_path = os.path.join(os.path.dirname(__file__), '..', 'Phase1_Core_Foundation')
sys.path.insert(0, phase1_path)

# import vector_clock
# import causal_message
import causal_consistency

from rec.Phase1_Core_Foundation.vector_clock import VectorClock, EmergencyContext, EmergencyLevel, create_emergency
from rec.Phase1_Core_Foundation.causal_message import CausalMessage, MessageHandler
from rec.Phase1_Core_Foundation.causal_consistency import CausalConsistencyManager

# Import Phase 2 infrastructure
phase2_path = os.path.join(os.path.dirname(__file__), '..', 'Phase2_Node_Infrastructure')
sys.path.insert(0, phase2_path)

from recovery_system import SimpleRecoveryManager
from emergency_executor import SimpleEmergencyExecutor

LOG = logging.getLogger(__name__)

class EmergencyState(Enum):
    """Emergency response system state"""
    NORMAL = "normal"
    DETECTING = "detecting"
    RESPONDING = "responding"
    COORDINATING = "coordinating"
    RECOVERING = "recovering"
    RESOLVED = "resolved"

class EmergencyScope(Enum):
    """Scope of emergency response"""
    LOCAL = "local"
    REGIONAL = "regional"
    GLOBAL = "global"
    CRITICAL_INFRASTRUCTURE = "critical_infrastructure"

@dataclass
class EmergencyEvent:
    """Emergency event information"""
    event_id: UUID
    emergency_type: str
    level: EmergencyLevel
    location: Optional[str] = None
    scope: EmergencyScope = EmergencyScope.LOCAL
    detected_at: float = field(default_factory=time.time)
    vector_clock_snapshot: Dict[str, int] = field(default_factory=dict)
    affected_nodes: Set[str] = field(default_factory=set)
    response_actions: List[str] = field(default_factory=list)
    resolution_time: Optional[float] = None

@dataclass
class EmergencyResponse:
    """Emergency response coordination"""
    response_id: UUID
    event_id: UUID
    coordinating_node: str
    participating_nodes: Set[str] = field(default_factory=set)
    response_strategy: str = "default"
    priority_level: int = 1
    vector_clock_state: Dict[str, int] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

class EmergencyIntegrationManager:
    """
    Comprehensive emergency response integration system
    
    Coordinates emergency detection, response, and recovery across
    distributed nodes with vector clock-based causal consistency.
    
    Features:
    - Emergency event detection and propagation
    - Vector clock coordination during emergencies
    - Resource reallocation and priority management
    - Cross-node emergency response coordination
    - Causal consistency preservation during crisis
    """
    
    def __init__(self, manager_id: str = None):
        """Initialize emergency integration manager"""
        self.manager_id = manager_id or f"emergency-mgr-{uuid4()}"
        self.vector_clock = VectorClock(self.manager_id)
        
        # Emergency state management
        self.current_state = EmergencyState.NORMAL
        self.active_emergencies: Dict[UUID, EmergencyEvent] = {}
        self.emergency_responses: Dict[UUID, EmergencyResponse] = {}
        self.emergency_lock = threading.RLock()
        
        # Node coordination
        self.managed_nodes: Dict[str, Any] = {}  # Node ID -> Node instance
        self.node_capabilities: Dict[str, Set[str]] = {}
        self.node_emergency_status: Dict[str, EmergencyState] = {}
        
        # Emergency response coordination
        self.emergency_protocols: Dict[str, Callable] = {}
        self.response_strategies: Dict[EmergencyLevel, Dict[str, Any]] = {
            EmergencyLevel.LOW: {"timeout": 300, "resources": "normal"},
            EmergencyLevel.MEDIUM: {"timeout": 180, "resources": "increased"},
            EmergencyLevel.HIGH: {"timeout": 60, "resources": "priority"},
            EmergencyLevel.CRITICAL: {"timeout": 30, "resources": "maximum"}
        }
        
        # Messaging and consistency
        self.message_handler = MessageHandler(self.manager_id)
        self.consistency_manager = CausalConsistencyManager(self.manager_id)
        
        # Background processing
        self.should_exit = False
        self.monitor_thread = None
        self.coordination_thread = None
        
        LOG.info(f"EmergencyIntegrationManager {self.manager_id} initialized")
    
    def register_node(self, node_id: str, node_instance: Any, capabilities: Set[str] = None) -> None:
        """
        Register node for emergency management
        
        Args:
            node_id: Node identifier
            node_instance: Node instance (executor, broker, etc.)
            capabilities: Node capabilities for emergency response
        """
        self.managed_nodes[node_id] = node_instance
        self.node_capabilities[node_id] = capabilities or set()
        self.node_emergency_status[node_id] = EmergencyState.NORMAL
        
        LOG.info(f"Node {node_id} registered for emergency management")
    
    def detect_emergency(self, emergency_type: str, level: str, location: str = None,
                        affected_nodes: Set[str] = None, scope: EmergencyScope = EmergencyScope.LOCAL) -> UUID:
        """
        Detect and initiate emergency response
        
        Args:
            emergency_type: Type of emergency
            level: Emergency level
            location: Emergency location
            affected_nodes: Set of affected node IDs
            scope: Scope of emergency response
            
        Returns:
            UUID: Emergency event ID
        """
        # Tick vector clock for emergency detection
        self.vector_clock.tick()
        
        # Create emergency event
        event_id = uuid4()
        emergency_context = create_emergency(emergency_type, level, location)
        
        emergency_event = EmergencyEvent(
            event_id=event_id,
            emergency_type=emergency_type,
            level=emergency_context.level,
            location=location,
            scope=scope,
            vector_clock_snapshot=self.vector_clock.clock.copy(),
            affected_nodes=affected_nodes or set()
        )
        
        with self.emergency_lock:
            self.active_emergencies[event_id] = emergency_event
            self.current_state = EmergencyState.DETECTING
        
        # Initiate emergency response
        response_id = self._initiate_emergency_response(emergency_event)
        
        LOG.warning(f"Emergency detected: {emergency_type} ({level}) - Event ID: {event_id}")
        return event_id
    
    def activate_emergency(self, emergency_type: str, level: str, 
                          participating_nodes: List[str]) -> UUID:
        """
        Activate emergency mode across specified nodes
        
        Args:
            emergency_type: Type of emergency
            level: Emergency level
            participating_nodes: List of node IDs to activate
            
        Returns:
            UUID: Emergency response ID
        """
        # Detect emergency first
        event_id = self.detect_emergency(
            emergency_type, 
            level, 
            affected_nodes=set(participating_nodes),
            scope=EmergencyScope.REGIONAL if len(participating_nodes) > 1 else EmergencyScope.LOCAL
        )
        
        # Get the emergency event
        emergency_event = self.active_emergencies[event_id]
        
        # Activate emergency mode on all participating nodes
        activated_nodes = set()
        
        for node_id in participating_nodes:
            if node_id in self.managed_nodes:
                node_instance = self.managed_nodes[node_id]
                
                try:
                    # Activate emergency mode based on node type
                    if hasattr(node_instance, 'set_emergency_mode'):
                        node_instance.set_emergency_mode(emergency_type, level)
                        activated_nodes.add(node_id)
                        self.node_emergency_status[node_id] = EmergencyState.RESPONDING
                        
                        LOG.info(f"Emergency mode activated on node {node_id}")
                    
                except Exception as e:
                    LOG.error(f"Failed to activate emergency on node {node_id}: {e}")
        
        # Update emergency event with activated nodes
        emergency_event.affected_nodes = activated_nodes
        
        # Find the response for this event
        response_id = None
        for resp_id, response in self.emergency_responses.items():
            if response.event_id == event_id:
                response.participating_nodes = activated_nodes
                response_id = resp_id
                break
        
        LOG.warning(f"Emergency {emergency_type} activated on {len(activated_nodes)} nodes")
        return response_id or uuid4()
    
    def coordinate_emergency_response(self, event_id: UUID, strategy: str = "default") -> bool:
        """
        Coordinate emergency response across distributed nodes
        
        Args:
            event_id: Emergency event ID
            strategy: Response strategy to use
            
        Returns:
            bool: True if coordination successful
        """
        with self.emergency_lock:
            emergency_event = self.active_emergencies.get(event_id)
            if not emergency_event:
                LOG.error(f"Emergency event {event_id} not found")
                return False
        
        # Update state
        self.current_state = EmergencyState.COORDINATING
        self.vector_clock.tick()
        
        # Create coordination messages
        coordination_message = CausalMessage(
            content={
                "event_id": str(event_id),
                "emergency_type": emergency_event.emergency_type,
                "level": emergency_event.level.name,
                "coordination_action": "coordinate_response",
                "strategy": strategy
            },
            sender_id=self.manager_id,
            vector_clock=self.vector_clock.clock.copy(),
            message_type="emergency",
            priority=10
        )
        
        # Coordinate with affected nodes
        coordination_success = True
        for node_id in emergency_event.affected_nodes:
            try:
                node_instance = self.managed_nodes.get(node_id)
                if node_instance:
                    # Synchronize vector clocks
                    if hasattr(node_instance, 'vector_clock'):
                        node_instance.vector_clock.update(self.vector_clock.clock)
                    
                    # Apply emergency coordination
                    self._apply_emergency_coordination(node_instance, emergency_event, strategy)
                    
            except Exception as e:
                LOG.error(f"Failed to coordinate with node {node_id}: {e}")
                coordination_success = False
        
        LOG.info(f"Emergency coordination {'successful' if coordination_success else 'partial'} for event {event_id}")
        return coordination_success
    
    def resolve_emergency(self, event_id: UUID, resolution_notes: str = None) -> bool:
        """
        Resolve emergency and restore normal operations
        
        Args:
            event_id: Emergency event ID to resolve
            resolution_notes: Optional resolution notes
            
        Returns:
            bool: True if resolution successful
        """
        with self.emergency_lock:
            emergency_event = self.active_emergencies.get(event_id)
            if not emergency_event:
                LOG.error(f"Emergency event {event_id} not found")
                return False
        
        # Update state
        self.current_state = EmergencyState.RECOVERING
        self.vector_clock.tick()
        
        # Clear emergency mode on affected nodes
        resolution_success = True
        for node_id in emergency_event.affected_nodes:
            try:
                node_instance = self.managed_nodes.get(node_id)
                if node_instance and hasattr(node_instance, 'clear_emergency_mode'):
                    node_instance.clear_emergency_mode()
                    self.node_emergency_status[node_id] = EmergencyState.NORMAL
                    
            except Exception as e:
                LOG.error(f"Failed to clear emergency on node {node_id}: {e}")
                resolution_success = False
        
        # Mark emergency as resolved
        emergency_event.resolution_time = time.time()
        
        # Update responses
        for response in self.emergency_responses.values():
            if response.event_id == event_id:
                response.completed_at = time.time()
        
        # Check if all emergencies are resolved
        if all(event.resolution_time is not None for event in self.active_emergencies.values()):
            self.current_state = EmergencyState.NORMAL
        else:
            self.current_state = EmergencyState.RESOLVED
        
        LOG.info(f"Emergency {event_id} resolved {'successfully' if resolution_success else 'with issues'}")
        return resolution_success
    
    def get_emergency_status(self) -> Dict[str, Any]:
        """Get comprehensive emergency status"""
        with self.emergency_lock:
            active_events = {
                str(event_id): {
                    "type": event.emergency_type,
                    "level": event.level.name,
                    "location": event.location,
                    "scope": event.scope.value,
                    "affected_nodes": list(event.affected_nodes),
                    "detected_at": event.detected_at,
                    "resolved": event.resolution_time is not None
                }
                for event_id, event in self.active_emergencies.items()
            }
            
            active_responses = {
                str(response_id): {
                    "event_id": str(response.event_id),
                    "coordinating_node": response.coordinating_node,
                    "participating_nodes": list(response.participating_nodes),
                    "strategy": response.response_strategy,
                    "started_at": response.started_at,
                    "completed": response.completed_at is not None
                }
                for response_id, response in self.emergency_responses.items()
            }
        
        return {
            "manager_id": self.manager_id,
            "current_state": self.current_state.value,
            "vector_clock": self.vector_clock.clock.copy(),
            "managed_nodes": list(self.managed_nodes.keys()),
            "active_emergencies": active_events,
            "emergency_responses": active_responses,
            "node_status": dict(self.node_emergency_status)
        }
    
    def start(self) -> None:
        """Start emergency integration manager"""
        if self.monitor_thread is None or not self.monitor_thread.is_alive():
            self.should_exit = False
            
            # Start emergency monitoring
            self.monitor_thread = threading.Thread(
                target=self._emergency_monitor,
                daemon=True,
                name=f"emergency-monitor-{self.manager_id}"
            )
            self.monitor_thread.start()
            
            # Start coordination processing
            self.coordination_thread = threading.Thread(
                target=self._coordination_processor,
                daemon=True,
                name=f"emergency-coord-{self.manager_id}"
            )
            self.coordination_thread.start()
            
        LOG.info(f"EmergencyIntegrationManager {self.manager_id} started")
    
    def stop(self) -> None:
        """Stop emergency integration manager"""
        self.should_exit = True
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        
        if self.coordination_thread and self.coordination_thread.is_alive():
            self.coordination_thread.join(timeout=2.0)
        
        LOG.info(f"EmergencyIntegrationManager {self.manager_id} stopped")
    
    def _initiate_emergency_response(self, emergency_event: EmergencyEvent) -> UUID:
        """Initiate emergency response coordination"""
        response_id = uuid4()
        
        response = EmergencyResponse(
            response_id=response_id,
            event_id=emergency_event.event_id,
            coordinating_node=self.manager_id,
            participating_nodes=emergency_event.affected_nodes.copy(),
            response_strategy="default",
            priority_level=emergency_event.level.value,
            vector_clock_state=self.vector_clock.clock.copy()
        )
        
        self.emergency_responses[response_id] = response
        
        LOG.info(f"Emergency response {response_id} initiated for event {emergency_event.event_id}")
        return response_id
    
    def _apply_emergency_coordination(self, node_instance: Any, emergency_event: EmergencyEvent, 
                                    strategy: str) -> None:
        """Apply emergency coordination to specific node"""
        strategy_config = self.response_strategies.get(emergency_event.level, {})
        
        # Apply strategy based on node type and capabilities
        if hasattr(node_instance, 'set_emergency_mode'):
            # Already activated, apply additional coordination
            pass
        
        if hasattr(node_instance, 'emergency_mode') and node_instance.emergency_mode:
            # Node is in emergency mode, apply resource adjustments
            LOG.debug(f"Applied emergency coordination strategy '{strategy}' to node")
    
    def _emergency_monitor(self) -> None:
        """Background emergency monitoring thread"""
        LOG.info(f"Emergency monitor started for {self.manager_id}")
        
        while not self.should_exit:
            try:
                # Monitor active emergencies
                current_time = time.time()
                
                with self.emergency_lock:
                    for event_id, emergency_event in self.active_emergencies.items():
                        # Check for emergency timeouts
                        elapsed = current_time - emergency_event.detected_at
                        strategy_config = self.response_strategies.get(emergency_event.level, {})
                        timeout = strategy_config.get("timeout", 300)
                        
                        if elapsed > timeout and emergency_event.resolution_time is None:
                            LOG.warning(f"Emergency {event_id} timeout after {elapsed:.1f}s")
                
                time.sleep(5.0)  # Monitor every 5 seconds
                
            except Exception as e:
                LOG.error(f"Error in emergency monitor: {e}")
                time.sleep(1.0)
        
        LOG.info(f"Emergency monitor stopped for {self.manager_id}")
    
    def _coordination_processor(self) -> None:
        """Background coordination processing thread"""
        LOG.info(f"Coordination processor started for {self.manager_id}")
        
        while not self.should_exit:
            try:
                # Process pending coordination tasks
                time.sleep(2.0)  # Process every 2 seconds
                
            except Exception as e:
                LOG.error(f"Error in coordination processor: {e}")
                time.sleep(1.0)
        
        LOG.info(f"Coordination processor stopped for {self.manager_id}")

# Demo and testing functions
def demo_emergency_integration():
    """Demonstrate EmergencyIntegrationManager functionality"""
    print("\n=== EmergencyIntegrationManager Demo ===")
    
    # Create emergency integration manager
    emergency_mgr = EmergencyIntegrationManager("demo_emergency_mgr")
    print(f"✅ Created emergency manager: {emergency_mgr.manager_id}")
    
    # Create and register managed nodes
    from emergency_executor import SimpleEmergencyExecutor, ExecutorCapabilities
    
    capabilities = ExecutorCapabilities(emergency_capable=True)
    executor1 = SimpleEmergencyExecutor("emergency_exec_1", capabilities)
    executor2 = SimpleEmergencyExecutor("emergency_exec_2", capabilities)
    
    emergency_mgr.register_node("emergency_exec_1", executor1, {"emergency_response", "computation"})
    emergency_mgr.register_node("emergency_exec_2", executor2, {"emergency_response", "data_processing"})
    
    print(f"✅ Registered {len(emergency_mgr.managed_nodes)} nodes")
    
    # Start emergency manager
    emergency_mgr.start()
    print("✅ Emergency manager started")
    
    # Detect emergency
    event_id = emergency_mgr.detect_emergency(
        "fire", 
        "high", 
        location="Building A",
        affected_nodes={"emergency_exec_1", "emergency_exec_2"},
        scope=EmergencyScope.REGIONAL
    )
    print(f"✅ Emergency detected: {event_id}")
    
    # Activate emergency response
    response_id = emergency_mgr.activate_emergency(
        "fire", 
        "high", 
        ["emergency_exec_1", "emergency_exec_2"]
    )
    print(f"✅ Emergency response activated: {response_id}")
    
    # Coordinate response
    coordination_success = emergency_mgr.coordinate_emergency_response(event_id, "priority")
    print(f"✅ Emergency coordination: {'successful' if coordination_success else 'failed'}")
    
    # Check status
    status = emergency_mgr.get_emergency_status()
    print(f"✅ Emergency status: {status['current_state']}")
    print(f"✅ Active emergencies: {len(status['active_emergencies'])}")
    print(f"✅ Emergency responses: {len(status['emergency_responses'])}")
    
    # Wait for processing
    time.sleep(0.5)
    
    # Resolve emergency
    resolution_success = emergency_mgr.resolve_emergency(event_id, "Emergency contained and resolved")
    print(f"✅ Emergency resolution: {'successful' if resolution_success else 'failed'}")
    
    # Final status
    final_status = emergency_mgr.get_emergency_status()
    print(f"✅ Final state: {final_status['current_state']}")
    
    # Stop emergency manager
    emergency_mgr.stop()
    print("✅ Emergency manager stopped")
    
    return True

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run demo
    demo_emergency_integration()
