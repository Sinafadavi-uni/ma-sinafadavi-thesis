# UCP Architecture Analysis - Day 2

**Student**: Sina Fadavi  
**Date**: August 2, 2025  

## What I Found Out Today

### Basic System Overview
After spending the morning reading code, I think I understand the basic structure now. Here's how it works:

```
1. Client sends job to Broker
2. Broker finds available Executor 
3. Executor runs the job
4. Results get stored in Datastore
```

### The Main Components

#### 1. Node.py - The Base Class
This is like the "parent" class that all other parts inherit from. Every node (broker, executor, datastore) is built on top of this. Key things it does:
- Creates a web server using FastAPI
- Has a `/ping` endpoint so other nodes can check if it's alive
- Uses something called "zeroconf" to find other nodes automatically
- Has a unique ID (UUID) for each node

#### 2. Broker.py - The Job Manager
The broker is like the "boss" that assigns work. It has two main parts:
- **DataBroker**: Handles data storage and retrieval
- **ExecutorBroker**: Manages which executor gets which job

#### 3. ExecutorBroker.py - The Scheduler
This is where the job scheduling happens. Important things I learned:
- Keeps a list of all available executors
- Has a queue of jobs waiting to be run
- Has a job_scheduler method that runs in a background thread
- Checks if executors are capable of running specific jobs

### Key Data Flow I Discovered

```
Job Submission:
Client → POST /job → DataBroker → adds to pending_jobs
                  → ExecutorBroker → adds to queued_jobs
                  
Job Processing:
job_scheduler() → picks job from queue → finds suitable executor
               → sends job to executor → executor runs it
               → results go back to datastore
```

### Where Vector Clocks Can Fit In

I think I found the perfect spots to add my vector clocks:

1. **Node Registration**: When executors register with broker
2. **Job Assignment**: When broker assigns job to executor  
3. **Job Completion**: When executor reports results back
4. **Heartbeat/Ping**: Regular status updates between nodes

### Current Problems This System Has

Looking at the code, I can see some issues that my vector clocks will solve:

1. **No proper ordering**: If two jobs finish at "same time", which one actually finished first?
2. **Executor failure**: What happens if executor dies while running a job?
3. **Network problems**: What if broker and executor can't talk for a while?
4. **Duplicate results**: What if executor comes back and sends old results?

All of these are exactly what vector clocks are designed to fix!

## Implementation Plan

### Phase 1: Add Vector Clocks to Base Node
- Modify Node.py to include a vector clock
- Add vector clock to ping/heartbeat messages
- Simple changes, shouldn't break anything

### Phase 2: Job Assignment with Vector Clocks  
- Modify ExecutorBroker to use vector clocks when assigning jobs
- Each job gets a vector timestamp when assigned
- Track job state changes with causal ordering

### Phase 3: Result Handling with Causal Consistency
- Modify result submission to include vector clocks
- Detect and handle duplicate results properly  
- Implement the "first-come-first-served" requirement

## Challenges I Expect

1. **Async Programming**: The system uses async/await which I'm still learning
2. **Threading**: Multiple threads running at same time - need to be careful with vector clock updates
3. **Networking**: HTTP requests between nodes - need to send vector clocks with messages
4. **Integration**: Adding vector clocks without breaking existing functionality

## Next Steps for Tomorrow

1. Start with simple vector clock integration in Node.py
2. Test that basic functionality still works
3. Add vector clocks to job assignment process
4. Create simple test cases

## Learning Resources I Need
- More about FastAPI and HTTP requests
- Python threading and async programming
- How to modify existing code safely

---

**Time spent today**: 6 hours (4 hours analysis + 2 hours documentation)  
**Confidence level**: 70% - I understand the basic structure but need to learn more about the details
