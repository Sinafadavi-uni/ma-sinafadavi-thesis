"""
Capability Scorer for Emergency-Aware Vector Clocks.

This module implements capability scoring algorithms for nodes in
distributed systems, with special consideration for emergency scenarios
and energy-constrained environments.

Classes:
    CapabilityScorer: Main capability scoring implementation
    ScoringStrategy: Interface for different scoring strategies
    EmergencyScorer: Emergency-aware capability scoring
    EnergyAwareScorer: Energy-efficient capability scoring

Author: Sina Fadavi
Date: August 2025
"""

from __future__ import annotations
from typing import Protocol, Dict, Any, Optional
from abc import ABC, abstractmethod
from enum import Enum
from uuid import UUID
import time

# Import from existing UCP model
from rec.model import Capabilities


class ScoringStrategy(Enum):
    """
    Available capability scoring strategies.
    
    Values:
        BALANCED: Equal weight to all capability factors
        ENERGY_AWARE: Prioritizes battery and energy efficiency
        PERFORMANCE: Prioritizes CPU and memory performance
        EMERGENCY: Optimized for emergency scenario requirements
        NETWORK_FIRST: Prioritizes network connectivity and reliability
    """
    BALANCED = "balanced"
    ENERGY_AWARE = "energy_aware"
    PERFORMANCE = "performance"
    EMERGENCY = "emergency"
    NETWORK_FIRST = "network_first"


class ScoringProtocol(Protocol):
    """Protocol defining the interface for capability scoring."""
    
    def calculate_score(self, capabilities: Capabilities, context: Dict[str, Any]) -> float:
        """Calculate capability score for given capabilities and context."""
        ...


