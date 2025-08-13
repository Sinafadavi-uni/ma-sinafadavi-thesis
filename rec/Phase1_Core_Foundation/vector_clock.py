"""
File 2: Vector Clock Implementation

Core vector clock implementation based on Lamport's algorithm,
extended for emergency scenarios and urban computing platforms.

This is the heart of the thesis - implements vector clock-based
causal consistency with emergency awareness.
"""

from typing import Dict, Optional
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enum for emergency levels
class EmergencyLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class VectorClock:
    def __init__(self, node_id: str):
        if not node_id:
            raise ValueError("Node ID cannot be empty")

        self.node_id = node_id
        self.clock = {}
        logger.info(f"Vector clock initialized for node: {node_id}")

    def tick(self) -> None:
        self.clock[self.node_id] = self.clock.get(self.node_id, 0) + 1

    def update(self, incoming_clock: Dict[str, int]) -> None:
        if not isinstance(incoming_clock, dict):
            raise TypeError("Incoming clock must be a dictionary")

        for node, time in incoming_clock.items():
            if not isinstance(time, int) or time < 0:
                raise ValueError(f"Invalid timestamp for {node}: {time}")
            self.clock[node] = max(self.clock.get(node, 0), time)

        self.tick()

    def compare(self, other_clock) -> str:
        if isinstance(other_clock, VectorClock):
            other_dict = other_clock.clock
        elif isinstance(other_clock, dict):
            other_dict = other_clock
        else:
            raise TypeError("Can only compare with VectorClock or dict")

        all_nodes = set(self.clock) | set(other_dict)
        self_less = False
        other_less = False

        for node in all_nodes:
            a = self.clock.get(node, 0)
            b = other_dict.get(node, 0)
            if a < b:
                self_less = True
            elif a > b:
                other_less = True

        if self_less and not other_less:
            return "before"
        elif other_less and not self_less:
            return "after"
        else:
            return "concurrent"

    def to_dict(self) -> Dict[str, int]:
        return dict(self.clock)

    def copy(self) -> 'VectorClock':
        new_vc = VectorClock(self.node_id)
        new_vc.clock = dict(self.clock)
        return new_vc

    def get_time_for_node(self, node_id: str) -> int:
        return self.clock.get(node_id, 0)

    def __str__(self) -> str:
        return f"VectorClock({self.node_id}): {self.clock}"

    def __repr__(self) -> str:
        return f"VectorClock(node_id='{self.node_id}', clock={self.clock})"

class EmergencyContext:
    def __init__(self, emergency_type: str, level: EmergencyLevel, location: Optional[str] = None):
        self.emergency_type = emergency_type
        self.level = level
        self.location = location
        self.timestamp = None

    def is_critical(self) -> bool:
        return self.level in (EmergencyLevel.HIGH, EmergencyLevel.CRITICAL)

    def get_priority_score(self) -> int:
        return self.level.value

    def __str__(self) -> str:
        return f"Emergency({self.emergency_type}/{self.level.name})"

def create_emergency(emergency_type: str, level, location: Optional[str] = None) -> EmergencyContext:
    if isinstance(level, str):
        level_map = {
            "low": EmergencyLevel.LOW,
            "medium": EmergencyLevel.MEDIUM,
            "high": EmergencyLevel.HIGH,
            "critical": EmergencyLevel.CRITICAL
        }
        level = level_map.get(level.lower(), EmergencyLevel.LOW)

    return EmergencyContext(emergency_type, level, location)

if __name__ == "__main__":
    print("✅ Vector Clock Implementation - File 2 Complete")

    clock1 = VectorClock("node1")
    clock2 = VectorClock("node2")

    clock1.tick()
    print(f"Clock1 after tick: {clock1.clock}")

    clock2.tick()
    clock1.update(clock2.clock)
    print(f"Clock1 after update: {clock1.clock}")

    relation = clock1.compare(clock2)
    print(f"Clock1 vs Clock2: {relation}")

    emergency = create_emergency("fire", "critical")
    print(f"Emergency: {emergency}, Critical: {emergency.is_critical()}")

    print("   Core vector clock with emergency support ready!")
    print("   Foundation for causal consistency and FCFS policies")

