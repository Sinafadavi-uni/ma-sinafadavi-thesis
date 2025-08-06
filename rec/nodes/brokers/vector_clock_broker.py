# Vector Clock Support on a Basic UCP Broker
# Step 5A: Enhanced with multi-broker coordination for UCP Part B.a compliance
# Trying to integrate vector clocks without messing with original logic too much

import threading  # Might need for later async stuff?
from typing import Any, Optional, Dict
from uuid import UUID
from datetime import datetime

from rec.model import NodeRole
from rec.nodes.brokers.databroker import DataBroker
from rec.nodes.brokers.executorbroker import ExecutorBroker
from rec.nodes.node import Node
from rec.util.log import LOG
from rec.replication.core.vector_clock import VectorClock, create_emergency


class VectorClockExecutorBroker(ExecutorBroker):
    """Enhanced executor broker with vector clock capabilities"""
    
    def __init__(self, on_job_started):
        super().__init__(on_job_started)
        self.node_id = "vector-clock-broker"
        self.vector_clock = VectorClock(self.node_id)
        self.emergency_context = create_emergency("none", "low")
        self.emergency_jobs = set()
    
    def delete_job_from_executor(self, job_id: UUID):
        """Remove job from executor tracking"""
        with self.cj_lock:
            self.completed_jobs.discard(job_id)
            self.emergency_jobs.discard(job_id)


