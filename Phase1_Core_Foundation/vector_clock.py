"""
File 2: Vector Clock Implementation

Core vector clock implementation based on Lamport's algorithm,
extended for emergency scenarios and urban computing platforms.

This is the heart of the thesis - implements vector clock-based
causal consistency with emergency awareness.
"""

from typing import Dict, List, Optional
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Emergency levels for priority classification
class EmergencyLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class VectorClock:
    """
    Vector Clock implementation based on Lamport's algorithm
    
    Implements logical time for distributed systems with causal ordering.
    Extended for emergency scenarios in urban computing platforms.
    
    Key Operations:
    - tick(): Increment local time (Lamport Rule 1)
    - update(): Merge with incoming clock (Lamport Rule 2)  
    - compare(): Determine causal relationship between events
    """
    
    def __init__(self, node_id: str):
        """
        Initialize vector clock for a node
        
        Args:
            node_id: Unique identifier for this node
        """
        if not node_id:
            raise ValueError("Node ID cannot be empty")
            
        self.node_id = node_id
        self.clock = {}  # Dictionary storing timestamp per node
        logger.info(f"Vector clock initialized for node: {node_id}")

    def tick(self) -> None:
        """
        Increment local timestamp (Lamport Rule 1)
        
        Called before any local event to advance logical time.
        This ensures local events have increasing timestamps.
        """
        self.clock[self.node_id] = self.clock.get(self.node_id, 0) + 1

    def update(self, incoming_clock: Dict[str, int]) -> None:
        """
        Update vector clock with incoming timestamps (Lamport Rule 2)
        
        Merges this clock with incoming clock data, taking maximum
        timestamp for each node, then increments local time.
        
        Args:
            incoming_clock: Dictionary of node_id -> timestamp pairs
        """
        if not isinstance(incoming_clock, dict):
            raise TypeError("Incoming clock must be a dictionary")
            
        # Merge clocks: take maximum timestamp for each node
        for node_id, timestamp in incoming_clock.items():
            if not isinstance(timestamp, int) or timestamp < 0:
                raise ValueError(f"Invalid timestamp for node {node_id}: {timestamp}")
            self.clock[node_id] = max(self.clock.get(node_id, 0), timestamp)
        
        # Increment local time after merge
        self.tick()

    def compare(self, other_clock) -> str:
        """
        Compare this vector clock with another to determine causal relationship
        
        Args:
            other_clock: Another VectorClock instance or clock dictionary
            
        Returns:
            str: "before", "after", or "concurrent"
                - "before": this clock causally precedes other
                - "after": other clock causally precedes this  
                - "concurrent": events are concurrent (no causal relationship)
        """
        # Handle both VectorClock objects and dictionaries
        if isinstance(other_clock, VectorClock):
            other_dict = other_clock.clock
        elif isinstance(other_clock, dict):
            other_dict = other_clock
        else:
            raise TypeError("Can only compare with VectorClock or dict")

        # Get all node IDs from both clocks
        all_nodes = set(self.clock.keys()) | set(other_dict.keys())
        
        self_less = False  # True if this clock is less in any dimension
        other_less = False  # True if other clock is less in any dimension
        
        # Compare timestamps for each node
        for node_id in all_nodes:
            self_time = self.clock.get(node_id, 0)
            other_time = other_dict.get(node_id, 0)
            
            if self_time < other_time:
                self_less = True
            elif self_time > other_time:
                other_less = True
        
        # Determine causal relationship
        if self_less and not other_less:
            return "before"  # This clock causally precedes other
        elif other_less and not self_less:
            return "after"   # Other clock causally precedes this
        else:
            return "concurrent"  # Events are concurrent
    
    def to_dict(self) -> Dict[str, int]:
        """
        Convert vector clock to dictionary representation
        
        Returns:
            dict: Copy of internal clock state
        """
        return dict(self.clock)
    
    def copy(self) -> 'VectorClock':
        """
        Create a copy of this vector clock
        
        Returns:
            VectorClock: New instance with same state
        """
        new_clock = VectorClock(self.node_id)
        new_clock.clock = dict(self.clock)
        return new_clock
    
    def get_time_for_node(self, node_id: str) -> int:
        """
        Get timestamp for a specific node
        
        Args:
            node_id: Node to get timestamp for
            
        Returns:
            int: Timestamp for the node (0 if not present)
        """
        return self.clock.get(node_id, 0)
    
    def __str__(self) -> str:
        """String representation of vector clock"""
        return f"VectorClock({self.node_id}): {self.clock}"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return f"VectorClock(node_id='{self.node_id}', clock={self.clock})"

class EmergencyContext:
    """
    Context information for emergency scenarios
    
    Encapsulates emergency type, priority level, and related metadata
    for emergency-aware distributed coordination.
    """
    
    def __init__(self, emergency_type: str, level: EmergencyLevel, location: Optional[str] = None):
        """
        Initialize emergency context
        
        Args:
            emergency_type: Type of emergency (e.g., "fire", "medical", "flood")
            level: Emergency priority level
            location: Optional location information
        """
        self.emergency_type = emergency_type
        self.level = level
        self.location = location
        self.timestamp = None  # Set when emergency is declared
        
    def is_critical(self) -> bool:
        """Check if emergency is high priority (HIGH or CRITICAL level)"""
        return self.level in (EmergencyLevel.HIGH, EmergencyLevel.CRITICAL)
    
    def get_priority_score(self) -> int:
        """Get numeric priority score for emergency"""
        return self.level.value
    
    def __str__(self) -> str:
        """String representation of emergency context"""
        return f"Emergency({self.emergency_type}/{self.level.name})"

def create_emergency(emergency_type: str, level, location: Optional[str] = None) -> EmergencyContext:
    """
    Create emergency context with flexible level specification
    
    Args:
        emergency_type: Type of emergency
        level: EmergencyLevel enum or string ("low", "medium", "high", "critical")
        location: Optional location
        
    Returns:
        EmergencyContext: Configured emergency context
    """
    # Convert string level to enum if needed
    if isinstance(level, str):
        level_map = {
            "low": EmergencyLevel.LOW,
            "medium": EmergencyLevel.MEDIUM,
            "high": EmergencyLevel.HIGH,
            "critical": EmergencyLevel.CRITICAL
        }
        level = level_map.get(level.lower(), EmergencyLevel.LOW)
    
    return EmergencyContext(emergency_type, level, location)

# Example usage and testing
if __name__ == "__main__":
    print("✅ Vector Clock Implementation - File 2 Complete")
    
    # Test basic vector clock operations
    clock1 = VectorClock("node1")
    clock2 = VectorClock("node2")
    
    # Test tick operation
    clock1.tick()
    print(f"Clock1 after tick: {clock1.clock}")
    
    # Test update operation
    clock2.tick()
    clock1.update(clock2.clock)
    print(f"Clock1 after update: {clock1.clock}")
    
    # Test comparison
    relation = clock1.compare(clock2)
    print(f"Clock1 vs Clock2: {relation}")
    
    # Test emergency context
    emergency = create_emergency("fire", "critical")
    print(f"Emergency: {emergency}, Critical: {emergency.is_critical()}")
    
    print("   Core vector clock with emergency support ready!")
    print("   Foundation for causal consistency and FCFS policies")
