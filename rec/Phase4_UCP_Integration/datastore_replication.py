"""
Datastore Replication Manager for UCP
Implements replicated and unreplicated datastore policies with
vector clock-based consistency for emergency scenarios.
"""

import time
import threading
import logging
import hashlib
from typing import Dict, Optional, List, Set, Any, Tuple
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

# Import Phase 1 foundation
import sys
import os
phase1_path = os.path.join(os.path.dirname(__file__), '..', 'Phase1_Core_Foundation')
sys.path.insert(0, phase1_path)

from vector_clock import VectorClock
from causal_consistency import CausalConsistencyManager

LOG = logging.getLogger(__name__)

class ReplicationStrategy(Enum):
    """Datastore replication strategies"""
    NONE = "none"  # No replication
    ASYNC = "async"  # Asynchronous replication
    SYNC = "sync"  # Synchronous replication
    EMERGENCY = "emergency"  # Emergency-only replication

@dataclass
class DataItem:
    """Data item with metadata"""
    key: str
    value: bytes
    vector_clock: Dict[str, int]
    checksum: str
    size: int
    created_at: float
    last_modified: float
    replication_factor: int = 1
    replicas: Set[str] = field(default_factory=set)

@dataclass
class DatastoreNode:
    """Datastore node information"""
    node_id: str
    host: str
    port: int
    capacity: int  # Total capacity in bytes
    used_space: int = 0
    available: bool = True
    last_heartbeat: float = field(default_factory=time.time)
    vector_clock: Optional[VectorClock] = None
    
    def __post_init__(self):
        if self.vector_clock is None:
            self.vector_clock = VectorClock(self.node_id)

