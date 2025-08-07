# Causal Messaging System
# Manages delivery and processing of messages with vector clock logic
# Helps us respect the causal order of events (even under messy conditions)

from typing import Dict, List, Any
from uuid import UUID
from dataclasses import dataclass
from datetime import datetime

from .vector_clock import VectorClock, EmergencyContext


# Lightweight message wrapper with a clock attached
@dataclass
class CausalMessage:
    content: Any  # Payload – could be anything
    sender_id: UUID
    vector_clock: Dict  # Copy of sender’s clock when they sent it
    message_type: str = "normal"  # default to normal messages
    priority: int = 1  # higher is more urgent
    
    def is_emergency(self):
        return self.message_type == "emergency"


# Core message manager – handles ordering, storage, and decision-making
class MessageHandler:
    def __init__(self, node_id, capabilities):
        self.node_id = node_id
        self.capabilities = capabilities
        self.vector_clock = VectorClock(node_id)
        self.pending_messages = []      # holding area for not-yet-ready messages
        self.processed_messages = []    # archive of what's been handled
        
    def send_message(self, content, recipient_id, is_emergency=False):
        # We're sending a new message – bump our clock first
        self.vector_clock.tick()
        
        # Wrap up everything we need
        return CausalMessage(
            content=content,
            sender_id=self.node_id,
            vector_clock=self.vector_clock.clock.copy(),  # send a snapshot
            message_type="emergency" if is_emergency else "normal",
            priority=5 if is_emergency else 1
        )
    
    def receive_message(self, message):
        # New message comes in – update our own clock view
        self.vector_clock.update(message.vector_clock)
        
        self.pending_messages.append(message)
        
        # Try to handle anything we can
        self._process_pending_messages()
    
    def _process_pending_messages(self):
        # Try to deliver messages in a reasonable order
        # Emergency first, then earliest in logical time
        
        self.pending_messages.sort(
            key=lambda msg: (-msg.priority, msg.vector_clock.get(msg.sender_id, 0))
        )
        
        indices_to_remove = []
        
        for idx, msg in enumerate(self.pending_messages):
            if self._can_process_message(msg):
                self._handle_message_content(msg)
                self.processed_messages.append(msg)
                indices_to_remove.append(idx)
        
        # Carefully remove them without breaking the loop
        for i in reversed(indices_to_remove):
            del self.pending_messages[i]
    
    def _can_process_message(self, msg):
        # Have we seen all the stuff that came before this message?
        for peer_id, time in msg.vector_clock.items():
            if peer_id == msg.sender_id:
                continue  # skip the sender's own counter
            
            if self.vector_clock.clock.get(peer_id, 0) < time:
                return False
        
        return True
    
    def _handle_message_content(self, msg):
        # Here’s where we’d normally do something useful with the message
        print(f"Processing message from {msg.sender_id}: {msg.content}")
        
        if msg.is_emergency():
            print(f"*** EMERGENCY ***: {msg.content}")
            # Possibly kick off an alert, siren, etc.
    
    def get_pending_count(self):
        return len(self.pending_messages)
    
    def has_emergency_pending(self):
        return any(m.is_emergency() for m in self.pending_messages)


# When nodes disagree, this helps decide which update wins
class ConflictResolver:
    def __init__(self):
        self.resolution_strategy = "capability_based"  # fallback: "timestamp_based"
    
    def resolve_conflict(self, updates, emergency_context=None):
        if self.resolution_strategy == "capability_based":
            return self._resolve_by_capability(updates, emergency_context)
        return self._resolve_by_timestamp(updates)
    
    def _resolve_by_capability(self, updates, emergency_context):
        if not updates:
            return None
        if len(updates) == 1:
            return updates[0]
        
        best_choice = updates[0]
        top_score = 0
        
        for update in updates:
            # NOTE: This is just a mock scoring – replace with real logic later
            fake_score = hash(str(update.sender_id)) % 100
            
            if emergency_context and emergency_context.is_critical():
                fake_score += 50  # emergency bump
            
            if fake_score > top_score:
                top_score = fake_score
                best_choice = update
        
        return best_choice
    
    def _resolve_by_timestamp(self, updates):
        if not updates:
            return None
        return max(updates, key=lambda u: max(u.vector_clock.values()))


# Helper to fire off an emergency to multiple recipients
def send_emergency_alert(sender_handler, emergency_type, location, recipients):
    """Dispatch an emergency message to multiple nodes"""
    
    payload = {
        'type': 'emergency_alert',
        'emergency_type': emergency_type,
        'location': location,
        'timestamp': datetime.now().isoformat(),
        'sender': sender_handler.node_id
    }
    
    sent_messages = []
    for recipient_id in recipients:
        msg = sender_handler.send_message(
            content=payload,
            recipient_id=recipient_id,
            is_emergency=True
        )
        sent_messages.append(msg)
    
    return sent_messages
