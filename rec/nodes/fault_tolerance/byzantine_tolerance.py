# 🛡️ Simple Byzantine Fault Tolerance - Student Friendly Implementation

import time
import random
from typing import Dict, List, Set, Optional
from uuid import uuid4
from dataclasses import dataclass
from collections import defaultdict

from rec.replication.core.vector_clock import VectorClock
from rec.util.log import LOG


@dataclass
class SimpleVote:
    """A simple vote from a node"""
    voter_id: str
    proposal_id: str
    vote: str  # "yes", "no", or "abstain"
    timestamp: float
    vector_clock: Dict[str, int]


@dataclass
class SimpleProposal:
    """A simple proposal that nodes can vote on"""
    proposal_id: str
    proposer_id: str
    content: str
    created_at: float
    votes: List[SimpleVote]
    status: str  # "pending", "accepted", "rejected"


class SimpleByzantineDetector:
    """Detects Byzantine (malicious/faulty) behavior in simple way"""
    
    def __init__(self, detector_id: str = None):
        self.detector_id = detector_id or f"byzantine_{uuid4().hex[:5]}"
        self.clock = VectorClock(self.detector_id)
        
        # Track suspicious behavior
        self.node_scores: Dict[str, float] = defaultdict(float)  # reputation scores
        self.suspicious_nodes: Set[str] = set()
        self.trusted_nodes: Set[str] = set()
        
        # Simple Byzantine detection rules
        self.max_reputation = 100.0
        self.min_reputation = 0.0
        self.suspicious_threshold = 30.0
        self.trusted_threshold = 80.0
        
        LOG.info(f"[ByzantineDetector] {self.detector_id} started")
    
    def register_node(self, node_id: str):
        """Register a new node with neutral reputation"""
        self.node_scores[node_id] = 50.0  # Start with neutral score
        LOG.info(f"[ByzantineDetector] Registered {node_id} with neutral reputation (50.0)")
    
    def report_good_behavior(self, node_id: str, reason: str = "good_action"):
        """Node did something good - increase reputation"""
        self.clock.tick()
        
        if node_id not in self.node_scores:
            self.register_node(node_id)
        
        # Increase reputation (but don't go above max)
        old_score = self.node_scores[node_id]
        self.node_scores[node_id] = min(self.max_reputation, old_score + 5.0)
        
        # Update trust status
        self._update_trust_status(node_id)
        
        LOG.info(f"[ByzantineDetector] {node_id} reputation: {old_score:.1f} -> {self.node_scores[node_id]:.1f} ({reason})")
    
    def report_bad_behavior(self, node_id: str, reason: str = "bad_action"):
        """Node did something suspicious - decrease reputation"""
        self.clock.tick()
        
        if node_id not in self.node_scores:
            self.register_node(node_id)
        
        # Decrease reputation (but don't go below min)
        old_score = self.node_scores[node_id]
        self.node_scores[node_id] = max(self.min_reputation, old_score - 10.0)
        
        # Update trust status
        self._update_trust_status(node_id)
        
        LOG.warning(f"[ByzantineDetector] {node_id} reputation: {old_score:.1f} -> {self.node_scores[node_id]:.1f} ({reason})")
    
    def _update_trust_status(self, node_id: str):
        """Update whether node is trusted or suspicious"""
        score = self.node_scores[node_id]
        
        # Remove from all sets first
        self.suspicious_nodes.discard(node_id)
        self.trusted_nodes.discard(node_id)
        
        # Add to appropriate set
        if score <= self.suspicious_threshold:
            self.suspicious_nodes.add(node_id)
            LOG.warning(f"[ByzantineDetector] {node_id} marked as SUSPICIOUS (score: {score:.1f})")
        elif score >= self.trusted_threshold:
            self.trusted_nodes.add(node_id)
            LOG.info(f"[ByzantineDetector] {node_id} marked as TRUSTED (score: {score:.1f})")
    
    def is_node_trusted(self, node_id: str) -> bool:
        """Check if node is trusted"""
        return node_id in self.trusted_nodes
    
    def is_node_suspicious(self, node_id: str) -> bool:
        """Check if node is suspicious"""
        return node_id in self.suspicious_nodes
    
    def get_node_reputation(self, node_id: str) -> float:
        """Get reputation score for node"""
        return self.node_scores.get(node_id, 50.0)
    
    def get_trusted_nodes(self) -> List[str]:
        """Get list of all trusted nodes"""
        return list(self.trusted_nodes)
    
    def get_suspicious_nodes(self) -> List[str]:
        """Get list of all suspicious nodes"""
        return list(self.suspicious_nodes)
    
    def get_status(self) -> Dict:
        """Get detector status"""
        return {
            "detector_id": self.detector_id,
            "total_nodes": len(self.node_scores),
            "trusted_nodes": len(self.trusted_nodes),
            "suspicious_nodes": len(self.suspicious_nodes),
            "neutral_nodes": len(self.node_scores) - len(self.trusted_nodes) - len(self.suspicious_nodes),
            "vector_clock": self.clock.clock
        }