class DatastoreReplicationManager:
    """
    Manages datastore replication with vector clock consistency
    
    Features:
    - Configurable replication strategies
    - Vector clock-based consistency
    - Emergency-aware replication
    - Bandwidth optimization
    - Automatic failover
    """
    
    def __init__(self, manager_id: str = None, default_replication: int = 2):
        """Initialize datastore replication manager"""
        self.manager_id = manager_id or f"datastore-repl-{uuid4()}"
        self.vector_clock = VectorClock(self.manager_id)
        self.consistency_manager = CausalConsistencyManager(self.manager_id)
        
        # Replication configuration
        self.default_replication_factor = default_replication
        self.current_strategy = ReplicationStrategy.ASYNC
        self.emergency_mode = False
        
        # Datastore management
        self.datastores: Dict[str, DatastoreNode] = {}
        self.datastore_lock = threading.RLock()
        
        # Data management
        self.data_registry: Dict[str, DataItem] = {}  # key -> DataItem
        self.replica_locations: Dict[str, Set[str]] = defaultdict(set)  # key -> {datastore_ids}
        self.pending_replications: List[Tuple[str, str]] = []  # [(key, target_datastore)]
        
        # Monitoring
        self.replication_metrics = {
            "total_replications": 0,
            "failed_replications": 0,
            "bandwidth_used": 0,
            "emergency_replications": 0
        }
        
        # Background threads
        self.should_exit = False
        self.replication_thread = None
        self.consistency_thread = None
        
        LOG.info(f"DatastoreReplicationManager {self.manager_id} initialized")
    
    def register_datastore(self, node_id: str, host: str, port: int, capacity: int) -> None:
        """Register a datastore node"""
        with self.datastore_lock:
            datastore = DatastoreNode(
                node_id=node_id,
                host=host,
                port=port,
                capacity=capacity
            )
            self.datastores[node_id] = datastore
            
        LOG.info(f"Datastore {node_id} registered with capacity {capacity}")
    
    def store_data(self, key: str, value: bytes, replication_factor: Optional[int] = None) -> bool:
        """
        Store data with replication
        
        Args:
            key: Data key
            value: Data value
            replication_factor: Override default replication
            
        Returns:
            bool: Success status
        """
        # Determine replication factor
        if replication_factor is None:
            replication_factor = self._get_replication_factor()
        
        # Calculate checksum
        checksum = hashlib.sha256(value).hexdigest()
        
        # Update vector clock
        self.vector_clock.tick()
        
        # Create data item
        data_item = DataItem(
            key=key,
            value=value,
            vector_clock=self.vector_clock.clock.copy(),
            checksum=checksum,
            size=len(value),
            created_at=time.time(),
            last_modified=time.time(),
            replication_factor=replication_factor
        )
        
        # Select datastores for storage
        selected_datastores = self._select_datastores_for_replication(
            data_item.size, replication_factor
        )
        
        if len(selected_datastores) < replication_factor:
            LOG.warning(f"Only {len(selected_datastores)} datastores available "
                       f"for replication factor {replication_factor}")
        
        # Store data
        success_count = 0
        for datastore_id in selected_datastores:
            if self._store_on_datastore(datastore_id, key, value, data_item):
                data_item.replicas.add(datastore_id)
                self.replica_locations[key].add(datastore_id)
                success_count += 1
        
        # Update registry
        self.data_registry[key] = data_item
        
        # Update metrics
        self.replication_metrics["total_replications"] += success_count
        self.replication_metrics["bandwidth_used"] += data_item.size * success_count
        
        LOG.info(f"Data {key} stored with {success_count}/{replication_factor} replicas")
        
        return success_count > 0
    
    def retrieve_data(self, key: str) -> Optional[bytes]:
        """
        Retrieve data from available replica
        
        Args:
            key: Data key
            
        Returns:
            Data value or None
        """
        data_item = self.data_registry.get(key)
        if not data_item:
            LOG.warning(f"Data {key} not found in registry")
            return None
        
        # Try replicas in order of availability
        for datastore_id in data_item.replicas:
            datastore = self.datastores.get(datastore_id)
            if datastore and datastore.available:
                value = self._retrieve_from_datastore(datastore_id, key)
                if value:
                    # Verify checksum
                    if hashlib.sha256(value).hexdigest() == data_item.checksum:
                        return value
                    else:
                        LOG.error(f"Checksum mismatch for {key} from {datastore_id}")
        
        LOG.error(f"Could not retrieve data {key} from any replica")
        return None
    
    def handle_datastore_failure(self, failed_datastore_id: str) -> None:
        """Handle datastore failure with re-replication"""
        LOG.warning(f"Handling failure of datastore {failed_datastore_id}")
        
        with self.datastore_lock:
            if failed_datastore_id in self.datastores:
                self.datastores[failed_datastore_id].available = False
        
        # Find all data that needs re-replication
        affected_keys = []
        for key, data_item in self.data_registry.items():
            if failed_datastore_id in data_item.replicas:
                affected_keys.append(key)
        
        LOG.info(f"Found {len(affected_keys)} keys affected by datastore failure")
        
        # Re-replicate affected data
        for key in affected_keys:
            self._ensure_replication_factor(key)
    
    def set_emergency_mode(self, emergency: bool = True) -> None:
        """Set emergency mode affecting replication behavior"""
        self.emergency_mode = emergency
        
        if emergency:
            # Switch to emergency strategy
            self.current_strategy = ReplicationStrategy.EMERGENCY
            LOG.warning("Emergency mode activated - minimizing replication")
        else:
            # Restore normal strategy
            self.current_strategy = ReplicationStrategy.ASYNC
            LOG.info("Emergency mode deactivated - normal replication resumed")
    
    def get_replication_status(self) -> Dict[str, Any]:
        """Get comprehensive replication status"""
        with self.datastore_lock:
            available_datastores = sum(
                1 for ds in self.datastores.values() if ds.available
            )
            total_capacity = sum(
                ds.capacity for ds in self.datastores.values()
            )
            used_capacity = sum(
                ds.used_space for ds in self.datastores.values()
            )
        
        return {
            "manager_id": self.manager_id,
            "strategy": self.current_strategy.value,
            "emergency_mode": self.emergency_mode,
            "datastores": {
                "total": len(self.datastores),
                "available": available_datastores
            },
            "capacity": {
                "total": total_capacity,
                "used": used_capacity,
                "available": total_capacity - used_capacity
            },
            "data_items": len(self.data_registry),
            "metrics": self.replication_metrics,
            "vector_clock": self.vector_clock.clock.copy()
        }
    
    def start(self) -> None:
        """Start replication manager"""
        if self.replication_thread is None or not self.replication_thread.is_alive():
            self.should_exit = False
            
            self.replication_thread = threading.Thread(
                target=self._replication_worker,
                daemon=True,
                name=f"replication-{self.manager_id}"
            )
            self.replication_thread.start()
            
            self.consistency_thread = threading.Thread(
                target=self._consistency_checker,
                daemon=True,
                name=f"consistency-{self.manager_id}"
            )
            self.consistency_thread.start()
            
        LOG.info(f"DatastoreReplicationManager {self.manager_id} started")
    
    def stop(self) -> None:
        """Stop replication manager"""
        self.should_exit = True
        
        if self.replication_thread and self.replication_thread.is_alive():
            self.replication_thread.join(timeout=2.0)
        
        if self.consistency_thread and self.consistency_thread.is_alive():
            self.consistency_thread.join(timeout=2.0)
        
        LOG.info(f"DatastoreReplicationManager {self.manager_id} stopped")
    
    # Private helper methods
    
    def _get_replication_factor(self) -> int:
        """Determine replication factor based on current strategy"""
        if self.current_strategy == ReplicationStrategy.NONE:
            return 1
        elif self.current_strategy == ReplicationStrategy.EMERGENCY:
            return 1  # Minimize replication in emergency
        else:
            return self.default_replication_factor
    
    def _select_datastores_for_replication(self, size: int, count: int) -> List[str]:
        """Select datastores for replication"""
        available = []
        
        with self.datastore_lock:
            for ds_id, datastore in self.datastores.items():
                if datastore.available and (datastore.capacity - datastore.used_space) >= size:
                    available.append(ds_id)
        
        # Sort by available space (load balancing)
        available.sort(key=lambda x: self.datastores[x].capacity - self.datastores[x].used_space, 
                      reverse=True)
        
        return available[:count]
    
    def _store_on_datastore(self, datastore_id: str, key: str, value: bytes, 
                           data_item: DataItem) -> bool:
        """Store data on specific datastore"""
        try:
            # Simulate storage operation
            with self.datastore_lock:
                datastore = self.datastores.get(datastore_id)
                if datastore:
                    datastore.used_space += data_item.size
                    # Update vector clock
                    datastore.vector_clock.update(data_item.vector_clock)
            
            LOG.debug(f"Stored {key} on datastore {datastore_id}")
            return True
            
        except Exception as e:
            LOG.error(f"Failed to store {key} on datastore {datastore_id}: {e}")
            self.replication_metrics["failed_replications"] += 1
            return False
    
    def _retrieve_from_datastore(self, datastore_id: str, key: str) -> Optional[bytes]:
        """Retrieve data from specific datastore"""
        try:
            # Simulate retrieval operation
            data_item = self.data_registry.get(key)
            if data_item and datastore_id in data_item.replicas:
                return data_item.value
            return None
            
        except Exception as e:
            LOG.error(f"Failed to retrieve {key} from datastore {datastore_id}: {e}")
            return None
    
    def _ensure_replication_factor(self, key: str) -> None:
        """Ensure data meets replication factor"""
        data_item = self.data_registry.get(key)
        if not data_item:
            return
        
        current_replicas = len([
            r for r in data_item.replicas 
            if r in self.datastores and self.datastores[r].available
        ])
        
        if current_replicas < data_item.replication_factor:
            needed = data_item.replication_factor - current_replicas
            LOG.info(f"Data {key} needs {needed} additional replicas")
            
            # Find new datastores
            candidates = self._select_datastores_for_replication(
                data_item.size, needed + current_replicas
            )
            
            # Filter out existing replicas
            new_datastores = [ds for ds in candidates if ds not in data_item.replicas][:needed]
            
            # Create new replicas
            for datastore_id in new_datastores:
                if self._store_on_datastore(datastore_id, key, data_item.value, data_item):
                    data_item.replicas.add(datastore_id)
                    self.replica_locations[key].add(datastore_id)
    
    def _replication_worker(self) -> None:
        """Background replication worker"""
        LOG.info(f"Replication worker started for {self.manager_id}")
        
        while not self.should_exit:
            try:
                # Process pending replications
                if self.pending_replications:
                    key, target = self.pending_replications.pop(0)
                    data_item = self.data_registry.get(key)
                    if data_item:
                        self._store_on_datastore(target, key, data_item.value, data_item)
                
                time.sleep(1.0)
                
            except Exception as e:
                LOG.error(f"Error in replication worker: {e}")
                time.sleep(1.0)
        
        LOG.info(f"Replication worker stopped for {self.manager_id}")
    
    def _consistency_checker(self) -> None:
        """Background consistency checker"""
        LOG.info(f"Consistency checker started for {self.manager_id}")
        
        while not self.should_exit:
            try:
                # Check replication factors
                for key, data_item in self.data_registry.items():
                    self._ensure_replication_factor(key)
                
                time.sleep(30.0)  # Check every 30 seconds
                
            except Exception as e:
                LOG.error(f"Error in consistency checker: {e}")
                time.sleep(5.0)
        
        LOG.info(f"Consistency checker stopped for {self.manager_id}")
