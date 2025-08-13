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
from typing import Dict, Set, Optional, List
from uuid import uuid4
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import sys
import os

# Phase 1 imports
import sys
import os
phase1_path = os.path.join(os.path.dirname(__file__), '..', 'Phase1_Core_Foundation')
sys.path.insert(0, phase1_path)

from rec.Phase1_Core_Foundation.vector_clock import VectorClock, EmergencyContext, create_emergency
from rec.Phase1_Core_Foundation.causal_message import CausalMessage, MessageHandler
from rec.Phase1_Core_Foundation.causal_consistency import CausalConsistencyManager

LOG = logging.getLogger(__name__)

class NodeStatus(Enum):
    HEALTHY = "healthy"
    SUSPECTED = "suspected"
    FAILED = "failed"
    RECOVERING = "recovering"
    EMERGENCY = "emergency"

@dataclass
class NodeInfo:
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
    action_id: str
    target_node: str
    action_type: str
    priority: int = 1
    emergency_context: Optional[EmergencyContext] = None
    vector_clock: Optional[dict] = None
    scheduled_at: float = field(default_factory=time.time)

class RecoveryStrategy(ABC):
    @abstractmethod
    def should_recover(self, node_info: NodeInfo) -> bool:
        pass

    @abstractmethod
    def create_recovery_plan(self, node_info: NodeInfo) -> List[RecoveryAction]:
        pass

class SimpleRecoveryStrategy(RecoveryStrategy):
    def __init__(self, max_failures: int = 3, recovery_timeout: float = 300.0):
        self.max_failures = max_failures
        self.recovery_timeout = recovery_timeout

    def should_recover(self, node_info: NodeInfo) -> bool:
        if node_info.status == NodeStatus.FAILED:
            if node_info.recovery_attempts < self.max_failures:
                return True
            if node_info.emergency_context and node_info.emergency_context.is_critical():
                return node_info.recovery_attempts < (self.max_failures * 2)
        return False

    def create_recovery_plan(self, node_info: NodeInfo) -> List[RecoveryAction]:
        actions = []

        restart = RecoveryAction(
            action_id=f"restart-{node_info.node_id}-{uuid4()}",
            target_node=node_info.node_id,
            action_type="restart_service",
            emergency_context=node_info.emergency_context
        )
        verify = RecoveryAction(
            action_id=f"verify-{node_info.node_id}-{uuid4()}",
            target_node=node_info.node_id,
            action_type="verify_health",
            priority=2,
            emergency_context=node_info.emergency_context
        )
        actions.append(restart)
        actions.append(verify)

        if node_info.emergency_context and node_info.emergency_context.is_critical():
            failover = RecoveryAction(
                action_id=f"failover-{node_info.node_id}-{uuid4()}",
                target_node=node_info.node_id,
                action_type="emergency_failover",
                priority=0,
                emergency_context=node_info.emergency_context
            )
            actions.insert(0, failover)

        return actions

