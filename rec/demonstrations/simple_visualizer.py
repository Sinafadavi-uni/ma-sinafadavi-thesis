# Task 9: Simple Vector Clock Visualizer  
# Student-friendly visualization tools for vector clocks

import time
from typing import Dict, List, Any
from datetime import datetime

# Import thesis components
from rec.replication.core.vector_clock import VectorClock, create_emergency


class SimpleVisualizer:
    """
    Simple visualizer for vector clocks and system state.
    
    Very easy to understand for students with average programming knowledge.
    Shows vector clock states in a readable text format.
    """
    
    def __init__(self):
        self.visualization_history = []
        self.current_time = None
    
    def print_vector_clock_state(self, clock: VectorClock, title: str = "Vector Clock"):
        """Print vector clock state in a nice format"""
        print(f"\n📊 {title}")
        print("-" * 30)
        print(f"Node ID: {clock.node_id}")
        print(f"Clock State: {clock.clock}")
        print(f"Local Time: {clock.clock.get(clock.node_id, 0)}")
        
        # Show other nodes this clock knows about
        other_nodes = [node for node in clock.clock.keys() if node != clock.node_id]
        if other_nodes:
            print("Known Nodes:")
            for node in other_nodes:
                print(f"  - {node}: time {clock.clock[node]}")
        else:
            print("No other nodes known yet")
    
    def visualize_clock_comparison(self, clock1: VectorClock, clock2: VectorClock):
        """Show comparison between two vector clocks"""
        print("\n🔍 VECTOR CLOCK COMPARISON")
        print("=" * 40)
        
        # Show both clocks
        self.print_vector_clock_state(clock1, f"Clock 1 ({clock1.node_id})")
        self.print_vector_clock_state(clock2, f"Clock 2 ({clock2.node_id})")
        
        # Show comparison result
        relation = clock1.compare(clock2.clock)
        print(f"\n🔗 Relationship: Clock 1 is '{relation}' relative to Clock 2")
        
        if relation == "before":
            print("   ➡️  Clock 1 events happened before Clock 2 events")
        elif relation == "after": 
            print("   ⬅️  Clock 1 events happened after Clock 2 events")
        elif relation == "concurrent":
            print("   🤝 Clock 1 and Clock 2 events happened concurrently")
        else:
            print("   ❓ Unknown relationship")
    
    def visualize_emergency_response(self, executors: List, emergency_type: str = "medical"):
        """Visualize emergency response across multiple executors"""
        print("\n🚨 EMERGENCY RESPONSE VISUALIZATION")
        print("=" * 50)
        print(f"Emergency Type: {emergency_type}")
        print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
        
        print("\n📋 Executor Status:")
        for i, executor in enumerate(executors, 1):
            if hasattr(executor, 'in_emergency'):
                status = "🚨 EMERGENCY" if executor.in_emergency else "✅ NORMAL"
                print(f"  {i}. {executor.executor_id}: {status}")
                
                if hasattr(executor, 'vector_clock'):
                    print(f"     Vector Clock: {executor.vector_clock.clock}")
                    
                if hasattr(executor, 'emergency_level') and executor.in_emergency:
                    print(f"     Emergency level: {executor.emergency_level}")
            else:
                print(f"  {i}. {getattr(executor, 'node_id', 'unknown')}: Status unknown")
    
    def create_simple_timeline(self, events: List[Dict[str, Any]]):
        """Create a simple timeline visualization of events"""
        print("\n⏰ EVENT TIMELINE")
        print("=" * 40)
        
        if not events:
            print("No events to display")
            return
        
        for i, event in enumerate(events, 1):
            timestamp = event.get('timestamp', f'Event {i}')
            node = event.get('node', 'unknown')
            action = event.get('action', 'unknown action')
            clock_state = event.get('clock_state', {})
            
            print(f"{i}. [{timestamp}] {node}")
            print(f"   Action: {action}")
            if clock_state:
                print(f"   Clock: {clock_state}")
            print()
    
    def visualize_system_health(self, system_data: Dict[str, Any]):
        """Simple visualization of overall system health"""
        print("\n💊 SYSTEM HEALTH DASHBOARD")
        print("=" * 40)
        
        # Basic system metrics
        total_nodes = system_data.get('total_nodes', 0)
        healthy_nodes = system_data.get('healthy_nodes', 0)
        emergency_active = system_data.get('emergency_active', False)
        
        print(f"Total Nodes: {total_nodes}")
        print(f"Healthy Nodes: {healthy_nodes}")
        print(f"Emergency Status: {'🚨 ACTIVE' if emergency_active else '✅ NORMAL'}")
        
        # Health percentage
        if total_nodes > 0:
            health_percent = (healthy_nodes / total_nodes) * 100
            print(f"System Health: {health_percent:.1f}%")
            
            if health_percent >= 80:
                print("   Status: 🟢 EXCELLENT")
            elif health_percent >= 60:
                print("   Status: 🟡 GOOD") 
            elif health_percent >= 40:
                print("   Status: 🟠 DEGRADED")
            else:
                print("   Status: 🔴 CRITICAL")
        
        # Recent events
        recent_events = system_data.get('recent_events', [])
        if recent_events:
            print(f"\nRecent Events: ({len(recent_events)} events)")
            for event in recent_events[-3:]:  # Show last 3 events
                print(f"  • {event}")


