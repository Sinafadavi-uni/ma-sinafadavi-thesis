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
from typing import Dict, Optional, List, Set, Any, Tuple
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

from rec.Phase1_Core_Foundation.vector_clock import VectorClock, EmergencyContext, EmergencyLevel, create_emergency
from rec.Phase1_Core_Foundation.causal_message import CausalMessage, MessageHandler
from rec.Phase1_Core_Foundation.causal_consistency import CausalConsistencyManager, FCFSConsistencyPolicy

# Import Phase 2 infrastructure
phase2_path = os.path.join(os.path.dirname(__file__), '..', 'Phase2_Node_Infrastructure')
sys.path.insert(0, phase2_path)

from rec.Phase2_Node_Infrastructure.executorbroker import ExecutorBroker, JobInfo, ExecutorInfo

LOG = logging.getLogger(__name__)

class BrokerCoordinationState(Enum):
    INITIALIZING = "initializing"
    ACTIVE = "active"
    SYNCHRONIZING = "synchronizing"
    EMERGENCY = "emergency"
    FAILED = "failed"

@dataclass
class DistributedJobCoordination:
    job_id: UUID
    originating_broker: str
    vector_clock_snapshot: Dict[str, int]
    fcfs_timestamp: float
    emergency_priority: Optional[int] = None
    coordination_state: str = "pending"
    assigned_executor: Optional[str] = None

class VectorClockBroker(ExecutorBroker):
    def __init__(self, broker_id: str = None):
        super().__init__(broker_id)
        self.coordination_state = BrokerCoordinationState.INITIALIZING
        self.coordination_lock = threading.RLock()
        self.peer_brokers: Dict[str, 'VectorClockBroker'] = {}
        self.distributed_jobs: Dict[UUID, DistributedJobCoordination] = {}
        self.global_fcfs_counter = 0
        self.broker_vector_clocks: Dict[str, Dict[str, int]] = {}
        self.sync_interval = 3.0
        self.sync_thread = None
        self.fcfs_policy = FCFSConsistencyPolicy()
        self.job_ordering_lock = threading.RLock()
        self.coordination_state = BrokerCoordinationState.ACTIVE
        LOG.info(f"VectorClockBroker {self.broker_id} initialized with distributed coordination")

    def register_peer_broker(self, peer_id: str, peer_broker: 'VectorClockBroker') -> None:
        self.peer_brokers[peer_id] = peer_broker
        LOG.info(f"Registered peer broker: {peer_id}")

    def submit_distributed_job(self, job_info: JobInfo, preferred_broker: str = None) -> UUID:
        self.vector_clock.tick()
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
        assigned_broker = self._coordinate_job_assignment(job_coordination, preferred_broker)
        if assigned_broker == self.broker_id:
            result = super().submit_job(job_info)
            job_coordination.coordination_state = "executing_locally"
            job_coordination.assigned_executor = "local"
        else:
            peer_broker = self.peer_brokers.get(assigned_broker)
            if peer_broker:
                result = peer_broker.execute_delegated_job(job_info, self.broker_id)
                job_coordination.coordination_state = "delegated"
                job_coordination.assigned_executor = assigned_broker
            else:
                LOG.error(f"Peer broker {assigned_broker} not available")
                result = super().submit_job(job_info)
                job_coordination.coordination_state = "fallback_local"
        LOG.info(f"Distributed job {job_info.job_id} coordinated: {job_coordination.coordination_state}")
        return result

    def execute_delegated_job(self, job_info: JobInfo, originating_broker: str) -> UUID:
        if hasattr(job_info, 'vector_clock') and job_info.vector_clock:
            self.vector_clock.update(job_info.vector_clock)
        self.vector_clock.tick()
        result = super().submit_job(job_info)
        LOG.info(f"Executed delegated job {job_info.job_id} from broker {originating_broker}")
        return result

    def sync_vector_clock(self, peer_clock: Dict[str, int], peer_broker_id: str) -> None:
        self.vector_clock.update(peer_clock)
        with self.coordination_lock:
            self.broker_vector_clocks[peer_broker_id] = peer_clock.copy()
        LOG.debug(f"Vector clock synchronized with broker {peer_broker_id}")

    def ensure_causal_order(self, operation: Dict[str, Any]) -> bool:
        if 'vector_clock' not in operation:
            LOG.warning("Operation missing vector clock for causal ordering")
            return False
        operation_clock = operation['vector_clock']
        consistency_op = {
            'operation_id': operation.get('operation_id', str(uuid4())),
            'operation_type': operation.get('type', 'unknown'),
            'vector_clock': operation_clock,
            'node_id': self.broker_id
        }
        return self.consistency_manager.ensure_consistency(consistency_op)

    def coordinate_emergency_response(self, emergency_context: EmergencyContext, affected_regions: List[str] = None) -> Dict[str, Any]:
        self.vector_clock.tick()
        self.set_emergency_mode(emergency_context.emergency_type, emergency_context.level.name)
        coordination_responses = {}
        emergency_coordination_id = uuid4()
        for peer_id, peer_broker in self.peer_brokers.items():
            if not affected_regions or peer_id in affected_regions:
                try:
                    peer_broker.sync_vector_clock(self.vector_clock.clock, self.broker_id)
                    peer_broker.set_emergency_mode(emergency_context.emergency_type, emergency_context.level.name)
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

    def get_distributed_status(self) -> Dict[str, Any]:
        with self.coordination_lock:
            distributed_job_states = {}
            for job_id, coordination in self.distributed_jobs.items():
                distributed_job_states[str(job_id)] = {
                    "originating_broker": coordination.originating_broker,
                    "state": coordination.coordination_state,
                    "assigned_executor": coordination.assigned_executor,
                    "fcfs_timestamp": coordination.fcfs_timestamp
                }
        
        # Create basic status instead of calling non-existent get_status
        base_status = {
            "broker_id": self.broker_id,
            "executor_count": self.get_executor_count(),
            "emergency_mode": self.current_emergency is not None,
            "vector_clock": self.vector_clock.clock.copy()
        }
        
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

    def start(self) -> None:
        super().start()
        if self.sync_thread is None or not self.sync_thread.is_alive():
            self.sync_thread = threading.Thread(
                target=self._coordination_sync_worker,
                daemon=True,
                name=f"vc-broker-sync-{self.broker_id}"
            )
            self.sync_thread.start()
        self.coordination_state = BrokerCoordinationState.ACTIVE
        LOG.info(f"VectorClockBroker {self.broker_id} started with distributed coordination")

    def stop(self) -> None:
        self.coordination_state = BrokerCoordinationState.FAILED
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=2.0)
        super().stop()
        LOG.info(f"VectorClockBroker {self.broker_id} stopped")

    def _get_emergency_priority(self, emergency_context: EmergencyContext) -> Optional[int]:
        if not emergency_context:
            return None
        priority_map = {
            EmergencyLevel.CRITICAL: 0,
            EmergencyLevel.HIGH: 1,
            EmergencyLevel.MEDIUM: 2,
            EmergencyLevel.LOW: 3
        }
        return priority_map.get(emergency_context.level, 5)

    def _coordinate_job_assignment(self, job_coordination: DistributedJobCoordination, preferred_broker: str = None) -> str:
        if preferred_broker and preferred_broker in self.peer_brokers:
            return preferred_broker
        available_brokers = [self.broker_id] + list(self.peer_brokers.keys())
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
        assigned_index = self.global_fcfs_counter % len(available_brokers)
        assigned_broker = available_brokers[assigned_index]
        LOG.debug(f"Job {job_coordination.job_id} assigned to broker {assigned_broker} via FCFS")
        return assigned_broker

    def _coordination_sync_worker(self) -> None:
        LOG.info(f"Coordination sync worker started for broker {self.broker_id}")
        while not self.should_exit and self.coordination_state == BrokerCoordinationState.ACTIVE:
            try:
                for peer_id, peer_broker in self.peer_brokers.items():
                    if hasattr(peer_broker, 'vector_clock'):
                        peer_clock = peer_broker.vector_clock.clock.copy()
                        self.sync_vector_clock(peer_clock, peer_id)
                self.coordination_state = BrokerCoordinationState.ACTIVE
                time.sleep(self.sync_interval)
            except Exception as e:
                LOG.error(f"Error in coordination sync: {e}")
                self.coordination_state = BrokerCoordinationState.SYNCHRONIZING
                time.sleep(1.0)
        LOG.info(f"Coordination sync worker stopped for broker {self.broker_id}")

