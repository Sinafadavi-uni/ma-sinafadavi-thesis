# 🔗 Consistency Module - Causal consistency and FCFS policies

from ..algorithms.vector_clock import VectorClock, EmergencyLevel, create_emergency
from ..algorithms.causal_message import CausalMessage

__all__ = [
    # Core consistency algorithms
    'VectorClock',
    'EmergencyLevel', 
    'create_emergency',
    'CausalMessage'
]
