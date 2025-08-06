#!/usr/bin/env python3
"""
FINAL VALIDATION SUITE - Pre-Step 6 Review
Comprehensive testing of all UCP Part B components
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import time
import json
import subprocess
from datetime import datetime
from typing import Dict, Any, List

def run_test_command(command: str, description: str) -> Dict[str, Any]:
    """Run a test command and capture results"""
    print(f"\n🧪 {description}")
    print(f"Command: {command}")
    print("-" * 60)
    
    start_time = time.time()
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=120  # 2 minute timeout
        )
        duration = time.time() - start_time
        
        success = result.returncode == 0
        print(f"✅ PASSED" if success else f"❌ FAILED")
        print(f"Duration: {duration:.2f}s")
        
        if not success and result.stderr:
            print(f"Error: {result.stderr}")
            
        return {
            "test": description,
            "command": command,
            "success": success,
            "duration": duration,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
        
    except subprocess.TimeoutExpired:
        print(f"❌ TIMEOUT after 2 minutes")
        return {
            "test": description,
            "command": command,
            "success": False,
            "duration": 120,
            "error": "TIMEOUT"
        }
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return {
            "test": description,
            "command": command,
            "success": False,
            "error": str(e)
        }

def check_file_integrity() -> Dict[str, Any]:
    """Check that all required files exist and have no syntax errors"""
    print("\n🔍 CHECKING FILE INTEGRITY")
    print("=" * 60)
    
    required_files = [
        "rec/replication/core/vector_clock.py",
        "rec/nodes/brokers/vector_clock_broker.py", 
        "rec/nodes/brokers/multi_broker_coordinator.py",
        "rec/nodes/enhanced_vector_clock_executor.py",
        "rec/nodes/vector_clock_executor.py",
        "rec/tests/test_ucp_part_b_compliance.py",
        "tests/step_5c_simplified_validation.py",
        "tests/step_5c_validation.py"
    ]
    
    results = {}
    for file_path in required_files:
        exists = os.path.exists(file_path)
        if exists:
            # Check for syntax errors
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                compile(content, file_path, 'exec')
                syntax_ok = True
            except SyntaxError as e:
                syntax_ok = False
                print(f"❌ {file_path}: Syntax Error - {e}")
            except Exception as e:
                syntax_ok = False
                print(f"❌ {file_path}: Error - {e}")
        else:
            syntax_ok = False
            print(f"❌ {file_path}: File not found")
            
        results[file_path] = {
            "exists": exists,
            "syntax_ok": syntax_ok if exists else False
        }
        
        if exists and syntax_ok:
            print(f"✅ {file_path}")
    
    return results

def main():
    """Run comprehensive validation suite"""
    print("=" * 80)
    print("🎯 FINAL VALIDATION SUITE - UCP PART B IMPLEMENTATION")
    print("=" * 80)
    print(f"Started: {datetime.now().isoformat()}")
    
    # Get Python executable
    python_exe = '"/home/sina/Desktop/Related Work/pr/ma-sinafadavi/.venv/bin/python"'
    
    # Test results
    results = {
        "suite_name": "Final_UCP_Part_B_Validation",
        "start_time": datetime.now().isoformat(),
        "tests": [],
        "file_integrity": {}
    }
    
    # 1. File Integrity Check
    results["file_integrity"] = check_file_integrity()
    
    # 2. Core Tests
    test_commands = [
        (f'{python_exe} tests/step_5c_simplified_validation.py', 
         "Step 5C Simplified Validation"),
        
        (f'PYTHONPATH="/home/sina/Desktop/Related Work/pr/ma-sinafadavi" {python_exe} rec/tests/test_ucp_part_b_compliance.py', 
         "UCP Part B Compliance Test"),
         
        (f'{python_exe} step_5d_compliance_report.py', 
         "Step 5D Compliance Report Generation"),
    ]
    
    for command, description in test_commands:
        test_result = run_test_command(command, description)
        results["tests"].append(test_result)
    
    # 3. Summary
    results["end_time"] = datetime.now().isoformat()
    
    # Calculate overall success
    file_success = all(
        info["exists"] and info["syntax_ok"] 
        for info in results["file_integrity"].values()
    )
    test_success = all(test["success"] for test in results["tests"])
    overall_success = file_success and test_success
    
    results["summary"] = {
        "file_integrity_passed": file_success,
        "all_tests_passed": test_success,
        "overall_success": overall_success,
        "total_tests": len(results["tests"]),
        "passed_tests": sum(1 for test in results["tests"] if test["success"]),
        "failed_tests": sum(1 for test in results["tests"] if not test["success"])
    }
    
    # Save results
    with open("final_validation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Print final summary
    print("\n" + "=" * 80)
    print("🏁 FINAL VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Overall Result: {'✅ PASSED' if overall_success else '❌ FAILED'}")
    print(f"File Integrity: {'✅ PASSED' if file_success else '❌ FAILED'}")
    print(f"Tests Passed: {results['summary']['passed_tests']}/{results['summary']['total_tests']}")
    
    if overall_success:
        print("\n🎉 UCP PART B IMPLEMENTATION IS COMPLETE AND READY FOR STEP 6!")
        print("📄 All components validated successfully")
        print("🚀 Performance optimization can begin")
    else:
        print("\n⚠️  Issues found that need resolution before Step 6")
        
    print(f"\n📄 Detailed results saved to: final_validation_results.json")
    print("=" * 80)
    
    return 0 if overall_success else 1

if __name__ == "__main__":
    sys.exit(main())
