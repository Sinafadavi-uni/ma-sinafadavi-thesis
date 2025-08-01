"""
Vector Clock Implementation for Distributed Systems.

This module implements vector clocks with capability-aware extensions for
causal consistency in distributed computing environments, particularly
optimized for emergency scenarios and energy-constrained devices.

Classes:
    VectorClock: Basic vector clock implementation
    CapabilityAwareVectorClock: Enhanced vector clock with capability scoring
    ClockRelation: Enumeration for clock comparison results

References:
    Lamport, L. (1978). Time, clocks, and the ordering of events in a 
    distributed system. Communications of the ACM, 21(7), 558-565.
    
    Fidge, C. J. (1988). Timestamps in message-passing systems that preserve 
    the partial ordering. Australian Computer Science Communications, 10(1), 56-66.

Author: Sina Fadavi
Date: August 2025
"""

from __future__ import annotations
from typing import Dict, Optional, Any, Union
from uuid import UUID
from enum import Enum
try:
    import msgpack
except ImportError:
    msgpack = None  # Will be installed during dependency setup

# Import from existing UCP model
from rec.model import Capabilities


class ClockRelation(Enum):
    """
    Represents the causal relationship between two vector clocks.
    
    Values:
        BEFORE: This clock happened before the other (this < other)
        AFTER: This clock happened after the other (this > other)  
        CONCURRENT: Clocks are concurrent (neither < nor >)
        EQUAL: Clocks are identical (this == other)
    """
    BEFORE = "before"
    AFTER = "after"
    CONCURRENT = "concurrent"
    EQUAL = "equal"