class SimpleConsensusManager:
    """Simple consensus system to handle Byzantine nodes"""
    
    def __init__(self, manager_id: str = None):
        self.manager_id = manager_id or f"consensus_{uuid4().hex[:5]}"
        self.clock = VectorClock(self.manager_id)
        
        # Consensus components
        self.byzantine_detector = SimpleByzantineDetector(f"byz_{uuid4().hex[:5]}")
        
        # Proposal management
        self.proposals: Dict[str, SimpleProposal] = {}
        self.active_nodes: Set[str] = set()
        
        # Simple consensus rules
        self.min_votes_needed = 3  # Need at least 3 votes
        self.approval_threshold = 0.6  # Need 60% approval
        
        LOG.info(f"[ConsensusManager] {self.manager_id} started")
    
    def register_node(self, node_id: str):
        """Register node for consensus"""
        self.active_nodes.add(node_id)
        self.byzantine_detector.register_node(node_id)
        LOG.info(f"[ConsensusManager] {node_id} joined consensus")
    
    def create_proposal(self, proposer_id: str, content: str) -> str:
        """Create a new proposal for voting"""
        self.clock.tick()
        
        proposal_id = f"prop_{uuid4().hex[:8]}"
        proposal = SimpleProposal(
            proposal_id=proposal_id,
            proposer_id=proposer_id,
            content=content,
            created_at=time.time(),
            votes=[],
            status="pending"
        )
        
        self.proposals[proposal_id] = proposal
        LOG.info(f"[ConsensusManager] New proposal {proposal_id}: {content}")
        
        return proposal_id
    
    def submit_vote(self, voter_id: str, proposal_id: str, vote: str) -> bool:
        """Submit a vote for a proposal"""
        self.clock.tick()
        
        if proposal_id not in self.proposals:
            LOG.error(f"[ConsensusManager] Unknown proposal {proposal_id}")
            return False
        
        proposal = self.proposals[proposal_id]
        
        if proposal.status != "pending":
            LOG.warning(f"[ConsensusManager] Proposal {proposal_id} is no longer pending")
            return False
        
        # Check if node already voted
        for existing_vote in proposal.votes:
            if existing_vote.voter_id == voter_id:
                LOG.warning(f"[ConsensusManager] {voter_id} already voted on {proposal_id}")
                return False
        
        # Create vote
        new_vote = SimpleVote(
            voter_id=voter_id,
            proposal_id=proposal_id,
            vote=vote,
            timestamp=time.time(),
            vector_clock=self.clock.clock.copy()
        )
        
        proposal.votes.append(new_vote)
        
        # Check if we can make a decision
        self._check_consensus(proposal_id)
        
        LOG.info(f"[ConsensusManager] {voter_id} voted '{vote}' on {proposal_id}")
        return True
    
    def _check_consensus(self, proposal_id: str):
        """Check if proposal has reached consensus"""
        proposal = self.proposals[proposal_id]
        
        if len(proposal.votes) < self.min_votes_needed:
            return  # Not enough votes yet
        
        # Count votes from trusted nodes only
        trusted_yes_votes = 0
        trusted_no_votes = 0
        total_trusted_votes = 0
        
        for vote in proposal.votes:
            if self.byzantine_detector.is_node_trusted(vote.voter_id):
                total_trusted_votes += 1
                if vote.vote == "yes":
                    trusted_yes_votes += 1
                elif vote.vote == "no":
                    trusted_no_votes += 1
        
        # If no trusted votes, use all votes but be careful
        if total_trusted_votes == 0:
            yes_votes = sum(1 for vote in proposal.votes if vote.vote == "yes")
            no_votes = sum(1 for vote in proposal.votes if vote.vote == "no")
            total_votes = yes_votes + no_votes
            
            if total_votes > 0:
                approval_rate = yes_votes / total_votes
            else:
                approval_rate = 0.0
        else:
            # Use only trusted votes
            if total_trusted_votes > 0:
                approval_rate = trusted_yes_votes / total_trusted_votes
            else:
                approval_rate = 0.0
        
        # Make decision
        if approval_rate >= self.approval_threshold:
            proposal.status = "accepted"
            LOG.info(f"[ConsensusManager] Proposal {proposal_id} ACCEPTED (approval: {approval_rate:.1%})")
            
            # Reward voters who voted correctly
            for vote in proposal.votes:
                if vote.vote == "yes":
                    self.byzantine_detector.report_good_behavior(vote.voter_id, "voted_with_majority")
        
        elif total_trusted_votes >= self.min_votes_needed or len(proposal.votes) >= len(self.active_nodes):
            proposal.status = "rejected"
            LOG.info(f"[ConsensusManager] Proposal {proposal_id} REJECTED (approval: {approval_rate:.1%})")
            
            # Reward voters who voted correctly
            for vote in proposal.votes:
                if vote.vote == "no":
                    self.byzantine_detector.report_good_behavior(vote.voter_id, "voted_with_majority")
    
    def detect_byzantine_behavior(self, node_id: str, behavior_type: str):
        """Report Byzantine behavior"""
        reasons = {
            "double_vote": "attempted to vote twice",
            "invalid_proposal": "proposed invalid content",
            "late_vote": "voted after consensus reached",
            "inconsistent_clock": "provided inconsistent vector clock"
        }
        
        reason = reasons.get(behavior_type, behavior_type)
        self.byzantine_detector.report_bad_behavior(node_id, reason)
        
        LOG.warning(f"[ConsensusManager] Byzantine behavior detected: {node_id} - {reason}")
    
    def get_proposal_status(self, proposal_id: str) -> Optional[Dict]:
        """Get status of a proposal"""
        if proposal_id not in self.proposals:
            return None
        
        proposal = self.proposals[proposal_id]
        return {
            "proposal_id": proposal.proposal_id,
            "proposer": proposal.proposer_id,
            "content": proposal.content,
            "status": proposal.status,
            "total_votes": len(proposal.votes),
            "yes_votes": sum(1 for vote in proposal.votes if vote.vote == "yes"),
            "no_votes": sum(1 for vote in proposal.votes if vote.vote == "no")
        }
    
    def get_consensus_status(self) -> Dict:
        """Get overall consensus system status"""
        return {
            "manager_id": self.manager_id,
            "active_nodes": len(self.active_nodes),
            "total_proposals": len(self.proposals),
            "pending_proposals": sum(1 for p in self.proposals.values() if p.status == "pending"),
            "accepted_proposals": sum(1 for p in self.proposals.values() if p.status == "accepted"),
            "rejected_proposals": sum(1 for p in self.proposals.values() if p.status == "rejected"),
            "byzantine_status": self.byzantine_detector.get_status(),
            "vector_clock": self.clock.clock
        }