class CapabilityScorer:
    """
    Main capability scoring implementation for distributed systems.
    
    Calculates capability scores for nodes based on their computational
    resources, energy state, network connectivity, and emergency context.
    Supports multiple scoring strategies optimized for different scenarios.
    
    The scorer considers:
    - Computational capabilities (CPU, memory)
    - Energy state (battery level, power consumption)
    - Network quality (connectivity, bandwidth, latency)
    - Emergency context (criticality, location relevance)
    - Historical performance data
    
    Attributes:
        strategy: Current scoring strategy
        emergency_context: Current emergency scenario context
        historical_data: Performance history for adaptive scoring
        
    Example:
        >>> scorer = CapabilityScorer(ScoringStrategy.EMERGENCY)
        >>> score = scorer.calculate_score(node_capabilities, emergency_context)
        >>> print(f"Node capability score: {score:.3f}")
    """
    
    def __init__(self, strategy: ScoringStrategy = ScoringStrategy.BALANCED) -> None:
        """
        Initialize capability scorer with specified strategy.
        
        Args:
            strategy: Scoring strategy to use for calculations
        """
        self.strategy: ScoringStrategy = strategy
        self.emergency_context: Dict[str, Any] = {}
        self.historical_data: Dict[UUID, Dict[str, float]] = {}
        self.weights: Dict[str, float] = self._get_strategy_weights(strategy)
    
    def _get_strategy_weights(self, strategy: ScoringStrategy) -> Dict[str, float]:
        """
        Get scoring weights for the specified strategy.
        
        Args:
            strategy: Scoring strategy to get weights for
            
        Returns:
            Dictionary of capability factor weights
            
        Time Complexity: O(1)
        """
        weight_configs = {
            ScoringStrategy.BALANCED: {
                'cpu': 0.25,
                'memory': 0.25,
                'battery': 0.25,
                'network': 0.20,
                'emergency_boost': 0.05
            },
            ScoringStrategy.ENERGY_AWARE: {
                'cpu': 0.15,
                'memory': 0.15,
                'battery': 0.45,
                'network': 0.20,
                'emergency_boost': 0.05
            },
            ScoringStrategy.PERFORMANCE: {
                'cpu': 0.40,
                'memory': 0.35,
                'battery': 0.10,
                'network': 0.10,
                'emergency_boost': 0.05
            },
            ScoringStrategy.EMERGENCY: {
                'cpu': 0.20,
                'memory': 0.20,
                'battery': 0.30,
                'network': 0.15,
                'emergency_boost': 0.15
            },
            ScoringStrategy.NETWORK_FIRST: {
                'cpu': 0.15,
                'memory': 0.15,
                'battery': 0.25,
                'network': 0.40,
                'emergency_boost': 0.05
            }
        }
        
        return weight_configs.get(strategy, weight_configs[ScoringStrategy.BALANCED])
    
    def calculate_score(
        self, 
        capabilities: Capabilities, 
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate capability score for given capabilities and context.
        
        Args:
            capabilities: Node's current capabilities
            context: Optional context information (emergency state, location, etc.)
            
        Returns:
            Capability score between 0.0 and 1.0
            
        Time Complexity: O(1)
        Space Complexity: O(1)
        
        Algorithm:
            1. Normalize capability values to [0, 1] range
            2. Apply strategy-specific weights
            3. Add emergency boost if applicable
            4. Apply historical performance modifier
            5. Clamp result to [0, 1] range
        """
        if context is None:
            context = {}
        
        # Normalize capability values
        cpu_score = self._normalize_capability(getattr(capabilities, 'cpu', 0), 'cpu')
        memory_score = self._normalize_capability(getattr(capabilities, 'memory', 0), 'memory')
        battery_score = self._normalize_capability(getattr(capabilities, 'battery', 0), 'battery')
        network_score = self._normalize_capability(getattr(capabilities, 'network', 0), 'network')
        
        # Calculate base score using strategy weights
        base_score = (
            cpu_score * self.weights['cpu'] +
            memory_score * self.weights['memory'] +
            battery_score * self.weights['battery'] +
            network_score * self.weights['network']
        )
        
        # Apply emergency boost
        emergency_boost = self._calculate_emergency_boost(capabilities, context)
        final_score = base_score + (emergency_boost * self.weights['emergency_boost'])
        
        # Apply historical performance modifier
        historical_modifier = self._get_historical_modifier(capabilities, context)
        final_score *= historical_modifier
        
        # Clamp to valid range
        return max(0.0, min(1.0, final_score))
    
    def _normalize_capability(self, value: float, capability_type: str) -> float:
        """
        Normalize capability value to [0, 1] range.
        
        Args:
            value: Raw capability value
            capability_type: Type of capability being normalized
            
        Returns:
            Normalized value between 0.0 and 1.0
        """
        # Standard normalization for percentage-based capabilities
        if capability_type in ['cpu', 'memory', 'battery', 'network']:
            return max(0.0, min(1.0, value / 100.0))
        
        # Default normalization
        return max(0.0, min(1.0, value))
    
    def _calculate_emergency_boost(
        self, 
        capabilities: Capabilities, 
        context: Dict[str, Any]
    ) -> float:
        """
        Calculate emergency priority boost for capability scoring.
        
        Args:
            capabilities: Node's capabilities
            context: Emergency context information
            
        Returns:
            Emergency boost value between 0.0 and 1.0
        """
        # Emergency boost factors
        emergency_level = context.get('emergency_level', 0)  # 0-5 scale
        location_relevance = context.get('location_relevance', 0.0)  # 0-1 scale
        criticality = context.get('criticality', 0.0)  # 0-1 scale
        
        # Calculate boost based on emergency factors
        boost = 0.0
        
        if emergency_level > 0:
            # Higher emergency level = higher boost
            boost += (emergency_level / 5.0) * 0.4
        
        if location_relevance > 0:
            # Closer to emergency = higher boost
            boost += location_relevance * 0.3
        
        if criticality > 0:
            # More critical role = higher boost
            boost += criticality * 0.3
        
        return max(0.0, min(1.0, boost))
    
    def _get_historical_modifier(
        self, 
        capabilities: Capabilities, 
        context: Dict[str, Any]
    ) -> float:
        """
        Get historical performance modifier for capability scoring.
        
        Args:
            capabilities: Node's capabilities
            context: Context information including node ID
            
        Returns:
            Historical modifier between 0.5 and 1.5
        """
        node_id = context.get('node_id')
        if not node_id or node_id not in self.historical_data:
            return 1.0  # No historical data, use neutral modifier
        
        history = self.historical_data[node_id]
        
        # Calculate reliability based on historical performance
        reliability = history.get('reliability', 1.0)  # 0-1 scale
        availability = history.get('availability', 1.0)  # 0-1 scale
        performance = history.get('performance', 1.0)  # 0-1 scale
        
        # Combine historical factors
        historical_score = (reliability * 0.4 + availability * 0.3 + performance * 0.3)
        
        # Convert to modifier (0.5 to 1.5 range)
        modifier = 0.5 + (historical_score * 1.0)
        
        return max(0.5, min(1.5, modifier))
    
    def update_strategy(self, new_strategy: ScoringStrategy) -> None:
        """
        Update the scoring strategy and recalculate weights.
        
        Args:
            new_strategy: New scoring strategy to use
        """
        self.strategy = new_strategy
        self.weights = self._get_strategy_weights(new_strategy)
    
    def set_emergency_context(self, context: Dict[str, Any]) -> None:
        """
        Set emergency context for capability scoring.
        
        Args:
            context: Emergency context information
        """
        self.emergency_context.update(context)
    
    def update_historical_data(
        self, 
        node_id: UUID, 
        performance_metrics: Dict[str, float]
    ) -> None:
        """
        Update historical performance data for a node.
        
        Args:
            node_id: ID of the node to update
            performance_metrics: Dictionary of performance metrics
        """
        if node_id not in self.historical_data:
            self.historical_data[node_id] = {}
        
        self.historical_data[node_id].update(performance_metrics)
        
        # Add timestamp for decay calculations
        self.historical_data[node_id]['last_update'] = time.time()
    
    def get_score_breakdown(
        self, 
        capabilities: Capabilities, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Get detailed breakdown of capability score calculation.
        
        Args:
            capabilities: Node's capabilities
            context: Optional context information
            
        Returns:
            Dictionary with detailed score breakdown
        """
        if context is None:
            context = {}
        
        # Calculate individual components
        cpu_score = self._normalize_capability(getattr(capabilities, 'cpu', 0), 'cpu')
        memory_score = self._normalize_capability(getattr(capabilities, 'memory', 0), 'memory')
        battery_score = self._normalize_capability(getattr(capabilities, 'battery', 0), 'battery')
        network_score = self._normalize_capability(getattr(capabilities, 'network', 0), 'network')
        
        emergency_boost = self._calculate_emergency_boost(capabilities, context)
        historical_modifier = self._get_historical_modifier(capabilities, context)
        
        # Calculate weighted components
        weighted_cpu = cpu_score * self.weights['cpu']
        weighted_memory = memory_score * self.weights['memory']
        weighted_battery = battery_score * self.weights['battery']
        weighted_network = network_score * self.weights['network']
        weighted_emergency = emergency_boost * self.weights['emergency_boost']
        
        base_score = weighted_cpu + weighted_memory + weighted_battery + weighted_network
        final_score = (base_score + weighted_emergency) * historical_modifier
        
        return {
            'cpu_raw': getattr(capabilities, 'cpu', 0),
            'memory_raw': getattr(capabilities, 'memory', 0),
            'battery_raw': getattr(capabilities, 'battery', 0),
            'network_raw': getattr(capabilities, 'network', 0),
            'cpu_normalized': cpu_score,
            'memory_normalized': memory_score,
            'battery_normalized': battery_score,
            'network_normalized': network_score,
            'weighted_cpu': weighted_cpu,
            'weighted_memory': weighted_memory,
            'weighted_battery': weighted_battery,
            'weighted_network': weighted_network,
            'emergency_boost': emergency_boost,
            'weighted_emergency': weighted_emergency,
            'historical_modifier': historical_modifier,
            'base_score': base_score,
            'final_score': max(0.0, min(1.0, final_score)),
            'strategy': self.strategy.value
        }
    
    def compare_nodes(
        self, 
        capabilities_a: Capabilities, 
        capabilities_b: Capabilities,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Compare capability scores between two nodes.
        
        Args:
            capabilities_a: First node's capabilities
            capabilities_b: Second node's capabilities
            context: Optional context information
            
        Returns:
            Comparison results with scores and winner
        """
        score_a = self.calculate_score(capabilities_a, context)
        score_b = self.calculate_score(capabilities_b, context)
        
        return {
            'node_a_score': score_a,
            'node_b_score': score_b,
            'difference': abs(score_a - score_b),
            'winner': 'a' if score_a > score_b else 'b' if score_b > score_a else 'tie',
            'confidence': abs(score_a - score_b) / max(score_a, score_b, 0.001)  # Avoid division by zero
        }
    
    def __str__(self) -> str:
        """String representation of the capability scorer."""
        return f"CapabilityScorer(strategy={self.strategy.value})"
    
    def __repr__(self) -> str:
        """Developer representation of the capability scorer."""
        return (f"CapabilityScorer(strategy={self.strategy}, "
                f"emergency_context={bool(self.emergency_context)}, "
                f"historical_nodes={len(self.historical_data)})")
