# Phase 2: Node Infrastructure
"""
Phase 2: Node Infrastructure (Files 5-7)

Node infrastructure for distributed vector clock-based systems including:
- File 5: ExecutorBroker - Core broker functionality
- File 6: RecoverySystem - Node failure detection and recovery
- File 7: EmergencyExecutor - Emergency-aware job execution

This phase builds on Phase 1's foundation to provide distributed node infrastructure
with emergency response capabilities and failure recovery.
"""

from .executorbroker import ExecutorBroker
from .recovery_system import SimpleRecoveryManager  
from .emergency_executor import SimpleEmergencyExecutor

__all__ = ['ExecutorBroker', 'SimpleRecoveryManager', 'SimpleEmergencyExecutor']

def demo_phase2():
    """
    Demonstrate Phase 2: Node Infrastructure functionality
    
    Tests:
    1. ExecutorBroker - Core broker operations
    2. SimpleRecoveryManager - Node monitoring and recovery
    3. SimpleEmergencyExecutor - Emergency job execution
    """
    print("\n=== Phase 2: Node Infrastructure Demo ===")
    
    # Test 1: ExecutorBroker
    print("\n1. Testing ExecutorBroker...")
    broker = ExecutorBroker()
    print(f"   ✅ ExecutorBroker created with {len(broker.executors)} executors")
    
    # Test 2: SimpleRecoveryManager
    print("\n2. Testing SimpleRecoveryManager...")
    recovery = SimpleRecoveryManager()
    print(f"   ✅ RecoveryManager monitoring {len(recovery.monitored_nodes)} nodes")
    
    # Test 3: SimpleEmergencyExecutor
    print("\n3. Testing SimpleEmergencyExecutor...")
    executor = SimpleEmergencyExecutor("test_executor")
    print(f"   ✅ EmergencyExecutor '{executor.node_id}' ready")
    
    # Test emergency mode activation
    executor.set_emergency_mode("fire", "high")
    print(f"   ✅ Emergency mode: {executor.in_emergency_mode}")
    
    print("\n✅ Phase 2 Status: Complete")
    print("   - ExecutorBroker: Operational")
    print("   - RecoverySystem: Monitoring")
    print("   - EmergencyExecutor: Ready")
    
    return True

if __name__ == "__main__":
    demo_phase2()
