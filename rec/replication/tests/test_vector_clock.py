"""
Unit tests for VectorClock and CapabilityAwareVectorClock.

Comprehensive test suite covering:
- Basic vector clock operations
- Causal relationship detection
- Capability-aware extensions
- Serialization/deserialization
- Edge cases and error conditions
- Property-based testing

Author: Sina Fadavi
Date: August 2025
"""

import pytest
from uuid import UUID, uuid4
from unittest.mock import Mock, patch
from typing import Dict, Any

# Import classes under test
from rec.replication.core.vector_clock import (
    VectorClock, 
    CapabilityAwareVectorClock, 
    ClockRelation
)

# Test fixtures will be imported once available
# from rec.model import Capabilities


class TestVectorClock:
    """Test suite for basic VectorClock functionality."""
    
    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.node_id_1 = uuid4()
        self.node_id_2 = uuid4()
        self.node_id_3 = uuid4()
        
        self.clock_1 = VectorClock(self.node_id_1)
        self.clock_2 = VectorClock(self.node_id_2)
        self.clock_3 = VectorClock(self.node_id_3)
    
    def test_vector_clock_initialization(self):
        """Test vector clock initialization with valid node ID."""
        clock = VectorClock(self.node_id_1)
        
        assert clock.node_id == self.node_id_1
        assert clock.clock == {self.node_id_1: 0}
        assert clock.get_time() == 0
    
    def test_vector_clock_initialization_invalid_id(self):
        """Test vector clock initialization with invalid node ID."""
        with pytest.raises(TypeError, match="node_id must be a UUID"):
            VectorClock("not-a-uuid")
    
    def test_increment_operation(self):
        """Test vector clock increment operation."""
        initial_time = self.clock_1.get_time()
        
        self.clock_1.increment()
        
        assert self.clock_1.get_time() == initial_time + 1
        assert self.clock_1.clock[self.node_id_1] == 1
    
    def test_multiple_increments(self):
        """Test multiple increment operations."""
        for i in range(5):
            self.clock_1.increment()
        
        assert self.clock_1.get_time() == 5
    
    def test_update_operation(self):
        """Test vector clock update with another clock."""
        # Set up scenario: clock_2 has higher timestamp
        self.clock_2.increment()
        self.clock_2.increment()
        
        initial_time_1 = self.clock_1.get_time()
        
        # Update clock_1 with clock_2's state
        self.clock_1.update(self.clock_2.clock)
        
        # clock_1 should now have clock_2's timestamp and incremented its own
        assert self.clock_1.get_time() == initial_time_1 + 1
        assert self.clock_1.get_time(self.node_id_2) == 2
    
    def test_compare_equal_clocks(self):
        """Test comparison of identical clocks."""
        clock_copy = VectorClock(self.node_id_1)
        
        relation = self.clock_1.compare(clock_copy)
        assert relation == ClockRelation.EQUAL
    
    def test_compare_before_relationship(self):
        """Test detection of before relationship."""
        # clock_1 happens before clock_2
        self.clock_1.increment()
        self.clock_2.update(self.clock_1.clock)
        
        relation = self.clock_1.compare(self.clock_2)
        assert relation == ClockRelation.BEFORE
    
    def test_compare_after_relationship(self):
        """Test detection of after relationship."""
        # clock_2 happens before clock_1
        self.clock_2.increment()
        self.clock_1.update(self.clock_2.clock)
        
        relation = self.clock_2.compare(self.clock_1)
        assert relation == ClockRelation.AFTER
    
    def test_compare_concurrent_clocks(self):
        """Test detection of concurrent relationship."""
        # Create concurrent events
        self.clock_1.increment()  # [1, 0]
        self.clock_2.increment()  # [0, 1]
        
        relation = self.clock_1.compare(self.clock_2)
        assert relation == ClockRelation.CONCURRENT
    
    def test_compare_invalid_type(self):
        """Test comparison with invalid type."""
        with pytest.raises(TypeError, match="Can only compare with another VectorClock"):
            self.clock_1.compare("not-a-clock")
    
    def test_get_time_specific_node(self):
        """Test getting timestamp for specific node."""
        self.clock_1.increment()
        self.clock_1.increment()
        
        # Get time for local node
        assert self.clock_1.get_time(self.node_id_1) == 2
        
        # Get time for unknown node (should return 0)
        assert self.clock_1.get_time(self.node_id_2) == 0
    
    def test_copy_operation(self):
        """Test vector clock copy operation."""
        self.clock_1.increment()
        self.clock_1.clock[self.node_id_2] = 5
        
        clock_copy = self.clock_1.copy()
        
        # Copy should be equal but independent
        assert clock_copy.compare(self.clock_1) == ClockRelation.EQUAL
        assert clock_copy is not self.clock_1
        assert clock_copy.clock is not self.clock_1.clock
        
        # Modifying copy shouldn't affect original
        clock_copy.increment()
        assert self.clock_1.compare(clock_copy) == ClockRelation.BEFORE
    
    @pytest.mark.skip(reason="Requires msgpack dependency")
    def test_serialization_roundtrip(self):
        """Test serialization and deserialization."""
        self.clock_1.increment()
        self.clock_1.clock[self.node_id_2] = 3
        
        # Serialize
        serialized = self.clock_1.serialize()
        assert isinstance(serialized, bytes)
        
        # Deserialize
        deserialized = VectorClock.deserialize(serialized)
        
        # Should be equal to original
        assert deserialized.compare(self.clock_1) == ClockRelation.EQUAL
        assert deserialized.node_id == self.clock_1.node_id
    
    def test_string_representation(self):
        """Test string representation of vector clock."""
        self.clock_1.increment()
        
        str_repr = str(self.clock_1)
        assert "VectorClock" in str_repr
        assert str(self.node_id_1) in str_repr
        assert "1" in str_repr
    
    def test_repr_representation(self):
        """Test developer representation of vector clock."""
        repr_str = repr(self.clock_1)
        assert "VectorClock" in repr_str
        assert "node_id" in repr_str
        assert "clock" in repr_str


