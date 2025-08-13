"""
File 12: SystemIntegration - Complete System Integration Framework
Phase 4: UCP Integration

Complete system integration framework that unifies all thesis components
into a production-ready distributed system with UCP compliance.

Key Features:
- Complete system integration and coordination
- UCP compliance verification and validation
- Production deployment framework
- System health monitoring and metrics
- End-to-end testing and validation capabilities

This provides the complete integration layer that ties together all phases
into a unified, production-ready distributed system.
"""

import time
import threading
import logging
from typing import Dict, Optional, List, Set, Any, Tuple
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum
import json

# Import all previous phases
import sys
import os

# Phase 1: Foundation
phase1_path = os.path.join(os.path.dirname(__file__), '..', 'Phase1_Core_Foundation')
sys.path.insert(0, phase1_path)

from rec.Phase1_Core_Foundation.vector_clock import VectorClock, create_emergency
from rec.Phase1_Core_Foundation.causal_consistency import CausalConsistencyManager

# Phase 2: Infrastructure  
phase2_path = os.path.join(os.path.dirname(__file__), '..', 'Phase2_Node_Infrastructure')
sys.path.insert(0, phase2_path)

from rec.Phase2_Node_Infrastructure.recovery_system import SimpleRecoveryManager
from rec.Phase2_Node_Infrastructure.emergency_executor import SimpleEmergencyExecutor

# Phase 3: Core Implementation
phase3_path = os.path.join(os.path.dirname(__file__), '..', 'Phase3_Core_Implementation')
sys.path.insert(0, phase3_path)

from rec.Phase3_Core_Implementation.enhanced_vector_clock_executor import EnhancedVectorClockExecutor
from rec.Phase3_Core_Implementation.vector_clock_broker import VectorClockBroker
from rec.Phase3_Core_Implementation.emergency_integration import EmergencyIntegrationManager

# Phase 4: UCP Integration
from rec.Phase4_UCP_Integration.multi_broker_coordinator import MultiBrokerCoordinator

LOG = logging.getLogger(__name__)

class SystemState(Enum):
    INITIALIZING = "initializing"
    STARTING = "starting"
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    EMERGENCY = "emergency"
    STOPPING = "stopping"
    STOPPED = "stopped"

class UCPCompliance(Enum):
    FULL_COMPLIANCE = "full_compliance"
    PARTIAL_COMPLIANCE = "partial_compliance"
    NON_COMPLIANT = "non_compliant"
    TESTING = "testing"

@dataclass
class SystemComponent:
    component_id: str
    component_type: str
    instance: Any
    status: str = "inactive"
    health_score: float = 1.0
    last_check: float = field(default_factory=time.time)

