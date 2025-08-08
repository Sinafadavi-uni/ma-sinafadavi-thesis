# Task 9: Simple Dashboard for System Monitoring
# Student-friendly dashboard for monitoring thesis system

import time
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import thesis components
from rec.replication.core.vector_clock import VectorClock, create_emergency
from rec.nodes.emergency_executor import SimpleEmergencyExecutor
from rec.demonstrations.simple_visualizer import SimpleVisualizer


class SimpleDashboard:
    """
    Simple dashboard for monitoring the thesis system.
    
    Very easy to understand for students with average programming knowledge.
    Shows system status, vector clocks, and emergency responses in real-time.
    """
    
    def __init__(self):
        self.dashboard_name = "Thesis System Dashboard"
        self.visualizer = SimpleVisualizer()
        self.monitored_components = {}
        self.dashboard_running = False
        self.update_interval = 2.0  # Update every 2 seconds
        self.dashboard_history = []
    
    def add_component(self, name: str, component: Any):
        """Add a component to monitor"""
        self.monitored_components[name] = {
            'component': component,
            'added_time': datetime.now(),
            'last_update': None,
            'status': 'active'
        }
        print(f"✅ Added component '{name}' to dashboard")
    
    def remove_component(self, name: str):
        """Remove a component from monitoring"""
        if name in self.monitored_components:
            del self.monitored_components[name]
            print(f"❌ Removed component '{name}' from dashboard")
        else:
            print(f"⚠️  Component '{name}' not found in dashboard")
    
    def get_component_status(self, name: str, component: Any) -> Dict[str, Any]:
        """Get status information for a component"""
        status = {
            'name': name,
            'type': type(component).__name__,
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'status': 'unknown'
        }
        
        try:
            # Check if it's a vector clock
            if hasattr(component, 'clock') and hasattr(component, 'node_id'):
                status.update({
                    'type': 'VectorClock',
                    'node_id': component.node_id,
                    'clock_state': component.clock.copy(),
                    'local_time': component.clock.get(component.node_id, 0),
                    'status': 'active'
                })
            
            # Check if it's an emergency executor
            elif hasattr(component, 'executor_id') and hasattr(component, 'in_emergency'):
                status.update({
                    'type': 'EmergencyExecutor',
                    'executor_id': component.executor_id,
                    'emergency_mode': component.in_emergency,
                    'has_pending_jobs': component.has_pending_jobs() if hasattr(component, 'has_pending_jobs') else False,
                    'status': 'emergency' if component.in_emergency else 'normal'
                })
                
                if component.emergency_context:
                    status['emergency_type'] = component.emergency_context.emergency_type
                    status['emergency_level'] = component.emergency_context.level
            
            # Check if it's a general system component
            elif hasattr(component, 'get_status'):
                try:
                    component_status = component.get_status()
                    status.update(component_status)
                    status['status'] = 'active'
                except:
                    status['status'] = 'error'
            
            else:
                status.update({
                    'status': 'active',
                    'info': 'Basic component (no specific status available)'
                })
        
        except Exception as e:
            status.update({
                'status': 'error',
                'error': str(e)
            })
        
        return status
    
    def update_dashboard(self):
        """Update dashboard with current component status"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Clear screen (simple way)
        print('\n' * 50)  # Simple screen clear for demo
        
        # Dashboard header
        print("📊 " + "=" * 60)
        print(f"📊 {self.dashboard_name.upper()}")
        print(f"📊 Last Update: {current_time}")
        print("📊 " + "=" * 60)
        
        if not self.monitored_components:
            print("\n📭 No components being monitored")
            print("   Use add_component() to start monitoring")
            return
        
        # System overview
        total_components = len(self.monitored_components)
        active_components = len([c for c in self.monitored_components.values() if c['status'] == 'active'])
        
        print(f"\n🔍 SYSTEM OVERVIEW")
        print(f"   Total Components: {total_components}")
        print(f"   Active Components: {active_components}")
        print(f"   Dashboard Uptime: {self.get_uptime()}")
        
        # Component details
        print(f"\n📋 COMPONENT STATUS")
        print("-" * 60)
        
        for name, comp_info in self.monitored_components.items():
            component = comp_info['component']
            status = self.get_component_status(name, component)
            
            # Status icon
            status_icon = {
                'active': '🟢',
                'emergency': '🔴', 
                'warning': '🟡',
                'error': '❌',
                'unknown': '⚪'
            }.get(status['status'], '⚪')
            
            print(f"{status_icon} {name} ({status['type']})")
            
            # Type-specific info
            if status['type'] == 'VectorClock':
                print(f"   Node: {status.get('node_id', 'unknown')}")
                print(f"   Local Time: {status.get('local_time', 0)}")
                print(f"   Clock: {status.get('clock_state', {})}")
            
            elif status['type'] == 'EmergencyExecutor':
                print(f"   Executor: {status.get('executor_id', 'unknown')}")
                print(f"   Mode: {status.get('emergency_mode', 'unknown')}")
                if status.get('emergency_mode'):
                    print(f"   Emergency: {status.get('emergency_type', 'unknown')} / {status.get('emergency_level', 'unknown')}")
                print(f"   Pending Jobs: {status.get('has_pending_jobs', 'unknown')}")
            
            elif status.get('error'):
                print(f"   Error: {status['error']}")
            
            print(f"   Last Check: {status['timestamp']}")
            print()
    
    def get_uptime(self) -> str:
        """Get dashboard uptime in a readable format"""
        if not hasattr(self, 'start_time'):
            return "Unknown"
        
        uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        
        if uptime_seconds < 60:
            return f"{int(uptime_seconds)} seconds"
        elif uptime_seconds < 3600:
            return f"{int(uptime_seconds // 60)} minutes"
        else:
            return f"{int(uptime_seconds // 3600)} hours"
    
    def start_monitoring(self, update_interval: Optional[float] = None):
        """Start continuous monitoring (non-blocking)"""
        if update_interval:
            self.update_interval = update_interval
        
        self.dashboard_running = True
        self.start_time = datetime.now()
        
        print(f"🚀 Dashboard monitoring started (updates every {self.update_interval}s)")
        print("   Use stop_monitoring() to stop, or Ctrl+C to interrupt")
        
        def monitor_loop():
            while self.dashboard_running:
                try:
                    self.update_dashboard()
                    time.sleep(self.update_interval)
                except KeyboardInterrupt:
                    print("\n\n👋 Dashboard monitoring interrupted by user")
                    self.dashboard_running = False
                    break
                except Exception as e:
                    print(f"\n❌ Dashboard error: {e}")
                    time.sleep(self.update_interval)
        
        # Run monitoring in a separate thread
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        
        return monitor_thread
    
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.dashboard_running = False
        print("🛑 Dashboard monitoring stopped")
    
    def take_snapshot(self):
        """Take a snapshot of current system state"""
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }
        
        for name, comp_info in self.monitored_components.items():
            component = comp_info['component']
            snapshot['components'][name] = self.get_component_status(name, component)
        
        self.dashboard_history.append(snapshot)
        print(f"📸 Snapshot taken at {snapshot['timestamp']}")
        return snapshot
    
    def show_history(self, last_n: int = 5):
        """Show recent dashboard history"""
        print(f"\n📚 DASHBOARD HISTORY (Last {last_n} snapshots)")
        print("-" * 50)
        
        if not self.dashboard_history:
            print("No history available yet")
            return
        
        recent_history = self.dashboard_history[-last_n:]
        
        for i, snapshot in enumerate(recent_history, 1):
            print(f"{i}. {snapshot['timestamp']}")
            for comp_name, comp_status in snapshot['components'].items():
                status_icon = {
                    'active': '🟢',
                    'emergency': '🔴',
                    'error': '❌'
                }.get(comp_status['status'], '⚪')
                print(f"   {status_icon} {comp_name}: {comp_status['status']}")
            print()


def demo_simple_dashboard():
    """Demonstrate the simple dashboard"""
    print("📊 SIMPLE DASHBOARD DEMO")
    print("=" * 40)
    
    dashboard = SimpleDashboard()
    
    print("\n1. Creating components to monitor...")
    # Create some components
    clock1 = VectorClock("demo_node_1")
    clock2 = VectorClock("demo_node_2")
    executor = SimpleEmergencyExecutor("demo_executor")
    
    # Add components to dashboard
    dashboard.add_component("Node 1", clock1)
    dashboard.add_component("Node 2", clock2)
    dashboard.add_component("Emergency Executor", executor)
    
    print("\n2. Taking initial snapshot...")
    dashboard.take_snapshot()
    
    print("\n3. Simulating some activity...")
    clock1.tick()  # Node 1 does something
    clock2.tick()  # Node 2 does something
    clock1.update(clock2.clock)  # Sync clocks
    
    # Activate emergency
    executor.set_emergency_mode("medical", "high")
    
    print("\n4. Updating dashboard...")
    dashboard.update_dashboard()
    
    print("\n5. Taking another snapshot...")
    dashboard.take_snapshot()
    
    print("\n6. Showing history...")
    dashboard.show_history()
    
    print("\n✅ Simple dashboard demo complete!")
    return True


def run_simple_dashboard():
    """Run the simple dashboard interactively"""
    print("📊 SIMPLE DASHBOARD")
    print("=" * 40)
    print("This will start a live dashboard monitoring system components")
    print()
    
    dashboard = SimpleDashboard()
    
    try:
        # Create some demo components
        print("Setting up demo components...")
        clock1 = VectorClock("hospital_node")
        clock2 = VectorClock("ambulance_node") 
        executor = SimpleEmergencyExecutor("emergency_response")
        
        dashboard.add_component("Hospital", clock1)
        dashboard.add_component("Ambulance", clock2)
        dashboard.add_component("Emergency System", executor)
        
        # Show initial state
        print("\nInitial dashboard state:")
        dashboard.update_dashboard()
        
        # Start monitoring
        monitor_thread = dashboard.start_monitoring(3.0)  # Update every 3 seconds
        
        # Simulate some activity
        print("\nSimulating system activity...")
        time.sleep(2)
        
        clock1.tick()
        clock2.tick()
        
        time.sleep(3)
        
        executor.set_emergency_mode("medical", "critical")
        
        time.sleep(3)
        
        clock1.update(clock2.clock)
        
        time.sleep(5)
        
        # Stop monitoring
        dashboard.stop_monitoring()
        
        print("\n🎉 Dashboard demo complete!")
        return True
        
    except KeyboardInterrupt:
        print("\n\n👋 Dashboard stopped by user")
        dashboard.stop_monitoring()
        return False
    except Exception as e:
        print(f"\n❌ Dashboard error: {e}")
        return False


if __name__ == "__main__":
    demo_simple_dashboard()
