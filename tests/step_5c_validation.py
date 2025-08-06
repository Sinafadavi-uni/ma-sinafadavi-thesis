# Step 5C: End-to-End System Validation
# Complete UCP Part B compliance verification and integration testing

import asyncio
import json
import os
import time
import threading
import requests
import subprocess
import tempfile
import signal
from typing import Dict, List, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from pathlib import Path

from rec.util.log import LOG


class UCPPartBValidationSuite:
    """
    Comprehensive end-to-end validation suite for UCP Part B compliance
    Tests the complete integration of all vector clock components
    """
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.test_results: Dict[str, Any] = {}
        self.broker_processes: List[subprocess.Popen] = []
        self.executor_processes: List[subprocess.Popen] = []
        self.test_start_time = None
        self.temp_dirs: List[str] = []
        
    def setup_test_environment(self) -> bool:
        """Setup complete multi-node test environment"""
        LOG.info("🔧 Setting up end-to-end test environment")
        
        try:
            # Create temporary directories for each node
            for i in range(3):
                temp_dir = tempfile.mkdtemp(prefix=f"ucp_test_broker_{i}_")
                self.temp_dirs.append(temp_dir)
                LOG.info(f"Created temp directory for broker {i}: {temp_dir}")
            
            for i in range(2):
                temp_dir = tempfile.mkdtemp(prefix=f"ucp_test_executor_{i}_")
                self.temp_dirs.append(temp_dir)
                LOG.info(f"Created temp directory for executor {i}: {temp_dir}")
                
            return True
            
        except Exception as e:
            LOG.error(f"❌ Failed to setup test environment: {e}")
            return False
    
    def start_multi_broker_network(self) -> bool:
        """Start a network of 3 coordinated brokers"""
        LOG.info("🚀 Starting multi-broker network")
        
        try:
            # Start 3 brokers with coordination enabled
            for i in range(3):
                port = 8000 + i
                temp_dir = self.temp_dirs[i]
                
                # Create broker startup script
                script_content = f'''
import sys
import os
sys.path.insert(0, "{self.workspace_path}")

from rec.nodes.brokers.vector_clock_broker import VectorClockBroker

# Start coordinated broker
broker = VectorClockBroker(
    host=["127.0.0.1"], 
    port={port},
    enable_coordination=True
)

try:
    LOG.info(f"Starting broker {i} on port {port}")
    broker.run()
except KeyboardInterrupt:
    LOG.info(f"Broker {i} shutting down gracefully")
    broker.stop()
except Exception as e:
    LOG.error(f"Broker {i} error: {{e}}")
    broker.stop()
'''
                
                script_path = Path(temp_dir) / "start_broker.py"
                with open(script_path, 'w') as f:
                    f.write(script_content)
                
                # Start broker process
                env = os.environ.copy()
                process = subprocess.Popen([
                    f"{self.workspace_path}/.venv/bin/python",
                    str(script_path)
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
                
                self.broker_processes.append(process)
                LOG.info(f"✅ Started broker {i} (PID: {process.pid}) on port {port}")
                
                # Give broker time to start
                time.sleep(3)
            
            # Wait for all brokers to be ready
            LOG.info("⏳ Waiting for brokers to initialize and discover each other...")
            time.sleep(15)  # Allow discovery and initial sync
            
            return self.verify_broker_network()
            
        except Exception as e:
            LOG.error(f"❌ Failed to start broker network: {e}")
            return False
    
    def verify_broker_network(self) -> bool:
        """Verify that all brokers are running and can communicate"""
        LOG.info("🔍 Verifying broker network connectivity")
        
        responsive_brokers = 0
        
        for i in range(3):
            port = 8000 + i
            try:
                response = requests.get(f"http://localhost:{port}/broker/vector-clock", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    broker_id = data.get("broker_id", f"unknown-{port}")
                    vector_clock = data.get("vector_clock", {})
                    
                    LOG.info(f"✅ Broker {i} (port {port}) responsive: {broker_id}")
                    LOG.debug(f"   Vector clock: {vector_clock}")
                    responsive_brokers += 1
                else:
                    LOG.warning(f"❌ Broker {i} (port {port}) returned HTTP {response.status_code}")
                    
            except Exception as e:
                LOG.warning(f"❌ Broker {i} (port {port}) not responsive: {e}")
        
        success = responsive_brokers >= 2  # At least 2 brokers must be working
        LOG.info(f"🎯 Broker network verification: {responsive_brokers}/3 brokers responsive")
        
        return success
    
    def test_emergency_scenario_integration(self) -> Dict[str, Any]:
        """Test complete emergency scenario with vector clock coordination"""
        LOG.info("🚨 Testing emergency scenario integration")
        
        test_result = {
            "test_name": "Emergency_Scenario_Integration",
            "start_time": datetime.now().isoformat(),
            "passed": False,
            "details": {}
        }
        
        try:
            # Step 1: Declare emergency on broker 0
            emergency_response = requests.post(
                "http://localhost:8000/broker/declare-emergency",
                params={"emergency_type": "validation_test_emergency"},
                timeout=10
            )
            
            if emergency_response.status_code != 200:
                raise Exception(f"Failed to declare emergency: HTTP {emergency_response.status_code}")
            
            emergency_data = emergency_response.json()
            test_result["details"]["emergency_declaration"] = {
                "status": emergency_data.get("status"),
                "emergency_type": emergency_data.get("emergency_type"),
                "timestamp": emergency_data.get("timestamp")
            }
            
            LOG.info("✅ Emergency declared on broker 0")
            
            # Step 2: Wait for sync propagation
            LOG.info("⏳ Waiting for emergency propagation across broker network...")
            time.sleep(70)  # Wait longer than sync interval (60s)
            
            # Step 3: Check if emergency propagated to other brokers
            propagation_results = []
            
            for i in range(1, 3):  # Check brokers 1 and 2
                port = 8000 + i
                try:
                    # Check vector clock updates
                    vc_response = requests.get(f"http://localhost:{port}/broker/vector-clock", timeout=5)
                    emergency_response = requests.get(f"http://localhost:{port}/broker/emergency-status", timeout=5)
                    
                    if vc_response.status_code == 200 and emergency_response.status_code == 200:
                        vc_data = vc_response.json()
                        emergency_data = emergency_response.json()
                        
                        # Check if vector clock was updated (indicates sync occurred)
                        vector_clock = vc_data.get("vector_clock", {})
                        has_updates = any(v > 0 for v in vector_clock.values())
                        
                        propagation_results.append({
                            "broker": f"broker-{i}",
                            "port": port,
                            "vector_clock_updated": has_updates,
                            "vector_clock": vector_clock,
                            "emergency_context": emergency_data.get("emergency_context"),
                            "sync_detected": has_updates
                        })
                        
                        LOG.info(f"✅ Broker {i} sync status: {has_updates}, emergency context: {emergency_data.get('emergency_context')}")
                    
                except Exception as e:
                    propagation_results.append({
                        "broker": f"broker-{i}",
                        "port": port,
                        "error": str(e)
                    })
                    LOG.warning(f"❌ Failed to check broker {i}: {e}")
            
            test_result["details"]["emergency_propagation"] = propagation_results
            
            # Step 4: Evaluate results
            successful_syncs = sum(1 for r in propagation_results if r.get("sync_detected", False))
            test_result["passed"] = successful_syncs >= 1  # At least one broker should sync
            
            LOG.info(f"🎯 Emergency propagation test: {successful_syncs}/{len(propagation_results)} brokers synced")
            
        except Exception as e:
            test_result["error"] = str(e)
            LOG.error(f"❌ Emergency scenario test failed: {e}")
        
        test_result["end_time"] = datetime.now().isoformat()
        return test_result
    
    def test_vector_clock_consistency(self) -> Dict[str, Any]:
        """Test vector clock consistency across the distributed system"""
        LOG.info("🕐 Testing vector clock consistency")
        
        test_result = {
            "test_name": "Vector_Clock_Consistency",
            "start_time": datetime.now().isoformat(),
            "passed": False,
            "details": {}
        }
        
        try:
            # Collect vector clocks from all brokers
            broker_clocks = []
            
            for i in range(3):
                port = 8000 + i
                try:
                    response = requests.get(f"http://localhost:{port}/broker/vector-clock", timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        broker_clocks.append({
                            "broker_id": data.get("broker_id"),
                            "port": port,
                            "vector_clock": data.get("vector_clock", {}),
                            "timestamp": datetime.now().isoformat()
                        })
                except Exception as e:
                    broker_clocks.append({
                        "port": port,
                        "error": str(e)
                    })
            
            test_result["details"]["broker_clocks"] = broker_clocks
            
            # Analyze consistency
            valid_clocks = [bc for bc in broker_clocks if "vector_clock" in bc]
            
            if len(valid_clocks) >= 2:
                # Check if vector clocks show synchronization activity
                all_clocks_have_updates = all(
                    any(v > 0 for v in bc["vector_clock"].values()) 
                    for bc in valid_clocks
                )
                
                # Check if at least some common nodes are present
                all_node_ids = set()
                for bc in valid_clocks:
                    all_node_ids.update(bc["vector_clock"].keys())
                
                common_nodes = set(valid_clocks[0]["vector_clock"].keys())
                for bc in valid_clocks[1:]:
                    common_nodes.intersection_update(bc["vector_clock"].keys())
                
                test_result["details"]["analysis"] = {
                    "valid_clocks_count": len(valid_clocks),
                    "all_clocks_have_updates": all_clocks_have_updates,
                    "total_unique_nodes": len(all_node_ids),
                    "common_nodes_count": len(common_nodes),
                    "common_nodes": list(common_nodes)
                }
                
                # Test passes if we have activity and some coordination
                test_result["passed"] = all_clocks_have_updates and len(common_nodes) > 0
                
                LOG.info(f"✅ Vector clock analysis: {len(valid_clocks)} valid clocks, {len(common_nodes)} common nodes")
            else:
                test_result["passed"] = False
                LOG.warning(f"❌ Insufficient valid clocks: {len(valid_clocks)}")
            
        except Exception as e:
            test_result["error"] = str(e)
            LOG.error(f"❌ Vector clock consistency test failed: {e}")
        
        test_result["end_time"] = datetime.now().isoformat()
        return test_result
    
    def test_performance_baseline(self) -> Dict[str, Any]:
        """Test performance baseline measurements"""
        LOG.info("📊 Testing performance baseline")
        
        test_result = {
            "test_name": "Performance_Baseline",
            "start_time": datetime.now().isoformat(),
            "passed": False,
            "details": {}
        }
        
        try:
            performance_metrics = []
            
            # Test broker response times
            for i in range(3):
                port = 8000 + i
                response_times = []
                
                for test_round in range(5):
                    try:
                        start_time = time.time()
                        response = requests.get(f"http://localhost:{port}/broker/vector-clock", timeout=10)
                        response_time = (time.time() - start_time) * 1000  # Convert to ms
                        
                        if response.status_code == 200:
                            response_times.append(response_time)
                    except Exception as e:
                        LOG.warning(f"Performance test failed for broker {i}, round {test_round}: {e}")
                
                if response_times:
                    avg_response_time = sum(response_times) / len(response_times)
                    max_response_time = max(response_times)
                    min_response_time = min(response_times)
                    
                    performance_metrics.append({
                        "broker": f"broker-{i}",
                        "port": port,
                        "avg_response_time_ms": round(avg_response_time, 2),
                        "max_response_time_ms": round(max_response_time, 2),
                        "min_response_time_ms": round(min_response_time, 2),
                        "successful_requests": len(response_times)
                    })
                    
                    LOG.info(f"✅ Broker {i} performance: avg {avg_response_time:.2f}ms, max {max_response_time:.2f}ms")
            
            test_result["details"]["performance_metrics"] = performance_metrics
            
            # Performance criteria: average response time should be < 1000ms
            if performance_metrics:
                avg_system_response = sum(pm["avg_response_time_ms"] for pm in performance_metrics) / len(performance_metrics)
                max_system_response = max(pm["max_response_time_ms"] for pm in performance_metrics)
                
                test_result["details"]["system_performance"] = {
                    "avg_system_response_ms": round(avg_system_response, 2),
                    "max_system_response_ms": round(max_system_response, 2),
                    "responsive_brokers": len(performance_metrics)
                }
                
                # Performance is acceptable if average < 1000ms and max < 5000ms
                test_result["passed"] = avg_system_response < 1000 and max_system_response < 5000
                
                LOG.info(f"🎯 System performance: avg {avg_system_response:.2f}ms, max {max_system_response:.2f}ms")
            else:
                test_result["passed"] = False
                LOG.warning("❌ No performance metrics collected")
            
        except Exception as e:
            test_result["error"] = str(e)
            LOG.error(f"❌ Performance baseline test failed: {e}")
        
        test_result["end_time"] = datetime.now().isoformat()
        return test_result
    
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run complete end-to-end validation suite"""
        LOG.info("🎯 Starting Step 5C: End-to-End System Validation")
        self.test_start_time = datetime.now()
        
        validation_results = {
            "validation_suite": "Step_5C_End_to_End_Validation",
            "start_time": self.test_start_time.isoformat(),
            "environment_setup": False,
            "broker_network": False,
            "tests": {},
            "overall_passed": False
        }
        
        try:
            # Setup test environment
            if not self.setup_test_environment():
                validation_results["error"] = "Failed to setup test environment"
                return validation_results
            
            validation_results["environment_setup"] = True
            
            # Start broker network
            if not self.start_multi_broker_network():
                validation_results["error"] = "Failed to start broker network"
                return validation_results
            
            validation_results["broker_network"] = True
            
            # Run validation tests
            LOG.info("🧪 Running validation test suite...")
            
            # Test 1: Emergency scenario integration
            validation_results["tests"]["emergency_integration"] = self.test_emergency_scenario_integration()
            
            # Test 2: Vector clock consistency
            validation_results["tests"]["vector_clock_consistency"] = self.test_vector_clock_consistency()
            
            # Test 3: Performance baseline
            validation_results["tests"]["performance_baseline"] = self.test_performance_baseline()
            
            # Evaluate overall results
            all_tests_passed = all(
                test_result.get("passed", False) 
                for test_result in validation_results["tests"].values()
            )
            
            validation_results["overall_passed"] = all_tests_passed
            validation_results["summary"] = {
                "environment_ready": validation_results["environment_setup"],
                "broker_network_operational": validation_results["broker_network"],
                "emergency_integration_working": validation_results["tests"]["emergency_integration"]["passed"],
                "vector_clock_consistent": validation_results["tests"]["vector_clock_consistency"]["passed"],
                "performance_acceptable": validation_results["tests"]["performance_baseline"]["passed"],
                "step_5c_complete": all_tests_passed
            }
            
            if all_tests_passed:
                LOG.info("✅ Step 5C: End-to-End System Validation PASSED")
            else:
                LOG.warning("❌ Step 5C: End-to-End System Validation FAILED")
            
        except Exception as e:
            validation_results["error"] = str(e)
            LOG.error(f"❌ Validation suite failed: {e}")
        
        finally:
            validation_results["end_time"] = datetime.now().isoformat()
            self.cleanup_test_environment()
        
        return validation_results
    
    def cleanup_test_environment(self):
        """Clean up test environment"""
        LOG.info("🧹 Cleaning up test environment")
        
        # Stop broker processes
        for i, process in enumerate(self.broker_processes):
            try:
                if process.poll() is None:  # Process is still running
                    process.terminate()
                    time.sleep(2)
                    if process.poll() is None:
                        process.kill()
                    LOG.info(f"✅ Stopped broker process {i}")
            except Exception as e:
                LOG.warning(f"❌ Error stopping broker process {i}: {e}")
        
        # Stop executor processes
        for i, process in enumerate(self.executor_processes):
            try:
                if process.poll() is None:
                    process.terminate()
                    time.sleep(2)
                    if process.poll() is None:
                        process.kill()
                    LOG.info(f"✅ Stopped executor process {i}")
            except Exception as e:
                LOG.warning(f"❌ Error stopping executor process {i}: {e}")
        
        # Clean up temporary directories
        import shutil
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir)
                LOG.debug(f"✅ Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                LOG.warning(f"❌ Failed to clean up {temp_dir}: {e}")
        
        LOG.info("🧹 Test environment cleanup completed")


def main():
    """Run Step 5C validation"""
    print("=" * 80)
    print("STEP 5C: END-TO-END SYSTEM VALIDATION")
    print("=" * 80)
    
    workspace_path = "/home/sina/Desktop/Related Work/pr/ma-sinafadavi"
    validator = UCPPartBValidationSuite(workspace_path)
    
    try:
        results = validator.run_comprehensive_validation()
        
        # Print results
        print("\n" + "=" * 60)
        print("STEP 5C VALIDATION RESULTS")
        print("=" * 60)
        
        if results.get("overall_passed"):
            print("✅ OVERALL RESULT: PASSED")
            print("\n🎉 End-to-End System Validation successful!")
            print("\n📋 Summary:")
            summary = results.get("summary", {})
            for key, value in summary.items():
                status = "✅" if value else "❌"
                print(f"  • {key.replace('_', ' ').title()}: {status}")
        else:
            print("❌ OVERALL RESULT: FAILED")
            print(f"\n❗ Validation failed")
            if "error" in results:
                print(f"🔍 Error: {results['error']}")
        
        print(f"\n⏱️  Duration: {results.get('start_time')} to {results.get('end_time')}")
        print("=" * 60)
        
        # Save detailed results
        results_file = Path(workspace_path) / "tests" / "step_5c_validation_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        return results.get("overall_passed", False)
        
    except KeyboardInterrupt:
        print("\n🛑 Validation interrupted by user")
        validator.cleanup_test_environment()
        return False
    except Exception as e:
        print(f"\n💥 Validation execution failed: {e}")
        validator.cleanup_test_environment()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
