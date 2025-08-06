# Vector Clock & Emergency Handling (Student Version)
# Inspired by Lamport’s logical clocks but extended for emergencies and serverless systems

from typing import Dict, List, Optional
from uuid import UUID
from enum import Enum

from rec.model import Capabilities


# Emergency levels — easier to work with than raw numbers
class EmergencyLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# Basic vector clock like Lamport described
class VectorClock:
    def __init__(self, node_id):
        self.node_id = node_id
        self.clock = {}  # Stores timestamp per node

    def tick(self):
        # Increment time for this node
        self.clock[self.node_id] = self.clock.get(self.node_id, 0) + 1

    def update(self, incoming):
        # Merge with another clock
        for nid, ts in incoming.items():
            self.clock[nid] = max(self.clock.get(nid, 0), ts)
        self.tick()  # bump after merge

    def compare(self, other):
        # Compare vector clocks - handle both VectorClock objects and dicts
        if isinstance(other, VectorClock):
            other_clock = other.clock
        else:
            other_clock = other
            
        all_ids = set(self.clock) | set(other_clock)
        ours_lagging = theirs_lagging = False

        for nid in all_ids:
            ours = self.clock.get(nid, 0)
            theirs = other_clock.get(nid, 0)
            if ours < theirs:
                theirs_lagging = True
            elif ours > theirs:
                ours_lagging = True

        if ours_lagging and not theirs_lagging:
            return "after"
        elif theirs_lagging and not ours_lagging:
            return "before"
        return "concurrent"
    
    def to_dict(self):
        # For status reporting
        return dict(self.clock)


# Stores info about the current emergency
class EmergencyContext:
    def __init__(self, emergency_type, level, location=None):
        self.emergency_type = emergency_type
        self.level = level
        self.location = location
        self.detected_at = None
        self.execution_type = "traditional"  # could be "serverless"

    def is_critical(self):
        return self.level in (EmergencyLevel.HIGH, EmergencyLevel.CRITICAL)

    def is_serverless_compatible(self):
        return self.emergency_type in [
            "fire", "medical", "disaster", "general", "critical"
        ]


# Whether job runs as normal job, serverless, or both
class ExecutionType(Enum):
    TRADITIONAL = "traditional"
    SERVERLESS = "serverless"
    HYBRID = "hybrid"


# Vector clock that can consider hardware specs
class CapabilityAwareVectorClock(VectorClock):
    def __init__(self, node_id, caps):
        super().__init__(node_id)
        self.capabilities = caps

    def get_capability_score(self, context=None):
        score = 0.0
        score += getattr(self.capabilities, "cpu_cores", 0)
        score += getattr(self.capabilities, "memory", 0) / 1024 * 0.5
        score += getattr(self.capabilities, "power", 0) / 100 * 2.0

        if context and context.is_critical():
            if getattr(self.capabilities, "has_medical_equipment", False):
                score += 5.0

        return score

    def should_handle_emergency(self, context, peer_scores):
        my_score = self.get_capability_score(context)
        return my_score >= max(peer_scores or [0])


# Just a helper to score nodes for different goals
class CapabilityScorer:
    def __init__(self):
        self.strategy = "basic"

    def score_node(self, caps, context=None):
        if self.strategy == "emergency" and context:
            return self._emergency_score(caps, context)
        if self.strategy == "energy_saving":
            return self._energy_score(caps)
        return self._basic_score(caps)

    def _basic_score(self, caps):
        s = 0
        s += getattr(caps, "cpu_cores", 0)
        s += getattr(caps, "memory", 0) / 1000
        s += getattr(caps, "power", 0) / 50
        return s

    def _emergency_score(self, caps, ctx):
        score = self._basic_score(caps)
        if ctx.emergency_type == "medical" and getattr(caps, "has_medical_equipment", False):
            score += 10
        elif ctx.emergency_type == "fire":
            score += 2
        return score

    def _energy_score(self, caps):
        return getattr(caps, "power", 0) / 10 + getattr(caps, "cpu_cores", 0) * 0.1

    def rank_nodes(self, node_cap_list, ctx=None):
        scored = [(nid, self.score_node(caps, ctx)) for nid, caps in node_cap_list]
        return sorted(scored, key=lambda x: x[1], reverse=True)


# For serverless use cases — extra stuff like cold starts
class ServerlessVectorClock(VectorClock):
    def __init__(self, function_id, capabilities=None):
        super().__init__(function_id)
        self.capabilities = capabilities or {}
        self.cold_start_count = 0
        self.execution_history = []
        self.is_warm = False

    def mark_cold_start(self):
        self.cold_start_count += 1
        self.is_warm = False
        self.tick()

    def mark_warm_execution(self):
        self.is_warm = True
        self.tick()

    def get_function_priority(self, emergency_context=None):
        base = 1.0
        if emergency_context and emergency_context.is_critical():
            multiplier = {
                "critical": 10,
                "medical": 8,
                "fire": 7,
                "disaster": 6,
                "general": 5
            }.get(emergency_context.emergency_type, 5)
            base *= multiplier

        if self.is_warm and emergency_context and emergency_context.is_critical():
            base *= 1.2

        return base

    def should_pre_warm(self, emergency_context=None):
        if emergency_context and emergency_context.is_serverless_compatible():
            return emergency_context.emergency_type in ["medical", "fire", "critical", "disaster"]
        return False


# A quick way to make emergency objects (useful for testing)
def create_emergency(em_type, level, loc=None):
    if isinstance(level, str):
        level = {
            "low": EmergencyLevel.LOW,
            "medium": EmergencyLevel.MEDIUM,
            "high": EmergencyLevel.HIGH,
            "critical": EmergencyLevel.CRITICAL
        }.get(level.lower(), EmergencyLevel.LOW)

    return EmergencyContext(em_type, level, loc)
