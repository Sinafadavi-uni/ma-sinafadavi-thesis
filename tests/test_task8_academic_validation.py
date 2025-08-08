# Task 8 Testing Suite - Simple student-friendly tests

import pytest
import json
from pathlib import Path

# Import Task 8 components
from rec.academic.task8_integration import Task8AcademicValidation, run_complete_task8
from rec.academic.thesis_validator import SimpleThesisValidator
from rec.academic.academic_benchmarks import SimpleAcademicBenchmark
from rec.academic.research_analyzer import SimpleResearchAnalyzer


class TestTask8Components:
    """Simple tests for Task 8 academic validation components"""
    
    def test_thesis_validator_creation(self):
        """Test that thesis validator can be created"""
        validator = SimpleThesisValidator()
        assert validator is not None
        assert hasattr(validator, 'validation_results')
        print("✅ Thesis validator creation test passed")
    
    def test_academic_benchmark_creation(self):
        """Test that academic benchmark can be created"""
        benchmark = SimpleAcademicBenchmark()
        assert benchmark is not None
        assert hasattr(benchmark, 'benchmark_results')
        print("✅ Academic benchmark creation test passed")
    
    def test_research_analyzer_creation(self):
        """Test that research analyzer can be created"""
        analyzer = SimpleResearchAnalyzer()
        assert analyzer is not None
        assert hasattr(analyzer, 'analysis_results')
        print("✅ Research analyzer creation test passed")
    
    def test_task8_integration_creation(self):
        """Test that Task 8 integration can be created"""
        task8 = Task8AcademicValidation()
        assert task8 is not None
        assert hasattr(task8, 'task8_results')
        print("✅ Task 8 integration creation test passed")


class TestTask8Validation:
    """Simple tests for Task 8 validation functionality"""
    
    def test_thesis_validation_basic(self):
        """Test basic thesis validation functionality"""
        validator = SimpleThesisValidator()
        validator.start_validation()
        
        # Check that some validation was performed
        assert len(validator.validation_results) > 0
        print("✅ Basic thesis validation test passed")
    
    def test_academic_benchmark_basic(self):
        """Test basic academic benchmarking functionality"""
        benchmark = SimpleAcademicBenchmark()
        benchmark.start_benchmarking()
        
        # Check that some benchmarking was performed
        assert len(benchmark.benchmark_results) > 0
        print("✅ Basic academic benchmark test passed")
    
    def test_research_analysis_basic(self):
        """Test basic research analysis functionality"""
        analyzer = SimpleResearchAnalyzer()
        analyzer.start_analysis()
        
        # Check that some analysis was performed
        assert len(analyzer.analysis_results) > 0
        print("✅ Basic research analysis test passed")


class TestTask8Integration:
    """Tests for complete Task 8 integration"""
    
    def test_task8_complete_flow(self):
        """Test complete Task 8 academic validation flow"""
        task8 = Task8AcademicValidation()
        task8.start_task8()
        
        # Generate comprehensive report
        report = task8.generate_comprehensive_academic_report()
        
        # Verify report structure
        assert 'task8_completion_date' in report
        assert 'academic_validation_summary' in report
        assert 'detailed_reports' in report
        
        # Verify summary metrics
        summary = report['academic_validation_summary']
        assert 'thesis_requirements_met' in summary
        assert 'benchmark_metrics_collected' in summary
        assert 'research_methodology_score' in summary
        assert 'overall_academic_score' in summary
        assert 'academic_submission_ready' in summary
        
        print("✅ Complete Task 8 integration test passed")
    
    def test_task8_report_generation(self):
        """Test Task 8 report generation"""
        task8 = Task8AcademicValidation()
        task8.start_task8()
        report = task8.generate_comprehensive_academic_report()
        
        # Test summary printing (should not raise errors)
        task8.print_task8_summary()
        
        print("✅ Task 8 report generation test passed")


def test_task8_basic_imports():
    """Test that all Task 8 modules can be imported without errors"""
    try:
        from rec.academic.thesis_validator import SimpleThesisValidator
        from rec.academic.academic_benchmarks import SimpleAcademicBenchmark
        from rec.academic.research_analyzer import SimpleResearchAnalyzer
        from rec.academic.task8_integration import Task8AcademicValidation
        print("✅ All Task 8 imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_task8_quick_validation():
    """Quick test to verify Task 8 is working properly"""
    print("🧪 Running Task 8 Quick Validation Test")
    print("-" * 40)
    
    try:
        # Test imports
        assert test_task8_basic_imports()
        
        # Test component creation
        validator = SimpleThesisValidator()
        benchmark = SimpleAcademicBenchmark()
        analyzer = SimpleResearchAnalyzer()
        task8 = Task8AcademicValidation()
        
        # Test basic functionality
        validator.start_validation()
        benchmark.start_benchmarking()
        analyzer.start_analysis()
        
        # Test integration
        task8.start_task8()
        report = task8.generate_comprehensive_academic_report()
        
        # Verify report exists and has required structure
        assert 'academic_validation_summary' in report
        
        print("✅ Task 8 quick validation passed - all components working!")
        return True
        
    except Exception as e:
        print(f"❌ Task 8 validation failed: {e}")
        return False


def run_task8_test_suite():
    """Run complete Task 8 test suite"""
    print("🧪 TASK 8 ACADEMIC VALIDATION TEST SUITE")
    print("=" * 50)
    
    success_count = 0
    total_tests = 0
    
    # Run quick validation first
    print("\n🔍 Quick Validation:")
    if test_task8_quick_validation():
        success_count += 1
    total_tests += 1
    
    # Run component tests
    print("\n🧩 Component Tests:")
    component_tests = TestTask8Components()
    try:
        component_tests.test_thesis_validator_creation()
        component_tests.test_academic_benchmark_creation()
        component_tests.test_research_analyzer_creation()
        component_tests.test_task8_integration_creation()
        success_count += 4
    except Exception as e:
        print(f"❌ Component tests failed: {e}")
    total_tests += 4
    
    # Run validation tests
    print("\n✅ Validation Tests:")
    validation_tests = TestTask8Validation()
    try:
        validation_tests.test_thesis_validation_basic()
        validation_tests.test_academic_benchmark_basic()
        validation_tests.test_research_analysis_basic()
        success_count += 3
    except Exception as e:
        print(f"❌ Validation tests failed: {e}")
    total_tests += 3
    
    # Run integration tests
    print("\n🔗 Integration Tests:")
    integration_tests = TestTask8Integration()
    try:
        integration_tests.test_task8_complete_flow()
        integration_tests.test_task8_report_generation()
        success_count += 2
    except Exception as e:
        print(f"❌ Integration tests failed: {e}")
    total_tests += 2
    
    # Print summary
    print("\n" + "="*50)
    print(f"🧪 TASK 8 TEST SUITE RESULTS")
    print("="*50)
    print(f"✅ Tests Passed: {success_count}/{total_tests}")
    print(f"📊 Success Rate: {(success_count/total_tests)*100:.1f}%")
    
    if success_count == total_tests:
        print("🎉 ALL TASK 8 TESTS PASSED!")
        print("🎓 Task 8 Academic Validation ready for use!")
    else:
        print("⚠️  Some tests failed - check implementation")
    
    return success_count == total_tests


if __name__ == "__main__":
    run_task8_test_suite()
