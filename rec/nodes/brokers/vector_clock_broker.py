# Vector Clock Support on a Basic UCP Broker
# Trying to integrate vector clocks without messing with original logic too much

import threading  # Might need for later async stuff?
from typing import Any, Optional
from uuid import UUID

from rec.model import NodeRole
from rec.nodes.brokers.databroker import DataBroker
from rec.nodes.brokers.vector_clock_executor_broker import VectorClockExecutorBroker
from rec.nodes.node import Node
from rec.util.log import LOG


class VectorClockBroker(Node):
    """
    Attempt to extend basic broker with vector clock logic.
    Should mostly behave like the original but with a few added features.
    
    Big ideas:
    - We still use the old data broker
    - But now we add VectorClockExecutorBroker to handle jobs more smartly
    - Also added some emergency job handling logic
    """

    def __init__(self, host: list[str], port: int, uvicorn_args: Optional[dict[str, Any]] = None):
        """
        Try to keep the same setup as the regular broker for compatibility.
        """
        super().__init__(host, port, "vector-clock-broker", uvicorn_args)
        
        self.data_broker = DataBroker()  # regular data broker still works fine
        self.executor_broker = VectorClockExecutorBroker(self.data_broker.add_pending_job)

        # Register both sets of endpoints
        self.data_broker.add_endpoints(self.fastapi_app)
        self.executor_broker.add_endpoints(self.fastapi_app)

        LOG.info("VectorClockBroker up and running")  # Noting success

    def add_endpoints(self):
        """
        Adding new endpoints, including vector clock introspection and emergency tools.
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

    def run(self) -> NodeRole:
        """
        Starts everything up.
        Hopefully same as original but now more aware of timing/emergencies.
        """
        LOG.info("Launching vector clock broker")

        self.executor_broker.start()  # kicks off the job runner

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
        """
        LOG.info("Gracefully stopping broker now")
        super().stop()
        self.executor_broker.stop()


# Run this directly to try it out
if __name__ == "__main__":
    # Fire up the broker on localhost
    broker = VectorClockBroker(["127.0.0.1"], 8000)
    try:
        result = broker.run()
        LOG.info(f"Exited with status: {result}")
    except KeyboardInterrupt:
        LOG.info("User ended the session")
        broker.stop()
    except Exception as e:
        LOG.error(f"Something broke: {e}")
        broker.stop()