class VectorClockBroker(Node):
    """
    Enhanced broker with vector clock logic and multi-broker coordination.
    Step 5A: Implements UCP Part B.a) - periodic metadata synchronization between brokers
    
    Should mostly behave like the original but with a few added features.
    
    Big ideas:
    - We still use the old data broker
    - But now we add VectorClockExecutorBroker to handle jobs more smartly
    - Also added some emergency job handling logic
    - NEW: Multi-broker coordination for distributed metadata sync
    """

    def __init__(self, host: list[str], port: int, uvicorn_args: Optional[dict[str, Any]] = None, 
                 enable_coordination: bool = True):
        """
        Try to keep the same setup as the regular broker for compatibility.
        NEW: Added coordination support for multi-broker environments
        """
        super().__init__(host, port, "vector-clock-broker", uvicorn_args)
        
        self.data_broker = DataBroker()  # regular data broker still works fine
        self.executor_broker = VectorClockExecutorBroker(self.data_broker.add_pending_job)
        self.coordination_enabled = enable_coordination
        self.coordinator = None

        # Register both sets of endpoints
        self.data_broker.add_endpoints(self.fastapi_app)
        self.executor_broker.add_endpoints(self.fastapi_app)

        LOG.info("VectorClockBroker up and running with coordination support")  # Noting success

    def add_endpoints(self):
        """
        Adding new endpoints, including vector clock introspection and emergency tools.
        Step 5A: Added multi-broker coordination endpoints for UCP Part B.a compliance
        Also keeps the old delete endpoint in place.
        """

        @self.fastapi_app.delete("/job/{job_id}")
        def nuke_job(job_id: UUID) -> None:
            # Called when we want to remove a job entirely
            LOG.debug(f"Trying to remove job {job_id}")

            self.executor_broker.vector_clock.tick()  # bump the clock so others know

            self.data_broker.delete_job_data(job_id)  # clear from data store
            self.executor_broker.delete_job_from_executor(job_id)  # and from executor

            LOG.info(f"Removed job {job_id} successfully")

        @self.fastapi_app.get("/broker/vector-clock")
        def fetch_clock() -> dict:
            # returns current vector clock state and related info
            return {
                "broker_id": str(self.executor_broker.node_id),
                "vector_clock": self.executor_broker.vector_clock.clock,
                "emergency_jobs": len(self.executor_broker.emergency_jobs),
                "total_executors": len(self.executor_broker.executors)
            }

        @self.fastapi_app.get("/broker/emergency-status")
        def show_emergency_info() -> dict:
            # tells us if we're in an emergency and what the deal is
            return {
                "emergency_context": self.executor_broker.emergency_context.emergency_type,
                "active_emergency_jobs": list(self.executor_broker.emergency_jobs),
                "emergency_job_count": len(self.executor_broker.emergency_jobs)
            }

        @self.fastapi_app.post("/broker/declare-emergency")
        def set_emergency(emergency_type: str = "general") -> dict:
            # This can be triggered externally to notify the broker
            LOG.warning(f"!! Emergency declared: {emergency_type} !!")

            self.executor_broker.vector_clock.tick()  # again, bump the clock

            # Set the new context (wasn't sure if there's a nicer way)
            self.executor_broker.emergency_context = self.executor_broker.emergency_context.__class__(
                emergency_type, "critical"
            )

            return {
                "status": "emergency_declared",
                "emergency_type": emergency_type,
                "timestamp": self.executor_broker.vector_clock.clock
            }

        # NEW: Multi-broker coordination endpoints for UCP Part B.a
        @self.fastapi_app.post("/broker/sync-metadata")
        def sync_metadata(peer_metadata: Dict) -> Dict:
            """
            Endpoint for peer brokers to sync metadata
            Implements UCP Part B.a requirement for periodic sync
            """
            try:
                # Log the sync attempt
                peer_id = peer_metadata.get("broker_id", "unknown")
                LOG.debug(f"Receiving metadata sync from peer {peer_id}")
                
                # Update our vector clock with peer's clock
                peer_clock = peer_metadata.get("vector_clock", {})
                if peer_clock:
                    self.executor_broker.vector_clock.update(peer_clock)
                    LOG.debug(f"Updated vector clock after sync with {peer_id}")
                
                # Return our current metadata
                return self._get_broker_metadata_dict()
                
            except Exception as e:
                LOG.error(f"Error during metadata sync: {e}")
                raise

        @self.fastapi_app.get("/broker/coordination-status") 
        def get_coordination_status() -> Dict:
            """Get status of multi-broker coordination"""
            if self.coordinator:
                return self.coordinator.get_coordination_status()
            else:
                return {
                    "coordinator_running": False,
                    "message": "Multi-broker coordination disabled"
                }

        @self.fastapi_app.get("/broker/metadata")
        def get_metadata() -> Dict:
            """Get current broker metadata for coordination"""
            return self._get_broker_metadata_dict()

    def _get_broker_metadata_dict(self) -> Dict:
        """Get current broker metadata as dictionary for coordination"""
        return {
            "broker_id": str(self.executor_broker.node_id),
            "vector_clock": self.executor_broker.vector_clock.clock.copy(),
            "executor_count": len(self.executor_broker.executors),
            "active_jobs": [str(job_id) for job_id in self.executor_broker.completed_jobs],
            "emergency_jobs": [str(job_id) for job_id in self.executor_broker.emergency_jobs],
            "last_updated": datetime.now().isoformat(),
            "capabilities": {
                "emergency_handling": True,
                "vector_clock_support": True,
                "max_executors": 100,
                "coordination_enabled": self.coordination_enabled
            }
        }

    def run(self) -> NodeRole:
        """
        Starts everything up.
        Step 5A: Enhanced with multi-broker coordination startup
        Hopefully same as original but now more aware of timing/emergencies.
        """
        LOG.info("Launching vector clock broker with coordination support")

        self.executor_broker.start()  # kicks off the job runner

        # Initialize multi-broker coordination if enabled
        if self.coordination_enabled:
            try:
                # Import here to avoid circular imports
                from rec.nodes.brokers.multi_broker_coordinator import MultiBrokerCoordinator
                
                # Extract port from the host configuration
                port = self.port if hasattr(self, 'port') else 8000
                self.coordinator = MultiBrokerCoordinator(self.executor_broker, port)
                self.coordinator.start_coordination()
                LOG.info("Multi-broker coordination started successfully")
                
            except Exception as e:
                LOG.warning(f"Failed to start multi-broker coordination: {e}")
                LOG.info("Continuing without coordination support")
                self.coordination_enabled = False

        # Add listener for datastore events (no changes here)
        self.add_service_listener(
            Node.zeroconf_service_type("datastore"),
            self.data_broker.datastore_listener
        )

        self.do_run()  # actually starts the server

        LOG.info("Broker has been shut down")
        return NodeRole.EXIT

    def stop(self):
        """
        Clean shutdown of both base broker and executor.
        Step 5A: Enhanced with coordination cleanup
        """
        LOG.info("Gracefully stopping broker now")
        
        # Stop coordination first
        if self.coordinator:
            try:
                self.coordinator.stop_coordination()
                LOG.info("Multi-broker coordination stopped")
            except Exception as e:
                LOG.warning(f"Error stopping coordination: {e}")
        
        super().stop()
        self.executor_broker.stop()


# Run this directly to try it out
if __name__ == "__main__":
    # Fire up the broker on localhost with coordination
    broker = VectorClockBroker(["127.0.0.1"], 8000, enable_coordination=True)
    try:
        result = broker.run()
        LOG.info(f"Exited with status: {result}")
    except KeyboardInterrupt:
        LOG.info("User ended the session")
        broker.stop()
    except Exception as e:
        LOG.error(f"Something broke: {e}")
        broker.stop()
