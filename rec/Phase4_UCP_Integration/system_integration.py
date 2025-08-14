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
from datastore_replication import DatastoreReplicationManager

# Phase 1: Foundation
phase1_path = os.path.join(os.path.dirname(__file__), '..', 'Phase1_Core_Foundation')
sys.path.insert(0, phase1_path)
from vector_clock import VectorClock, create_emergency
from causal_consistency import CausalConsistencyManager

# Phase 2: Infrastructure  
phase2_path = os.path.join(os.path.dirname(__file__), '..', 'Phase2_Node_Infrastructure')
sys.path.insert(0, phase2_path)
from recovery_system import SimpleRecoveryManager
from emergency_executor import SimpleEmergencyExecutor

# Phase 3: Core Implementation
phase3_path = os.path.join(os.path.dirname(__file__), '..', 'Phase3_Core_Implementation')
sys.path.insert(0, phase3_path)
from enhanced_vector_clock_executor import EnhancedVectorClockExecutor
from vector_clock_broker import VectorClockBroker
from emergency_integration import EmergencyIntegrationManager

# Phase 4: UCP Integration
from multi_broker_coordinator import MultiBrokerCoordinator

LOG = logging.getLogger(__name__)

class SystemState(Enum):
    """System integration state"""
    INITIALIZING = "initializing"
    STARTING = "starting"
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    EMERGENCY = "emergency"
    STOPPING = "stopping"
    STOPPED = "stopped"

class UCPCompliance(Enum):
    """UCP compliance levels"""
    FULL_COMPLIANCE = "full_compliance"
    PARTIAL_COMPLIANCE = "partial_compliance"
    NON_COMPLIANT = "non_compliant"
    TESTING = "testing"

@dataclass
class SystemComponent:
    """System component information"""
    component_id: str
    component_type: str
    instance: Any
    status: str = "inactive"
    health_score: float = 1.0
    last_check: float = field(default_factory=time.time)

