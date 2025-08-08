# Academic Validation Module for Master's Thesis
# Simple student-friendly academic validation tools

"""
Task 8: Academic Validation & Benchmarking
==========================================

This module provides simple academic validation tools for the thesis:
- Thesis requirement validation
- Academic benchmarking 
- Research contribution analysis
- Performance comparison
"""

# Make validation classes available at module level
from .thesis_validator import SimpleThesisValidator
from .academic_benchmarks import SimpleAcademicBenchmark  
from .research_analyzer import SimpleResearchAnalyzer

__all__ = [
    'SimpleThesisValidator',
    'SimpleAcademicBenchmark', 
    'SimpleResearchAnalyzer'
]
