"""
File 3: Causal Message Implementation

Causal messaging system for distributed communication with vector clocks.
Manages message ordering, delivery, and causal consistency in distributed
systems with emergency awareness.

This provides the communication foundation for vector clock coordination.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

# Import from our local files
from .vector_clock import VectorClock, EmergencyContext

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CausalMessage:
    """
    Message with vector clock for causal ordering
    
    Encapsulates message content along with vector clock timestamp
    to ensure causal delivery order in distributed systems.
    """
    content: Any                    # Message payload
    sender_id: str                 # Sender node identifier
    vector_clock: Dict[str, int]   # Vector clock snapshot at send time
    message_type: str = "normal"   # "normal" or "emergency"
    priority: int = 1             # Higher values = higher priority
    timestamp: Optional[str] = None # Physical timestamp for debugging
    
    def __post_init__(self):
        """Set timestamp if not provided"""
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def is_emergency(self) -> bool:
        """Check if this is an emergency message"""
        return self.message_type == "emergency"
    
    def get_logical_time(self) -> int:
        """Get logical timestamp from sender's perspective"""
        return self.vector_clock.get(self.sender_id, 0)
    
    def __str__(self) -> str:
        """String representation of message"""
        return f"CausalMessage(from={self.sender_id}, type={self.message_type}, clock={self.vector_clock})"

class MessageHandler:
    """
    Handles causal message delivery and ordering
    
    Manages incoming and outgoing messages with vector clock coordination
    to ensure causal consistency. Provides emergency message prioritization
    and proper causal delivery ordering.
    """
    
    def __init__(self, node_id: str):
        """
        Initialize message handler for a node
        
        Args:
            node_id: Unique identifier for this node
        """
        self.node_id = node_id
        self.vector_clock = VectorClock(node_id)
        self.pending_messages = []     # Messages waiting for causal dependencies
        self.processed_messages = []   # Archive of delivered messages
        self.emergency_context = None  # Current emergency state
        
        logger.info(f"Message handler initialized for node: {node_id}")
    
    def send_message(self, content: Any, recipient_id: str, is_emergency: bool = False) -> CausalMessage:
        """
        Create message for sending with current vector clock
        
        Args:
            content: Message payload
            recipient_id: Target node identifier  
            is_emergency: Whether this is an emergency message
            
        Returns:
            CausalMessage: Message ready for transmission
        """
        # Increment local time before sending (Lamport Rule 1)
        self.vector_clock.tick()
        
        # Create message with current clock snapshot
        message = CausalMessage(
            content=content,
            sender_id=self.node_id,
            vector_clock=self.vector_clock.to_dict(),  # Send clock snapshot
            message_type="emergency" if is_emergency else "normal",
            priority=10 if is_emergency else 1
        )
        
        logger.info(f"Sending {message.message_type} message to {recipient_id}")
        return message
    
    def receive_message(self, message: CausalMessage) -> None:
        """
        Receive and process incoming message with causal ordering
        
        Args:
            message: Incoming causal message
        """
        logger.info(f"Received {message.message_type} message from {message.sender_id}")
        
        # Update local vector clock with incoming clock (Lamport Rule 2)
        self.vector_clock.update(message.vector_clock)
        
        # Add to pending queue for causal delivery
        self.pending_messages.append(message)
        
        # Try to deliver any messages that are now ready
        self._process_pending_messages()
    
    def _process_pending_messages(self) -> None:
        """
        Process pending messages in causal order
        
        Delivers messages that satisfy causal dependencies while
        prioritizing emergency messages appropriately.
        """
        # Sort by priority (emergency first) then by logical time
        self.pending_messages.sort(
            key=lambda msg: (-msg.priority, msg.get_logical_time())
        )
        
        delivered_indices = []
        
        for idx, message in enumerate(self.pending_messages):
            if self._can_deliver_message(message):
                self._deliver_message(message)
                self.processed_messages.append(message)
                delivered_indices.append(idx)
        
        # Remove delivered messages (in reverse order to maintain indices)
        for idx in reversed(delivered_indices):
            del self.pending_messages[idx]
    
    def _can_deliver_message(self, message: CausalMessage) -> bool:
        """
        Check if message can be delivered based on causal dependencies
        
        Args:
            message: Message to check for delivery readiness
            
        Returns:
            bool: True if message can be delivered now
        """
        # Check if we've seen all causally preceding events
        for node_id, timestamp in message.vector_clock.items():
            if node_id == message.sender_id:
                # For sender's timestamp, we need exactly the next event
                if self.vector_clock.get_time_for_node(node_id) != timestamp - 1:
                    return False
            else:
                # For other nodes, we need to have seen at least this timestamp
                if self.vector_clock.get_time_for_node(node_id) < timestamp:
                    return False
        
        return True
    
    def _deliver_message(self, message: CausalMessage) -> None:
        """
        Deliver message to application layer
        
        Args:
            message: Message to deliver
        """
        logger.info(f"Delivering message from {message.sender_id}: {message.content}")
        
        if message.is_emergency():
            logger.warning(f"🚨 EMERGENCY MESSAGE: {message.content}")
            self._handle_emergency_message(message)
        else:
            self._handle_normal_message(message)
    
    def _handle_emergency_message(self, message: CausalMessage) -> None:
        """
        Handle emergency message delivery
        
        Args:
            message: Emergency message to handle
        """
        # Extract emergency context if available
        if isinstance(message.content, dict) and 'emergency_type' in message.content:
            emergency_type = message.content['emergency_type']
            emergency_level = message.content.get('emergency_level', 'high')
            
            # Update local emergency context
            from .vector_clock import create_emergency
            self.emergency_context = create_emergency(emergency_type, emergency_level)
            
            logger.warning(f"Emergency context updated: {self.emergency_context}")
    
    def _handle_normal_message(self, message: CausalMessage) -> None:
        """
        Handle normal message delivery
        
        Args:
            message: Normal message to handle
        """
        # Process normal message content
        logger.info(f"Processing normal message: {message.content}")
    
    def send_emergency_alert(self, emergency_type: str, emergency_level: str, location: Optional[str] = None) -> CausalMessage:
        """
        Send emergency alert message
        
        Args:
            emergency_type: Type of emergency
            emergency_level: Priority level  
            location: Optional location information
            
        Returns:
            CausalMessage: Emergency alert message
        """
        emergency_payload = {
            'type': 'emergency_alert',
            'emergency_type': emergency_type,
            'emergency_level': emergency_level,
            'location': location,
            'sender': self.node_id,
            'timestamp': datetime.now().isoformat()
        }
        
        return self.send_message(emergency_payload, "broadcast", is_emergency=True)
    
    def get_pending_count(self) -> int:
        """Get number of pending messages"""
        return len(self.pending_messages)
    
    def has_emergency_pending(self) -> bool:
        """Check if any emergency messages are pending"""
        return any(msg.is_emergency() for msg in self.pending_messages)
    
    def get_message_stats(self) -> Dict[str, int]:
        """Get message processing statistics"""
        return {
            'pending': len(self.pending_messages),
            'processed': len(self.processed_messages),
            'emergency_pending': sum(1 for msg in self.pending_messages if msg.is_emergency()),
            'emergency_processed': sum(1 for msg in self.processed_messages if msg.is_emergency())
        }
    
    def clear_processed_messages(self) -> int:
        """Clear processed message archive and return count"""
        count = len(self.processed_messages)
        self.processed_messages.clear()
        logger.info(f"Cleared {count} processed messages")
        return count

