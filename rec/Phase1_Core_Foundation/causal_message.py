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

from .vector_clock import VectorClock, EmergencyContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CausalMessage:
    content: Any
    sender_id: str
    vector_clock: Dict[str, int]
    message_type: str = "normal"
    priority: int = 1
    timestamp: Optional[str] = None
    emergency_context: Optional[EmergencyContext] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.emergency_context and self.emergency_context.is_critical():
            self.message_type = "emergency"
            self.priority = 10

    def is_emergency(self) -> bool:
        return self.message_type == "emergency"

    def get_logical_time(self) -> int:
        return self.vector_clock.get(self.sender_id, 0)

    def __str__(self) -> str:
        return f"CausalMessage(from={self.sender_id}, type={self.message_type}, clock={self.vector_clock})"

class MessageHandler:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.vector_clock = VectorClock(node_id)
        self.pending_messages = []
        self.processed_messages = []
        self.emergency_context = None
        logger.info(f"Message handler initialized for node: {node_id}")

    def send_message(self, content: Any, recipient_id: str, is_emergency: bool = False) -> CausalMessage:
        self.vector_clock.tick()
        msg_type = "emergency" if is_emergency else "normal"
        prio = 10 if is_emergency else 1

        message = CausalMessage(
            content=content,
            sender_id=self.node_id,
            vector_clock=self.vector_clock.to_dict(),
            message_type=msg_type,
            priority=prio
        )

        logger.info(f"Sending {msg_type} message to {recipient_id}")
        return message

    def receive_message(self, message: CausalMessage) -> None:
        logger.info(f"Received {message.message_type} message from {message.sender_id}")
        self.vector_clock.update(message.vector_clock)
        self.pending_messages.append(message)
        self._process_pending_messages()

    def _process_pending_messages(self) -> None:
        self.pending_messages.sort(key=lambda m: (-m.priority, m.get_logical_time()))
        ready_to_remove = []

        for i, msg in enumerate(self.pending_messages):
            if self._can_deliver_message(msg):
                self._deliver_message(msg)
                self.processed_messages.append(msg)
                ready_to_remove.append(i)

        for i in reversed(ready_to_remove):
            del self.pending_messages[i]

    def _can_deliver_message(self, message: CausalMessage) -> bool:
        for node, ts in message.vector_clock.items():
            local_ts = self.vector_clock.get_time_for_node(node)

            if node == message.sender_id:
                if local_ts != ts - 1:
                    return False
            else:
                if local_ts < ts:
                    return False

        return True

    def _deliver_message(self, message: CausalMessage) -> None:
        logger.info(f"Delivering message from {message.sender_id}: {message.content}")

        if message.is_emergency():
            logger.warning(f"🚨 EMERGENCY MESSAGE: {message.content}")
            self._handle_emergency_message(message)
        else:
            self._handle_normal_message(message)

    def _handle_emergency_message(self, message: CausalMessage) -> None:
        if isinstance(message.content, dict) and 'emergency_type' in message.content:
            emergency_type = message.content['emergency_type']
            emergency_level = message.content.get('emergency_level', 'high')

            from .vector_clock import create_emergency
            self.emergency_context = create_emergency(emergency_type, emergency_level)

            logger.warning(f"Emergency context updated: {self.emergency_context}")

    def _handle_normal_message(self, message: CausalMessage) -> None:
        logger.info(f"Processing normal message: {message.content}")

    def send_emergency_alert(self, emergency_type: str, emergency_level: str, location: Optional[str] = None) -> CausalMessage:
        data = {
            'type': 'emergency_alert',
            'emergency_type': emergency_type,
            'emergency_level': emergency_level,
            'location': location,
            'sender': self.node_id,
            'timestamp': datetime.now().isoformat()
        }

        return self.send_message(data, "broadcast", is_emergency=True)

    def get_pending_count(self) -> int:
        return len(self.pending_messages)

    def has_emergency_pending(self) -> bool:
        return any(msg.is_emergency() for msg in self.pending_messages)

    def get_message_stats(self) -> Dict[str, int]:
        return {
            'pending': len(self.pending_messages),
            'processed': len(self.processed_messages),
            'emergency_pending': sum(1 for m in self.pending_messages if m.is_emergency()),
            'emergency_processed': sum(1 for m in self.processed_messages if m.is_emergency())
        }

    def clear_processed_messages(self) -> int:
        count = len(self.processed_messages)
        self.processed_messages.clear()
        logger.info(f"Cleared {count} processed messages")
        return count

def broadcast_emergency(handlers: List[MessageHandler], emergency_type: str, emergency_level: str, location: Optional[str] = None) -> List[CausalMessage]:
    if not handlers:
        return []

    sender = handlers[0]
    alert_msg = sender.send_emergency_alert(emergency_type, emergency_level, location)

    for h in handlers[1:]:
        h.receive_message(alert_msg)

    return [alert_msg]

def create_message_network(node_ids: List[str]) -> Dict[str, MessageHandler]:
    net = {}
    for node_id in node_ids:
        net[node_id] = MessageHandler(node_id)

    logger.info(f"Created message network with {len(net)} nodes")
    return net

if __name__ == "__main__":
    print("✅ Causal Message Implementation - File 3 Complete")

    handler1 = MessageHandler("node1")
    handler2 = MessageHandler("node2")

    msg = handler1.send_message("Hello from node1", "node2")
    handler2.receive_message(msg)
    print(f"Message delivered: {handler2.get_message_stats()}")

    emergency_msg = handler1.send_emergency_alert("fire", "critical", "Building A")
    handler2.receive_message(emergency_msg)
    print(f"Emergency delivered: {handler2.get_message_stats()}")

    print("   Causal messaging with emergency support ready!")
    print("   Foundation for distributed vector clock coordination")