class SystemIntegrationFramework:
    """
    Complete system integration framework
    
    Unifies all thesis components into a production-ready distributed system
    with UCP compliance, health monitoring, and end-to-end coordination.
    
    Features:
    - Complete system integration and startup/shutdown
    - UCP compliance verification
    - Health monitoring and metrics collection
    - Emergency response coordination
    - Production deployment support
    """
    
    def __init__(self, system_id: str = None):
        """Initialize system integration framework"""
        self.system_id = system_id or f"integrated-system-{uuid4()}"
        self.vector_clock = VectorClock(self.system_id)
        
        # System state
        self.current_state = SystemState.INITIALIZING
        self.ucp_compliance = UCPCompliance.TESTING
        
        # Component management
        self.registered_components: Dict[str, SystemComponent] = {}
        self.component_lock = threading.RLock()
        
        # System coordinators
        self.multi_broker_coordinator: Optional[MultiBrokerCoordinator] = None
        self.emergency_manager: Optional[EmergencyIntegrationManager] = None
        self.recovery_manager: Optional[SimpleRecoveryManager] = None
        
        # Add datastore replication manager
        self.datastore_replication_manager: Optional[DatastoreReplicationManager] = None
        
        # System metrics and monitoring
        self.system_metrics = {
            "startup_time": None,
            "total_components": 0,
            "operational_components": 0,
            "error_count": 0,
            "emergency_count": 0,
            "uptime": 0.0
        }
        
        # Monitoring threads
        self.should_exit = False
        self.health_monitor_thread = None
        self.metrics_thread = None
        
        LOG.info(f"SystemIntegrationFramework {self.system_id} initialized")
    
    def register_coordinator(self, coordinator: MultiBrokerCoordinator) -> None:
        """Register multi-broker coordinator"""
        self.multi_broker_coordinator = coordinator
        self._register_component("multi_broker_coordinator", "coordinator", coordinator)
        LOG.info("Multi-broker coordinator registered")
    
    def register_executor(self, executor: Any) -> None:
        """Register executor (any type)"""
        component_id = getattr(executor, 'node_id', getattr(executor, 'executor_id', str(uuid4())))
        self._register_component(component_id, "executor", executor)
        LOG.info(f"Executor {component_id} registered")
    
    def register_broker(self, broker: VectorClockBroker) -> None:
        """Register vector clock broker"""
        self._register_component(broker.broker_id, "broker", broker)
        LOG.info(f"Broker {broker.broker_id} registered")
    
    def register_emergency_manager(self, manager: EmergencyIntegrationManager) -> None:
        """Register emergency integration manager"""
        self.emergency_manager = manager
        self._register_component(manager.manager_id, "emergency_manager", manager)
        LOG.info("Emergency manager registered")
    
    def register_recovery_manager(self, manager: SimpleRecoveryManager) -> None:
        """Register recovery manager"""
        self.recovery_manager = manager
        self._register_component(manager.manager_id, "recovery_manager", manager)
        LOG.info("Recovery manager registered")
    
    def register_datastore_replication(self, replication_manager: DatastoreReplicationManager) -> None:
        """Register datastore replication manager"""
        self.datastore_replication_manager = replication_manager
        self._register_component("datastore_replication", "replication_manager", replication_manager)
        LOG.info("Datastore replication manager registered")
    
    def start_system(self) -> bool:
        """
        Start the complete integrated system
        
        Returns:
            bool: True if system started successfully
        """
        startup_start = time.time()
        self.current_state = SystemState.STARTING
        self.vector_clock.tick()
        
        LOG.info(f"Starting integrated system {self.system_id}...")
        
        try:
            # Start core coordinators first
            if self.multi_broker_coordinator:
                self.multi_broker_coordinator.start()
                self._update_component_status("multi_broker_coordinator", "active")
            
            if self.emergency_manager:
                self.emergency_manager.start()
                self._update_component_status(self.emergency_manager.manager_id, "active")
            
            if self.recovery_manager:
                self.recovery_manager.start()
                self._update_component_status(self.recovery_manager.manager_id, "active")
            
            # Start datastore replication manager
            if self.datastore_replication_manager:
                self.datastore_replication_manager.start()
                self._update_component_status("datastore_replication", "active")
            
            # Start registered components
            for component_id, component in self.registered_components.items():
                if hasattr(component.instance, 'start') and component.status != "active":
                    try:
                        component.instance.start()
                        self._update_component_status(component_id, "active")
                        LOG.info(f"Started component: {component_id}")
                    except Exception as e:
                        LOG.error(f"Failed to start component {component_id}: {e}")
                        self._update_component_status(component_id, "failed")
            
            # Start monitoring
            self._start_monitoring()
            
            # Update system state
            self.current_state = SystemState.OPERATIONAL
            self.system_metrics["startup_time"] = time.time() - startup_start
            self.system_metrics["total_components"] = len(self.registered_components)
            
            # Verify UCP compliance
            self.ucp_compliance = self._check_ucp_compliance()
            
            LOG.info(f"Integrated system {self.system_id} started successfully "
                    f"in {self.system_metrics['startup_time']:.2f}s")
            return True
            
        except Exception as e:
            LOG.error(f"Failed to start integrated system: {e}")
            self.current_state = SystemState.DEGRADED
            return False
    
    def stop_system(self) -> None:
        """Stop the complete integrated system"""
        self.current_state = SystemState.STOPPING
        self.should_exit = True
        
        LOG.info(f"Stopping integrated system {self.system_id}...")
        
        # Stop monitoring
        if self.health_monitor_thread and self.health_monitor_thread.is_alive():
            self.health_monitor_thread.join(timeout=2.0)
        
        if self.metrics_thread and self.metrics_thread.is_alive():
            self.metrics_thread.join(timeout=2.0)
        
        # Stop registered components
        for component_id, component in self.registered_components.items():
            if hasattr(component.instance, 'stop') and component.status == "active":
                try:
                    component.instance.stop()
                    self._update_component_status(component_id, "stopped")
                    LOG.info(f"Stopped component: {component_id}")
                except Exception as e:
                    LOG.error(f"Failed to stop component {component_id}: {e}")
        
        # Stop core coordinators
        if self.recovery_manager:
            self.recovery_manager.stop()
        
        if self.emergency_manager:
            self.emergency_manager.stop()
        
        if self.multi_broker_coordinator:
            self.multi_broker_coordinator.stop()
        
        self.current_state = SystemState.STOPPED
        LOG.info(f"Integrated system {self.system_id} stopped")
    
    def verify_ucp_compliance(self) -> bool:
        """
        Verify UCP compliance of the integrated system
        
        Returns:
            bool: True if system is UCP compliant
        """
        compliance_checks = {
            "vector_clock_coordination": False,
            "emergency_response": False,
            "causal_consistency": False,
            "fcfs_policy": False,
            "distributed_execution": False,
            "datastore_replication": False  # New check
        }
        
        try:
            # Check vector clock coordination
            if self.multi_broker_coordinator:
                coordination_status = self.multi_broker_coordinator.get_global_status()
                compliance_checks["vector_clock_coordination"] = (
                    "vector_clock" in coordination_status and 
                    len(coordination_status["broker_clusters"]) > 0
                )
            
            # Check emergency response
            if self.emergency_manager:
                emergency_status = self.emergency_manager.get_emergency_status()
                compliance_checks["emergency_response"] = (
                    "manager_id" in emergency_status and
                    len(emergency_status["managed_nodes"]) > 0
                )
            
            # Check causal consistency
            consistency_components = [
                comp for comp in self.registered_components.values()
                if hasattr(comp.instance, 'consistency_manager')
            ]
            compliance_checks["causal_consistency"] = len(consistency_components) > 0
            
            # Check FCFS policy
            fcfs_components = [
                comp for comp in self.registered_components.values()
                if hasattr(comp.instance, 'fcfs_policy')
            ]
            compliance_checks["fcfs_policy"] = len(fcfs_components) > 0
            
            # Check distributed execution
            executor_components = [
                comp for comp in self.registered_components.values()
                if comp.component_type == "executor"
            ]
            compliance_checks["distributed_execution"] = len(executor_components) > 0
            
            # Check datastore replication
            if self.datastore_replication_manager:
                repl_status = self.datastore_replication_manager.get_replication_status()
                compliance_checks["datastore_replication"] = (
                    repl_status["datastores"]["available"] > 0 and
                    repl_status["strategy"] != "none"
                )
            
            # Determine compliance level
            passed_checks = sum(1 for check in compliance_checks.values() if check)
            total_checks = len(compliance_checks)
            
            if passed_checks == total_checks:
                self.ucp_compliance = UCPCompliance.FULL_COMPLIANCE
            elif passed_checks >= total_checks * 0.8:
                self.ucp_compliance = UCPCompliance.PARTIAL_COMPLIANCE
            else:
                self.ucp_compliance = UCPCompliance.NON_COMPLIANT
            
            LOG.info(f"UCP compliance: {self.ucp_compliance.value} "
                    f"({passed_checks}/{total_checks} checks passed)")
            
            return self.ucp_compliance == UCPCompliance.FULL_COMPLIANCE
            
        except Exception as e:
            LOG.error(f"Error verifying UCP compliance: {e}")
            self.ucp_compliance = UCPCompliance.NON_COMPLIANT
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        with self.component_lock:
            component_status = {}
            operational_count = 0
            
            for comp_id, component in self.registered_components.items():
                component_status[comp_id] = {
                    "type": component.component_type,
                    "status": component.status,
                    "health_score": component.health_score,
                    "last_check": component.last_check
                }
                
                if component.status == "active":
                    operational_count += 1
        
        # Calculate uptime
        if self.system_metrics["startup_time"]:
            uptime = time.time() - (time.time() - self.system_metrics["startup_time"])
        else:
            uptime = 0.0
        
        return {
            "system_id": self.system_id,
            "state": self.current_state.value,
            "ucp_compliance": self.ucp_compliance.value,
            "vector_clock": self.vector_clock.clock.copy(),
            "components": component_status,
            "metrics": {
                **self.system_metrics,
                "operational_components": operational_count,
                "uptime": uptime
            },
            "coordinators": {
                "multi_broker": self.multi_broker_coordinator is not None,
                "emergency": self.emergency_manager is not None,
                "recovery": self.recovery_manager is not None
            }
        }
    
    def _register_component(self, component_id: str, component_type: str, instance: Any) -> None:
        """Register system component"""
        with self.component_lock:
            component = SystemComponent(
                component_id=component_id,
                component_type=component_type,
                instance=instance
            )
            self.registered_components[component_id] = component
    
    def _update_component_status(self, component_id: str, status: str) -> None:
        """Update component status"""
        with self.component_lock:
            if component_id in self.registered_components:
                self.registered_components[component_id].status = status
                self.registered_components[component_id].last_check = time.time()
    
    def _check_ucp_compliance(self) -> UCPCompliance:
        """Internal UCP compliance check"""
        try:
            # Quick compliance verification
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
        """Start system monitoring threads"""
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
        """Background health monitoring"""
        LOG.info(f"System health monitor started for {self.system_id}")
        
        while not self.should_exit:
            try:
                with self.component_lock:
                    for component in self.registered_components.values():
                        # Simple health check - component should respond
                        try:
                            if hasattr(component.instance, 'get_status'):
                                status = component.instance.get_status()
                                component.health_score = 1.0
                            elif hasattr(component.instance, 'heartbeat'):
                                component.instance.heartbeat()
                                component.health_score = 1.0
                            else:
                                component.health_score = 0.8  # Assumed healthy
                                
                            component.last_check = time.time()
                            
                        except Exception as e:
                            component.health_score = 0.0
                            LOG.warning(f"Health check failed for {component.component_id}: {e}")
                
                time.sleep(30.0)  # Health check every 30 seconds
                
            except Exception as e:
                LOG.error(f"Error in health monitor: {e}")
                time.sleep(5.0)
        
        LOG.info(f"System health monitor stopped for {self.system_id}")
    
    def _metrics_collector(self) -> None:
        """Background metrics collection"""
        LOG.info(f"System metrics collector started for {self.system_id}")
        
        while not self.should_exit:
            try:
                # Update operational component count
                with self.component_lock:
                    operational = sum(1 for comp in self.registered_components.values() 
                                    if comp.status == "active")
                    self.system_metrics["operational_components"] = operational
                
                time.sleep(60.0)  # Collect metrics every minute
                
            except Exception as e:
                LOG.error(f"Error in metrics collector: {e}")
                time.sleep(10.0)
        
        LOG.info(f"System metrics collector stopped for {self.system_id}")