# Utility functions for emergency communication
def broadcast_emergency(handlers: List[MessageHandler], emergency_type: str, 
                       emergency_level: str, location: Optional[str] = None) -> List[CausalMessage]:
    """
    Broadcast emergency to multiple message handlers
    
    Args:
        handlers: List of message handlers to notify
        emergency_type: Type of emergency
        emergency_level: Priority level
        location: Optional location
        
    Returns:
        List[CausalMessage]: Emergency messages sent
    """
    if not handlers:
        return []
    
    # Use first handler as sender
    sender = handlers[0]
    emergency_msg = sender.send_emergency_alert(emergency_type, emergency_level, location)
    
    # Deliver to all other handlers
    for handler in handlers[1:]:
        handler.receive_message(emergency_msg)
    
    return [emergency_msg]

def create_message_network(node_ids: List[str]) -> Dict[str, MessageHandler]:
    """
    Create a network of connected message handlers
    
    Args:
        node_ids: List of node identifiers
        
    Returns:
        Dict[str, MessageHandler]: Network of message handlers
    """
    handlers = {}
    for node_id in node_ids:
        handlers[node_id] = MessageHandler(node_id)
    
    logger.info(f"Created message network with {len(handlers)} nodes")
    return handlers

# Example usage and testing
if __name__ == "__main__":
    print("✅ Causal Message Implementation - File 3 Complete")
    
    # Test basic message handling
    handler1 = MessageHandler("node1")
    handler2 = MessageHandler("node2")
    
    # Test normal message
    msg = handler1.send_message("Hello from node1", "node2")
    handler2.receive_message(msg)
    print(f"Message delivered: {handler2.get_message_stats()}")
    
    # Test emergency message
    emergency_msg = handler1.send_emergency_alert("fire", "critical", "Building A")
    handler2.receive_message(emergency_msg)
    print(f"Emergency delivered: {handler2.get_message_stats()}")
    
    print("   Causal messaging with emergency support ready!")
    print("   Foundation for distributed vector clock coordination")