def demo_byzantine_fault_tolerance():
    """Simple demo of Byzantine fault tolerance"""
    print("🛡️ DEMO: Byzantine Fault Tolerance")
    print("=" * 40)
    
    # Create consensus manager
    consensus = SimpleConsensusManager("demo_consensus")
    
    # Register nodes (some will be Byzantine)
    nodes = ["alice", "bob", "charlie", "dave", "eve"]  # eve will be Byzantine
    for node in nodes:
        consensus.register_node(node)
    
    print(f"\n1. Registered {len(nodes)} nodes in consensus")
    
    # Create a proposal
    proposal_id = consensus.create_proposal("alice", "Add new emergency protocol")
    print(f"\n2. Alice proposed: {consensus.get_proposal_status(proposal_id)['content']}")
    
    # Normal nodes vote honestly
    print("\n3. Honest nodes voting...")
    consensus.submit_vote("alice", proposal_id, "yes")
    consensus.submit_vote("bob", proposal_id, "yes") 
    consensus.submit_vote("charlie", proposal_id, "no")
    consensus.submit_vote("dave", proposal_id, "yes")
    
    # Eve tries Byzantine behavior
    print("\n4. Eve attempting Byzantine behavior...")
    # Try to vote twice
    consensus.submit_vote("eve", proposal_id, "yes")
    consensus.submit_vote("eve", proposal_id, "no")  # Should be rejected
    
    # Report Byzantine behavior
    consensus.detect_byzantine_behavior("eve", "double_vote")
    
    print("\n5. Final results:")
    proposal_status = consensus.get_proposal_status(proposal_id)
    print(f"   Proposal status: {proposal_status['status']}")
    print(f"   Total votes: {proposal_status['total_votes']}")
    print(f"   Yes: {proposal_status['yes_votes']}, No: {proposal_status['no_votes']}")
    
    consensus_status = consensus.get_consensus_status()
    byz_status = consensus_status['byzantine_status']
    print(f"   Trusted nodes: {byz_status['trusted_nodes']}")
    print(f"   Suspicious nodes: {byz_status['suspicious_nodes']}")
    
    print("\n🎉 Byzantine fault tolerance demo complete!")


if __name__ == "__main__":
    demo_byzantine_fault_tolerance()