class VectorClock:
    """
    Basic vector clock implementation for distributed systems.
    
    A vector clock maintains a logical timestamp for each node in a distributed
    system, enabling determination of causal relationships between events.
    
    Time Complexity:
        - increment(): O(1)
        - update(): O(n) where n is number of nodes
        - compare(): O(n) where n is number of nodes
        - serialize(): O(n) where n is number of nodes
    
    Space Complexity: O(n) where n is number of nodes in the system
    
    Attributes:
        node_id: Unique identifier for this node
        clock: Dictionary mapping node IDs to their logical timestamps
        
    Example:
        >>> clock = VectorClock(UUID("12345678-1234-5678-9012-123456789abc"))
        >>> clock.increment()
        >>> other_clock = VectorClock(UUID("87654321-4321-8765-2109-987654321cba"))
        >>> relation = clock.compare(other_clock)
        >>> print(relation)  # ClockRelation.CONCURRENT
    """
    
    def __init__(self, node_id: UUID) -> None:
        """
        Initialize a vector clock for the given node.
        
        Args:
            node_id: Unique identifier for this node in the distributed system
            
        Raises:
            TypeError: If node_id is not a UUID
        """
        if not isinstance(node_id, UUID):
            raise TypeError("node_id must be a UUID")
            
        self.node_id: UUID = node_id
        self.clock: Dict[UUID, int] = {node_id: 0}
    
    def increment(self) -> None:
        """
        Increment this node's logical timestamp.
        
        This should be called before sending a message or performing a local event.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        self.clock[self.node_id] += 1
    
    def update(self, other_clock: Dict[UUID, int]) -> None:
        """
        Update this vector clock with timestamps from another clock.
        
        This implements the vector clock update rule: for each node,
        take the maximum of the local timestamp and the received timestamp,
        then increment the local node's timestamp.
        
        Args:
            other_clock: Dictionary mapping node IDs to timestamps
            
        Time Complexity: O(n) where n is number of nodes in other_clock
        Space Complexity: O(k) where k is number of new nodes
        """
        # Update with maximum of current and received timestamps
        for node_id, timestamp in other_clock.items():
            current_time = self.clock.get(node_id, 0)
            self.clock[node_id] = max(current_time, timestamp)
        
        # Increment local node's timestamp
        self.increment()
    
    def compare(self, other: VectorClock) -> ClockRelation:
        """
        Compare this vector clock with another to determine causal relationship.
        
        Args:
            other: Another VectorClock to compare with
            
        Returns:
            ClockRelation indicating the causal relationship
            
        Time Complexity: O(n) where n is total number of unique nodes
        Space Complexity: O(1)
        
        Algorithm:
            - EQUAL: All timestamps are identical
            - BEFORE: All our timestamps ≤ other's, with at least one <
            - AFTER: All our timestamps ≥ other's, with at least one >
            - CONCURRENT: Neither BEFORE nor AFTER relationship holds
        """
        if not isinstance(other, VectorClock):
            raise TypeError("Can only compare with another VectorClock")
        
        all_nodes = set(self.clock.keys()) | set(other.clock.keys())
        
        our_less = False
        our_greater = False
        
        for node_id in all_nodes:
            our_time = self.clock.get(node_id, 0)
            other_time = other.clock.get(node_id, 0)
            
            if our_time < other_time:
                our_less = True
            elif our_time > other_time:
                our_greater = True
        
        if not our_less and not our_greater:
            return ClockRelation.EQUAL
        elif our_less and not our_greater:
            return ClockRelation.BEFORE
        elif our_greater and not our_less:
            return ClockRelation.AFTER
        else:
            return ClockRelation.CONCURRENT
    
    def copy(self) -> VectorClock:
        """
        Create a deep copy of this vector clock.
        
        Returns:
            New VectorClock instance with same state
            
        Time Complexity: O(n) where n is number of nodes
        Space Complexity: O(n) where n is number of nodes
        """
        new_clock = VectorClock(self.node_id)
        new_clock.clock = self.clock.copy()
        return new_clock
    
    def get_time(self, node_id: Optional[UUID] = None) -> int:
        """
        Get the logical timestamp for a specific node.
        
        Args:
            node_id: Node to get timestamp for. If None, returns local node's time.
            
        Returns:
            Logical timestamp for the specified node
            
        Time Complexity: O(1)
        """
        if node_id is None:
            node_id = self.node_id
        return self.clock.get(node_id, 0)
    
    def serialize(self) -> bytes:
        """
        Serialize the vector clock to bytes using msgpack.
        
        Returns:
            Serialized vector clock as bytes
            
        Time Complexity: O(n) where n is number of nodes
        Space Complexity: O(n) where n is number of nodes
        """
        data = {
            'node_id': str(self.node_id),
            'clock': {str(node_id): timestamp for node_id, timestamp in self.clock.items()}
        }
        return msgpack.packb(data)
    
    @classmethod
    def deserialize(cls, data: bytes) -> VectorClock:
        """
        Deserialize a vector clock from bytes.
        
        Args:
            data: Serialized vector clock data
            
        Returns:
            VectorClock instance
            
        Raises:
            ValueError: If data is invalid or corrupted
            
        Time Complexity: O(n) where n is number of nodes
        Space Complexity: O(n) where n is number of nodes
        """
        try:
            unpacked = msgpack.unpackb(data, strict_map_key=False)
            node_id = UUID(unpacked['node_id'])
            clock_data = {UUID(node_id): timestamp 
                         for node_id, timestamp in unpacked['clock'].items()}
            
            vector_clock = cls(node_id)
            vector_clock.clock = clock_data
            return vector_clock
            
        except (msgpack.exceptions.ExtraData, 
                msgpack.exceptions.InvalidDocument,
                KeyError, 
                ValueError) as e:
            raise ValueError(f"Invalid vector clock data: {e}")
    
    def __str__(self) -> str:
        """String representation of the vector clock."""
        clock_str = ', '.join(f"{node_id}: {time}" for node_id, time in self.clock.items())
        return f"VectorClock({clock_str})"
    
    def __repr__(self) -> str:
        """Developer representation of the vector clock."""
        return f"VectorClock(node_id={self.node_id}, clock={self.clock})"


class CapabilityAwareVectorClock(VectorClock):
    """
    Vector clock implementation with capability-aware conflict resolution.
    
    Extends basic vector clocks with node capability information to enable
    intelligent conflict resolution in resource-constrained environments
    and emergency scenarios.
    
    This implementation assigns capability scores to nodes based on their
    computational resources, battery level, network connectivity, and
    emergency priority, enabling better decision-making during concurrent
    updates and network partitions.
    
    Attributes:
        capabilities: Node's computational and resource capabilities
        capability_weight: Computed weight based on current capabilities
        
    Example:
        >>> from rec.model import Capabilities
        >>> caps = Capabilities(cpu=80, memory=70, battery=90, network=85)
        >>> clock = CapabilityAwareVectorClock(node_id, caps)
        >>> weight = clock.get_capability_weight()
        >>> print(f"Node capability weight: {weight}")
    """
    
    def __init__(self, node_id: UUID, capabilities: Capabilities) -> None:
        """
        Initialize a capability-aware vector clock.
        
        Args:
            node_id: Unique identifier for this node
            capabilities: Node's computational and resource capabilities
            
        Raises:
            TypeError: If capabilities is not a Capabilities instance
        """
        super().__init__(node_id)
        
        if not isinstance(capabilities, Capabilities):
            raise TypeError("capabilities must be a Capabilities instance")
            
        self.capabilities: Capabilities = capabilities
        self.capability_weight: float = self._calculate_capability_weight()
    
    def _calculate_capability_weight(self) -> float:
        """
        Calculate capability weight based on node's current capabilities.
        
        The weight combines multiple factors:
        - CPU performance (25%)
        - Memory availability (20%)
        - Battery level (30%)
        - Network quality (20%)
        - Emergency priority boost (5%)
        
        Returns:
            Capability weight between 0.0 and 1.0
            
        Time Complexity: O(1)
        """
        # Normalize capability values to 0-1 range
        cpu_score = getattr(self.capabilities, 'cpu', 0) / 100.0
        memory_score = getattr(self.capabilities, 'memory', 0) / 100.0
        battery_score = getattr(self.capabilities, 'battery', 0) / 100.0
        network_score = getattr(self.capabilities, 'network', 0) / 100.0
        
        # Emergency priority boost (placeholder for future implementation)
        emergency_boost = 0.0
        
        # Weighted combination
        weight = (
            cpu_score * 0.25 +
            memory_score * 0.20 +
            battery_score * 0.30 +
            network_score * 0.20 +
            emergency_boost * 0.05
        )
        
        return max(0.0, min(1.0, weight))  # Clamp to [0, 1]
    
    def update_capabilities(self, new_capabilities: Capabilities) -> None:
        """
        Update node capabilities and recalculate weight.
        
        Args:
            new_capabilities: Updated capability information
            
        Time Complexity: O(1)
        """
        self.capabilities = new_capabilities
        self.capability_weight = self._calculate_capability_weight()
    
    def get_capability_weight(self) -> float:
        """
        Get the current capability weight for this node.
        
        Returns:
            Capability weight between 0.0 and 1.0
            
        Time Complexity: O(1)
        """
        return self.capability_weight
    
    def compare_with_capability(self, other: CapabilityAwareVectorClock) -> ClockRelation:
        """
        Compare clocks with capability-aware conflict resolution.
        
        When clocks are concurrent, use capability weights to determine
        precedence for conflict resolution.
        
        Args:
            other: Another CapabilityAwareVectorClock to compare with
            
        Returns:
            ClockRelation, with capability-based resolution for concurrent clocks
            
        Time Complexity: O(n) where n is number of nodes
        """
        basic_relation = self.compare(other)
        
        # If not concurrent, return basic relation
        if basic_relation != ClockRelation.CONCURRENT:
            return basic_relation
        
        # For concurrent clocks, use capability weights
        if self.capability_weight > other.capability_weight:
            return ClockRelation.AFTER  # We have precedence
        elif self.capability_weight < other.capability_weight:
            return ClockRelation.BEFORE  # Other has precedence
        else:
            # Same capability weight, use node ID as tiebreaker
            if self.node_id > other.node_id:
                return ClockRelation.AFTER
            else:
                return ClockRelation.BEFORE
    
    def serialize(self) -> bytes:
        """
        Serialize capability-aware vector clock to bytes.
        
        Returns:
            Serialized clock with capability information
            
        Time Complexity: O(n) where n is number of nodes
        """
        data = {
            'node_id': str(self.node_id),
            'clock': {str(node_id): timestamp for node_id, timestamp in self.clock.items()},
            'capabilities': {
                'cpu': getattr(self.capabilities, 'cpu', 0),
                'memory': getattr(self.capabilities, 'memory', 0), 
                'battery': getattr(self.capabilities, 'battery', 0),
                'network': getattr(self.capabilities, 'network', 0),
            },
            'capability_weight': self.capability_weight
        }
        return msgpack.packb(data)
    
    @classmethod
    def deserialize(cls, data: bytes) -> CapabilityAwareVectorClock:
        """
        Deserialize capability-aware vector clock from bytes.
        
        Args:
            data: Serialized clock data
            
        Returns:
            CapabilityAwareVectorClock instance
            
        Raises:
            ValueError: If data is invalid or corrupted
        """
        try:
            unpacked = msgpack.unpackb(data, strict_map_key=False)
            node_id = UUID(unpacked['node_id'])
            
            # Reconstruct capabilities (simplified for stub)
            cap_data = unpacked['capabilities']
            # TODO: Create proper Capabilities object when available
            capabilities = type('Capabilities', (), cap_data)()
            
            clock_data = {UUID(node_id): timestamp 
                         for node_id, timestamp in unpacked['clock'].items()}
            
            vector_clock = cls(node_id, capabilities)
            vector_clock.clock = clock_data
            vector_clock.capability_weight = unpacked['capability_weight']
            
            return vector_clock
            
        except (msgpack.exceptions.ExtraData,
                msgpack.exceptions.InvalidDocument, 
                KeyError, 
                ValueError) as e:
            raise ValueError(f"Invalid capability-aware vector clock data: {e}")
    
    def __str__(self) -> str:
        """String representation with capability weight."""
        clock_str = ', '.join(f"{node_id}: {time}" for node_id, time in self.clock.items())
        return f"CapabilityAwareVectorClock({clock_str}, weight={self.capability_weight:.3f})"
    
    def __repr__(self) -> str:
        """Developer representation with full details."""
        return (f"CapabilityAwareVectorClock(node_id={self.node_id}, "
                f"clock={self.clock}, capability_weight={self.capability_weight})")
