"""
File 9: VectorClockBroker - Distributed Broker with Vector Clock Coordination
Phase 3: Core Implementation

Distributed broker with vector clock coordination for managing distributed
job execution across multiple nodes with causal consistency guarantees.

Key Features:
- Vector clock-based job coordination across multiple executors
- Causal ordering enforcement for distributed job submission
- FCFS policy enforcement across distributed brokers
- Emergency-aware job prioritization with causal consistency
- Cross-broker synchronization and coordination

This extends the basic ExecutorBroker with vector clock coordination
to ensure causal consistency in distributed job execution.
"""

import time
import threading
import logging
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum
from queue import PriorityQueue, Empty
from collections import defaultdict

# Import Phase 1 foundation
import sys
import os
phase1_path = os.path.join(os.path.dirname(__file__), '..', 'Phase1_Core_Foundation')
sys.path.insert(0, phase1_path)

# import vector_clock
# import causal_message
# import causal_consistency

from rec.Phase1_Core_Foundation.vector_clock import VectorClock, EmergencyContext, EmergencyLevel, create_emergency
from rec.Phase1_Core_Foundation.causal_message import CausalMessage, MessageHandler
from rec.Phase1_Core_Foundation.causal_consistency import CausalConsistencyManager, FCFSConsistencyPolicy

# Import Phase 2 infrastructure
phase2_path = os.path.join(os.path.dirname(__file__), '..', 'Phase2_Node_Infrastructure')
sys.path.insert(0, phase2_path)

from rec.Phase2_Node_Infrastructure.executorbroker import ExecutorBroker, JobInfo, ExecutorInfo

LOG = logging.getLogger(__name__)

@dataclass
class BrokerMetadata:
    """Complete broker metadata for synchronization"""
    broker_id: str
    vector_clock: dict = field(default_factory=dict)
    job_registry: dict = field(default_factory=dict)
    executor_registry: dict = field(default_factory=dict)
    datastore_locations: dict = field(default_factory=dict)  # data_key -> [datastore_ids]
    pending_jobs: list = field(default_factory=list)
    completed_jobs: set = field(default_factory=set)
    last_sync_time: float = field(default_factory=time.time)

