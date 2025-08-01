# Simple Vector Clock Implementation for Emergency Systems
# Student implementation based on Lamport's vector clock paper

from .core.vector_clock import VectorClock, CapabilityAwareVectorClock, CapabilityScorer
from .core.causal_message import CausalMessage, MessageHandler

__version__ = "0.1.0"
__author__ = "Sina Fadavi"

__all__ = [
    "VectorClock",
    "CapabilityAwareVectorClock", 
    "CausalMessage",
    "MessageHandler",
    "CapabilityScorer",
]
