"""
Causal Message Implementation for Distributed Systems.

This module implements causal message passing with vector clock timestamps
for maintaining causal consistency in distributed systems.

Classes:
    CausalMessage: Message with causal context
    CausalMessageHandler: Handles causal message processing
    MessagePriority: Enumeration for message priorities

Author: Sina Fadavi
Date: August 2025
"""

from __future__ import annotations
from typing import Any, Dict, Optional, List, Union
from uuid import UUID
from enum import Enum
from dataclasses import dataclass
from .vector_clock import VectorClock, CapabilityAwareVectorClock

try:
    import msgpack
except ImportError:
    msgpack = None


class MessagePriority(Enum):
    """
    Priority levels for causal messages in emergency scenarios.
    
    Values:
        LOW: Regular operational messages
        NORMAL: Standard system messages
        HIGH: Important system updates
        CRITICAL: Emergency scenario messages
        EMERGENCY: Life-critical emergency messages
    """
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


@dataclass
class CausalMessage:
    """
    Message with causal context for distributed systems.
    
    A causal message contains both the message content and the causal
    context (vector clock) that establishes the happens-before relationship
    with other messages in the system.
    
    Attributes:
        message_id: Unique identifier for this message
        sender_id: ID of the node that sent this message
        content: The actual message payload
        vector_clock: Vector clock timestamp when message was sent
        capability_signature: Sender's capability weight at send time
        priority: Message priority for emergency scenarios
        timestamp: Physical timestamp (for debugging/logging)
        dependencies: List of message IDs this message depends on
        
    Example:
        >>> from uuid import uuid4
        >>> clock = VectorClock(sender_id)
        >>> message = CausalMessage(
        ...     message_id=uuid4(),
        ...     sender_id=sender_id,
        ...     content={'operation': 'update', 'data': 'example'},
        ...     vector_clock=clock.clock.copy(),
        ...     priority=MessagePriority.NORMAL
        ... )
    """
    
    message_id: UUID
    sender_id: UUID
    content: Any
    vector_clock: Dict[UUID, int]
    capability_signature: float = 0.0
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: Optional[float] = None
    dependencies: Optional[List[UUID]] = None
    
    def __post_init__(self) -> None:
        """Initialize dependencies list if not provided."""
        if self.dependencies is None:
            self.dependencies = []
    
    def serialize(self) -> bytes:
        """
        Serialize the causal message to bytes.
        
        Returns:
            Serialized message as bytes
            
        Raises:
            RuntimeError: If msgpack is not available
            
        Time Complexity: O(n + m) where n is vector clock size, m is content size
        """
        if msgpack is None:
            raise RuntimeError("msgpack not available - install with pip install msgpack")
        
        data = {
            'message_id': str(self.message_id),
            'sender_id': str(self.sender_id),
            'content': self.content,
            'vector_clock': {str(node_id): timestamp 
                           for node_id, timestamp in self.vector_clock.items()},
            'capability_signature': self.capability_signature,
            'priority': self.priority.value,
            'timestamp': self.timestamp,
            'dependencies': [str(dep_id) for dep_id in (self.dependencies or [])]
        }
        return msgpack.packb(data)
    
    @classmethod
    def deserialize(cls, data: bytes) -> CausalMessage:
        """
        Deserialize a causal message from bytes.
        
        Args:
            data: Serialized message data
            
        Returns:
            CausalMessage instance
            
        Raises:
            ValueError: If data is invalid
            RuntimeError: If msgpack is not available
        """
        if msgpack is None:
            raise RuntimeError("msgpack not available - install with pip install msgpack")
        
        try:
            unpacked = msgpack.unpackb(data, strict_map_key=False)
            
            return cls(
                message_id=UUID(unpacked['message_id']),
                sender_id=UUID(unpacked['sender_id']),
                content=unpacked['content'],
                vector_clock={UUID(node_id): timestamp 
                            for node_id, timestamp in unpacked['vector_clock'].items()},
                capability_signature=unpacked.get('capability_signature', 0.0),
                priority=MessagePriority(unpacked.get('priority', MessagePriority.NORMAL.value)),
                timestamp=unpacked.get('timestamp'),
                dependencies=[UUID(dep_id) for dep_id in unpacked.get('dependencies', [])]
            )
            
        except (msgpack.exceptions.ExtraData,
                msgpack.exceptions.InvalidDocument,
                KeyError,
                ValueError) as e:
            raise ValueError(f"Invalid causal message data: {e}")
    
    def has_dependency(self, message_id: UUID) -> bool:
        """
        Check if this message depends on another message.
        
        Args:
            message_id: ID of the message to check dependency for
            
        Returns:
            True if this message depends on the given message
        """
        return message_id in (self.dependencies or [])
    
    def add_dependency(self, message_id: UUID) -> None:
        """
        Add a dependency to this message.
        
        Args:
            message_id: ID of the message this message depends on
        """
        if self.dependencies is None:
            self.dependencies = []
        if message_id not in self.dependencies:
            self.dependencies.append(message_id)
    
    def __str__(self) -> str:
        """String representation of the causal message."""
        deps_str = f", deps={len(self.dependencies or [])}"
        return (f"CausalMessage(id={self.message_id}, sender={self.sender_id}, "
                f"priority={self.priority.name}{deps_str})")