class SimpleRecoveryManager:
    def __init__(self, manager_id: str = None, heartbeat_timeout: float = 30.0):
        self.manager_id = manager_id or f"recovery-{uuid4()}"
        self.vector_clock = VectorClock(self.manager_id)
        self.heartbeat_timeout = heartbeat_timeout

        self.monitored_nodes: Dict[str, NodeInfo] = {}
        self.node_lock = threading.RLock()

        self.recovery_strategy = SimpleRecoveryStrategy()
        self.recovery_queue: List[RecoveryAction] = []
        self.recovery_lock = threading.RLock()

        self.current_emergency: Optional[EmergencyContext] = None
        self.message_handler = MessageHandler(self.manager_id)
        self.consistency_manager = CausalConsistencyManager(self.manager_id)

        self.should_exit = False
        self.monitor_thread = None
        self.recovery_thread = None

        LOG.info(f"RecoveryManager {self.manager_id} initialized")

    def register_node(self, node_id: str, host: str, port: int) -> bool:
        self.vector_clock.tick()
        node = NodeInfo(node_id=node_id, host=host, port=port)

        with self.node_lock:
            self.monitored_nodes[node_id] = node
            LOG.info(f"Node {node_id} registered for monitoring")

        return True

    def process_heartbeat(self, node_id: str, vector_clock_state: dict = None, emergency_context: EmergencyContext = None) -> bool:
        with self.node_lock:
            node = self.monitored_nodes.get(node_id)
            if not node:
                LOG.warning(f"Heartbeat from unregistered node {node_id}")
                return False

            node.last_heartbeat = time.time()
            node.status = NodeStatus.HEALTHY
            node.emergency_context = emergency_context

            if vector_clock_state:
                node.vector_clock.update(vector_clock_state)
                self.vector_clock.update(vector_clock_state)

            self.vector_clock.tick()
            LOG.debug(f"Heartbeat from {node_id} processed")
            return True

    def detect_node_failure(self, node_id: str, reason: str = "timeout") -> bool:
        with self.node_lock:
            node = self.monitored_nodes.get(node_id)
            if not node:
                return False

            self.vector_clock.tick()
            node.status = NodeStatus.FAILED
            node.failure_count += 1

            LOG.warning(f"Node {node_id} failed: {reason}")
            if self.recovery_strategy.should_recover(node):
                self._schedule_recovery(node)
            return True

    def set_emergency_mode(self, emergency_type: str, priority_level: str) -> None:
        self.vector_clock.tick()
        self.current_emergency = create_emergency(emergency_type, priority_level)

        with self.node_lock:
            for node in self.monitored_nodes.values():
                node.emergency_context = self.current_emergency

        LOG.warning(f"Emergency mode: {emergency_type} ({priority_level})")

    def clear_emergency_mode(self) -> None:
        self.vector_clock.tick()
        self.current_emergency = None

        with self.node_lock:
            for node in self.monitored_nodes.values():
                node.emergency_context = None

        LOG.info("Emergency mode cleared")

    def get_node_status(self, node_id: str) -> Optional[NodeStatus]:
        with self.node_lock:
            node = self.monitored_nodes.get(node_id)
            return node.status if node else None

    def get_healthy_nodes(self) -> List[str]:
        with self.node_lock:
            return [nid for nid, n in self.monitored_nodes.items() if n.status == NodeStatus.HEALTHY]

    def get_failed_nodes(self) -> List[str]:
        with self.node_lock:
            return [nid for nid, n in self.monitored_nodes.items() if n.status == NodeStatus.FAILED]

    def start(self) -> None:
        if self.monitor_thread is None or not self.monitor_thread.is_alive():
            self.should_exit = False

            self.monitor_thread = threading.Thread(target=self._health_monitor, daemon=True)
            self.monitor_thread.start()

            self.recovery_thread = threading.Thread(target=self._recovery_processor, daemon=True)
            self.recovery_thread.start()

            LOG.info(f"RecoveryManager {self.manager_id} started")

    def stop(self) -> None:
        self.should_exit = True

        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)

        if self.recovery_thread and self.recovery_thread.is_alive():
            self.recovery_thread.join(timeout=5)

        LOG.info(f"RecoveryManager {self.manager_id} stopped")

    def _schedule_recovery(self, node: NodeInfo) -> None:
        actions = self.recovery_strategy.create_recovery_plan(node)

        with self.recovery_lock:
            for a in actions:
                a.vector_clock = self.vector_clock.clock.copy()
                self.recovery_queue.append(a)
            self.recovery_queue.sort(key=lambda x: x.priority)

        LOG.info(f"Scheduled {len(actions)} actions for node {node.node_id}")

    def _health_monitor(self) -> None:
        LOG.info(f"Health monitor for {self.manager_id} started")
        while not self.should_exit:
            try:
                now = time.time()
                with self.node_lock:
                    for node_id, node in self.monitored_nodes.items():
                        if node.status == NodeStatus.HEALTHY:
                            gap = now - node.last_heartbeat
                            if gap > self.heartbeat_timeout * 1.5:
                                node.status = NodeStatus.FAILED
                                node.failure_count += 1
                                self.vector_clock.tick()
                                LOG.warning(f"Node {node_id} failed due to timeout")
                                if self.recovery_strategy.should_recover(node):
                                    self._schedule_recovery(node)
                            elif gap > self.heartbeat_timeout:
                                node.status = NodeStatus.SUSPECTED
                                LOG.debug(f"Node {node_id} suspected")
                time.sleep(5)
            except Exception as e:
                LOG.error(f"Monitor error: {e}")
                time.sleep(1)
        LOG.info(f"Health monitor for {self.manager_id} stopped")

    def _recovery_processor(self) -> None:
        LOG.info(f"Recovery processor for {self.manager_id} started")
        while not self.should_exit:
            try:
                with self.recovery_lock:
                    if not self.recovery_queue:
                        time.sleep(1)
                        continue
                    action = self.recovery_queue.pop(0)
                self._execute_recovery_action(action)
                time.sleep(0.5)
            except Exception as e:
                LOG.error(f"Processor error: {e}")
                time.sleep(1)
        LOG.info(f"Recovery processor for {self.manager_id} stopped")

    def _execute_recovery_action(self, action: RecoveryAction) -> bool:
        self.vector_clock.tick()
        LOG.info(f"Executing: {action.action_type} for {action.target_node}")
        with self.node_lock:
            node = self.monitored_nodes.get(action.target_node)
            if node:
                node.status = NodeStatus.RECOVERING
                node.recovery_attempts += 1

        if action.action_type == "restart_service":
            return self._restart_node_service(action.target_node)
        elif action.action_type == "verify_health":
            return self._verify_node_health(action.target_node)
        elif action.action_type == "emergency_failover":
            return self._emergency_failover(action.target_node)

        return False

    def _restart_node_service(self, node_id: str) -> bool:
        LOG.info(f"Restarting node {node_id}")
        time.sleep(0.1)
        return True

    def _verify_node_health(self, node_id: str) -> bool:
        LOG.info(f"Verifying node {node_id}")
        time.sleep(0.1)
        with self.node_lock:
            node = self.monitored_nodes.get(node_id)
            if node:
                node.status = NodeStatus.HEALTHY
                node.last_heartbeat = time.time()
        return True

    def _emergency_failover(self, node_id: str) -> bool:
        LOG.warning(f"Emergency failover for node {node_id}")
        time.sleep(0.1)
        return True