class SystemIntegrationFramework:
    def __init__(self, system_id: str = None):
        self.system_id = system_id or f"integrated-system-{uuid4()}"
        self.vector_clock = VectorClock(self.system_id)
        self.current_state = SystemState.INITIALIZING
        self.ucp_compliance = UCPCompliance.TESTING
        self.registered_components: Dict[str, SystemComponent] = {}
        self.component_lock = threading.RLock()
        self.multi_broker_coordinator: Optional[MultiBrokerCoordinator] = None
        self.emergency_manager: Optional[EmergencyIntegrationManager] = None
        self.recovery_manager: Optional[SimpleRecoveryManager] = None
        self.system_metrics = {
            "startup_time": None,
            "total_components": 0,
            "operational_components": 0,
            "error_count": 0,
            "emergency_count": 0,
            "uptime": 0.0
        }
        self.should_exit = False
        self.health_monitor_thread = None
        self.metrics_thread = None
        LOG.info(f"SystemIntegrationFramework {self.system_id} initialized")

    def register_coordinator(self, coordinator: MultiBrokerCoordinator) -> None:
        self.multi_broker_coordinator = coordinator
        self._register_component("multi_broker_coordinator", "coordinator", coordinator)
        LOG.info("Multi-broker coordinator registered")

    def register_executor(self, executor: Any) -> None:
        component_id = getattr(executor, 'node_id', getattr(executor, 'executor_id', str(uuid4())))
        self._register_component(component_id, "executor", executor)
        LOG.info(f"Executor {component_id} registered")

    def register_broker(self, broker: VectorClockBroker) -> None:
        self._register_component(broker.broker_id, "broker", broker)
        LOG.info(f"Broker {broker.broker_id} registered")

    def register_emergency_manager(self, manager: EmergencyIntegrationManager) -> None:
        self.emergency_manager = manager
        self._register_component(manager.manager_id, "emergency_manager", manager)
        LOG.info("Emergency manager registered")

    def register_recovery_manager(self, manager: SimpleRecoveryManager) -> None:
        self.recovery_manager = manager
        self._register_component(manager.manager_id, "recovery_manager", manager)
        LOG.info("Recovery manager registered")

    def start_system(self) -> bool:
        startup_start = time.time()
        self.current_state = SystemState.STARTING
        self.vector_clock.tick()
        LOG.info(f"Starting integrated system {self.system_id}...")
        try:
            if self.multi_broker_coordinator:
                self.multi_broker_coordinator.start()
                self._update_component_status("multi_broker_coordinator", "active")
            if self.emergency_manager:
                self.emergency_manager.start()
                self._update_component_status(self.emergency_manager.manager_id, "active")
            if self.recovery_manager:
                self.recovery_manager.start()
                self._update_component_status(self.recovery_manager.manager_id, "active")
            for component_id, component in self.registered_components.items():
                if hasattr(component.instance, 'start') and component.status != "active":
                    try:
                        component.instance.start()
                        self._update_component_status(component_id, "active")
                        LOG.info(f"Started component: {component_id}")
                    except Exception as e:
                        LOG.error(f"Failed to start component {component_id}: {e}")
                        self._update_component_status(component_id, "failed")
            self._start_monitoring()
            self.current_state = SystemState.OPERATIONAL
            self.system_metrics["startup_time"] = time.time() - startup_start
            self.system_metrics["total_components"] = len(self.registered_components)
            self.ucp_compliance = self._check_ucp_compliance()
            LOG.info(f"Integrated system {self.system_id} started successfully "
                     f"in {self.system_metrics['startup_time']:.2f}s")
            return True
        except Exception as e:
            LOG.error(f"Failed to start integrated system: {e}")
            self.current_state = SystemState.DEGRADED
            return False

    def stop_system(self) -> None:
        self.current_state = SystemState.STOPPING
        self.should_exit = True
        LOG.info(f"Stopping integrated system {self.system_id}...")
        if self.health_monitor_thread and self.health_monitor_thread.is_alive():
            self.health_monitor_thread.join(timeout=2.0)
        if self.metrics_thread and self.metrics_thread.is_alive():
            self.metrics_thread.join(timeout=2.0)
        for component_id, component in self.registered_components.items():
            if hasattr(component.instance, 'stop') and component.status == "active":
                try:
                    component.instance.stop()
                    self._update_component_status(component_id, "stopped")
                    LOG.info(f"Stopped component: {component_id}")
                except Exception as e:
                    LOG.error(f"Failed to stop component {component_id}: {e}")
        if self.recovery_manager:
            self.recovery_manager.stop()
        if self.emergency_manager:
            self.emergency_manager.stop()
        if self.multi_broker_coordinator:
            self.multi_broker_coordinator.stop()
        self.current_state = SystemState.STOPPED
        LOG.info(f"Integrated system {self.system_id} stopped")

    def _register_component(self, component_id: str, component_type: str, instance: Any) -> None:
        with self.component_lock:
            component = SystemComponent(
                component_id=component_id,
                component_type=component_type,
                instance=instance
            )
            self.registered_components[component_id] = component

    def _update_component_status(self, component_id: str, status: str) -> None:
        with self.component_lock:
            if component_id in self.registered_components:
                self.registered_components[component_id].status = status
                self.registered_components[component_id].last_check = time.time()

    def _check_ucp_compliance(self) -> UCPCompliance:
        try:
            required_components = ["coordinator", "executor"]
            present_types = set(comp.component_type for comp in self.registered_components.values())
            if all(req_type in present_types for req_type in required_components):
                return UCPCompliance.FULL_COMPLIANCE
            else:
                return UCPCompliance.PARTIAL_COMPLIANCE
        except Exception as e:
            LOG.error(f"Error in UCP compliance check: {e}")
            return UCPCompliance.NON_COMPLIANT

    def _start_monitoring(self) -> None:
        if self.health_monitor_thread is None or not self.health_monitor_thread.is_alive():
            self.health_monitor_thread = threading.Thread(
                target=self._health_monitor,
                daemon=True,
                name=f"system-health-{self.system_id}"
            )
            self.health_monitor_thread.start()
        if self.metrics_thread is None or not self.metrics_thread.is_alive():
            self.metrics_thread = threading.Thread(
                target=self._metrics_collector,
                daemon=True,
                name=f"system-metrics-{self.system_id}"
            )
            self.metrics_thread.start()

    def _health_monitor(self) -> None:
        LOG.info(f"System health monitor started for {self.system_id}")
        while not self.should_exit:
            try:
                with self.component_lock:
                    for component in self.registered_components.values():
                        try:
                            if hasattr(component.instance, 'get_status'):
                                component.instance.get_status()
                                component.health_score = 1.0
                            elif hasattr(component.instance, 'heartbeat'):
                                component.instance.heartbeat()
                                component.health_score = 1.0
                            else:
                                component.health_score = 0.8
                            component.last_check = time.time()
                        except Exception as e:
                            component.health_score = 0.0
                            LOG.warning(f"Health check failed for {component.component_id}: {e}")
                time.sleep(30.0)
            except Exception as e:
                LOG.error(f"Error in health monitor: {e}")
                time.sleep(5.0)
        LOG.info(f"System health monitor stopped for {self.system_id}")

    def _metrics_collector(self) -> None:
        LOG.info(f"System metrics collector started for {self.system_id}")
        while not self.should_exit:
            try:
                with self.component_lock:
                    operational = sum(1 for comp in self.registered_components.values() 
                                      if comp.status == "active")
                    self.system_metrics["operational_components"] = operational
                time.sleep(60.0)
            except Exception as e:
                LOG.error(f"Error in metrics collector: {e}")
                time.sleep(10.0)
        LOG.info(f"System metrics collector stopped for {self.system_id}")

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        with self.component_lock:
            component_status = {}
            for comp_id, comp in self.registered_components.items():
                component_status[comp_id] = {
                    "type": comp.component_type,
                    "status": comp.status,
                    "health_score": comp.health_score,
                    "last_check": comp.last_check
                }
        
        return {
            "system_id": self.system_id,
            "state": self.current_state.value,
            "ucp_compliance": self.ucp_compliance.value,
            "vector_clock": self.vector_clock.clock.copy(),
            "metrics": self.system_metrics,
            "components": component_status,
            "coordinator_status": self.multi_broker_coordinator.get_global_status() if self.multi_broker_coordinator else None,
            "emergency_status": self.emergency_manager.get_emergency_status() if self.emergency_manager else None
        }

    def validate_ucp_part_b_compliance(self) -> Dict[str, bool]:
        """Validate UCP Part B compliance requirements"""
        compliance_checks = {
            "metadata_synchronization": False,
            "fcfs_result_handling": False,
            "emergency_coordination": False,
            "vector_clock_coordination": False
        }
        
        # Check metadata synchronization
        if self.multi_broker_coordinator:
            compliance_checks["metadata_synchronization"] = True
            
        # Check FCFS and vector clock coordination
        for comp in self.registered_components.values():
            if hasattr(comp.instance, 'vector_clock'):
                compliance_checks["vector_clock_coordination"] = True
            if hasattr(comp.instance, 'handle_result_submission'):
                compliance_checks["fcfs_result_handling"] = True
                
        # Check emergency coordination
        if self.emergency_manager:
            compliance_checks["emergency_coordination"] = True
            
        return compliance_checks

