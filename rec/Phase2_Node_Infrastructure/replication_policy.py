"""
replication_policy.py
=====================

This module defines simple classes for configuring replication policies
within the Urban Compute Platform (UCP).  Data replication incurs
network and storage overhead, so operators may wish to replicate only
certain classes of metadata or adjust how frequently entries are
synchronised.  A ``ReplicationPolicy`` describes whether a
metadata key should be replicated and the minimum time interval between
replication events.  A ``ReplicationPolicyManager`` maintains a set
of policies keyed by prefixes and provides helper methods to resolve
policies for specific keys.

In practice you might integrate these classes with the metadata store
and broker components to filter outgoing updates.  For example::

    from replication_policy import ReplicationPolicyManager, ReplicationPolicy
    policy_manager = ReplicationPolicyManager()
    policy_manager.set_policy("job:", ReplicationPolicy(replicate=True, sync_interval=5.0))
    policy_manager.set_policy("temp:", ReplicationPolicy(replicate=False))

    # When synchronising metadata, call ``should_replicate(key)`` to decide
    # whether to include the entry in outbound replication.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ReplicationPolicy:
    """Configuration for how a metadata key should be replicated.

    Attributes
    ----------
    replicate: bool
        If ``True`` then the metadata key should be included when
        synchronising state with peer brokers.  If ``False`` the key will
        remain local to the node and will not be sent over the wire.
    sync_interval: float
        The minimum number of seconds that should elapse between successive
        replication events for entries governed by this policy.  This
        value can be used by higher‑level components to throttle update
        frequency.  Defaults to 30 seconds.
    """
    replicate: bool
    sync_interval: float = 30.0


class ReplicationPolicyManager:
    """Manages replication policies for metadata keys.

    Policies are stored in a dictionary keyed by prefix.  When a
    policy is requested for a specific key, the longest matching prefix
    determines which policy is returned; if no prefix matches the
    ``default_policy`` is used.
    """

    def __init__(self, default_policy: ReplicationPolicy | None = None) -> None:
        # Use a default policy that replicates all keys every 30 seconds.
        self.default_policy: ReplicationPolicy = default_policy or ReplicationPolicy(True, 30.0)
        self._policies: Dict[str, ReplicationPolicy] = {}

    def set_policy(self, prefix: str, policy: ReplicationPolicy) -> None:
        """Register a policy for keys beginning with ``prefix``.

        Later registrations override earlier ones for the same prefix.
        Prefixes are matched using simple ``str.startswith`` semantics.
        """
        self._policies[prefix] = policy

    def get_policy(self, key: str) -> ReplicationPolicy:
        """Return the most specific policy for ``key``.

        The longest prefix match wins.  If no configured prefix applies
        then the ``default_policy`` is returned.
        """
        best_prefix = ""
        chosen_policy: ReplicationPolicy | None = None
        for prefix, policy in self._policies.items():
            if key.startswith(prefix) and len(prefix) >= len(best_prefix):
                best_prefix = prefix
                chosen_policy = policy
        return chosen_policy or self.default_policy

    def should_replicate(self, key: str) -> bool:
        """Return ``True`` if the key should be replicated."""
        return self.get_policy(key).replicate

    def get_sync_interval(self, key: str) -> float:
        """Return the minimum replication interval (in seconds) for ``key``."""
        return self.get_policy(key).sync_interval


__all__ = ["ReplicationPolicy", "ReplicationPolicyManager"]