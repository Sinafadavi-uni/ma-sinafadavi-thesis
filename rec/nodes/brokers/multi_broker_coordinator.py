
# Periodically shares broker metadata and syncs vector clocks

import time
import threading
import requests
from typing import Dict, Any, Tuple, List
from uuid import uuid4
from dataclasses import dataclass, asdict
from datetime import datetime

from rec.replication.core.vector_clock import VectorClock
from rec.nodes.brokers.vector_clock_broker import VectorClockExecutorBroker
from rec.util.log import LOG
from rec.model import NodeRole, Address


@dataclass
class BrokerMetadata:
    """Metadata all brokers share with each other."""
    broker_id: str
    vector_clock: Dict[str, int]
    executor_count: int
    active_jobs: List[str]
    emergency_jobs: List[str]
    last_updated: str
    capabilities: Dict[str, Any]


@dataclass
class PeerBroker:
    """Info about one peer broker."""
    broker_id: str
    host: str
    port: int
    last_seen: float
    vector_clock: Dict[str, int]
    is_healthy: bool = True


class MultiBrokerCoordinator:
    """
    Coordinates metadata between brokers.
    Periodically discovers peers and syncs metadata (per UCP guidelines).
    """

    def __init__(self, broker: VectorClockExecutorBroker, discovery_port: int = 8000):
        self.broker = broker
        self.discovery_port = discovery_port
        self.peers: Dict[str, PeerBroker] = {}
        self.running = False
        self.sync_interval = 60
        self.metadata_lock = threading.RLock()
        LOG.info(f"[Coordinator] Initialized for broker {broker.node_id}")

    def start(self):
        """Start peer discovery and metadata sync loops."""
        self.running = True
        threading.Thread(target=self._discover_loop, daemon=True).start()
        threading.Thread(target=self._sync_loop, daemon=True).start()
        LOG.info("[Coordinator] Started coordination threads")

    def stop(self):
        """Stop the loops cleanly."""
        self.running = False
        LOG.info("[Coordinator] Stopped coordination")

    def _discover_loop(self):
        """Every 30s, scan known ports to discover peer brokers."""
        while self.running:
            self._discover_peers()
            time.sleep(30)

    def _discover_peers(self):
        # Looking for brokers running on localhost ports 8000–8004
        for port in range(8000, 8005):
            if port == self.discovery_port:
                continue
            try:
                resp = requests.get(f"http://localhost:{port}/broker/vector-clock", timeout=3)
                if resp.status_code == 200:
                    data = resp.json()
                    peer_id = data.get("broker_id")
                    vc = data.get("vector_clock", {})
                    self._register_peer(peer_id, "localhost", port, vc)
            except:
                pass  # No broker here, or timed out

    def _register_peer(self, peer_id: str, host: str, port: int, vc: Dict[str, int]):
        with self.metadata_lock:
            if peer_id not in self.peers:
                LOG.info(f"[Coordinator] New peer found: {peer_id}@{host}:{port}")
            self.peers[peer_id] = PeerBroker(peer_id, host, port, time.time(), vc)

    def _sync_loop(self):
        """Every sync_interval, send metadata to peers."""
        while self.running:
            self._sync_metadata()
            time.sleep(self.sync_interval)

    def _sync_metadata(self):
        if not self.peers:
            return
        my_meta = self._get_my_metadata()
        for pid, peer in list(self.peers.items()):
            try:
                resp = requests.post(f"http://{peer.host}:{peer.port}/broker/sync-metadata",
                                     json=asdict(my_meta), timeout=5)
                if resp.status_code == 200:
                    pdata = resp.json()
                    self._merge_peer(BrokerMetadata(**pdata))
                    peer.last_seen = time.time()
                    peer.is_healthy = True
            except Exception as e:
                peer.is_healthy = False
                LOG.warning(f"[Coordinator] Sync failed with {pid}: {e}")

    def _get_my_metadata(self) -> BrokerMetadata:
        with self.metadata_lock:
            return BrokerMetadata(
                broker_id=self.broker.node_id,
                vector_clock=self.broker.vector_clock.clock.copy(),
                executor_count=len(self.broker.executors),
                active_jobs=[str(j) for j in self.broker.completed_jobs],
                emergency_jobs=[str(j) for j in self.broker.emergency_jobs],
                last_updated=datetime.now().isoformat(),
                capabilities={
                    "vector_clock": True,
                    "emergency_support": True
                }
            )

    def _merge_peer(self, peer_meta: BrokerMetadata):
        """Merge peer metadata—main task is to update our vector clock."""
        self.broker.vector_clock.update(peer_meta.vector_clock)
        LOG.debug(f"[Coordinator] Merged metadata from {peer_meta.broker_id}. New clock: {self.broker.vector_clock.clock}")

    def get_status(self) -> Dict[str, Any]:
        with self.metadata_lock:
            return {
                "coordinator_running": self.running,
                "peer_count": len(self.peers),
                "healthy_peers": sum(1 for p in self.peers.values() if p.is_healthy),
                "peers": {pid: p.is_healthy for pid, p in self.peers.items()}
            }

    # === METHOD ALIASES FOR VECTOR CLOCK BROKER COMPATIBILITY ===
    
    def start_coordination(self):
        """Alias for start() - expected by VectorClockBroker"""
        return self.start()
    
    def stop_coordination(self):
        """Alias for stop() - expected by VectorClockBroker"""
        return self.stop()
    
    def get_coordination_status(self) -> Dict[str, Any]:
        """Alias for get_status() - expected by VectorClockBroker"""
        return self.get_status()


def create_coordinator(on_job_started, port: int = 8000) -> Tuple[VectorClockExecutorBroker, MultiBrokerCoordinator]:
    broker = VectorClockExecutorBroker(on_job_started)
    coordinator = MultiBrokerCoordinator(broker, port)
    return broker, coordinator


# 📦 Example usage
if __name__ == "__main__":
    def dummy_starter(job_id, job_info):
        LOG.info(f"[Broker] Job started: {job_id}")

    broker, coord = create_coordinator(dummy_starter, port=8000)
    coord.start()
    try:
        LOG.info("Coordinator running... press Ctrl+C to stop.")
        time.sleep(120)
    except KeyboardInterrupt:
        LOG.info("Caught interrupt — stopping.")
    finally:
        coord.stop()