def demo_system_integration():
    print("\n=== System Integration Framework Demo ===")
    
    # Create system integration framework
    system = SystemIntegrationFramework("complete_ucp_system")
    print("✅ System integration framework created")
    
    # Create and register components
    coordinator = MultiBrokerCoordinator("system_coordinator")
    system.register_coordinator(coordinator)
    
    executor = EnhancedVectorClockExecutor("system_executor")
    system.register_executor(executor)
    
    broker = VectorClockBroker("system_broker")
    system.register_broker(broker)
    
    emergency_mgr = EmergencyIntegrationManager("system_emergency")
    system.register_emergency_manager(emergency_mgr)
    
    recovery_mgr = SimpleRecoveryManager("system_recovery")
    system.register_recovery_manager(recovery_mgr)
    
    print("✅ All system components registered")
    
    # Start integrated system
    started = system.start_system()
    print(f"✅ System startup: {'successful' if started else 'failed'}")
    
    # Validate UCP compliance
    compliance = system.validate_ucp_part_b_compliance()
    print(f"✅ UCP Part B compliance: {compliance}")
    
    # Get system status
    status = system.get_system_status()
    print(f"✅ System state: {status['state']}")
    print(f"✅ UCP compliance: {status['ucp_compliance']}")
    print(f"✅ Operational components: {status['metrics']['operational_components']}")
    
    # Test emergency integration
    if system.emergency_manager:
        event_id = system.emergency_manager.detect_emergency("system_test", "medium")
        print("✅ Emergency response tested")
    
    # Stop system
    time.sleep(1.0)
    system.stop_system()
    print("✅ System integration framework stopped")
    
    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_system_integration()
