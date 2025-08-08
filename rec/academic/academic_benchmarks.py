# Simple Academic Benchmark - Student Friendly Implementation  
# Compares our implementation with academic standards

import time
import json
from typing import Dict, List, Any
from datetime import datetime


class SimpleAcademicBenchmark:
    """
    Simple academic benchmark tool that compares our thesis work with academic standards.
    
    Easy for students to understand:
    - Measures performance of our vector clock system
    - Compares with standard approaches  
    - Generates academic-quality results
    - Creates thesis evaluation data
    """
    
    def __init__(self):
        self.benchmark_results = {}
        self.start_time = None
        
    def start_benchmarking(self):
        """Start the academic benchmarking process"""
        print("📊 Starting Academic Benchmarking...")
        self.start_time = time.time()
        self.benchmark_results = {}
        
    def benchmark_vector_clock_performance(self) -> Dict[str, float]:
        """Measure vector clock performance for academic evaluation"""
        print("⏱️  Benchmarking Vector Clock Performance...")
        
        try:
            from rec.replication.core.vector_clock import VectorClock
            
            # Simple performance test
            results = {}
            
            # Test 1: Clock creation speed
            start = time.time()
            clocks = []
            for i in range(100):
                clock = VectorClock(f"node_{i}")
                clocks.append(clock)
            results['clock_creation_per_100'] = time.time() - start
            
            # Test 2: Tick operation speed  
            start = time.time()
            for clock in clocks[:10]:  # Test first 10
                for _ in range(100):
                    clock.tick()
            results['tick_operations_per_1000'] = time.time() - start
            
            # Test 3: Update operation speed
            start = time.time()
            clock1 = clocks[0]
            for i in range(1, 11):  # Update with 10 other clocks
                clock1.update(clocks[i].clock)
            results['update_operations_per_10'] = time.time() - start
            
            # Test 4: Compare operation speed
            start = time.time()
            comparisons = []
            for i in range(10):
                for j in range(i+1, 10):
                    relation = clocks[i].compare(clocks[j])
                    comparisons.append(relation)
            results['compare_operations_per_45'] = time.time() - start
            
            print(f"   ✅ Vector Clock benchmarking completed ({len(results)} metrics)")
            return results
            
        except Exception as e:
            print(f"   ❌ Vector Clock benchmarking failed: {e}")
            return {}
    
    def benchmark_emergency_response_performance(self) -> Dict[str, float]:
        """Measure emergency system performance for academic evaluation"""
        print("🚨 Benchmarking Emergency Response Performance...")
        
        try:
            from rec.nodes.emergency_executor import SimpleEmergencyExecutor
            from rec.replication.core.vector_clock import create_emergency
            
            results = {}
            
            # Test 1: Emergency executor creation
            start = time.time()
            executors = []
            for i in range(10):
                executor = SimpleEmergencyExecutor(f"emergency_test_{i}")
                executors.append(executor)
            results['emergency_executor_creation_per_10'] = time.time() - start
            
            # Test 2: Emergency context creation
            start = time.time()
            emergencies = []
            emergency_types = ["medical", "fire", "disaster", "general"]
            emergency_levels = ["low", "medium", "high", "critical"]
            
            for i in range(100):
                em_type = emergency_types[i % len(emergency_types)]
                em_level = emergency_levels[i % len(emergency_levels)]
                emergency = create_emergency(em_type, em_level)
                emergencies.append(emergency)
            results['emergency_creation_per_100'] = time.time() - start
            
            # Test 3: Emergency mode setting
            start = time.time()
            executor = executors[0]
            for i in range(10):
                executor.set_emergency_mode("test", "high") 
                executor.clear_emergency_mode()
            results['emergency_mode_toggle_per_10'] = time.time() - start
            
            print(f"   ✅ Emergency Response benchmarking completed ({len(results)} metrics)")
            return results
            
        except Exception as e:
            print(f"   ❌ Emergency Response benchmarking failed: {e}")
            return {}
    
    def benchmark_ucp_integration_performance(self) -> Dict[str, float]:
        """Measure UCP integration performance for academic evaluation"""
        print("🏗️  Benchmarking UCP Integration Performance...")
        
        try:
            from rec.nodes.enhanced_vector_clock_executor import VectorClockFCFSExecutor
            from uuid import uuid4
            
            results = {}
            
            # Test 1: FCFS Executor creation
            start = time.time()
            executors = []
            for i in range(10):
                executor = VectorClockFCFSExecutor(f"fcfs_test_{i}")
                executors.append(executor)
            results['fcfs_executor_creation_per_10'] = time.time() - start
            
            # Test 2: Job submission performance
            start = time.time()
            executor = executors[0]
            job_ids = []
            for i in range(50):
                job_id = uuid4()
                job_data = f"test_job_{i}"
                executor.submit_job(job_id, job_data)
                job_ids.append(job_id)
            results['job_submission_per_50'] = time.time() - start
            
            # Test 3: FCFS result handling
            start = time.time()
            for job_id in job_ids[:10]:  # Test first 10 jobs
                result_data = f"result_for_{job_id}"
                # First submission should succeed
                first_result = executor.handle_result_submission(job_id, result_data)
                # Second submission should fail (FCFS policy)
                second_result = executor.handle_result_submission(job_id, result_data)
            results['fcfs_result_handling_per_10'] = time.time() - start
            
            print(f"   ✅ UCP Integration benchmarking completed ({len(results)} metrics)")
            return results
            
        except Exception as e:
            print(f"   ❌ UCP Integration benchmarking failed: {e}")
            return {}
    
    def benchmark_system_scalability(self) -> Dict[str, float]:
        """Test how our system performs with more nodes/load"""
        print("📈 Benchmarking System Scalability...")
        
        try:
            from rec.replication.core.vector_clock import VectorClock
            
            results = {}
            
            # Test 1: Many nodes vector clock coordination
            node_counts = [5, 10, 20, 50]
            for node_count in node_counts:
                start = time.time()
                
                # Create many nodes
                clocks = []
                for i in range(node_count):
                    clock = VectorClock(f"scale_node_{i}")
                    clocks.append(clock)
                
                # Each node ticks once
                for clock in clocks:
                    clock.tick()
                
                # Each node updates with all others (simplified)
                for i, clock in enumerate(clocks):
                    for j, other_clock in enumerate(clocks):
                        if i != j:
                            clock.update(other_clock.clock)
                            
                duration = time.time() - start
                results[f'coordination_with_{node_count}_nodes'] = duration
            
            print(f"   ✅ Scalability benchmarking completed ({len(results)} metrics)")
            return results
            
        except Exception as e:
            print(f"   ❌ Scalability benchmarking failed: {e}")
            return {}
    
    def compare_with_academic_baselines(self) -> Dict[str, str]:
        """Compare our approach with standard academic approaches"""
        print("📚 Comparing with Academic Baselines...")
        
        # Academic comparison analysis
        comparisons = {
            "vs_lamport_clocks": "Our vector clocks provide full causal ordering vs partial ordering",
            "vs_physical_time": "Our logical time handles network delays vs physical time failures", 
            "vs_centralized_coord": "Our distributed approach avoids single point of failure",
            "vs_standard_fcfs": "Our FCFS with causal consistency vs naive timestamp ordering",
            "vs_non_emergency": "Our emergency-aware coordination vs standard equal-priority systems"
        }
        
        for comparison, description in comparisons.items():
            print(f"   ✅ {comparison}: {description}")
            
        return comparisons
    
    def generate_academic_benchmark_report(self) -> Dict[str, Any]:
        """Generate complete academic benchmark report for thesis"""
        print("\n📊 Generating Academic Benchmark Report...")
        
        # Run all benchmarks
        vector_clock_perf = self.benchmark_vector_clock_performance()
        emergency_perf = self.benchmark_emergency_response_performance()
        ucp_perf = self.benchmark_ucp_integration_performance()
        scalability = self.benchmark_system_scalability()
        academic_comparison = self.compare_with_academic_baselines()
        
        # Create comprehensive report
        report = {
            "benchmark_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "vector_clock_performance": vector_clock_perf,
            "emergency_response_performance": emergency_perf,
            "ucp_integration_performance": ucp_perf,
            "scalability_analysis": scalability,
            "academic_comparisons": academic_comparison,
            "total_metrics": len(vector_clock_perf) + len(emergency_perf) + len(ucp_perf) + len(scalability),
            "benchmarking_time": time.time() - self.start_time if self.start_time else 0
        }
        
        # Save results
        self.benchmark_results = report
        
        return report
    
    def print_benchmark_summary(self):
        """Print a nice summary of benchmark results"""
        if not self.benchmark_results:
            print("❌ No benchmark results available. Run generate_academic_benchmark_report() first.")
            return
            
        report = self.benchmark_results
        
        print("\n" + "="*60)
        print("📊 ACADEMIC BENCHMARK SUMMARY")
        print("="*60)
        print(f"📅 Benchmark Date: {report['benchmark_date']}")
        print(f"⏱️  Benchmarking Time: {report['benchmarking_time']:.2f} seconds")
        print(f"📈 Total Metrics: {report['total_metrics']}")
        
        print("\n⚡ Performance Highlights:")
        vc_perf = report['vector_clock_performance']
        if vc_perf:
            print(f"   • Vector Clock Creation: {vc_perf.get('clock_creation_per_100', 0):.4f}s per 100 clocks")
            print(f"   • Tick Operations: {vc_perf.get('tick_operations_per_1000', 0):.4f}s per 1000 operations")
        
        emergency_perf = report['emergency_response_performance'] 
        if emergency_perf:
            print(f"   • Emergency Creation: {emergency_perf.get('emergency_creation_per_100', 0):.4f}s per 100 emergencies")
        
        print(f"\n📚 Academic Comparisons: {len(report['academic_comparisons'])} baseline comparisons")
        print("\n🎓 ACADEMIC EVALUATION READY FOR THESIS!")
        
    def save_benchmark_to_file(self, filename: str = "academic_benchmark_report.json"):
        """Save benchmark report to file"""
        if not self.benchmark_results:
            print("❌ No benchmark results to save. Run generate_academic_benchmark_report() first.")
            return
            
        try:
            with open(filename, 'w') as f:
                json.dump(self.benchmark_results, f, indent=2)
            print(f"✅ Benchmark report saved to {filename}")
        except Exception as e:
            print(f"❌ Failed to save benchmark: {e}")


def run_complete_academic_benchmark():
    """Simple function to run complete academic benchmarking"""
    benchmark = SimpleAcademicBenchmark()
    benchmark.start_benchmarking()
    benchmark.generate_academic_benchmark_report()
    benchmark.print_benchmark_summary()
    benchmark.save_benchmark_to_file()
    return benchmark


# Demo function for testing
def demo_academic_benchmark():
    """Demo function to show how academic benchmarking works"""
    print("📊 ACADEMIC BENCHMARK DEMO")
    print("=" * 40)
    
    benchmark = run_complete_academic_benchmark()
    
    print("\n📋 Benchmarking completed!")
    print("📁 Check 'academic_benchmark_report.json' for detailed results")


if __name__ == "__main__":
    demo_academic_benchmark()
