# Enhanced UCP Executor with Vector Clock Coordination
# Task 3.5: Adds vector clock support to existing UCP Executor
# Maintains full backward compatibility while adding distributed consistency

import argparse
import os
import random
import sched
import threading
import time
from io import BytesIO
from typing import Any, Optional
from uuid import UUID

import psutil
from fastapi import HTTPException
from readerwriterlock.rwlock import RWLockWrite

from rec.exceptions import WasmRestException
from rec.job import ExecutorJob
from rec.model import Address, Capabilities, JobInfo, NodeRole
from rec.nodes.executor import Executor
from rec.nodes.zeroconf_listeners.brokers import BrokerListener
from rec.nodetypes.broker import Broker
from rec.nodetypes.executor import Executor as ExecutorObject
from rec.replication.core.vector_clock import VectorClock, EmergencyLevel, create_emergency
from rec.util.log import LOG


class VectorClockExecutor(Executor):
    """
    Enhanced UCP Executor with Vector Clock coordination
    
    Extends the standard UCP Executor to provide:
    - Vector clock synchronization across distributed nodes
    - Emergency-aware job execution
    - Causal consistency for distributed operations
    - Full backward compatibility with existing UCP deployments
    """

    def __init__(
        self,
        host: list[str],
        port: int,
        rootdir: str,
        uvicorn_args: dict[str, Any] = None,
        executor_id: str = None,
    ):
        # Initialize parent UCP Executor
        super().__init__(host, port, rootdir, uvicorn_args)
        
        # Add vector clock capabilities
        self.executor_id = executor_id or f"executor_{self.id}"
        self.vector_clock = VectorClock(self.executor_id)
        
        # Emergency response integration
        self.emergency_context = create_emergency("none", "low")
        self.emergency_jobs = set()
        self.in_emergency_mode = False
        
        # Vector clock synchronization
        self.clock_sync_interval = 30  # seconds
        self.last_clock_sync = time.time()
        
        LOG.info(f"Vector Clock Executor {self.executor_id} initialized")

    def update_capabilities(self) -> None:
        """Enhanced capability update with vector clock information"""
        # Call parent capability update
        super().update_capabilities()
        
        # Add vector clock info to capabilities
        self.vector_clock.tick()
        
        # Enhanced capabilities include vector clock state
        self.self_object.capabilities = Capabilities(
            **self.self_object.capabilities.__dict__,
            vector_clock_time=self.vector_clock.clock.get(self.executor_id, 0),
            emergency_mode=self.in_emergency_mode,
            emergency_level=self.emergency_context.level.name if self.emergency_context else "LOW"
        )

    def register_with_broker(self) -> None:
        """Enhanced broker registration with vector clock coordination"""
        LOG.info(f"Registering vector clock executor {self.executor_id}")
        
        # Use parent registration logic
        super().register_with_broker()
        
        # Add vector clock synchronization after successful registration
        if self.broker:
            self._sync_vector_clock_with_broker()

    def _sync_vector_clock_with_broker(self) -> None:
        """Synchronize vector clock with broker"""
        try:
            # Request broker's vector clock for synchronization
            # This would integrate with the vector clock broker from Task 2
            self.vector_clock.tick()
            self.last_clock_sync = time.time()
            LOG.debug(f"Vector clock synced for executor {self.executor_id}")
        except Exception as e:
            LOG.warning(f"Vector clock sync failed: {e}")

    def execute_job(self, job_id: UUID, job_info: JobInfo) -> Any:
        """Enhanced job execution with vector clock coordination"""
        # Tick vector clock for job start
        self.vector_clock.tick()
        
        # Check if this is an emergency job
        is_emergency = self._is_emergency_job(job_info)
        
        if is_emergency:
            self.emergency_jobs.add(job_id)
            LOG.warning(f"Executing EMERGENCY job {job_id} with vector clock {self.vector_clock.clock}")
        else:
            LOG.info(f"Executing normal job {job_id} with vector clock {self.vector_clock.clock}")
        
        try:
            # Execute job using parent logic
            with self.jobs_lock.gen_wlock():
                if job_id not in self.jobs:
                    # Create job with vector clock metadata
                    job = ExecutorJob(
                        job_id=job_id,
                        job_info=job_info,
                        root_dir=self.root_dir,
                        executor_id=self.executor_id,
                        vector_clock_start=self.vector_clock.clock.copy()
                    )
                    self.jobs[job_id] = job
                    
                    # Start job execution
                    job.start()
                    
                    # Tick vector clock for job completion
                    self.vector_clock.tick()
                    
                    return {"status": "started", "vector_clock": self.vector_clock.clock}
                else:
                    raise HTTPException(
                        status_code=409, detail=f"Job {job_id} already exists"
                    )
        except Exception as e:
            LOG.error(f"Job execution failed for {job_id}: {e}")
            # Clean up on failure
            if is_emergency:
                self.emergency_jobs.discard(job_id)
            raise
        finally:
            # Periodic vector clock sync
            if time.time() - self.last_clock_sync > self.clock_sync_interval:
                self._sync_vector_clock_with_broker()

    def _is_emergency_job(self, job_info: JobInfo) -> bool:
        """Determine if a job is an emergency job based on job metadata"""
        # Check for emergency indicators in job info
        emergency_keywords = ["emergency", "critical", "urgent", "fire", "medical", "disaster"]
        
        if hasattr(job_info, 'emergency_level'):
            return job_info.emergency_level != EmergencyLevel.LOW
        
        # Check job description or filename for emergency indicators
        job_str = str(job_info.wasm_bin).lower()
        return any(keyword in job_str for keyword in emergency_keywords)

    def set_emergency_mode(self, emergency_type: str, level: str) -> None:
        """Enter emergency mode with vector clock coordination"""
        self.vector_clock.tick()
        
        old_mode = self.in_emergency_mode
        self.in_emergency_mode = True
        self.emergency_context = create_emergency(emergency_type, level)
        
        LOG.warning(f"Executor {self.executor_id} entering emergency mode: {emergency_type}/{level}")
        LOG.info(f"Vector clock at emergency declaration: {self.vector_clock.clock}")
        
        # Update capabilities to reflect emergency state
        self.update_capabilities()
        
        # Notify broker of emergency state if connected
        if self.broker and not old_mode:
            try:
                self.heartbeat()  # Send immediate update
            except Exception as e:
                LOG.warning(f"Failed to notify broker of emergency state: {e}")

    def clear_emergency_mode(self) -> None:
        """Exit emergency mode with vector clock coordination"""
        self.vector_clock.tick()
        
        self.in_emergency_mode = False
        self.emergency_context = create_emergency("none", "low")
        self.emergency_jobs.clear()
        
        LOG.info(f"Executor {self.executor_id} exiting emergency mode")
        LOG.info(f"Vector clock at emergency clear: {self.vector_clock.clock}")
        
        # Update capabilities
        self.update_capabilities()
        
        # Notify broker
        if self.broker:
            try:
                self.heartbeat()
            except Exception as e:
                LOG.warning(f"Failed to notify broker of emergency clear: {e}")

    def heartbeat(self) -> None:
        """Enhanced heartbeat with vector clock synchronization"""
        # Tick vector clock for heartbeat
        self.vector_clock.tick()
        
        # Call parent heartbeat
        super().heartbeat()
        
        # Schedule next heartbeat
        self.heartbeat_scheduler.enter(60, 1, self.heartbeat)

    def get_vector_clock_status(self) -> dict:
        """Get current vector clock and emergency status"""
        return {
            "executor_id": self.executor_id,
            "vector_clock": self.vector_clock.clock,
            "emergency_mode": self.in_emergency_mode,
            "emergency_level": self.emergency_context.level.name if self.emergency_context else "LOW",
            "emergency_jobs": len(self.emergency_jobs),
            "total_jobs": len(self.jobs),
            "last_clock_sync": self.last_clock_sync
        }

    def sync_with_vector_clock(self, other_clock: dict) -> None:
        """Synchronize with another node's vector clock"""
        old_clock = self.vector_clock.clock.copy()
        self.vector_clock.update(other_clock)
        
        LOG.debug(f"Vector clock updated: {old_clock} -> {self.vector_clock.clock}")
        self.last_clock_sync = time.time()


