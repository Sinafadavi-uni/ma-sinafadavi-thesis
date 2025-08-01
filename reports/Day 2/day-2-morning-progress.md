# Day 2 Progress Report - UCP Architecture Analysis

**Date**: August 2, 2025  
**Student**: Sina Fadavi  
**Focus**: Understanding existing Urban Compute Platform (UCP) architecture  

## Morning Session (9:00 AM - 1:00 PM)

### What I'm Learning Today
Today I need to understand how the existing system works before I can add my vector clocks to it. It's like learning how a car engine works before you try to add new parts to it.

### Current System Analysis

#### 1. Main Components I Found
Looking through the code, I found these main parts:
- **Broker**: Manages jobs and decides which executor should run them
- **Executor**: Actually runs the jobs (like running programs)
- **Datastore**: Stores files and results
- **Client**: Sends jobs to the system

#### 2. How They Talk to Each Other
I'm still figuring this out, but it looks like:
```
Client → Broker → Executor → Datastore
```

The client sends a job to the broker, broker picks an executor, executor runs it and saves results to datastore.

### What I Discovered So Far

#### Heartbeat System
In the node.py file, I found something called "heartbeat" - it's like the nodes saying "I'm still alive" to each other every few seconds. This is important because my vector clocks need to know when nodes are alive or dead.

#### Capability System  
In model.py, there's a Capabilities class that tracks:
- How much memory a node has
- How many CPU cores
- Power level
- If it has a battery

This is perfect! My vector clocks already work with capabilities for emergency prioritization.

### Challenges I'm Having
1. The code is more complex than my simple vector clock implementation
2. There are lots of networking parts I don't fully understand yet
3. I need to figure out where exactly to add my vector clocks

### Next Steps for Afternoon
1. Draw a simple diagram of how data flows
2. Find the exact spots where I can add vector clocks
3. Plan the integration without breaking existing code

## Learning Notes
- FastAPI is used for web APIs (I need to learn more about this)
- Zeroconf is for finding other nodes on the network automatically
- The system uses async/await which I'm still learning

## Questions for Myself
- Where exactly do nodes exchange messages?
- How does the broker keep track of all executors?
- What happens when a node crashes right now?

---
*Time spent: 4 hours*  
*Status: Learning and analyzing*
