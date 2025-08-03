# 🧪 Vector Clock + Emergency Broker
# This is my try at extending a job broker with vector clock support and emergency logic
# Includes pre-warming serverless functions and some basic heuristics

import time
import copy
import threading
from uuid import uuid4, UUID
from typing import Optional, Callable, List, Dict
from dataclasses import dataclass, field
from queue import Queue

from rec.nodes.node import Node
from rec.model import Capabilities, JobInfo
from rec.nodetypes.executor import Executor
from rec.util.log import LOG

from rec.replication.core.vector_clock import VectorClock, EmergencyContext, ExecutionType
from rec.replication.core.causal_message import CausalMessage, MessageHandler


@dataclass
class EnhancedQueuedJob:
    job_id: str
    command: str
    timestamp: float
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    priority: float = 1.0
    node_id: UUID = None
    vector_clock: VectorClock = None
    emergency_context: EmergencyContext = None
    execution_type: ExecutionType = ExecutionType.TRADITIONAL
    function_name: Optional[str] = None
    requires_pre_warm: bool = False


class VectorClockExecutorBroker(Node):
    def __init__(self, capabilities: Capabilities, port: int = 8080, on_job_started: Optional[Callable[[str, str], None]] = None):
        super().__init__(host=["localhost"], port=port)
        
        # Store capabilities separately since Node doesn't handle them
        self.capabilities = capabilities

        self.node_id = uuid4()
        self.vector_clock = VectorClock(self.node_id)
        self.message_handler = MessageHandler(self.node_id, capabilities)

        self.executors: Dict[UUID, Executor] = {}
        self.executor_lock = threading.Lock()
        self.queued_jobs = Queue()
        self.completed_jobs = set()
        self.should_exit = False

        self.emergency_context = EmergencyContext("none", "normal")
        self.emergency_jobs = set()

        self.serverless_jobs = set()
        self.warm_functions = set()
        self.serverless_functions = {}

        self._on_job_started = on_job_started
        LOG.info(f"Vector Clock Broker started with node ID {self.node_id}")

    def queue_job(self, job_id, command, description="", dependencies=None):
        if self.should_exit:
            raise RuntimeError("Broker is not active")

        if dependencies is None:
            dependencies = []

        is_emergency = self._check_emergency(command, description)
        priority = self._get_priority(command, description, is_emergency)
        execution_type = self._get_execution_type(command, description)

        # If job is emergency, update context
        if is_emergency:
            self._set_emergency_context(command, description)

        # Serverless-related info
        function_name = self._extract_function_name(command) if execution_type == ExecutionType.SERVERLESS else None
        needs_warm = self._should_warm(function_name, is_emergency)

        # Vector clock updated before queueing
        self.vector_clock.tick()

        job = EnhancedQueuedJob(
            job_id=job_id,
            command=command,
            timestamp=time.time(),
            description=description,
            dependencies=dependencies,
            priority=priority,
            node_id=self.node_id,
            vector_clock=copy.deepcopy(self.vector_clock),
            emergency_context=copy.deepcopy(self.emergency_context),
            execution_type=execution_type,
            function_name=function_name,
            requires_pre_warm=needs_warm
        )

        if is_emergency:
            self.emergency_jobs.add(job_id)

        if execution_type == ExecutionType.SERVERLESS:
            self.serverless_jobs.add(job_id)
            if needs_warm and function_name:
                self._warm_function(function_name)

        self.queued_jobs.put(job)
        LOG.info(f"Queued job {job_id} (type: {execution_type}, emergency: {is_emergency})")

        return job

    def _check_emergency(self, cmd, desc):
        keywords = ["fire", "urgent", "medical", "disaster", "critical"]
        content = (cmd + " " + desc).lower()
        return any(word in content for word in keywords)

    def _get_priority(self, cmd, desc, emergency):
        base = 1.0
        if emergency:
            if "critical" in cmd or desc:
                return base * 10
            elif "medical" in desc:
                return base * 8
            elif "fire" in desc:
                return base * 7
            return base * 5
        if "priority" in desc or "quick" in cmd:
            return base * 1.5
        return base

    def _get_execution_type(self, cmd, desc):
        text = (cmd + " " + desc).lower()
        if "lambda" in text or "invoke" in text or "serverless" in text:
            return ExecutionType.SERVERLESS
        return ExecutionType.TRADITIONAL

    def _set_emergency_context(self, cmd, desc):
        text = (cmd + " " + desc).lower()
        if "medical" in text:
            typ = "medical"
        elif "fire" in text:
            typ = "fire"
        elif "disaster" in text:
            typ = "disaster"
        else:
            typ = "general"

        severity = "high" if "critical" in text else "medium"
        self.emergency_context = EmergencyContext(typ, severity)
        LOG.info(f"Emergency set: {typ}/{severity}")

    def _extract_function_name(self, cmd):
        if "--function-name" in cmd:
            parts = cmd.split()
            if "--function-name" in parts:
                idx = parts.index("--function-name")
                if idx + 1 < len(parts):
                    return parts[idx + 1]
        return None

    def _should_warm(self, fname, emergency):
        if not fname:
            return False
        if emergency:
            return True
        stats = self.serverless_functions.get(fname, {})
        if stats.get("avg_cold_start_ms", 0) > 1000:
            return True
        last_time = stats.get("last_execution", 0)
        if time.time() - last_time > 300:
            return True
        return False

    def _warm_function(self, fname):
        if fname in self.warm_functions:
            return
        self.warm_functions.add(fname)
        self.serverless_functions.setdefault(fname, {})["pre_warmed_at"] = time.time()
        LOG.info(f"Function {fname} pre-warmed")

    def handle_message(self, message: CausalMessage):
        self.vector_clock.update(message.sender_id, message.timestamp)
        self.message_handler.handle_message(message)
        LOG.debug(f"Message from {message.sender_id} processed")

    def get_status(self):
        return {
            "node_id": str(self.node_id),
            "vector_clock": self.vector_clock.to_dict(),
            "emergency": {
                "type": self.emergency_context.emergency_type,
                "level": self.emergency_context.level
            },
            "queued": self.queued_jobs.qsize(),
            "emergency_jobs": len(self.emergency_jobs),
            "serverless_jobs": len(self.serverless_jobs),
            "warm_functions": len(self.warm_functions),
            "executors": len(self.executors)
        }
