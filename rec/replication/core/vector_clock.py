# Vector Clock for Coordinating Emergency Systems
# Inspired by Lamport's logical clocks idea
# Used when system clocks aren't quite trustworthy

from typing import Dict, List, Optional
from uuid import UUID
from enum import Enum

# Bringing in node capability definitions
from rec.model import Capabilities


# Emergency level indicator – a bit nicer than plain numbers
class EmergencyLevel(Enum):
    LOW = 1
    MEDIUM = 2 
    HIGH = 3
    CRITICAL = 4


# Basic implementation of a vector clock – follows Lamport's paper
class VectorClock:
    def __init__(self, node_id):
        self.node_id = node_id
        self.clock = {}  # This keeps track of logical time for each node we know
        
    def tick(self):
        # Increment local time – typically called before sending a message
        self.clock[self.node_id] = self.clock.get(self.node_id, 0) + 1
        
    def update(self, incoming_clock):
        # Merge another node's clock into ours
        for peer_id, time_val in incoming_clock.items():
            current = self.clock.get(peer_id, 0)
            self.clock[peer_id] = max(current, time_val)
        
        self.tick()  # Bump our clock post-receive
    
    def compare(self, incoming_clock):
        # Determine event order relation between this and another clock
        all_keys = set(self.clock) | set(incoming_clock)
        
        ours_earlier = False
        theirs_earlier = False
        
        for node in all_keys:
            our_time = self.clock.get(node, 0)
            their_time = incoming_clock.get(node, 0)
            if our_time < their_time:
                theirs_earlier = True
            elif our_time > their_time:
                ours_earlier = True
        
        if ours_earlier and not theirs_earlier:
            return 'after'
        elif theirs_earlier and not ours_earlier:
            return 'before'
        return 'concurrent'


# Holds details of an emergency – still pretty lightweight
class EmergencyContext:
    def __init__(self, emergency_type, level, location=None):
        self.emergency_type = emergency_type  # "fire", "quake", etc
        self.level = level
        self.location = location
        self.detected_at = None  # Timestamp might be set later
    
    def is_critical(self):
        # Quick check for serious situations
        return self.level in (EmergencyLevel.HIGH, EmergencyLevel.CRITICAL)


# Like a vector clock but smarter – knows about node capabilities
class CapabilityAwareVectorClock(VectorClock):
    def __init__(self, node_id, capabilities):
        super().__init__(node_id)
        self.capabilities = capabilities  # This includes CPU, power, etc.
        
    def get_capability_score(self, emergency_context=None):
        # Gives us a rough score for how capable this node is
        score = 0.0
        
        # Add basic specs
        score += getattr(self.capabilities, 'cpu_cores', 0) * 1.0
        mem = getattr(self.capabilities, 'memory', 0)
        score += (mem / 1024) * 0.5
        
        power = getattr(self.capabilities, 'power', 0)
        score += (power / 100) * 2.0
        
        # Bonus if emergency and we have special equipment
        if emergency_context and emergency_context.is_critical():
            if getattr(self.capabilities, 'has_medical_equipment', False):
                score += 5.0  # Maybe overkill, but good for triage
            
        return score
    
    def should_handle_emergency(self, context, other_scores):
        # Try to be the lead responder if we score the highest
        my_score = self.get_capability_score(context)
        
        if not other_scores:  # We're all alone in this
            return True
        
        return my_score >= max(other_scores)


# This guy helps us sort out which nodes are better for what
class CapabilityScorer:
    def __init__(self):
        self.strategy = "basic"  # Could tweak this for emergencies or battery-saving
    
    def score_node(self, caps, context=None):
        # Depending on mode, pick a different formula
        if self.strategy == "emergency" and context:
            return self._emergency_score(caps, context)
        if self.strategy == "energy_saving":
            return self._energy_score(caps)
        return self._basic_score(caps)
    
    def _basic_score(self, caps):
        # Really simple scoring – adds the basics
        score = 0.0
        score += getattr(caps, 'cpu_cores', 0)
        score += getattr(caps, 'memory', 0) / 1000
        score += getattr(caps, 'power', 0) / 50
        return score
    
    def _emergency_score(self, caps, ctx):
        # When it's urgent, factor in special gear
        base = self._basic_score(caps)
        
        if ctx.emergency_type == "medical":
            if getattr(caps, 'has_medical_equipment', False):
                base += 10.0
        elif ctx.emergency_type == "fire":
            base += 2.0  # Placeholder: maybe comms or sensors later
            
        return base
    
    def _energy_score(self, caps):
        # Prioritize saving juice
        power_score = getattr(caps, 'power', 0) / 10
        cpu_bonus = getattr(caps, 'cpu_cores', 0) * 0.1
        return power_score + cpu_bonus
    
    def rank_nodes(self, node_cap_pairs, ctx=None):
        # Score and sort list of (node_id, capabilities)
        scores = []
        for node_id, caps in node_cap_pairs:
            val = self.score_node(caps, ctx)
            scores.append((node_id, val))
        
        return sorted(scores, key=lambda pair: pair[1], reverse=True)


# Handy way to build an emergency scenario – mostly for tests
def create_emergency(emergency_type, severity_level, location=None):
    level_enum = severity_level
    if isinstance(severity_level, str):
        level_map = {
            'low': EmergencyLevel.LOW,
            'medium': EmergencyLevel.MEDIUM,
            'high': EmergencyLevel.HIGH,
            'critical': EmergencyLevel.CRITICAL
        }
        level_enum = level_map.get(severity_level.lower(), EmergencyLevel.LOW)
    
    return EmergencyContext(emergency_type, level_enum, location)
