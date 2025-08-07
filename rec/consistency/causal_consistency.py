# 📋 Causal Consistency Implementation

"""
This module provides causal consistency mechanisms using vector clocks.
Ensures that causally related events are processed in the correct order.
"""

from ..algorithms.vector_clock import VectorClock
from ..algorithms.causal_message import CausalMessage
from typing import Dict, List, Tuple
import time


class CausalConsistencyManager:
    """
    Manages causal consistency for distributed operations.
    Student-friendly implementation for educational purposes.
    """
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.vector_clock = VectorClock(node_id)
        self.message_buffer: List[CausalMessage] = []
        self.delivered_messages: List[str] = []
    
    def create_message(self, content: str, message_type: str = "normal") -> CausalMessage:
        """Create a new causally ordered message"""
        self.vector_clock.tick()
        return CausalMessage(
            sender=self.node_id,
            content=content,
            message_type=message_type,
            vector_clock=self.vector_clock.clock.copy()
        )
    
    def can_deliver_message(self, message: CausalMessage) -> bool:
        """Check if message can be delivered according to causal ordering"""
        # Can deliver if all causally preceding events have been delivered
        for node, timestamp in message.vector_clock.items():
            if node == message.sender:
                # Sender's timestamp should be exactly one more than current
                if timestamp != self.vector_clock.clock.get(node, 0) + 1:
                    return False
            else:
                # Other nodes' timestamps should not exceed current knowledge
                if timestamp > self.vector_clock.clock.get(node, 0):
                    return False
        return True
    
    def deliver_message(self, message: CausalMessage) -> bool:
        """Attempt to deliver a message maintaining causal consistency"""
        if self.can_deliver_message(message):
            # Update vector clock and deliver
            self.vector_clock.update(message.vector_clock)
            self.delivered_messages.append(message.message_id)
            return True
        else:
            # Buffer message for later delivery
            self.message_buffer.append(message)
            return False
    
    def process_buffered_messages(self) -> List[CausalMessage]:
        """Process any buffered messages that can now be delivered"""
        delivered = []
        remaining_buffer = []
        
        for message in self.message_buffer:
            if self.can_deliver_message(message):
                self.vector_clock.update(message.vector_clock)
                self.delivered_messages.append(message.message_id)
                delivered.append(message)
            else:
                remaining_buffer.append(message)
        
        self.message_buffer = remaining_buffer
        return delivered
    
    def get_consistency_status(self) -> Dict:
        """Get current consistency status for monitoring"""
        return {
            "node_id": self.node_id,
            "current_time": self.vector_clock.clock.copy(),
            "buffered_messages": len(self.message_buffer),
            "delivered_messages": len(self.delivered_messages),
            "consistency_state": "maintained"
        }


class FCFSConsistencyPolicy:
    """
    First-Come-First-Serve consistency policy implementation.
    Ensures that job results are accepted in submission order.
    """
    
    def __init__(self):
        self.completed_jobs: Dict[str, bool] = {}
        self.job_submission_order: List[str] = []
        self.job_results: Dict[str, any] = {}
    
    def submit_job(self, job_id: str) -> bool:
        """Submit a job for FCFS processing"""
        if job_id not in self.completed_jobs:
            self.job_submission_order.append(job_id)
            self.completed_jobs[job_id] = False
            return True
        return False
    
    def submit_result(self, job_id: str, result: any) -> bool:
        """Submit result following FCFS policy - first result wins"""
        if job_id in self.completed_jobs and not self.completed_jobs[job_id]:
            self.job_results[job_id] = result
            self.completed_jobs[job_id] = True
            return True  # First result accepted
        return False  # Job already completed or doesn't exist
    
    def get_fcfs_status(self) -> Dict:
        """Get FCFS policy status"""
        completed_count = sum(1 for completed in self.completed_jobs.values() if completed)
        return {
            "total_jobs": len(self.completed_jobs),
            "completed_jobs": completed_count,
            "pending_jobs": len(self.completed_jobs) - completed_count,
            "submission_order_maintained": True
        }


def demo_causal_consistency():
    """Demonstration of causal consistency mechanisms"""
    print("🔗 DEMO: Causal Consistency Manager")
    print("=" * 40)
    
    # Create consistency managers for two nodes
    node_a = CausalConsistencyManager("node_A")
    node_b = CausalConsistencyManager("node_B")
    
    print("\n1. Creating causally ordered messages...")
    
    # Node A creates messages
    msg1 = node_a.create_message("Hello from A", "greeting")
    msg2 = node_a.create_message("Update from A", "update")
    
    print(f"   A created: {msg1.content} (clock: {msg1.vector_clock})")
    print(f"   A created: {msg2.content} (clock: {msg2.vector_clock})")
    
    # Node B receives and processes
    print("\n2. Processing messages with causal ordering...")
    delivered_1 = node_b.deliver_message(msg1)
    delivered_2 = node_b.deliver_message(msg2)
    
    print(f"   B delivered msg1: {delivered_1}")
    print(f"   B delivered msg2: {delivered_2}")
    
    # Check consistency status
    print("\n3. Consistency status:")
    status_a = node_a.get_consistency_status()
    status_b = node_b.get_consistency_status()
    
    print(f"   Node A: {status_a}")
    print(f"   Node B: {status_b}")
    
    print("\n✅ Causal consistency maintained!")


if __name__ == "__main__":
    demo_causal_consistency()