class TestCapabilityAwareVectorClock:
    """Test suite for CapabilityAwareVectorClock functionality."""
    
    def setup_method(self):
        """Set up test fixtures with mock capabilities."""
        self.node_id_1 = uuid4()
        self.node_id_2 = uuid4()
        
        # Create mock capabilities
        self.capabilities_1 = Mock()
        self.capabilities_1.cpu = 80
        self.capabilities_1.memory = 70
        self.capabilities_1.battery = 90
        self.capabilities_1.network = 85
        
        self.capabilities_2 = Mock()
        self.capabilities_2.cpu = 60
        self.capabilities_2.memory = 50
        self.capabilities_2.battery = 40
        self.capabilities_2.network = 70
        
        self.clock_1 = CapabilityAwareVectorClock(self.node_id_1, self.capabilities_1)
        self.clock_2 = CapabilityAwareVectorClock(self.node_id_2, self.capabilities_2)
    
    def test_capability_aware_initialization(self):
        """Test initialization with capabilities."""
        assert self.clock_1.node_id == self.node_id_1
        assert self.clock_1.capabilities == self.capabilities_1
        assert 0.0 <= self.clock_1.capability_weight <= 1.0
    
    def test_capability_aware_initialization_invalid_capabilities(self):
        """Test initialization with invalid capabilities."""
        with pytest.raises(TypeError, match="capabilities must be a Capabilities instance"):
            CapabilityAwareVectorClock(self.node_id_1, "not-capabilities")
    
    def test_capability_weight_calculation(self):
        """Test capability weight calculation."""
        # High-capability node should have higher weight
        weight_1 = self.clock_1.get_capability_weight()
        weight_2 = self.clock_2.get_capability_weight()
        
        assert weight_1 > weight_2
        assert 0.0 <= weight_1 <= 1.0
        assert 0.0 <= weight_2 <= 1.0
    
    def test_update_capabilities(self):
        """Test updating capabilities and recalculating weight."""
        old_weight = self.clock_1.get_capability_weight()
        
        # Create new capabilities with different values
        new_capabilities = Mock()
        new_capabilities.cpu = 40
        new_capabilities.memory = 30
        new_capabilities.battery = 20
        new_capabilities.network = 25
        
        self.clock_1.update_capabilities(new_capabilities)
        new_weight = self.clock_1.get_capability_weight()
        
        assert new_weight != old_weight
        assert new_weight < old_weight  # Should be lower due to reduced capabilities
        assert self.clock_1.capabilities == new_capabilities
    
    def test_compare_with_capability_before_relationship(self):
        """Test capability-aware comparison with before relationship."""
        # Create normal before relationship
        self.clock_1.increment()
        self.clock_2.update(self.clock_1.clock)
        
        # Should return BEFORE regardless of capabilities
        relation = self.clock_1.compare_with_capability(self.clock_2)
        assert relation == ClockRelation.BEFORE
    
    def test_compare_with_capability_concurrent_relationship(self):
        """Test capability-aware comparison with concurrent clocks."""
        # Create concurrent clocks
        self.clock_1.increment()  # [1, 0]
        self.clock_2.increment()  # [0, 1]
        
        # Higher capability node should have precedence
        relation = self.clock_1.compare_with_capability(self.clock_2)
        
        # clock_1 has higher capabilities, so should be AFTER
        assert relation == ClockRelation.AFTER
        
        # Reverse comparison
        relation_reverse = self.clock_2.compare_with_capability(self.clock_1)
        assert relation_reverse == ClockRelation.BEFORE
    
    def test_compare_with_capability_equal_weights(self):
        """Test capability-aware comparison with equal capability weights."""
        # Make capabilities equal
        self.clock_2.capabilities = self.clock_1.capabilities
        self.clock_2.capability_weight = self.clock_1.capability_weight
        
        # Create concurrent clocks
        self.clock_1.increment()
        self.clock_2.increment()
        
        # Should use node ID as tiebreaker
        relation = self.clock_1.compare_with_capability(self.clock_2)
        
        # Result should be deterministic based on node IDs
        if self.node_id_1 > self.node_id_2:
            assert relation == ClockRelation.AFTER
        else:
            assert relation == ClockRelation.BEFORE
    
    @pytest.mark.skip(reason="Requires msgpack dependency")
    def test_capability_aware_serialization(self):
        """Test serialization of capability-aware vector clock."""
        self.clock_1.increment()
        
        # Serialize
        serialized = self.clock_1.serialize()
        assert isinstance(serialized, bytes)
        
        # Deserialize
        deserialized = CapabilityAwareVectorClock.deserialize(serialized)
        
        # Should preserve all information
        assert deserialized.node_id == self.clock_1.node_id
        assert deserialized.capability_weight == self.clock_1.capability_weight
        assert deserialized.compare(self.clock_1) == ClockRelation.EQUAL
    
    def test_capability_aware_string_representation(self):
        """Test string representation includes capability weight."""
        str_repr = str(self.clock_1)
        
        assert "CapabilityAwareVectorClock" in str_repr
        assert "weight=" in str_repr
        assert str(self.clock_1.capability_weight)[:5] in str_repr


