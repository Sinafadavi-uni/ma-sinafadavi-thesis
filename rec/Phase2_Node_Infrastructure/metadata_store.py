"""
metadata_store.py
===================

This module provides a very simple metadata store for brokers and executors
in a distributed Urban Compute Platform (UCP).  The UCP paper’s data
replication requirement states that brokers should periodically sync their
metadata so that data items remain discoverable across the network.  The
``MetadataStore`` class below implements a tiny key–value store with a
``sync_with_peer`` method that merges state from another store.  In a real
deployment this would likely be backed by a durable database and would
support version vectors, conflict resolution, filtering by replication
policy, etc.  Here we keep it deliberately simple to illustrate the
concept.

Usage::

    local_store = MetadataStore()
    local_store.update("job:123", {"status": "running", "executor": "node-a"})
    remote_store = MetadataStore()
    remote_store.update("job:456", {"status": "queued"})
    # merge remote state into local store
    local_store.sync_with_peer(remote_store)

Note that the store does not delete keys when synchronising.  In a real
implementation you would track tombstones to support deletions and garbage
collection.
"""

from typing import Dict, Any, Optional
import threading
import time
try:
    # Import optional replication policy manager if available.
    from .replication_policy import ReplicationPolicyManager  # type: ignore
except ImportError:
    # Define a stub type for type checkers when the policy module is absent.
    class ReplicationPolicyManager:
        pass


class MetadataStore:
    """A thread‑safe in‑memory metadata store.

    The store holds arbitrary key–value pairs (e.g. job metadata, file
    descriptors).  It exposes methods to update values and to merge state
    from another ``MetadataStore`` instance.  Synchronisation is performed
    under a lock to avoid concurrent modifications.  The store can be
    configured with a ``ReplicationPolicyManager`` to control which
    entries are propagated to peers and to throttle update frequency.
    """

    def __init__(self, policy_manager: Optional[ReplicationPolicyManager] = None) -> None:
        """Create a new MetadataStore.

        Parameters
        ----------
        policy_manager: ReplicationPolicyManager, optional
            An optional manager that determines which keys should be
            replicated and how often.  If supplied, the store will consult
            this manager when synchronising with peers to filter out
            non‑replicated keys.  If omitted, all keys are considered
            replicable.
        """
        self._data: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._policy_manager = policy_manager
        # Track last synchronisation times for throttling updates.
        self._last_synced: Dict[str, float] = {}

    def update(self, key: str, value: Any) -> None:
        """Update or insert a metadata entry.

        Parameters
        ----------
        key: str
            The metadata key (e.g. ``"job:uuid"``).
        value: Any
            The metadata value (arbitrary JSON‑serialisable data).
        """
        with self._lock:
            self._data[key] = value

    def get(self, key: str) -> Any:
        """Retrieve a metadata value by key.  Returns ``None`` if missing."""
        with self._lock:
            return self._data.get(key)

    def snapshot(self) -> Dict[str, Any]:
        """Return a shallow copy of the current metadata state."""
        with self._lock:
            return dict(self._data)

    def sync_with_peer(self, peer_store: "MetadataStore") -> None:
        """Merge metadata from ``peer_store`` into this store.

        For each key in the peer’s store, if our local store is missing that
        key we will copy it.  If the key exists locally we leave the
        existing value untouched.  In a real implementation you might use
        vector clocks or Lamport timestamps to decide which value to keep.

        Parameters
        ----------
        peer_store: MetadataStore
            The peer’s metadata store from which to merge entries.
        """
        remote_data = peer_store.snapshot()
        now = time.time()
        with self._lock:
            for key, value in remote_data.items():
                # Decide whether to replicate this key based on policy.
                should_sync = True
                if self._policy_manager is not None:
                    should_sync = self._policy_manager.should_replicate(key)
                    if should_sync:
                        interval = self._policy_manager.get_sync_interval(key)
                        last = self._last_synced.get(key, 0.0)
                        if (now - last) < interval:
                            should_sync = False
                if not should_sync:
                    continue
                if key not in self._data:
                    self._data[key] = value
                # Record the time of this sync for throttling.
                self._last_synced[key] = now


__all__ = ["MetadataStore"]