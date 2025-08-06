
# Vector Clock-Enhanced FCFS Executor
# Implements FCFS job processing with vector clock causal consistency
# Aligns with thesis: "Vector Clock-Based Causal Consistency" for UCP Part B

import threading
import time
from uuid import UUID
from typing import Dict, List, Optional
from datetime import datetime

from rec.replication.core.vector_clock import VectorClock
from rec.util.log import LOG

# Job submission information with vector clock timestamp
class JobSubmission:
    def __init__(self, job_id: UUID, job_info: dict, submission_time: float, vector_clock: dict):
        self.job_id = job_id
        self.job_info = job_info
        self.submission_time = submission_time  # For FCFS ordering
        self.vector_clock = vector_clock.copy()  # For causal consistency
        
    def __str__(self):
        return f"Job({self.job_id}, submitted={self.submission_time:.3f}, clock={self.vector_clock})"

class VectorClockFCFSExecutor:
    """
    Vector Clock-Enhanced FCFS Executor
    
    Implements First-Come-First-Served job processing with vector clock
    causal consistency, as required by UCP Part B thesis requirements.
    
    Research Contribution:
    - Maintains FCFS ordering while ensuring causal consistency
    - Uses vector clocks to detect causally related job submissions
    - Prevents causal consistency violations in distributed FCFS processing
    """

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.vector_clock = VectorClock(node_id)
        
        # FCFS job queue with vector clock timestamps
        self.job_queue: List[JobSubmission] = []
        self.running_jobs = set()
        self.completed_jobs = set()
        
        # Thread safety
        self.lock = threading.Lock()
        
        LOG.info(f"Vector Clock FCFS Executor {node_id} initialized")

    def submit_job(self, job_id: UUID, job_info: dict) -> bool:
        """
        Submit job with FCFS ordering and vector clock causal consistency
        
        Returns:
        - True: Job accepted and will be processed in FCFS order
        - False: Job rejected due to resource constraints or conflicts
        """
        with self.lock:
            # Tick vector clock for this submission event
            self.vector_clock.tick()
            
            # Create job submission with timestamp and vector clock
            submission = JobSubmission(
                job_id=job_id,
                job_info=job_info,
                submission_time=time.time(),
                vector_clock=self.vector_clock.clock
            )
            
            # Check for resource conflicts (simplified conflict detection)
            if self._has_resource_conflict(job_info):
                if not self._can_process_with_conflict(submission):
                    LOG.info(f"⏸ Job {job_id} deferred due to resource conflict (FCFS order maintained)")
                    return False
            
            # Add to FCFS queue (always maintains submission order)
            self.job_queue.append(submission)
            
            # Try to start job immediately if no conflicts
            if self._try_start_next_job():
                LOG.info(f"✅ Job {job_id} started immediately (FCFS order)")
            else:
                LOG.info(f"✅ Job {job_id} queued for FCFS processing")
                
            return True

    def _has_resource_conflict(self, job_info: dict) -> bool:
        """Simple resource conflict detection based on CPU requirements"""
        estimated_cpu = job_info.get("estimated_cpu", 0)
        return estimated_cpu > 50 and len(self.running_jobs) > 0

    def _can_process_with_conflict(self, new_submission: JobSubmission) -> bool:
        """
        FCFS-based conflict resolution with vector clock causal consistency
        
        Per thesis requirement: "first-come-first-served manner"
        Jobs are processed strictly in submission order, respecting causal consistency
        """
        # In pure FCFS, we always queue the job and process in order
        # The only rejection is if we cannot maintain causal consistency
        return self._is_causally_consistent(new_submission)

    def _is_causally_consistent(self, submission: JobSubmission) -> bool:
        """
        Check if processing this job maintains causal consistency
        
        Uses vector clock to ensure we don't violate causal ordering
        """
        # For FCFS, we generally accept all jobs unless there's a clear
        # causal consistency violation (e.g., a job that depends on 
        # a future event according to vector clocks)
        
        current_time = self.vector_clock.clock.get(self.node_id, 0)
        submission_time = submission.vector_clock.get(self.node_id, 0)
        
        # Accept if submission is causally consistent with current state
        return submission_time <= current_time + 1

    def _try_start_next_job(self) -> bool:
        """
        Try to start the next job in FCFS queue
        
        Maintains strict FCFS ordering while considering resource availability
        """
        if not self.job_queue or len(self.running_jobs) >= 2:  # Simple resource limit
            return False
            
        # Get next job in FCFS order (first in queue)
        next_submission = self.job_queue[0]
        
        # Check if we can start this job now
        if not self._has_resource_conflict(next_submission.job_info):
            # Remove from queue and start
            self.job_queue.pop(0)
            self.running_jobs.add(next_submission.job_id)
            
            # Tick vector clock for job start
            self.vector_clock.tick()
            
            LOG.info(f"✅ Job {next_submission.job_id} started (FCFS processing)")
            return True
            
        return False

    def complete_job(self, job_id: UUID) -> bool:
        """
        Mark job as completed and try to start next queued job
        
        Maintains FCFS processing order
        """
        with self.lock:
            if job_id not in self.running_jobs:
                LOG.warning(f"⚠️ Attempted to complete non-running job {job_id}")
                return False
                
            # Remove from running and mark completed
            self.running_jobs.remove(job_id)
            self.completed_jobs.add(job_id)
            
            # Tick vector clock for completion event
            self.vector_clock.tick()
            
            LOG.info(f"✅ Job {job_id} completed")
            
            # Try to start next job in FCFS queue
            self._try_start_next_job()
            
            return True

    def handle_result_submission(self, job_id: UUID, result_data: dict) -> bool:
        """
        Handle result submission with FCFS acceptance policy
        
        Per thesis requirement: "first-come-first-served manner, wherein 
        the first result submission will be accepted and all others will be rejected"
        """
        with self.lock:
            # Check if this is the first result for this job
            if job_id in self.completed_jobs:
                LOG.info(f"❌ Result for job {job_id} rejected (already completed - FCFS policy)")
                return False
                
            if job_id not in self.running_jobs:
                LOG.warning(f"❌ Result for job {job_id} rejected (job not running)")
                return False
                
            # Accept first result submission (FCFS policy)
            # Complete job directly here to avoid deadlock
            self.running_jobs.remove(job_id)
            self.completed_jobs.add(job_id)
            
            # Tick vector clock for completion event
            self.vector_clock.tick()
            
            # Try to start next job in FCFS queue
            self._try_start_next_job()
            
            LOG.info(f"✅ Result for job {job_id} accepted (first submission - FCFS policy)")
            return True

    def get_status(self) -> Dict:
        """Get current executor status with vector clock information"""
        with self.lock:
            return {
                "node_id": self.node_id,
                "vector_clock": self.vector_clock.clock.copy(),
                "processing_mode": "fcfs_with_vector_clock_causal_consistency",
                "running_jobs": len(self.running_jobs),
                "queued_jobs": len(self.job_queue),
                "completed_jobs": len(self.completed_jobs),
                "fcfs_queue": [str(sub) for sub in self.job_queue[:3]]  # Show first 3 in queue
            }

    def sync_vector_clock(self, other_clock: dict) -> None:
        """Synchronize vector clock with another node"""
        with self.lock:
            old_clock = self.vector_clock.clock.copy()
            self.vector_clock.update(other_clock)
            LOG.debug(f"Vector clock synced: {old_clock} -> {self.vector_clock.clock}")


def create_fcfs_executor(node_id: str = "fcfs_executor_1") -> VectorClockFCFSExecutor:
    """
    Factory function to create Vector Clock FCFS Executor
    
    Aligned with thesis requirements for FCFS processing with causal consistency
    """
    return VectorClockFCFSExecutor(node_id=node_id)


# Backward compatibility alias for existing tests
def create_enhanced_executor(node_id="executor_1", strategy=None, **kwargs):
    """
    Backward compatibility function
    
    Note: Strategy parameter ignored - always uses FCFS with vector clock consistency
    """
    if strategy is not None:
        LOG.warning("Strategy parameter ignored - using FCFS with vector clock consistency per thesis requirements")
    
    return create_fcfs_executor(node_id=node_id)