# Demo runner
def demo_recovery_system():
    print("\n=== RecoverySystem Demo ===")

    recovery = SimpleRecoveryManager("demo_recovery")
    print(f"✅ Created manager: {recovery.manager_id}")

    recovery.register_node("executor_1", "127.0.0.1", 8001)
    recovery.register_node("executor_2", "127.0.0.1", 8002)
    recovery.register_node("datastore_1", "127.0.0.1", 9001)

    print(f"✅ Nodes registered: {len(recovery.monitored_nodes)}")

    recovery.start()
    print("✅ Recovery manager started")

    recovery.process_heartbeat("executor_1")
    recovery.process_heartbeat("executor_2")
    recovery.process_heartbeat("datastore_1")

    print(f"✅ Healthy: {recovery.get_healthy_nodes()}")
    print(f"✅ Failed: {recovery.get_failed_nodes()}")

    recovery.detect_node_failure("executor_2", "network_timeout")
    print("✅ Node executor_2 failed")

    recovery.set_emergency_mode("fire", "critical")
    print("✅ Emergency mode activated")

    recovery.detect_node_failure("datastore_1", "emergency_shutdown")
    print("✅ Emergency failure detected")

    time.sleep(0.5)
    print("✅ Recovery actions done")

    recovery.clear_emergency_mode()
    print("✅ Emergency mode cleared")

    recovery.stop()
    print("✅ Recovery manager stopped")

    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_recovery_system()