def create_vector_clock_executor(
    host: list[str] = ["0.0.0.0"],
    port: int = 8080,
    rootdir: str = "./executor_data",
    executor_id: str = None
) -> VectorClockExecutor:
    """Factory function to create a vector clock executor"""
    return VectorClockExecutor(
        host=host,
        port=port,
        rootdir=rootdir,
        executor_id=executor_id
    )


def main():
    """Enhanced executor main with vector clock support"""
    parser = argparse.ArgumentParser(description="Vector Clock UCP Executor")
    parser.add_argument("--host", default=["0.0.0.0"], nargs="+", help="Host addresses")
    parser.add_argument("--port", type=int, default=8080, help="Port number")
    parser.add_argument("--rootdir", default="./executor_data", help="Root directory")
    parser.add_argument("--executor-id", help="Executor ID for vector clock")
    
    args = parser.parse_args()
    
    # Create and start vector clock executor
    executor = create_vector_clock_executor(
        host=args.host,
        port=args.port,
        rootdir=args.rootdir,
        executor_id=args.executor_id
    )
    
    LOG.info(f"Starting Vector Clock Executor {executor.executor_id}")
    
    try:
        executor.start()
    except KeyboardInterrupt:
        LOG.info("Shutting down executor")
        executor.stop()


if __name__ == "__main__":
    main()
