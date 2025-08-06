# UCP Data Flow Analysis

**Student**: Sina Fadavi  
**Date**: August 2, 2025  

## Current System Data Flow

### Normal Job Processing Flow
```
1. Client submits job
   POST /job → Broker (DataBroker)
   
2. Job gets queued  
   DataBroker → adds to pending_jobs
   DataBroker → calls ExecutorBroker.add_pending_job()
   
3. Job assignment
   ExecutorBroker.job_scheduler() → picks job from queue
   → finds suitable executor using capabilities
   → sends job to executor via HTTP
   
4. Job execution
   Executor receives job → runs WASM binary
   → stores results in datastore
   → reports completion to broker
   
5. Results retrieval
   Client → GET /results/{job_id} → Datastore
```

### Node Discovery and Communication
```
1. Node startup
   Each node registers with Zeroconf (automatic network discovery)
   
2. Heartbeat/Ping
   Nodes send periodic ping requests to check if others are alive
   GET /ping → returns node name and status
   
3. Executor registration  
   Executor → PUT /executors/register → Broker
   Broker tests connection and adds executor to available list
```

### Current Problems I Found

#### 1. No Event Ordering
```
Problem: What if two events happen at "same time"?
Example: 
- Executor A finishes job at 14:30:15
- Executor B finishes job at 14:30:15  
- Which one actually finished first?

Current system: Uses wall clock time (unreliable)
My solution: Vector clocks provide causal ordering
```

#### 2. Failure Handling Issues
```
Problem: What happens when executor fails?
Current behavior:
- Job just stays "running" forever
- No automatic redeployment 
- No cleanup of failed jobs

My solution: Vector clocks detect failures and handle redeployment
```

#### 3. Duplicate Results Problem
```
Problem: Executor fails, comes back, sends old results
Current behavior:
- System might accept duplicate results
- No way to know which result came "first"

My solution: Vector clocks determine causal ordering of results
```

## Planned Integration Points

### 1. Node.py Changes
```python
# Add to Node.__init__()
self.vector_clock = CapabilityAwareVectorClock(self.id, capabilities)

# Modify ping endpoint
@app.get("/ping")
def ping():
    return {
        "name": service_name,
        "vector_clock": self.vector_clock.clock,
        "capabilities": self.capabilities
    }
```

### 2. ExecutorBroker Changes
```python
# Add to job assignment
def assign_job(self, job_id, executor):
    # Increment vector clock for assignment event
    self.vector_clock.tick()
    
    # Include vector clock in job assignment
    assignment = {
        "job_id": job_id,
        "assigned_at": self.vector_clock.clock.copy(),
        "executor_id": executor.id
    }
```

### 3. Executor Changes  
```python
# Add to job completion reporting
def report_completion(self, job_id, result):
    # Increment vector clock for completion
    self.vector_clock.tick()
    
    # Include vector clock in result
    completion = {
        "job_id": job_id,
        "result": result,
        "completed_at": self.vector_clock.clock.copy()
    }
```

## Message Flow with Vector Clocks

### Enhanced Job Processing
```
1. Client → Broker: Submit job
   Broker vector clock: [Broker:1]
   
2. Broker → Executor: Assign job  
   Broker vector clock: [Broker:2]
   Message includes: {job_info, vector_clock: [Broker:2]}
   
3. Executor receives assignment
   Executor updates: [Broker:2, Executor:1] 
   Executor increments: [Broker:2, Executor:2]
   
4. Executor → Broker: Report completion
   Message includes: {result, vector_clock: [Broker:2, Executor:3]}
   
5. Broker receives result
   Broker updates: [Broker:2, Executor:3]
   Broker increments: [Broker:3, Executor:3]
```

### Failure Scenario with Vector Clocks
```
1. Executor fails during job execution
   Last known state: [Broker:2, Executor:2]
   
2. Broker detects failure (no heartbeat)
   Broker increments: [Broker:3, Executor:2]
   
3. Broker redeploys job to new executor
   New assignment: [Broker:4, Executor:2] 
   
4. Failed executor comes back, tries to submit old result
   Old result has: [Broker:2, Executor:2]
   Current state: [Broker:4, Executor:2, NewExecutor:1]
   
5. System rejects old result (causally earlier)
   Only accepts result from new executor
```

## Benefits of This Approach

### 1. Correct Event Ordering
- Always know which event happened before another
- Works even with network delays and clock skew

### 2. Proper Failure Handling  
- Detect when executors fail
- Redeploy jobs with correct causal context
- Reject stale results from recovered executors

### 3. Emergency Prioritization
- Hospital nodes get priority during medical emergencies
- Critical jobs processed first during disasters

### 4. Network Partition Tolerance
- System continues working during network problems  
- All nodes sync correctly when network restored

## Implementation Challenges

### 1. Threading Issues
- Multiple threads updating vector clocks
- Need locks to prevent race conditions
- Solution: Use thread-safe vector clock operations

### 2. HTTP Message Format
- Need to include vector clocks in HTTP requests
- Modify existing API endpoints carefully
- Solution: Add vector clock fields to existing messages

### 3. Backward Compatibility
- Don't break existing functionality
- Need to handle nodes without vector clocks
- Solution: Make vector clocks optional initially

## Next Steps

1. **Week 2**: Start with simple vector clock integration in Node.py
2. **Week 3**: Add vector clocks to job assignment process  
3. **Week 4**: Implement failure handling (main thesis requirement)
4. **Week 5**: Testing and performance optimization

---

**Understanding Level**: 80% - I understand the system well enough to start implementation  
**Confidence**: High - Clear plan for integration without breaking existing code