# Demo and testing functions
def demo_system_integration():
    """Demonstrate SystemIntegrationFramework functionality"""
    print("\n=== SystemIntegrationFramework Demo ===")
    
    # Create system integration framework
    integration = SystemIntegrationFramework("demo_system")
    print(f"✅ Created integration framework: {integration.system_id}")
    
    # Create and register components
    from enhanced_vector_clock_executor import EnhancedVectorClockExecutor, ExecutorCapabilities
    from vector_clock_broker import VectorClockBroker
    from multi_broker_coordinator import MultiBrokerCoordinator
    
    # Create components
    coordinator = MultiBrokerCoordinator("demo_coordinator")
    broker1 = VectorClockBroker("demo_broker_1")
    broker2 = VectorClockBroker("demo_broker_2")
    
    capabilities = ExecutorCapabilities(emergency_capable=True)
    executor1 = EnhancedVectorClockExecutor("demo_executor_1", capabilities)
    executor2 = EnhancedVectorClockExecutor("demo_executor_2", capabilities)
    
    # Register components
    integration.register_coordinator(coordinator)
    integration.register_broker(broker1)
    integration.register_broker(broker2)
    integration.register_executor(executor1)
    integration.register_executor(executor2)
    
    print(f"✅ Registered {len(integration.registered_components)} components")
    
    # Start integrated system
    startup_success = integration.start_system()
    print(f"✅ System startup: {'successful' if startup_success else 'failed'}")
    
    # Verify UCP compliance
    compliance_result = integration.verify_ucp_compliance()
    print(f"✅ UCP compliance: {'verified' if compliance_result else 'failed'}")
    
    # Get system status
    status = integration.get_system_status()
    print(f"✅ System status: {status['state']}")
    print(f"✅ Operational components: {status['metrics']['operational_components']}")
    print(f"✅ UCP compliance level: {status['ucp_compliance']}")
    
    # Wait for monitoring
    time.sleep(1.0)
    
    # Stop system
    integration.stop_system()
    print("✅ System stopped")
    
    return True

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run demo
    demo_system_integration()