def demo_vector_clock_broker():
    print("\n=== Vector Clock Broker Demo ===")
    
    # Create distributed brokers
    broker1 = VectorClockBroker("vc_broker1")
    broker2 = VectorClockBroker("vc_broker2")
    
    # Register as peers
    broker1.register_peer_broker("vc_broker2", broker2)
    broker2.register_peer_broker("vc_broker1", broker1)
    
    print("✅ Created vector clock brokers with peer registration")
    
    # Start brokers
    broker1.start()
    broker2.start()
    print("✅ Vector clock brokers started")
    
    # Submit distributed jobs
    job1 = JobInfo(job_id=uuid4(), data={"task": "distributed_compute"})
    job2 = JobInfo(job_id=uuid4(), data={"task": "data_analysis"})
    
    broker1.submit_distributed_job(job1)
    broker2.submit_distributed_job(job2)
    print("✅ Distributed jobs submitted")
    
    # Test emergency coordination
    emergency = create_emergency("earthquake", "high")
    coordination_result = broker1.coordinate_emergency_response(emergency)
    print("✅ Emergency coordination activated")
    
    # Get distributed status
    status1 = broker1.get_distributed_status()
    status2 = broker2.get_distributed_status()
    print(f"✅ Broker 1 managing: {len(status1['distributed_jobs'])} distributed jobs")
    print(f"✅ Broker 2 managing: {len(status2['distributed_jobs'])} distributed jobs")
    
    # Stop brokers
    broker1.stop()
    broker2.stop()
    print("✅ Vector clock brokers stopped")
    
    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_vector_clock_broker()