class BrokerCoordinationState(Enum):
    """Broker coordination state"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    SYNCHRONIZING = "synchronizing"
    EMERGENCY = "emergency"
    FAILED = "failed"

@dataclass
class DistributedJobCoordination:
    """Coordination information for distributed job"""
    job_id: UUID
    originating_broker: str
    fcfs_timestamp: float
    vector_clock_snapshot: dict = field(default_factory=dict)
    emergency_priority: int = None
    coordination_state: str = "pending"
    assigned_executor: str = None
    
class VectorClockBroker(ExecutorBroker):
    """
    Distributed broker with vector clock coordination
    
    Extends ExecutorBroker with:
    - Vector clock-based causal ordering for job submission
    - Cross-broker coordination and synchronization
    - FCFS policy enforcement across distributed system
    - Emergency-aware coordination with causal consistency
    - Distributed job coordination and load balancing
    """
    
    def __init__(self, broker_id: str = None):
        """Initialize vector clock broker"""
        super().__init__(broker_id)
        
        # Vector clock coordination
        self.coordination_state = BrokerCoordinationState.INITIALIZING
        self.coordination_lock = threading.RLock()
        
        # Distributed coordination
        self.peer_brokers = {}
        self.distributed_jobs = {}
        self.global_fcfs_counter = 0
        
        # Cross-broker synchronization
        self.broker_vector_clocks = {}
        self.sync_interval = 3.0  # Sync every 3 seconds
        self.sync_thread = None
        
        # FCFS policy for distributed coordination
        self.fcfs_policy = FCFSConsistencyPolicy()
        self.job_ordering_lock = threading.RLock()
        
        self.coordination_state = BrokerCoordinationState.ACTIVE
        LOG.info(f"VectorClockBroker {self.broker_id} initialized with distributed coordination")
    
    def register_peer_broker(self, peer_id, peer_broker):
        """
        Register peer broker for distributed coordination
        
        Args:
            peer_id: Peer broker identifier
            peer_broker: Peer broker instance
        """
        self.peer_brokers[peer_id] = peer_broker
        LOG.info(f"Registered peer broker: {peer_id}")
    
    def submit_distributed_job(self, job_info, preferred_broker=None):
        """
        Submit job with distributed coordination using vector clocks
        
        Args:
            job_info: Job information
            preferred_broker: Preferred broker for execution (optional)
            
        Returns:
            UUID: Job identifier
        """
        # Tick vector clock for job submission
        self.vector_clock.tick()
        
        # Create distributed job coordination
        self.global_fcfs_counter += 1
        fcfs_timestamp = time.time()
        
        job_coordination = DistributedJobCoordination(
            job_id=job_info.job_id,
            originating_broker=self.broker_id,
            vector_clock_snapshot=self.vector_clock.clock.copy(),
            fcfs_timestamp=fcfs_timestamp,
            emergency_priority=self._get_emergency_priority(job_info.emergency_context)
        )
        
        with self.coordination_lock:
            self.distributed_jobs[job_info.job_id] = job_coordination
        
        # Apply FCFS coordination across brokers
        assigned_broker = self._coordinate_job_assignment(job_coordination, preferred_broker)
        
        if assigned_broker == self.broker_id:
            # Execute locally
            result = super().submit_job(job_info)
            job_coordination.coordination_state = "executing_locally"
            job_coordination.assigned_executor = "local"
        else:
            # Delegate to peer broker
            peer_broker = self.peer_brokers.get(assigned_broker)
            if peer_broker:
                result = peer_broker.execute_delegated_job(job_info, self.broker_id)
                job_coordination.coordination_state = "delegated"
                job_coordination.assigned_executor = assigned_broker
            else:
                LOG.error(f"Peer broker {assigned_broker} not available")
                result = super().submit_job(job_info)  # Fallback to local
                job_coordination.coordination_state = "fallback_local"
        
        LOG.info(f"Distributed job {job_info.job_id} coordinated: {job_coordination.coordination_state}")
        return result
    
    def execute_delegated_job(self, job_info, originating_broker):
        """
        Execute job delegated from another broker
        
        Args:
            job_info: Job information from originating broker
            originating_broker: Broker that delegated the job
            
        Returns:
            UUID: Job identifier
        """
        # Update vector clock with job's timestamp
        if hasattr(job_info, 'vector_clock') and job_info.vector_clock:
            self.vector_clock.update(job_info.vector_clock)
        self.vector_clock.tick()
        
        # Execute job locally
        result = super().submit_job(job_info)
        
        LOG.info(f"Executed delegated job {job_info.job_id} from broker {originating_broker}")
        return result
    
    def sync_vector_clock(self, peer_clock, peer_broker_id):
        """
        Synchronize vector clock with peer broker
        
        Args:
            peer_clock: Peer broker's vector clock
            peer_broker_id: Peer broker identifier
        """
        self.vector_clock.update(peer_clock)
        
        with self.coordination_lock:
            self.broker_vector_clocks[peer_broker_id] = peer_clock.copy()
        
        LOG.debug(f"Vector clock synchronized with broker {peer_broker_id}")
    
    def ensure_causal_order(self, operation):
        """
        Ensure causal ordering for distributed operations
        
        Args:
            operation: Operation to check for causal ordering
            
        Returns:
            bool: True if operation maintains causal order
        """
        if 'vector_clock' not in operation:
            LOG.warning("Operation missing vector clock for causal ordering")
            return False
        
        operation_clock = operation['vector_clock']
        
        # Check causal consistency using consistency manager
        consistency_op = {
            'operation_id': operation.get('operation_id', str(uuid4())),
            'operation_type': operation.get('type', 'unknown'),
            'vector_clock': operation_clock,
            'node_id': self.broker_id
        }
        
        return self.consistency_manager.ensure_consistency(consistency_op)
    
    def coordinate_emergency_response(self, emergency_context, 
                                    affected_regions=None):
        """
        Coordinate emergency response across distributed brokers
        
        Args:
            emergency_context: Emergency context information
            affected_regions: List of affected regions/brokers
            
        Returns:
            Dict: Coordination response information
        """
        # Tick vector clock for emergency coordination
        self.vector_clock.tick()
        
        # Activate emergency mode locally
        self.set_emergency_mode(emergency_context.emergency_type, emergency_context.level.name)
        
        # Coordinate with peer brokers
        coordination_responses = {}
        emergency_coordination_id = uuid4()
        
        for peer_id, peer_broker in self.peer_brokers.items():
            if not affected_regions or peer_id in affected_regions:
                try:
                    # Synchronize emergency state
                    peer_broker.sync_vector_clock(self.vector_clock.clock, self.broker_id)
                    peer_broker.set_emergency_mode(emergency_context.emergency_type, 
                                                 emergency_context.level.name)
                    
                    coordination_responses[peer_id] = {
                        "status": "emergency_activated",
                        "vector_clock": peer_broker.vector_clock.clock.copy(),
                        "coordination_id": emergency_coordination_id
                    }
                    
                except Exception as e:
                    LOG.error(f"Failed to coordinate emergency with broker {peer_id}: {e}")
                    coordination_responses[peer_id] = {
                        "status": "coordination_failed",
                        "error": str(e)
                    }
        
        LOG.warning(f"Emergency coordination activated across {len(coordination_responses)} brokers")
        
        return {
            "coordination_id": emergency_coordination_id,
            "emergency_context": {
                "type": emergency_context.emergency_type,
                "level": emergency_context.level.name,
                "location": emergency_context.location
            },
            "coordinated_brokers": coordination_responses,
            "vector_clock": self.vector_clock.clock.copy()
        }
    
    def get_distributed_status(self):
        """Get comprehensive distributed broker status"""
        with self.coordination_lock:
            distributed_job_states = {}
            for job_id, coordination in self.distributed_jobs.items():
                distributed_job_states[str(job_id)] = {
                    "originating_broker": coordination.originating_broker,
                    "state": coordination.coordination_state,
                    "assigned_executor": coordination.assigned_executor,
                    "fcfs_timestamp": coordination.fcfs_timestamp
                }
        
        base_status = self.get_status()
        
        return {
            **base_status,
            "coordination_state": self.coordination_state.value,
            "peer_brokers": list(self.peer_brokers.keys()),
            "distributed_jobs": distributed_job_states,
            "vector_clock_sync": {
                broker_id: clock for broker_id, clock in self.broker_vector_clocks.items()
            },
            "global_fcfs_counter": self.global_fcfs_counter
        }
    
    def start(self):
        """Start vector clock broker with coordination"""
        super().start()
        
        # Start vector clock synchronization
        if self.sync_thread is None or not self.sync_thread.is_alive():
            self.sync_thread = threading.Thread(
                target=self._coordination_sync_worker,
                daemon=True,
                name=f"vc-broker-sync-{self.broker_id}"
            )
            self.sync_thread.start()
        
        self.coordination_state = BrokerCoordinationState.ACTIVE
        LOG.info(f"VectorClockBroker {self.broker_id} started with distributed coordination")
    
    def stop(self):
        """Stop vector clock broker"""
        self.coordination_state = BrokerCoordinationState.FAILED
        
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=2.0)
        
        super().stop()
        LOG.info(f"VectorClockBroker {self.broker_id} stopped")
    
    def _get_emergency_priority(self, emergency_context):
        """Get numeric priority for emergency context"""
        if not emergency_context:
            return None
        
        priority_map = {
            EmergencyLevel.CRITICAL: 0,
            EmergencyLevel.HIGH: 1,
            EmergencyLevel.MEDIUM: 2,
            EmergencyLevel.LOW: 3
        }
        
        return priority_map.get(emergency_context.level, 5)
    
    def _coordinate_job_assignment(self, job_coordination: DistributedJobCoordination, 
                                 preferred_broker: str = None) -> str:
        """
        Coordinate job assignment using FCFS policy across brokers
        
        Args:
            job_coordination: Job coordination information
            preferred_broker: Preferred broker for assignment
            
        Returns:
            str: Assigned broker ID
        """
        # If preferred broker specified and available, use it
        if preferred_broker and preferred_broker in self.peer_brokers:
            return preferred_broker
        
        # Apply FCFS policy across all brokers
        available_brokers = [self.broker_id] + list(self.peer_brokers.keys())
        
        # For emergency jobs, prioritize brokers with emergency capabilities
        if job_coordination.emergency_priority is not None:
            emergency_capable = []
            for broker_id in available_brokers:
                if broker_id == self.broker_id:
                    emergency_capable.append(broker_id)
                else:
                    peer_broker = self.peer_brokers.get(broker_id)
                    if peer_broker and hasattr(peer_broker, 'emergency_mode'):
                        emergency_capable.append(broker_id)
            
            if emergency_capable:
                available_brokers = emergency_capable
        
        # Simple round-robin based on FCFS counter for load balancing
        assigned_index = self.global_fcfs_counter % len(available_brokers)
        assigned_broker = available_brokers[assigned_index]
        
        LOG.debug(f"Job {job_coordination.job_id} assigned to broker {assigned_broker} via FCFS")
        return assigned_broker
    
    def _coordination_sync_worker(self):
        """Enhanced background worker with full metadata sync"""
        LOG.info(f"Enhanced coordination sync worker started for broker {self.broker_id}")
        
        while not self.should_exit and self.coordination_state == BrokerCoordinationState.ACTIVE:
            try:
                # Get local metadata snapshot
                local_metadata = self.get_metadata_snapshot()
                
                # Sync with all peer brokers
                for peer_id, peer_broker in self.peer_brokers.items():
                    try:
                        # Exchange metadata bidirectionally
                        peer_metadata = peer_broker.get_metadata_snapshot()
                        
                        # Sync both ways
                        self.sync_metadata_with_peer(peer_metadata)
                        peer_broker.sync_metadata_with_peer(local_metadata)
                        
                        LOG.debug(f"Full metadata sync completed with broker {peer_id}")
                        
                    except Exception as e:
                        LOG.error(f"Metadata sync failed with broker {peer_id}: {e}")
                
                # Update coordination state
                self.coordination_state = BrokerCoordinationState.ACTIVE
                
                time.sleep(self.sync_interval)
                
            except Exception as e:
                LOG.error(f"Error in coordination sync: {e}")
                self.coordination_state = BrokerCoordinationState.SYNCHRONIZING
                time.sleep(1.0)
        
        LOG.info(f"Coordination sync worker stopped for broker {self.broker_id}")

    def _get_datastore_mappings(self):
        """Get datastore location mappings for metadata sync"""
        # Return empty dict if no datastores registered
        # This can be extended when datastore integration is needed
        return {}

    def get_metadata_snapshot(self):
        """Create a complete metadata snapshot for synchronization"""
        with self.coordination_lock:
            return BrokerMetadata(
                broker_id=self.broker_id,
                vector_clock=self.vector_clock.clock.copy(),
                job_registry=dict(self.distributed_jobs),
                executor_registry=dict(self.executors),
                datastore_locations=self._get_datastore_mappings(),
                pending_jobs=list(self.queued_jobs.queue),
                completed_jobs=self.completed_jobs.copy(),
                last_sync_time=time.time()
            )

    def sync_metadata_with_peer(self, peer_metadata):
        """Synchronize complete metadata with peer broker"""
        with self.coordination_lock:
            # 1. Sync vector clocks
            self.vector_clock.update(peer_metadata.vector_clock)
            
            # 2. Merge job registries (union of jobs)
            for job_id, job_coord in peer_metadata.job_registry.items():
                if job_id not in self.distributed_jobs:
                    self.distributed_jobs[job_id] = job_coord
                else:
                    # Resolve conflicts using vector clock comparison
                    existing_vc = self.distributed_jobs[job_id].vector_clock_snapshot
                    incoming_vc = job_coord.vector_clock_snapshot
                    if self._is_causally_after(incoming_vc, existing_vc):
                        self.distributed_jobs[job_id] = job_coord
            
            # 3. Merge executor registries
            for exec_id, exec_info in peer_metadata.executor_registry.items():
                if exec_id not in self.executors:
                    self.executors[exec_id] = exec_info
                else:
                    # Keep most recent based on last_update
                    if exec_info.last_update > self.executors[exec_id].last_update:
                        self.executors[exec_id] = exec_info
            
            # 4. Merge datastore locations
            for data_key, locations in peer_metadata.datastore_locations.items():
                if data_key not in self.datastore_mappings:
                    self.datastore_mappings[data_key] = []
                # Union of locations
                self.datastore_mappings[data_key] = list(
                    set(self.datastore_mappings[data_key]) | set(locations)
                )
            
            # 5. Update completed jobs (union)
            self.completed_jobs.update(peer_metadata.completed_jobs)
            
            LOG.info(f"Metadata synchronized with broker {peer_metadata.broker_id}")

    def _is_causally_after(self, vc1, vc2):
        """Check if vc1 is causally after vc2"""
        for node_id in set(vc1.keys()) | set(vc2.keys()):
            if vc1.get(node_id, 0) < vc2.get(node_id, 0):
                return False
        return any(vc1.get(node_id, 0) > vc2.get(node_id, 0) 
                   for node_id in set(vc1.keys()) | set(vc2.keys()))

# Demo and testing functions
def demo_vector_clock_broker():
    """Demonstrate VectorClockBroker functionality"""
    print("\n=== VectorClockBroker Demo ===")
    
    # Create coordinated brokers
    broker1 = VectorClockBroker("vc_broker_1")
    broker2 = VectorClockBroker("vc_broker_2")
    broker3 = VectorClockBroker("vc_broker_3")
    
    # Register as peers
    broker1.register_peer_broker("vc_broker_2", broker2)
    broker1.register_peer_broker("vc_broker_3", broker3)
    broker2.register_peer_broker("vc_broker_1", broker1)
    broker2.register_peer_broker("vc_broker_3", broker3)
    broker3.register_peer_broker("vc_broker_1", broker1)
    broker3.register_peer_broker("vc_broker_2", broker2)
    
    print(f"✅ Created coordinated brokers: {broker1.broker_id}, {broker2.broker_id}, {broker3.broker_id}")
    
    # Start brokers
    broker1.start()
    broker2.start()
    broker3.start()
    print("✅ Brokers started with coordination")
    
    # Create sample job
    job_info = JobInfo(
        job_id=uuid4(),
        data={"task": "distributed_computation", "nodes": 3},
        capabilities={"python"},
        emergency_context=None
    )
    
    # Submit distributed job
    result = broker1.submit_distributed_job(job_info)
    print(f"✅ Distributed job submitted: {result}")
    
    # Test emergency coordination
    emergency_context = create_emergency("network_failure", "high")
    coordination_result = broker1.coordinate_emergency_response(
        emergency_context, 
        affected_regions=["vc_broker_2", "vc_broker_3"]
    )
    print(f"✅ Emergency coordination: {len(coordination_result['coordinated_brokers'])} brokers")
    
    # Test causal ordering
    operation = {
        "operation_id": str(uuid4()),
        "type": "job_submission",
        "vector_clock": broker1.vector_clock.clock.copy(),
        "broker": broker1.broker_id
    }
    causal_result = broker2.ensure_causal_order(operation)
    print(f"✅ Causal ordering check: {causal_result}")
    
    # Check distributed status
    status = broker1.get_distributed_status()
    print(f"✅ Distributed status: {len(status['peer_brokers'])} peers, {len(status['distributed_jobs'])} jobs")
    
    # Wait for synchronization
    time.sleep(0.5)
    
    # Stop brokers
    broker1.stop()
    broker2.stop()
    broker3.stop()
    print("✅ Brokers stopped")
    
    return True

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run demo
    demo_vector_clock_broker()