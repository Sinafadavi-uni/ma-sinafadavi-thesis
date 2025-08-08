"""
File 1: Base Consistency Manager Interface

Foundation interface for all consistency management implementations.
Required by all consistency policies including causal consistency
and FCFS consistency implementations.

This is the absolute foundation that all consistency mechanisms depend on.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseConsistencyManager(ABC):
    """
    Abstract base class for all consistency managers
    
    Provides the interface that all consistency implementations
    must follow. This includes causal consistency, FCFS policies,
    and any other consistency mechanisms.
    
    All consistency managers in the system inherit from this base.
    """
    
    def __init__(self, node_id: str):
        """
        Initialize base consistency manager
        
        Args:
            node_id: Unique identifier for this node
        """
        self.node_id = node_id
        self.active = True
        logger.info(f"Base consistency manager initialized for node: {node_id}")
    
    @abstractmethod
    def ensure_consistency(self, operation: Dict[str, Any]) -> bool:
        """
        Ensure consistency for a given operation
        
        Args:
            operation: Operation data that needs consistency checking
            
        Returns:
            bool: True if operation maintains consistency, False otherwise
        """
        pass
    
    @abstractmethod
    def validate_operation(self, operation: Dict[str, Any]) -> bool:
        """
        Validate that an operation is consistent with current state
        
        Args:
            operation: Operation to validate
            
        Returns:
            bool: True if operation is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def update_state(self, state_update: Dict[str, Any]) -> None:
        """
        Update internal consistency state
        
        Args:
            state_update: New state information to incorporate
        """
        pass
    
    def get_node_id(self) -> str:
        """Get the node identifier"""
        return self.node_id
    
    def is_active(self) -> bool:
        """Check if consistency manager is active"""
        return self.active
    
    def activate(self) -> None:
        """Activate the consistency manager"""
        self.active = True
        logger.info(f"Consistency manager activated for node: {self.node_id}")
    
    def deactivate(self) -> None:
        """Deactivate the consistency manager"""
        self.active = False
        logger.info(f"Consistency manager deactivated for node: {self.node_id}")

class ConsistencyPolicy(ABC):
    """
    Abstract base class for consistency policies
    
    Consistency policies define specific rules for how consistency
    should be maintained. Examples include FCFS, priority-based,
    or causal ordering policies.
    """
    
    def __init__(self, policy_name: str):
        """
        Initialize consistency policy
        
        Args:
            policy_name: Name of this consistency policy
        """
        self.policy_name = policy_name
        self.enabled = True
        logger.info(f"Consistency policy '{policy_name}' initialized")
    
    @abstractmethod
    def apply_policy(self, operation: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Apply the consistency policy to an operation
        
        Args:
            operation: Operation to apply policy to
            context: Current system context
            
        Returns:
            bool: True if operation satisfies policy, False otherwise
        """
        pass
    
    @abstractmethod
    def check_violation(self, operation: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Check if an operation violates the consistency policy
        
        Args:
            operation: Operation to check
            context: Current system context
            
        Returns:
            bool: True if operation violates policy, False otherwise
        """
        pass
    
    def get_policy_name(self) -> str:
        """Get the policy name"""
        return self.policy_name
    
    def is_enabled(self) -> bool:
        """Check if policy is enabled"""
        return self.enabled
    
    def enable(self) -> None:
        """Enable the policy"""
        self.enabled = True
        logger.info(f"Policy '{self.policy_name}' enabled")
    
    def disable(self) -> None:
        """Disable the policy"""
        self.enabled = False
        logger.info(f"Policy '{self.policy_name}' disabled")

# Example usage for testing
if __name__ == "__main__":
    print("✅ Base Consistency Manager Interface - File 1 Complete")
    print("   Foundation for all consistency implementations")
    print("   Ready for CausalConsistencyManager and FCFSConsistencyPolicy")
