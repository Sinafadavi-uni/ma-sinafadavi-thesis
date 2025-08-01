# Vector Clock for Emergency Systems
# Based on Lamport's paper about logical time in distributed systems
# This helps us order events when clocks aren't synchronized

from typing import Dict, List, Optional
from uuid import UUID
from enum import Enum

# Import our node capabilities model
from rec.model import Capabilities


# Simple enum for emergency levels - learned this is better than just numbers
class EmergencyLevel(Enum):
    LOW = 1
    MEDIUM = 2 
    HIGH = 3
    CRITICAL = 4


# Basic vector clock class - implements the algorithm from Lamport's paper
class VectorClock:
    def __init__(self, node_id):
        # Each node has its own ID and keeps track of all nodes it knows about
        self.node_id = node_id
        self.clock = {}  # maps node_id -> timestamp
        
    def tick(self):
        # Increment our own logical time (this happens before sending a message)
        if self.node_id not in self.clock:
            self.clock[self.node_id] = 0
        self.clock[self.node_id] += 1
        
    def update(self, other_clock):
        # When we receive a message, update our clock with the sender's info
        # Rule: take the maximum of both clocks for each node
        for node_id, timestamp in other_clock.items():
            if node_id not in self.clock:
                self.clock[node_id] = 0
            self.clock[node_id] = max(self.clock[node_id], timestamp)
        
        # Always increment our own time after receiving
        self.tick()
    
    def compare(self, other_clock):
        # Compare two clocks to see which happened first
        # Returns: 'before', 'after', or 'concurrent'
        
        # Get all nodes from both clocks
        all_nodes = set(self.clock.keys()) | set(other_clock.keys())
        
        self_smaller = False
        other_smaller = False
        
        for node in all_nodes:
            self_time = self.clock.get(node, 0)
            other_time = other_clock.get(node, 0)
            
            if self_time < other_time:
                other_smaller = True
            elif self_time > other_time:
                self_smaller = True
        
        # Determine relationship
        if self_smaller and not other_smaller:
            return 'before'
        elif other_smaller and not self_smaller:
            return 'after'
        else:
            return 'concurrent'


# Emergency context - keeps track of what kind of emergency we're dealing with
class EmergencyContext:
    def __init__(self, emergency_type, level, location=None):
        self.emergency_type = emergency_type  # like "medical", "fire", "earthquake"
        self.level = level  # EmergencyLevel enum
        self.location = location  # where the emergency is happening
        self.detected_at = None  # when we first detected it
        
    def is_critical(self):
        # Helper to check if this is a serious emergency
        return self.level in [EmergencyLevel.HIGH, EmergencyLevel.CRITICAL]


# Enhanced vector clock that considers node capabilities for emergencies
class CapabilityAwareVectorClock(VectorClock):
    def __init__(self, node_id, capabilities):
        # Start with basic vector clock
        super().__init__(node_id)
        self.capabilities = capabilities
        
    def get_capability_score(self, emergency_context=None):
        # Calculate how useful this node is (higher = better)
        # Basic formula: CPU + Memory + Power, with emergency boosts
        
        score = 0.0
        
        # Basic hardware score
        if hasattr(self.capabilities, 'cpu_cores'):
            score += self.capabilities.cpu_cores * 1.0
        if hasattr(self.capabilities, 'memory'):
            score += (self.capabilities.memory / 1024) * 0.5  # convert MB to GB-ish
        if hasattr(self.capabilities, 'power'):
            score += (self.capabilities.power / 100) * 2.0  # power percentage
            
        # Emergency bonus - if we're in an emergency, medical equipment gets priority
        if emergency_context and emergency_context.is_critical():
            # Check if this node has medical capabilities
            if hasattr(self.capabilities, 'has_medical_equipment'):
                if self.capabilities.has_medical_equipment:
                    score += 5.0  # big bonus for medical equipment during emergencies
                    
        return score
    
    def should_handle_emergency(self, emergency_context, other_nodes_scores):
        # Decide if this node should handle an emergency
        # Simple rule: we handle it if we have the highest capability score
        
        my_score = self.get_capability_score(emergency_context)
        
        # If no other nodes, we have to handle it
        if not other_nodes_scores:
            return True
            
        # Check if we're the best option
        max_other_score = max(other_nodes_scores)
        return my_score >= max_other_score


# Simple capability scorer for ranking nodes
class CapabilityScorer:
    def __init__(self):
        # Different scoring strategies for different situations
        self.strategy = "basic"  # can be "basic", "emergency", "energy_saving"
    
    def score_node(self, capabilities, emergency_context=None):
        # Score a node based on its capabilities
        
        if self.strategy == "emergency" and emergency_context:
            return self._emergency_score(capabilities, emergency_context)
        elif self.strategy == "energy_saving":
            return self._energy_score(capabilities)
        else:
            return self._basic_score(capabilities)
    
    def _basic_score(self, capabilities):
        # Simple scoring: just add up the main specs
        score = 0.0
        if hasattr(capabilities, 'cpu_cores'):
            score += capabilities.cpu_cores
        if hasattr(capabilities, 'memory'):
            score += capabilities.memory / 1000  # normalize memory
        if hasattr(capabilities, 'power'):
            score += capabilities.power / 50  # normalize power
        return score
    
    def _emergency_score(self, capabilities, emergency_context):
        # Emergency scoring: prioritize based on emergency type
        score = self._basic_score(capabilities)
        
        # Bonus for emergency-relevant capabilities
        if emergency_context.emergency_type == "medical":
            if hasattr(capabilities, 'has_medical_equipment') and capabilities.has_medical_equipment:
                score += 10.0
        elif emergency_context.emergency_type == "fire":
            # Maybe prioritize nodes with sensors or communication equipment
            score += 2.0
            
        return score
    
    def _energy_score(self, capabilities):
        # Energy-conscious scoring: prefer nodes with more battery
        score = 0.0
        if hasattr(capabilities, 'power'):
            score = capabilities.power / 10  # mainly based on power level
        if hasattr(capabilities, 'cpu_cores'):
            score += capabilities.cpu_cores * 0.1  # small bonus for CPU
        return score
    
    def rank_nodes(self, nodes_with_capabilities, emergency_context=None):
        # Rank a list of nodes by their capability scores
        # nodes_with_capabilities should be [(node_id, capabilities), ...]
        
        scored_nodes = []
        for node_id, capabilities in nodes_with_capabilities:
            score = self.score_node(capabilities, emergency_context)
            scored_nodes.append((node_id, score))
        
        # Sort by score (highest first)
        scored_nodes.sort(key=lambda x: x[1], reverse=True)
        return scored_nodes


# Helper function to create emergency contexts easily
def create_emergency(emergency_type, severity_level, location=None):
    """Create an emergency context - helper function for testing"""
    if isinstance(severity_level, str):
        # Convert string to enum
        level_map = {
            'low': EmergencyLevel.LOW,
            'medium': EmergencyLevel.MEDIUM,
            'high': EmergencyLevel.HIGH,
            'critical': EmergencyLevel.CRITICAL
        }
        severity_level = level_map.get(severity_level.lower(), EmergencyLevel.LOW)
    
    emergency = EmergencyContext(emergency_type, severity_level, location)
    return emergency
