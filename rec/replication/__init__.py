"""
Vector Clock-Based Causal Consistency Implementation.

This package provides a capability-aware vector clock implementation for
distributed systems with energy-aware synchronization and emergency scenario
optimization.

Author: Sina Fadavi
Project: Master's Thesis - Vector Clock-Based Causal Consistency
University: [University Name]
Date: August 2025

Modules:
    core: Core vector clock and causal messaging implementations
    tests: Comprehensive test suite with unit and integration tests
    docs: Technical documentation and design specifications
    examples: Usage examples and demonstrations

References:
    Lamport, L. (1978). Time, clocks, and the ordering of events in a 
    distributed system. Communications of the ACM, 21(7), 558-565.
"""

from .core.vector_clock import VectorClock, CapabilityAwareVectorClock
from .core.causal_message import CausalMessage, CausalMessageHandler
from .core.capability_scorer import CapabilityScorer

__version__ = "0.1.0"
__author__ = "Sina Fadavi"
__email__ = "sina.fadavi@[university].edu"

__all__ = [
    "VectorClock",
    "CapabilityAwareVectorClock", 
    "CausalMessage",
    "CausalMessageHandler",
    "CapabilityScorer",
]