class TestVectorClockProperties:
    """Property-based tests for vector clock invariants."""
    
    @pytest.mark.skip(reason="Requires hypothesis dependency")
    def test_clock_ordering_properties(self):
        """Test mathematical properties of vector clock ordering."""
        # This would use hypothesis for property-based testing
        # Example property: if A happens-before B and B happens-before C,
        # then A happens-before C (transitivity)
        pass
    
    @pytest.mark.skip(reason="Requires hypothesis dependency") 
    def test_causality_preservation(self):
        """Test that causal relationships are preserved."""
        # Property: if event A causally precedes event B,
        # then timestamp(A) < timestamp(B) in vector clock ordering
        pass


class TestVectorClockIntegration:
    """Integration tests for vector clock interactions."""
    
    def test_multi_node_scenario(self):
        """Test vector clocks in multi-node scenario."""
        # Create three nodes
        nodes = [uuid4() for _ in range(3)]
        clocks = [VectorClock(node_id) for node_id in nodes]
        
        # Simulate distributed algorithm
        # Node 0 sends message to Node 1
        clocks[0].increment()
        clocks[1].update(clocks[0].clock)
        
        # Node 1 sends message to Node 2
        clocks[1].increment()
        clocks[2].update(clocks[1].clock)
        
        # Verify causal ordering
        assert clocks[0].compare(clocks[1]) == ClockRelation.BEFORE
        assert clocks[1].compare(clocks[2]) == ClockRelation.BEFORE
        assert clocks[0].compare(clocks[2]) == ClockRelation.BEFORE
    
    def test_network_partition_scenario(self):
        """Test vector clock behavior during network partition."""
        # Create partition: nodes 0,1 vs node 2
        nodes = [uuid4() for _ in range(3)]
        clocks = [VectorClock(node_id) for node_id in nodes]
        
        # Partition 1: nodes 0 and 1 communicate
        clocks[0].increment()
        clocks[1].update(clocks[0].clock)
        clocks[1].increment()
        clocks[0].update(clocks[1].clock)
        
        # Partition 2: node 2 operates independently
        clocks[2].increment()
        clocks[2].increment()
        
        # Events in different partitions should be concurrent
        assert clocks[0].compare(clocks[2]) == ClockRelation.CONCURRENT
        assert clocks[1].compare(clocks[2]) == ClockRelation.CONCURRENT


# Performance benchmarks
class TestVectorClockPerformance:
    """Performance tests for vector clock operations."""
    
    @pytest.mark.performance
    def test_increment_performance(self):
        """Benchmark increment operation performance."""
        import time
        
        clock = VectorClock(uuid4())
        iterations = 10000
        
        start_time = time.time()
        for _ in range(iterations):
            clock.increment()
        end_time = time.time()
        
        duration = end_time - start_time
        ops_per_second = iterations / duration
        
        # Should be very fast (> 100k ops/second)
        assert ops_per_second > 100000, f"Increment too slow: {ops_per_second} ops/sec"
    
    @pytest.mark.performance
    def test_compare_performance(self):
        """Benchmark compare operation performance."""
        import time
        
        clock1 = VectorClock(uuid4())
        clock2 = VectorClock(uuid4())
        
        # Add some complexity
        for _ in range(10):
            clock1.increment()
            clock2.increment()
            clock1.update(clock2.clock)
        
        iterations = 1000
        start_time = time.time()
        for _ in range(iterations):
            clock1.compare(clock2)
        end_time = time.time()
        
        duration = end_time - start_time
        ops_per_second = iterations / duration
        
        # Should be reasonably fast (> 10k ops/second)
        assert ops_per_second > 10000, f"Compare too slow: {ops_per_second} ops/sec"
