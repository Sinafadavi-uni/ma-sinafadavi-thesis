# Causal Message Handling
# This handles sending and receiving messages with vector clocks
# Ensures messages are processed in the right order

from typing import Dict, List, Any
from uuid import UUID
from dataclasses import dataclass
from datetime import datetime

from .vector_clock import VectorClock, EmergencyContext


# Simple message class that includes timing information
@dataclass
class CausalMessage:
    content: Any  # the actual message data
    sender_id: UUID  # who sent it
    vector_clock: Dict  # timing info from sender
    message_type: str = "normal"  # can be "normal", "emergency", etc.
    priority: int = 1  # higher numbers = higher priority
    
    def is_emergency(self):
        return self.message_type == "emergency"


# Handles message ordering using vector clocks
class MessageHandler:
    def __init__(self, node_id, capabilities):
        self.node_id = node_id
        self.capabilities = capabilities
        self.vector_clock = VectorClock(node_id)
        self.pending_messages = []  # messages waiting to be processed
        self.processed_messages = []  # messages we've already handled
        
    def send_message(self, content, recipient_id, is_emergency=False):
        # Prepare a message for sending
        
        # Update our clock before sending
        self.vector_clock.tick()
        
        # Create the message
        message = CausalMessage(
            content=content,
            sender_id=self.node_id,
            vector_clock=self.vector_clock.clock.copy(),
            message_type="emergency" if is_emergency else "normal",
            priority=5 if is_emergency else 1
        )
        
        return message
    
    def receive_message(self, message):
        # Receive a message and decide when to process it
        
        # Update our vector clock with sender's timing
        self.vector_clock.update(message.vector_clock)
        
        # Add to pending messages
        self.pending_messages.append(message)
        
        # Try to process messages in order
        self._process_pending_messages()
    
    def _process_pending_messages(self):
        # Process messages in causal order
        # Emergency messages get priority
        
        # Sort by priority first, then by causal order
        self.pending_messages.sort(key=lambda msg: (-msg.priority, msg.vector_clock.get(msg.sender_id, 0)))
        
        processed_this_round = []
        
        for i, message in enumerate(self.pending_messages):
            if self._can_process_message(message):
                # Process this message
                self._handle_message_content(message)
                self.processed_messages.append(message)
                processed_this_round.append(i)
        
        # Remove processed messages (in reverse order to not mess up indices)
        for i in reversed(processed_this_round):
            del self.pending_messages[i]
    
    def _can_process_message(self, message):
        # Check if we can process this message now
        # Rule: we can process it if we've seen all messages that happened before it
        
        for sender_id, timestamp in message.vector_clock.items():
            if sender_id == message.sender_id:
                continue  # skip the sender's own timestamp
                
            our_timestamp = self.vector_clock.clock.get(sender_id, 0)
            if our_timestamp < timestamp:
                # We haven't seen all messages from this sender yet
                return False
        
        return True
    
    def _handle_message_content(self, message):
        # Actually process the message content
        # This is where the real work happens
        
        print(f"Processing message from {message.sender_id}: {message.content}")
        
        if message.is_emergency():
            print(f"EMERGENCY MESSAGE: {message.content}")
            # Handle emergency-specific logic here
            
    def get_pending_count(self):
        # How many messages are waiting to be processed
        return len(self.pending_messages)
    
    def has_emergency_pending(self):
        # Check if any pending messages are emergencies
        return any(msg.is_emergency() for msg in self.pending_messages)


# Simple conflict resolver for when nodes disagree
class ConflictResolver:
    def __init__(self):
        self.resolution_strategy = "capability_based"  # or "timestamp_based"
    
    def resolve_conflict(self, conflicting_updates, emergency_context=None):
        # Resolve conflicts between different node updates
        # Returns the "winning" update
        
        if self.resolution_strategy == "capability_based":
            return self._resolve_by_capability(conflicting_updates, emergency_context)
        else:
            return self._resolve_by_timestamp(conflicting_updates)
    
    def _resolve_by_capability(self, updates, emergency_context):
        # Choose the update from the most capable node
        
        if not updates:
            return None
            
        if len(updates) == 1:
            return updates[0]
        
        # Score each update based on sender capability
        best_update = updates[0]
        best_score = 0
        
        for update in updates:
            # Simple scoring - in real implementation, we'd look up actual capabilities
            score = hash(str(update.sender_id)) % 100  # fake capability score
            
            if emergency_context and emergency_context.is_critical():
                score += 50  # boost for emergency situations
                
            if score > best_score:
                best_score = score
                best_update = update
        
        return best_update
    
    def _resolve_by_timestamp(self, updates):
        # Choose the update with the latest timestamp
        
        if not updates:
            return None
            
        # Find the most recent update
        latest_update = max(updates, key=lambda u: max(u.vector_clock.values()))
        return latest_update


# Helper function to create and send emergency alerts
def send_emergency_alert(sender_handler, emergency_type, location, recipients):
    """Send an emergency alert to multiple recipients"""
    
    alert_content = {
        'type': 'emergency_alert',
        'emergency_type': emergency_type,
        'location': location,
        'timestamp': datetime.now().isoformat(),
        'sender': sender_handler.node_id
    }
    
    messages_sent = []
    for recipient in recipients:
        message = sender_handler.send_message(
            content=alert_content,
            recipient_id=recipient,
            is_emergency=True
        )
        messages_sent.append(message)
    
    return messages_sent
