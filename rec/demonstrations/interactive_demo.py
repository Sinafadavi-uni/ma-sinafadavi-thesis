# Task 9: Interactive Demonstration System
# Simple student-friendly interactive demos with user input

import time
import random
from typing import Dict, List, Any

# Import thesis components
from rec.replication.core.vector_clock import VectorClock, create_emergency
from rec.nodes.emergency_executor import SimpleEmergencyExecutor
from rec.demonstrations.simple_visualizer import SimpleVisualizer


class SimpleInteractiveDemo:
    """
    Interactive demonstration system for thesis components.
    
    Simple class that lets users interact with the system step by step.
    Designed for students with average programming knowledge.
    """
    
    def __init__(self):
        self.demo_name = "Interactive Thesis Demo"
        self.visualizer = SimpleVisualizer()
        self.current_nodes = {}
        self.demo_history = []
    
    def wait_for_user(self, message: str = "Press Enter to continue..."):
        """Simple function to wait for user input"""
        try:
            input(f"\n{message}")
        except KeyboardInterrupt:
            print("\n\n👋 Demo stopped by user. Thanks for participating!")
            return False
        return True
    
    def show_menu(self, title: str, options: List[str]) -> int:
        """Show a simple menu and get user choice"""
        print(f"\n📋 {title}")
        print("-" * 30)
        
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        
        while True:
            try:
                choice = input(f"\nChoose option (1-{len(options)}): ").strip()
                choice_num = int(choice)
                if 1 <= choice_num <= len(options):
                    return choice_num
                else:
                    print(f"Please enter a number between 1 and {len(options)}")
            except (ValueError, KeyboardInterrupt):
                print("Please enter a valid number (or Ctrl+C to exit)")
    
    def interactive_vector_clock_demo(self):
        """Interactive demonstration of vector clocks"""
        print("\n🕐 INTERACTIVE VECTOR CLOCK DEMO")
        print("=" * 50)
        print("Learn how vector clocks work by creating and using them!")
        
        if not self.wait_for_user():
            return False
        
        # Let user create nodes
        print("\n1. Creating Vector Clock Nodes")
        node_names = []
        
        while len(node_names) < 3:
            node_name = input(f"\nEnter name for node {len(node_names) + 1} (or 'done' to stop): ").strip()
            if node_name.lower() == 'done' and len(node_names) >= 2:
                break
            elif node_name and node_name not in node_names:
                node_names.append(node_name)
                clock = VectorClock(node_name)
                self.current_nodes[node_name] = clock
                print(f"✅ Created vector clock for '{node_name}'")
            elif node_name in node_names:
                print("That node name already exists!")
            else:
                print("Please enter a valid node name")
        
        # Show created nodes
        print(f"\n📊 Created {len(node_names)} nodes:")
        for name in node_names:
            self.visualizer.print_vector_clock_state(self.current_nodes[name])
        
        if not self.wait_for_user("Ready to simulate events?"):
            return False
        
        # Interactive event simulation
        print("\n2. Simulating Events")
        for round_num in range(3):
            print(f"\n--- Round {round_num + 1} ---")
            
            # Let user choose which node does something
            choice = self.show_menu(
                "Which node should perform an action?",
                node_names + ["Show current state", "Skip round"]
            )
            
            if choice <= len(node_names):
                chosen_node = node_names[choice - 1]
                self.current_nodes[chosen_node].tick()
                print(f"\n✅ {chosen_node} performed an action!")
                self.visualizer.print_vector_clock_state(self.current_nodes[chosen_node])
                
                # Ask about synchronization
                if len(node_names) > 1:
                    sync_choice = input(f"\nSync {chosen_node} with another node? (y/n): ").lower()
                    if sync_choice == 'y':
                        other_nodes = [n for n in node_names if n != chosen_node]
                        sync_choice = self.show_menu("Sync with which node?", other_nodes)
                        other_node = other_nodes[sync_choice - 1]
                        
                        print(f"\n🔄 Synchronizing {chosen_node} with {other_node}...")
                        self.current_nodes[chosen_node].update(self.current_nodes[other_node].clock)
                        self.visualizer.visualize_clock_comparison(
                            self.current_nodes[chosen_node], 
                            self.current_nodes[other_node]
                        )
            
            elif choice == len(node_names) + 1:  # Show current state
                print("\n📊 Current State of All Nodes:")
                for name in node_names:
                    self.visualizer.print_vector_clock_state(self.current_nodes[name])
        
        print("\n✅ Interactive vector clock demo complete!")
        return True
    
    def interactive_emergency_demo(self):
        """Interactive emergency response demonstration"""
        print("\n🚨 INTERACTIVE EMERGENCY RESPONSE DEMO")
        print("=" * 50)
        print("Experience how the emergency response system works!")
        
        if not self.wait_for_user():
            return False
        
        # Create emergency executor
        print("\n1. Setting up Emergency Response System")
        executor_name = input("Enter name for your emergency executor: ").strip() or "demo_executor"
        executor = SimpleEmergencyExecutor(executor_name)
        
        print(f"✅ Emergency executor '{executor_name}' created!")
        print(f"Emergency mode: {executor.in_emergency}")
        
        if not self.wait_for_user("Ready to submit jobs?"):
            return False
        
        # Interactive job submission
        print("\n2. Submitting Jobs")
        jobs_submitted = []
        
        for job_round in range(3):
            print(f"\n--- Job Round {job_round + 1} ---")
            
            # Let user choose job type
            job_type_choice = self.show_menu(
                "What type of job do you want to submit?",
                ["Normal job", "Emergency job", "Check job queue", "Process next job"]
            )
            
            if job_type_choice == 1:  # Normal job
                job_id = f"normal_job_{len(jobs_submitted) + 1}"
                job_data = {"task": "normal_task", "priority": "normal"}
                success = executor.submit_job(job_id, job_data)
                status = "accepted" if success else "rejected"
                print(f"📋 Normal job '{job_id}': {status}")
                if success:
                    jobs_submitted.append(job_id)
            
            elif job_type_choice == 2:  # Emergency job
                # First check if we need to activate emergency mode
                if not executor.in_emergency:
                    emergency_type = input("Emergency type (medical/fire/police): ").strip() or "medical"
                    emergency_level = input("Emergency level (low/medium/high/critical): ").strip() or "high"
                    executor.set_emergency_mode(emergency_type, emergency_level)
                    print(f"🚨 Emergency mode activated: {emergency_type} / {emergency_level}")
                
                job_id = f"emergency_job_{len(jobs_submitted) + 1}"
                job_data = {"task": "emergency_task", "priority": "critical", "type": "emergency"}
                success = executor.submit_job(job_id, job_data)
                status = "accepted" if success else "rejected"
                print(f"🚨 Emergency job '{job_id}': {status}")
                if success:
                    jobs_submitted.append(job_id)
            
            elif job_type_choice == 3:  # Check queue
                print(f"\n📊 Job Queue Status:")
                print(f"   Has pending jobs: {executor.has_pending_jobs()}")
                print(f"   Emergency mode: {executor.in_emergency}")
                if executor.emergency_context:
                    print(f"   Emergency type: {executor.emergency_context.emergency_type}")
                print(f"   Total jobs submitted: {len(jobs_submitted)}")
            
            elif job_type_choice == 4:  # Process job
                if executor.has_pending_jobs():
                    job = executor.get_next_job()
                    if job:
                        job_type = job.get('type', 'normal')
                        print(f"⚡ Processing {job_type} job: {job['job_id']}")
                        # Simulate processing time
                        time.sleep(0.5)
                        print(f"✅ Job {job['job_id']} completed!")
                    else:
                        print("❌ No job available to process")
                else:
                    print("📭 No pending jobs in queue")
        
        print("\n✅ Interactive emergency demo complete!")
        return True
    
    def interactive_system_exploration(self):
        """Interactive exploration of the complete system"""
        print("\n🔍 INTERACTIVE SYSTEM EXPLORATION")
        print("=" * 50)
        print("Explore the complete thesis system at your own pace!")
        
        if not self.wait_for_user():
            return False
        
        exploration_menu = [
            "Vector Clock Operations",
            "Emergency Response Simulation", 
            "System Health Check",
            "View Demo History",
            "Exit exploration"
        ]
        
        while True:
            choice = self.show_menu("What would you like to explore?", exploration_menu)
            
            if choice == 1:  # Vector clocks
                self.interactive_vector_clock_demo()
            elif choice == 2:  # Emergency response
                self.interactive_emergency_demo()
            elif choice == 3:  # System health
                self.show_system_health()
            elif choice == 4:  # Demo history
                self.show_demo_history()
            elif choice == 5:  # Exit
                print("\n👋 Thanks for exploring the system!")
                break
            
            if not self.wait_for_user("Continue exploring?"):
                break
        
        return True
    
    def show_system_health(self):
        """Show current system health"""
        print("\n💊 SYSTEM HEALTH CHECK")
        print("-" * 30)
        
        health_data = {
            'total_nodes': len(self.current_nodes),
            'healthy_nodes': len(self.current_nodes),  # Assume all healthy for demo
            'emergency_active': False,
            'recent_events': [
                'Interactive demo started',
                'User exploration in progress',
                f'{len(self.current_nodes)} nodes created'
            ]
        }
        
        self.visualizer.visualize_system_health(health_data)
    
    def show_demo_history(self):
        """Show history of demo interactions"""
        print("\n📚 DEMO HISTORY")
        print("-" * 30)
        
        if not self.demo_history:
            print("No demo history yet - start exploring to build history!")
        else:
            for i, event in enumerate(self.demo_history, 1):
                print(f"{i}. {event}")


def run_interactive_demo():
    """Run the complete interactive demonstration"""
    print("🎮 INTERACTIVE THESIS DEMONSTRATION")
    print("=" * 50)
    print("Welcome to the interactive thesis demo!")
    print("You can explore vector clocks and emergency response at your own pace.")
    print()
    
    demo = SimpleInteractiveDemo()
    
    try:
        # Main interactive loop
        demo.interactive_system_exploration()
        
        print("\n🎉 INTERACTIVE DEMO COMPLETE!")
        print("Thanks for exploring the vector clock emergency system!")
        return True
        
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user. Thanks for participating!")
        return False
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        print("⚠️  Some features may need additional setup")
        return False


def quick_interactive_test():
    """Quick test of interactive features"""
    print("🧪 Quick Interactive Test")
    print("-" * 30)
    
    demo = SimpleInteractiveDemo()
    
    # Test basic functionality without user input
    demo.current_nodes['test_node'] = VectorClock('test_node')
    demo.show_system_health()
    
    print("✅ Interactive demo components working!")
    return True


if __name__ == "__main__":
    run_interactive_demo()
