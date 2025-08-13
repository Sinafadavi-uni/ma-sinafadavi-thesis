"""
File 1: Base Consistency Manager Interface

Foundation interface for all consistency management implementations.
Required by all consistency policies including causal consistency
and FCFS consistency implementations.

This is the absolute foundation that all consistency mechanisms depend on.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

# Setting up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseConsistencyManager(ABC):
    """
    Base class for all consistency managers (abstract)
    """

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.active = True
        logger.info(f"Base consistency manager initialized for node: {node_id}")

    @abstractmethod
    def ensure_consistency(self, operation: Dict[str, Any]) -> bool:
        """
        Must be implemented to check consistency for the operation
        """
        pass

    @abstractmethod
    def validate_operation(self, operation: Dict[str, Any]) -> bool:
        """
        Should check if operation is valid in current state
        """
        pass

    @abstractmethod
    def update_state(self, state_update: Dict[str, Any]) -> None:
        """
        Should update manager's internal state
        """
        pass

    def get_node_id(self) -> str:
        return self.node_id

    def is_active(self) -> bool:
        return self.active

    def activate(self) -> None:
        self.active = True
        logger.info(f"Consistency manager activated for node: {self.node_id}")

    def deactivate(self) -> None:
        self.active = False
        logger.info(f"Consistency manager deactivated for node: {self.node_id}")

class ConsistencyPolicy(ABC):
    """
    Base class for consistency policies (like FCFS, causal, etc.)
    """

    def __init__(self, policy_name: str):
        self.policy_name = policy_name
        self.enabled = True
        logger.info(f"Consistency policy '{policy_name}' initialized")

    @abstractmethod
    def apply_policy(self, operation: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Must be implemented to apply policy rules to the operation
        """
        pass

    @abstractmethod
    def check_violation(self, operation: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Must check if the operation breaks the policy rules
        """
        pass

    def get_policy_name(self) -> str:
        return self.policy_name

    def is_enabled(self) -> bool:
        return self.enabled

    def enable(self) -> None:
        self.enabled = True
        logger.info(f"Policy '{self.policy_name}' enabled")

    def disable(self) -> None:
        self.enabled = False
        logger.info(f"Policy '{self.policy_name}' disabled")

# Just to test it runs
if __name__ == "__main__":
    print("✅ Base Consistency Manager Interface - File 1 Complete")
    print("   Foundation for all consistency implementations")
    print("   Ready for CausalConsistencyManager and FCFSConsistencyPolicy")
