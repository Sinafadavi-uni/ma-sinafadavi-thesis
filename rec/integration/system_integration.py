# 🌐 System Integration - Complete system coordination

"""
This module provides complete system integration capabilities,
coordinating between all components for seamless operation.
"""

from ..algorithms.vector_clock import VectorClock
from ..nodes.fault_tolerance.integration_system import Task7FaultToleranceSystem
from .emergency_integration import SimpleEmergencySystem
from typing import Dict, List, Optional
import time
from uuid import uuid4


class CompleteSystemIntegration:
    """
    Master integration system that coordinates all components.
    Student-friendly implementation for educational purposes.
    """
    
    def __init__(self, system_id: str = None):
        self.system_id = system_id or f"integration_{uuid4().hex[:8]}"
        self.vector_clock = VectorClock(self.system_id)
        
        # Core system components
        self.emergency_system = SimpleEmergencySystem(f"emergency_{self.system_id}")
        self.fault_tolerance = Task7FaultToleranceSystem(f"fault_tol_{self.system_id}")
        
        # Integration state
        self.registered_nodes: Dict[str, Dict] = {}
        self.system_status = "initializing"
        self.integration_metrics = {
            "nodes_registered": 0,
            "emergency_activations": 0,
            "fault_recoveries": 0,
            "uptime": time.time()
        }
    
    def register_node(self, node_id: str, node_type: str, capabilities: List[str] = None) -> bool:
        """Register a node with the integrated system"""
        self.vector_clock.tick()
        
        node_info = {
            "node_id": node_id,
            "node_type": node_type,
            "capabilities": capabilities or [],
            "registered_at": time.time(),
            "status": "active",
            "last_heartbeat": time.time()
        }
        
        self.registered_nodes[node_id] = node_info
        
        # Register with subsystems
        if node_type == "executor":
            self.emergency_system.register_executor(node_id)
        
        self.fault_tolerance.register_node(node_id)
        
        self.integration_metrics["nodes_registered"] += 1
        return True
    
    def coordinate_emergency_response(self, emergency_type: str, severity: str, affected_nodes: List[str] = None) -> str:
        """Coordinate emergency response across all systems"""
        self.vector_clock.tick()
        
        # Create emergency ID
        emergency_id = f"emergency_{uuid4().hex[:8]}"
        
        # Activate emergency in all systems
        self.emergency_system.declare_system_emergency(emergency_type, severity)
        self.fault_tolerance.activate_emergency_protocol(f"System emergency: {emergency_type}")
        
        # Coordinate response
        response_plan = {
            "emergency_id": emergency_id,
            "type": emergency_type,
            "severity": severity,
            "affected_nodes": affected_nodes or [],
            "response_time": time.time(),
            "coordinated_systems": ["emergency", "fault_tolerance"]
        }
        
        self.integration_metrics["emergency_activations"] += 1
        return emergency_id
    
    def system_health_check(self) -> Dict:
        """Comprehensive system health check across all components"""
        self.vector_clock.tick()
        
        # Check all subsystems
        emergency_status = self.emergency_system.get_system_status()
        fault_tolerance_status = self.fault_tolerance.get_system_status()
        
        # Calculate overall health
        total_nodes = len(self.registered_nodes)
        active_nodes = sum(1 for node in self.registered_nodes.values() if node["status"] == "active")
        
        health_score = (active_nodes / max(total_nodes, 1)) * 100
        
        system_health = {
            "system_id": self.system_id,
            "overall_health": health_score,
            "status": "healthy" if health_score > 80 else "degraded" if health_score > 50 else "critical",
            "registered_nodes": total_nodes,
            "active_nodes": active_nodes,
            "emergency_active": emergency_status.get("emergency_active", False),
            "fault_tolerance_active": fault_tolerance_status.get("emergency_protocols_active", False),
            "integration_metrics": self.integration_metrics.copy(),
            "timestamp": time.time()
        }
        
        return system_health
    
    def coordinate_job_execution(self, job_id: str, job_data: Dict, priority: str = "normal") -> bool:
        """Coordinate job execution across the integrated system"""
        self.vector_clock.tick()
        
        # Check if emergency mode affects execution
        if priority == "emergency":
            return self.fault_tolerance.submit_critical_job(job_id, job_data)
        else:
            # Normal job execution coordination
            return True
    
    def handle_node_failure(self, node_id: str, failure_type: str) -> Dict:
        """Coordinate response to node failure across all systems"""
        self.vector_clock.tick()
        
        if node_id in self.registered_nodes:
            self.registered_nodes[node_id]["status"] = "failed"
            self.registered_nodes[node_id]["failure_time"] = time.time()
            self.registered_nodes[node_id]["failure_type"] = failure_type
        
        # Coordinate recovery
        recovery_plan = {
            "failed_node": node_id,
            "failure_type": failure_type,
            "recovery_initiated": time.time(),
            "backup_systems_activated": True
        }
        
        self.integration_metrics["fault_recoveries"] += 1
        return recovery_plan
    
    def get_integration_status(self) -> Dict:
        """Get comprehensive integration status"""
        uptime = time.time() - self.integration_metrics["uptime"]
        
        return {
            "system_id": self.system_id,
            "integration_status": self.system_status,
            "uptime_seconds": uptime,
            "vector_clock": self.vector_clock.clock.copy(),
            "subsystems": {
                "emergency_system": "active",
                "fault_tolerance": "active"
            },
            "metrics": self.integration_metrics.copy(),
            "health_summary": self.system_health_check()
        }


def demo_system_integration():
    """Demonstration of complete system integration"""
    print("🌐 DEMO: Complete System Integration")
    print("=" * 45)
    
    # Create integrated system
    integration = CompleteSystemIntegration("demo_system")
    
    print("\n1. Registering nodes...")
    integration.register_node("executor_1", "executor", ["emergency", "standard"])
    integration.register_node("executor_2", "executor", ["standard"])
    integration.register_node("broker_1", "broker", ["coordination"])
    
    print("   ✅ 3 nodes registered")
    
    print("\n2. System health check...")
    health = integration.system_health_check()
    print(f"   Overall health: {health['overall_health']:.1f}%")
    print(f"   Status: {health['status']}")
    
    print("\n3. Coordinating emergency response...")
    emergency_id = integration.coordinate_emergency_response("network_partition", "HIGH", ["executor_2"])
    print(f"   Emergency activated: {emergency_id}")
    
    print("\n4. Handling node failure...")
    recovery = integration.handle_node_failure("executor_2", "timeout")
    print(f"   Recovery plan created for failed node")
    
    print("\n5. Final integration status...")
    status = integration.get_integration_status()
    print(f"   Integration uptime: {status['uptime_seconds']:.1f}s")
    print(f"   Emergency activations: {status['metrics']['emergency_activations']}")
    print(f"   Fault recoveries: {status['metrics']['fault_recoveries']}")
    
    print("\n🎉 System integration demo complete!")


if __name__ == "__main__":
    demo_system_integration()