def demo_simple_visualization():
    """Demonstrate the simple visualization tools"""
    print("🎨 SIMPLE VISUALIZATION DEMO")
    print("=" * 40)
    
    visualizer = SimpleVisualizer()
    
    print("\n1. Creating vector clocks for visualization...")
    clock1 = VectorClock("node_A")
    clock2 = VectorClock("node_B")
    
    # Simulate some events
    clock1.tick()  # Node A does something
    clock2.tick()  # Node B does something
    clock2.tick()  # Node B does something else
    
    # Show individual clocks
    visualizer.print_vector_clock_state(clock1, "Node A Clock")
    visualizer.print_vector_clock_state(clock2, "Node B Clock")
    
    print("\n2. Comparing vector clocks...")
    visualizer.visualize_clock_comparison(clock1, clock2)
    
    print("\n3. Synchronizing clocks...")
    clock1.update(clock2.clock)
    visualizer.visualize_clock_comparison(clock1, clock2)
    
    print("\n4. System health visualization...")
    system_data = {
        'total_nodes': 5,
        'healthy_nodes': 4,
        'emergency_active': False,
        'recent_events': [
            'Node A started',
            'Node B synchronized', 
            'Normal operation resumed'
        ]
    }
    visualizer.visualize_system_health(system_data)
    
    print("\n✅ Simple visualization demo complete!")
    return True


def demo_emergency_visualization():
    """Demonstrate emergency response visualization"""
    print("\n🚨 EMERGENCY VISUALIZATION DEMO")
    print("=" * 40)
    
    visualizer = SimpleVisualizer()
    
    # Create some mock executor data for visualization
    class MockExecutor:
        def __init__(self, executor_id, in_emergency=False):
            self.executor_id = executor_id
            self.in_emergency = in_emergency
            self.vector_clock = VectorClock(executor_id)
            self.emergency_level = create_emergency("medical", "high") if in_emergency else None
    
    # Create mock executors
    executors = [
        MockExecutor("hospital_1", True),
        MockExecutor("ambulance_1", True), 
        MockExecutor("office_1", False),
        MockExecutor("fire_dept_1", False)
    ]
    
    # Visualize emergency response
    visualizer.visualize_emergency_response(executors, "medical")
    
    print("\n✅ Emergency visualization demo complete!")
    return True


if __name__ == "__main__":
    demo_simple_visualization()
    demo_emergency_visualization()
