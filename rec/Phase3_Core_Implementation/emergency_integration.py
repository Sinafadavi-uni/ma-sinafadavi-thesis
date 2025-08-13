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

import sys
import os
phase1_path = os.path.join(os.path.dirname(__file__), '..', 'Phase1_Core_Foundation')
sys.path.insert(0, phase1_path)

from rec.Phase1_Core_Foundation.vector_clock import VectorClock, EmergencyContext, EmergencyLevel, create_emergency
from rec.Phase1_Core_Foundation.causal_message import CausalMessage, MessageHandler
from rec.Phase1_Core_Foundation.causal_consistency import CausalConsistencyManager

phase2_path = os.path.join(os.path.dirname(__file__), '..', 'Phase2_Node_Infrastructure')
sys.path.insert(0, phase2_path)

from rec.Phase2_Node_Infrastructure.recovery_system import SimpleRecoveryManager
from rec.Phase2_Node_Infrastructure.emergency_executor import SimpleEmergencyExecutor

LOG = logging.getLogger(__name__)

class EmergencyState(Enum):
    NORMAL = "normal"
    DETECTING = "detecting"
    RESPONDING = "responding"
    COORDINATING = "coordinating"
    RECOVERING = "recovering"
    RESOLVED = "resolved"

class EmergencyScope(Enum):
    LOCAL = "local"
    REGIONAL = "regional"
    GLOBAL = "global"
    CRITICAL_INFRASTRUCTURE = "critical_infrastructure"

