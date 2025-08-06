# Step 5C: End-to-End System Validation (Simplified)
# Quick validation test for UCP Part B compliance

import json
import time
import requests
import threading
from typing import Dict, Any
from datetime import datetime
from pathlib import Path

import sys
import os
sys.path.insert(0, "/home/sina/Desktop/Related Work/pr/ma-sinafadavi")

from rec.util.log import LOG
from rec.nodes.brokers.vector_clock_broker import VectorClockBroker


class QuickValidationTest:
    """Simplified validation test for Step 5C"""
    
    def __init__(self):
        self.test_results = {}
        self.brokers = []
        
    def test_broker_coordination_basic(self) -> Dict[str, Any]:
        """Test basic broker coordination functionality"""
        LOG.info("🧪 Testing basic broker coordination")
        
        test_result = {
            "test_name": "Basic_Broker_Coordination",
            "start_time": datetime.now().isoformat(),
            "passed": False,
            "details": {}
        }
        
        try:
            # Create two coordinated brokers
            broker1 = VectorClockBroker(["127.0.0.1"], 8000, enable_coordination=True)
            broker2 = VectorClockBroker(["127.0.0.1"], 8001, enable_coordination=True)
            
            # Start brokers in separate threads
            def start_broker1():
                try:
                    broker1.run()
                except:
                    pass
                    
            def start_broker2():
                try:
                    broker2.run()
                except:
                    pass
            
            thread1 = threading.Thread(target=start_broker1, daemon=True)
            thread2 = threading.Thread(target=start_broker2, daemon=True)
            
            thread1.start()
            time.sleep(3)  # Let first broker start
            thread2.start()
            time.sleep(5)  # Let second broker start and discover first
            
            # Test broker communication
            broker_responses = []
            
            for port in [8000, 8001]:
                try:
                    response = requests.get(f"http://localhost:{port}/broker/vector-clock", timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        broker_responses.append({
                            "port": port,
                            "broker_id": data.get("broker_id"),
                            "vector_clock": data.get("vector_clock"),
                            "responsive": True
                        })
                    else:
                        broker_responses.append({"port": port, "responsive": False, "status": response.status_code})
                except Exception as e:
                    broker_responses.append({"port": port, "responsive": False, "error": str(e)})
            
            test_result["details"]["broker_responses"] = broker_responses
            
            # Test coordination endpoints
            coordination_status = []
            
            for port in [8000, 8001]:
                try:
                    response = requests.get(f"http://localhost:{port}/broker/coordination-status", timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        coordination_status.append({
                            "port": port,
                            "coordinator_running": data.get("coordinator_running", False),
                            "total_peers": data.get("total_peers", 0)
                        })
                except Exception as e:
                    coordination_status.append({"port": port, "error": str(e)})
            
            test_result["details"]["coordination_status"] = coordination_status
            
            # Evaluate results
            responsive_brokers = sum(1 for br in broker_responses if br.get("responsive", False))
            active_coordinators = sum(1 for cs in coordination_status if cs.get("coordinator_running", False))
            
            test_result["passed"] = responsive_brokers >= 2 and active_coordinators >= 1
            test_result["summary"] = {
                "responsive_brokers": responsive_brokers,
                "active_coordinators": active_coordinators
            }
            
            LOG.info(f"✅ Basic coordination test: {responsive_brokers}/2 brokers responsive, {active_coordinators} coordinators active")
            
            # Cleanup
            try:
                broker1.stop()
                broker2.stop()
            except:
                pass
            
        except Exception as e:
            test_result["error"] = str(e)
            LOG.error(f"❌ Basic coordination test failed: {e}")
        
        test_result["end_time"] = datetime.now().isoformat()
        return test_result
    
    def test_enhanced_conflict_resolution(self) -> Dict[str, Any]:
        """Test enhanced conflict resolution capabilities"""
        LOG.info("⚔️ Testing enhanced conflict resolution")
        
        test_result = {
            "test_name": "Enhanced_Conflict_Resolution",
            "start_time": datetime.now().isoformat(),
            "passed": False,
            "details": {}
        }
        
        try:
            from rec.nodes.enhanced_vector_clock_executor import SimpleEnhancedExecutor, ConflictStrategy, JobPriority
            import tempfile
            
            # Test different conflict resolution strategies
            strategies_tested = []
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Note: temp_dir not needed for SimpleEnhancedExecutor
                
                for strategy in ConflictStrategy:
                    strategy_result = {
                        "strategy": strategy.value,
                        "test_successful": False
                    }
                    
                    try:
                        # Create executor with specific strategy
                        executor_with_strategy = SimpleEnhancedExecutor(
                            node_id=f"test-{strategy.value}", 
                            strategy=strategy
                        )
                        
                        # Test basic functionality by getting status
                        stats = executor_with_strategy.status()
                        
                        if stats.get("strategy") == strategy.value:
                            strategy_result["test_successful"] = True
                            strategy_result["stats"] = {
                                "current_strategy": stats.get("strategy"),
                                "running_jobs": len(stats.get("running", [])),
                                "node_id": stats.get("node")
                            }
                        
                    except Exception as e:
                        strategy_result["error"] = str(e)
                    
                    strategies_tested.append(strategy_result)
                    LOG.info(f"✅ Tested strategy: {strategy.value}")
            
            test_result["details"]["strategies_tested"] = strategies_tested
            
            # Evaluate results
            successful_strategies = sum(1 for st in strategies_tested if st["test_successful"])
            test_result["passed"] = successful_strategies == 4  # All 4 strategies should work
            
            test_result["summary"] = {
                "total_strategies": len(strategies_tested),
                "successful_strategies": successful_strategies,
                "strategy_names": [st["strategy"] for st in strategies_tested if st["test_successful"]]
            }
            
            LOG.info(f"✅ Conflict resolution test: {successful_strategies}/4 strategies working")
            
        except Exception as e:
            test_result["error"] = str(e)
            LOG.error(f"❌ Conflict resolution test failed: {e}")
        
        test_result["end_time"] = datetime.now().isoformat()
        return test_result
    
    def test_vector_clock_functionality(self) -> Dict[str, Any]:
        """Test vector clock functionality"""
        LOG.info("🕐 Testing vector clock functionality")
        
        test_result = {
            "test_name": "Vector_Clock_Functionality",
            "start_time": datetime.now().isoformat(),
            "passed": False,
            "details": {}
        }
        
        try:
            from rec.replication.core.vector_clock import VectorClock
            
            # Test basic vector clock operations
            clock1 = VectorClock("node1")
            clock2 = VectorClock("node2")
            
            # Test tick operations
            initial_time1 = clock1.clock.copy()
            clock1.tick()
            after_tick1 = clock1.clock.copy()
            
            # Test update operations
            clock2.tick()
            clock2.tick()
            clock1.update(clock2.clock)
            after_update1 = clock1.clock.copy()
            
            test_result["details"]["vector_clock_operations"] = {
                "initial_clock1": initial_time1,
                "after_tick_clock1": after_tick1,
                "clock2_after_ticks": clock2.clock.copy(),
                "clock1_after_update": after_update1
            }
            
            # Verify vector clock properties
            tick_worked = after_tick1.get("node1", 0) > initial_time1.get("node1", 0)
            update_worked = after_update1.get("node2", 0) > 0
            
            test_result["passed"] = tick_worked and update_worked
            test_result["summary"] = {
                "tick_functionality": tick_worked,
                "update_functionality": update_worked
            }
            
            LOG.info(f"✅ Vector clock test: tick={tick_worked}, update={update_worked}")
            
        except Exception as e:
            test_result["error"] = str(e)
            LOG.error(f"❌ Vector clock test failed: {e}")
        
        test_result["end_time"] = datetime.now().isoformat()
        return test_result
    
    def run_step_5c_validation(self) -> Dict[str, Any]:
        """Run Step 5C validation tests"""
        LOG.info("🎯 Starting Step 5C: End-to-End System Validation")
        
        validation_results = {
            "validation_suite": "Step_5C_End_to_End_Validation",
            "start_time": datetime.now().isoformat(),
            "tests": {},
            "overall_passed": False
        }
        
        try:
            # Test 1: Vector Clock Functionality
            validation_results["tests"]["vector_clock"] = self.test_vector_clock_functionality()
            
            # Test 2: Enhanced Conflict Resolution
            validation_results["tests"]["conflict_resolution"] = self.test_enhanced_conflict_resolution()
            
            # Test 3: Basic Broker Coordination
            validation_results["tests"]["broker_coordination"] = self.test_broker_coordination_basic()
            
            # Evaluate overall results
            all_tests_passed = all(
                test_result.get("passed", False) 
                for test_result in validation_results["tests"].values()
            )
            
            validation_results["overall_passed"] = all_tests_passed
            validation_results["summary"] = {
                "vector_clock_working": validation_results["tests"]["vector_clock"]["passed"],
                "conflict_resolution_working": validation_results["tests"]["conflict_resolution"]["passed"],
                "broker_coordination_working": validation_results["tests"]["broker_coordination"]["passed"],
                "step_5c_complete": all_tests_passed
            }
            
            if all_tests_passed:
                LOG.info("✅ Step 5C: End-to-End System Validation PASSED")
            else:
                LOG.warning("❌ Step 5C: End-to-End System Validation FAILED")
            
        except Exception as e:
            validation_results["error"] = str(e)
            LOG.error(f"❌ Validation suite failed: {e}")
        
        validation_results["end_time"] = datetime.now().isoformat()
        return validation_results


def main():
    """Run Step 5C validation"""
    print("=" * 80)
    print("STEP 5C: END-TO-END SYSTEM VALIDATION (SIMPLIFIED)")
    print("=" * 80)
    
    validator = QuickValidationTest()
    
    try:
        results = validator.run_step_5c_validation()
        
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
            print(f"\n❗ Some validation tests failed")
            if "error" in results:
                print(f"🔍 Error: {results['error']}")
            
            # Show individual test results
            print("\n📋 Test Details:")
            for test_name, test_result in results.get("tests", {}).items():
                status = "✅ PASSED" if test_result.get("passed", False) else "❌ FAILED"
                print(f"  • {test_name.replace('_', ' ').title()}: {status}")
                if not test_result.get("passed", False) and "error" in test_result:
                    print(f"    Error: {test_result['error']}")
        
        print(f"\n⏱️  Duration: {results.get('start_time')} to {results.get('end_time')}")
        print("=" * 60)
        
        # Save detailed results
        workspace_path = "/home/sina/Desktop/Related Work/pr/ma-sinafadavi"
        results_file = Path(workspace_path) / "tests" / "step_5c_validation_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        return results.get("overall_passed", False)
        
    except KeyboardInterrupt:
        print("\n🛑 Validation interrupted by user")
        return False
    except Exception as e:
        print(f"\n💥 Validation execution failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