class CausalMessageHandler:
    """
    Handles processing and ordering of causal messages.
    
    This class manages the reception, ordering, and delivery of causal messages
    according to causal consistency guarantees. It maintains a buffer of
    undelivered messages and ensures messages are delivered in causal order.
    
    Attributes:
        node_id: ID of the local node
        vector_clock: Local vector clock for causal ordering
        message_buffer: Buffer for messages waiting for dependencies
        delivered_messages: Set of already delivered message IDs
        
    Example:
        >>> handler = CausalMessageHandler(node_id, local_clock)
        >>> messages_to_deliver = handler.receive_message(incoming_message)
        >>> for message in messages_to_deliver:
        ...     process_message(message)
    """
    
    def __init__(self, node_id: UUID, vector_clock: VectorClock) -> None:
        """
        Initialize causal message handler.
        
        Args:
            node_id: ID of the local node
            vector_clock: Local vector clock for causal ordering
        """
        self.node_id: UUID = node_id
        self.vector_clock: VectorClock = vector_clock
        self.message_buffer: Dict[UUID, CausalMessage] = {}
        self.delivered_messages: set[UUID] = set()
        self.dependency_graph: Dict[UUID, List[UUID]] = {}
    
    def prepare_message(self, content: Any, priority: MessagePriority = MessagePriority.NORMAL) -> CausalMessage:
        """
        Prepare a message for sending with current causal context.
        
        Args:
            content: The message content to send
            priority: Priority level for the message
            
        Returns:
            CausalMessage ready for transmission
            
        Time Complexity: O(1)
        """
        from uuid import uuid4
        import time
        
        # Increment local clock before sending
        self.vector_clock.increment()
        
        # Create message with current causal context
        message = CausalMessage(
            message_id=uuid4(),
            sender_id=self.node_id,
            content=content,
            vector_clock=self.vector_clock.clock.copy(),
            capability_signature=getattr(self.vector_clock, 'capability_weight', 0.0),
            priority=priority,
            timestamp=time.time()
        )
        
        return message
    
    def receive_message(self, message: CausalMessage) -> List[CausalMessage]:
        """
        Process received message and return deliverable messages.
        
        Args:
            message: Received causal message
            
        Returns:
            List of messages that can now be delivered in causal order
            
        Time Complexity: O(m) where m is number of buffered messages
        """
        # Skip if already delivered
        if message.message_id in self.delivered_messages:
            return []
        
        # Add to buffer
        self.message_buffer[message.message_id] = message
        
        # Try to deliver messages in causal order
        deliverable = self._find_deliverable_messages()
        
        # Remove delivered messages from buffer
        for msg in deliverable:
            self.delivered_messages.add(msg.message_id)
            self.message_buffer.pop(msg.message_id, None)
            
        return deliverable
    
    def _find_deliverable_messages(self) -> List[CausalMessage]:
        """
        Find messages that can be delivered according to causal ordering.
        
        Returns:
            List of messages ready for delivery
            
        Time Complexity: O(m²) where m is number of buffered messages
        """
        deliverable = []
        
        for message in self.message_buffer.values():
            if self._can_deliver_message(message):
                deliverable.append(message)
        
        # Sort by priority and then by timestamp for deterministic ordering
        deliverable.sort(key=lambda msg: (-msg.priority.value, msg.timestamp or 0))
        
        return deliverable
    
    def _can_deliver_message(self, message: CausalMessage) -> bool:
        """
        Check if a message can be delivered according to causal ordering.
        
        Args:
            message: Message to check for delivery
            
        Returns:
            True if message can be delivered now
            
        Time Complexity: O(n) where n is number of nodes in vector clock
        """
        # Check vector clock constraints
        for node_id, timestamp in message.vector_clock.items():
            local_time = self.vector_clock.get_time(node_id)
            
            if node_id == message.sender_id:
                # Message from sender must be exactly local_time + 1
                if timestamp != local_time + 1:
                    return False
            else:
                # Messages from other nodes must be ≤ local_time
                if timestamp > local_time:
                    return False
        
        # Check explicit dependencies
        if message.dependencies:
            for dep_id in message.dependencies:
                if dep_id not in self.delivered_messages:
                    return False
        
        return True
    
    def update_local_clock(self, message: CausalMessage) -> None:
        """
        Update local vector clock based on delivered message.
        
        Args:
            message: Message that was just delivered
            
        Time Complexity: O(n) where n is number of nodes
        """
        self.vector_clock.update(message.vector_clock)
    
    def get_buffer_size(self) -> int:
        """
        Get the current size of the message buffer.
        
        Returns:
            Number of messages waiting for delivery
        """
        return len(self.message_buffer)
    
    def get_pending_dependencies(self) -> Dict[UUID, List[UUID]]:
        """
        Get information about pending message dependencies.
        
        Returns:
            Dictionary mapping message IDs to their unmet dependencies
        """
        pending = {}
        
        for msg_id, message in self.message_buffer.items():
            unmet_deps = []
            if message.dependencies:
                for dep_id in message.dependencies:
                    if dep_id not in self.delivered_messages:
                        unmet_deps.append(dep_id)
            
            if unmet_deps:
                pending[msg_id] = unmet_deps
        
        return pending
    
    def __str__(self) -> str:
        """String representation of the message handler."""
        return (f"CausalMessageHandler(node={self.node_id}, "
                f"buffered={len(self.message_buffer)}, "
                f"delivered={len(self.delivered_messages)})")
