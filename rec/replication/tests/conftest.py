"""
Test configuration and utilities for vector clock implementation.

This module sets up the testing framework for comprehensive testing
of vector clock components including unit tests, integration tests,
property-based tests, and performance benchmarks.
"""

import pytest
import sys
from pathlib import Path

# Add the project root to the Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