@dataclass
class EmergencyEvent:
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
    def __init__(self, manager_id: str = None):
        self.manager_id = manager_id or f"emergency-mgr-{uuid4()}"
        self.vector_clock = VectorClock(self.manager_id)

        self.current_state = EmergencyState.NORMAL
        self.active_emergencies = {}
        self.emergency_responses = {}
        self.emergency_lock = threading.RLock()

        self.managed_nodes = {}
        self.node_capabilities = {}
        self.node_emergency_status = {}

        self.emergency_protocols = {}
        self.response_strategies = {
            EmergencyLevel.LOW: {"timeout": 300, "resources": "normal"},
            EmergencyLevel.MEDIUM: {"timeout": 180, "resources": "increased"},
            EmergencyLevel.HIGH: {"timeout": 60, "resources": "priority"},
            EmergencyLevel.CRITICAL: {"timeout": 30, "resources": "maximum"}
        }

        self.message_handler = MessageHandler(self.manager_id)
        self.consistency_manager = CausalConsistencyManager(self.manager_id)

        self.should_exit = False
        self.monitor_thread = None
        self.coordination_thread = None

        LOG.info(f"EmergencyIntegrationManager {self.manager_id} initialized")

    def register_node(self, node_id: str, node_instance: Any, capabilities: Set[str] = None) -> None:
        self.managed_nodes[node_id] = node_instance
        self.node_capabilities[node_id] = capabilities or set()
        self.node_emergency_status[node_id] = EmergencyState.NORMAL
        LOG.info(f"Node {node_id} registered for emergency management")

    def detect_emergency(self, emergency_type: str, level: str, location: str = None,
                         affected_nodes: Set[str] = None, scope: EmergencyScope = EmergencyScope.LOCAL) -> UUID:
        self.vector_clock.tick()
        event_id = uuid4()
        emergency_context = create_emergency(emergency_type, level, location)

        event = EmergencyEvent(
            event_id=event_id,
            emergency_type=emergency_type,
            level=emergency_context.level,
            location=location,
            scope=scope,
            vector_clock_snapshot=self.vector_clock.clock.copy(),
            affected_nodes=affected_nodes or set()
        )

        with self.emergency_lock:
            self.active_emergencies[event_id] = event
            self.current_state = EmergencyState.DETECTING

        self._initiate_emergency_response(event)
        LOG.warning(f"Emergency detected: {emergency_type} ({level}) - ID: {event_id}")
        return event_id

    def activate_emergency(self, emergency_type: str, level: str, participating_nodes: List[str]) -> UUID:
        event_id = self.detect_emergency(emergency_type, level, affected_nodes=set(participating_nodes),
                                         scope=EmergencyScope.REGIONAL if len(participating_nodes) > 1 else EmergencyScope.LOCAL)

        event = self.active_emergencies[event_id]
        activated_nodes = set()

        for node_id in participating_nodes:
            if node_id in self.managed_nodes:
                node = self.managed_nodes[node_id]
                if hasattr(node, 'set_emergency_mode'):
                    try:
                        node.set_emergency_mode(emergency_type, level)
                        activated_nodes.add(node_id)
                        self.node_emergency_status[node_id] = EmergencyState.RESPONDING
                        LOG.info(f"Emergency mode set on node {node_id}")
                    except Exception as e:
                        LOG.error(f"Failed to activate emergency on node {node_id}: {e}")

        event.affected_nodes = activated_nodes

        for resp_id, response in self.emergency_responses.items():
            if response.event_id == event_id:
                response.participating_nodes = activated_nodes
                return resp_id

        LOG.warning(f"Emergency {emergency_type} activated on {len(activated_nodes)} nodes")
        return uuid4()

    def _initiate_emergency_response(self, emergency_event: EmergencyEvent) -> UUID:
        response_id = uuid4()
        response = EmergencyResponse(
            response_id=response_id,
            event_id=emergency_event.event_id,
            coordinating_node=self.manager_id,
            participating_nodes=emergency_event.affected_nodes.copy(),
            priority_level=emergency_event.level.value,
            vector_clock_state=self.vector_clock.clock.copy()
        )
        self.emergency_responses[response_id] = response
        LOG.info(f"Emergency response {response_id} initiated for event {emergency_event.event_id}")
        return response_id

    def coordinate_emergency_response(self, event_id: UUID, strategy: str = "default") -> bool:
        with self.emergency_lock:
            event = self.active_emergencies.get(event_id)
            if not event:
                LOG.error(f"Event {event_id} not found")
                return False

        self.current_state = EmergencyState.COORDINATING
        self.vector_clock.tick()

        msg = CausalMessage(
            content={
                "event_id": str(event_id),
                "emergency_type": event.emergency_type,
                "level": event.level.name,
                "coordination_action": "coordinate_response",
                "strategy": strategy
            },
            sender_id=self.manager_id,
            vector_clock=self.vector_clock.clock.copy(),
            message_type="emergency",
            priority=10
        )

        success = True
        for node_id in event.affected_nodes:
            node = self.managed_nodes.get(node_id)
            if node:
                try:
                    if hasattr(node, 'vector_clock'):
                        node.vector_clock.update(self.vector_clock.clock)
                    self._apply_emergency_coordination(node, event, strategy)
                except Exception as e:
                    LOG.error(f"Coordination failed for node {node_id}: {e}")
                    success = False

        LOG.info(f"Coordination for {event_id} {'succeeded' if success else 'partially succeeded'}")
        return success

    def _apply_emergency_coordination(self, node, event, strategy):
        if hasattr(node, 'emergency_mode') and node.emergency_mode:
            LOG.debug(f"Applying strategy {strategy} to node during emergency")

    def resolve_emergency(self, event_id: UUID, resolution_notes: str = None) -> bool:
        with self.emergency_lock:
            event = self.active_emergencies.get(event_id)
            if not event:
                LOG.error(f"Event {event_id} not found")
                return False

        self.current_state = EmergencyState.RECOVERING
        self.vector_clock.tick()

        success = True
        for node_id in event.affected_nodes:
            node = self.managed_nodes.get(node_id)
            if node and hasattr(node, 'clear_emergency_mode'):
                try:
                    node.clear_emergency_mode()
                    self.node_emergency_status[node_id] = EmergencyState.NORMAL
                except Exception as e:
                    LOG.error(f"Failed to resolve emergency for {node_id}: {e}")
                    success = False

        event.resolution_time = time.time()

        for response in self.emergency_responses.values():
            if response.event_id == event_id:
                response.completed_at = time.time()

        self.current_state = EmergencyState.NORMAL if all(ev.resolution_time for ev in self.active_emergencies.values()) else EmergencyState.RESOLVED
        LOG.info(f"Emergency {event_id} resolved")
        return success

    def get_emergency_status(self) -> Dict[str, Any]:
        with self.emergency_lock:
            active = {
                str(eid): {
                    "type": e.emergency_type,
                    "level": e.level.name,
                    "location": e.location,
                    "scope": e.scope.value,
                    "affected_nodes": list(e.affected_nodes),
                    "detected_at": e.detected_at,
                    "resolved": e.resolution_time is not None
                }
                for eid, e in self.active_emergencies.items()
            }

            responses = {
                str(rid): {
                    "event_id": str(r.event_id),
                    "coordinating_node": r.coordinating_node,
                    "participating_nodes": list(r.participating_nodes),
                    "strategy": r.response_strategy,
                    "started_at": r.started_at,
                    "completed": r.completed_at is not None
                }
                for rid, r in self.emergency_responses.items()
            }

        return {
            "manager_id": self.manager_id,
            "current_state": self.current_state.value,
            "vector_clock": self.vector_clock.clock.copy(),
            "managed_nodes": list(self.managed_nodes.keys()),
            "active_emergencies": active,
            "emergency_responses": responses,
            "node_status": dict(self.node_emergency_status)
        }

    def start(self):
        if self.monitor_thread is None or not self.monitor_thread.is_alive():
            self.should_exit = False
            self.monitor_thread = threading.Thread(target=self._emergency_monitor, daemon=True)
            self.monitor_thread.start()
            self.coordination_thread = threading.Thread(target=self._coordination_processor, daemon=True)
            self.coordination_thread.start()
        LOG.info(f"EmergencyIntegrationManager {self.manager_id} started")

    def stop(self):
        self.should_exit = True
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        if self.coordination_thread and self.coordination_thread.is_alive():
            self.coordination_thread.join(timeout=2)
        LOG.info(f"EmergencyIntegrationManager {self.manager_id} stopped")

    def _emergency_monitor(self):
        LOG.info(f"Emergency monitor started for {self.manager_id}")
        while not self.should_exit:
            try:
                now = time.time()
                with self.emergency_lock:
                    for eid, e in self.active_emergencies.items():
                        elapsed = now - e.detected_at
                        config = self.response_strategies.get(e.level, {})
                        if elapsed > config.get("timeout", 300) and not e.resolution_time:
                            LOG.warning(f"Emergency {eid} timed out after {elapsed:.1f}s")
                time.sleep(5)
            except Exception as err:
                LOG.error(f"Emergency monitor error: {err}")
                time.sleep(1)
        LOG.info(f"Emergency monitor stopped for {self.manager_id}")

    def _coordination_processor(self):
        LOG.info(f"Coordination processor started for {self.manager_id}")
        while not self.should_exit:
            try:
                time.sleep(2)
            except Exception as err:
                LOG.error(f"Coordination processor error: {err}")
                time.sleep(1)
        LOG.info(f"Coordination processor stopped for {self.manager_id}")

def demo_emergency_integration():
    print("\n=== Emergency Integration Demo ===")
    
    # Create emergency manager
    manager = EmergencyIntegrationManager("emergency_coordinator")
    print("✅ Emergency integration manager created")
    
    # Create test nodes
    executor1 = SimpleEmergencyExecutor("emergency_node1")
    executor2 = SimpleEmergencyExecutor("emergency_node2")
    
    # Register nodes with manager
    manager.register_node("emergency_node1", executor1, {"compute", "emergency"})
    manager.register_node("emergency_node2", executor2, {"storage", "emergency"})
    print("✅ Emergency-capable nodes registered")
    
    # Start manager and nodes
    manager.start()
    executor1.start()
    executor2.start()
    print("✅ Emergency system started")
    
    # Detect and activate emergency
    event_id = manager.detect_emergency("fire", "critical", "Building A")
    response_id = manager.activate_emergency("fire", "critical", ["emergency_node1", "emergency_node2"])
    print("✅ Emergency detected and activated")
    
    # Coordinate emergency response
    coordination_success = manager.coordinate_emergency_response(event_id, "evacuation_protocol")
    print(f"✅ Emergency coordination: {'successful' if coordination_success else 'partial'}")
    
    # Get emergency status
    status = manager.get_emergency_status()
    print(f"✅ Managing {len(status['active_emergencies'])} active emergencies")
    print(f"✅ Emergency responses: {len(status['emergency_responses'])}")
    
    # Resolve emergency
    time.sleep(0.5)
    resolved = manager.resolve_emergency(event_id, "Emergency contained successfully")
    print(f"✅ Emergency resolution: {'successful' if resolved else 'failed'}")
    
    # Stop everything
    executor1.stop()
    executor2.stop() 
    manager.stop()
    print("✅ Emergency integration system stopped")
    
    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_emergency_integration()
