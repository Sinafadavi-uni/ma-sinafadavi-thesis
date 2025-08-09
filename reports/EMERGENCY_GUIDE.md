# Emergency Response System - User Guide

## Overview

This implements a simple emergency response system for distributed executors. It builds on the vector clock foundation and broker integration from previous implementations.

## Key Features

### 🚨 Emergency-Aware Executors
- **Emergency Job Priority**: Emergency jobs always process before normal jobs
- **Emergency Modes**: Different emergency levels (LOW, MEDIUM, HIGH, CRITICAL)
- **Simple Queue Management**: Separate queues for normal and emergency jobs

### 🔄 Recovery System
- **Failure Detection**: Track which executors are healthy vs failed
- **Job Reassignment**: Automatically redistribute jobs from failed executors
- **System Coordination**: Coordinate emergency responses across multiple executors

### ⚡ Vector Clock Integration
- **Distributed Timing**: All components use vector clocks for coordination
- **Emergency Synchronization**: Clock updates when emergencies are declared
- **Simple Conflict Resolution**: Easy-to-understand ordering of events

## Quick Start

### 1. Create a Simple Emergency System

```python
from rec.nodes.emergency_integration import create_emergency_system

# Create the system
system = create_emergency_system("my_emergency_system")

# Add some executors
exec1 = system.add_executor("fire_station")
exec2 = system.add_executor("medical_center") 
exec3 = system.add_executor("general_service")
```

### 2. Submit Jobs

```python
# Submit normal jobs
normal_job = system.submit_normal_job()
print(f"Normal job submitted: {normal_job}")

# Submit emergency jobs
emergency_job = system.submit_emergency_job("fire")
print(f"Emergency job submitted: {emergency_job}")
```

### 3. Handle Emergencies

```python
# Declare system-wide emergency
system.declare_system_emergency("medical", "high")

# All executors now prioritize emergency jobs
# Normal jobs are paused during high/critical emergencies

# Clear emergency when resolved
system.clear_system_emergency()
```

### 4. Monitor System Status

```python
# Get overview of entire system
status = system.get_system_overview()
print(f"Healthy executors: {status['executor_summary']['healthy_executors']}")
print(f"Emergency active: {status['emergency_status']['active']}")
print(f"Jobs submitted: {status['job_counts']}")
```

## Components Overview

### SimpleEmergencyExecutor
**File**: `rec/nodes/emergency_executor.py`

Simple executor that can handle both normal and emergency jobs.

**Key Methods**:
- `receive_job(job_id, job_info, is_emergency=False)` - Add a job to the queue
- `set_emergency_mode(emergency_type, level)` - Enter emergency mode
- `clear_emergency_mode()` - Return to normal operation
- `get_status()` - Get current executor status

**Example**:
```python
from rec.nodes.emergency_executor import create_emergency_executor

executor = create_emergency_executor("my_executor")
executor.set_emergency_mode("fire", "high")
status = executor.get_status()
```

### SimpleRecoveryManager
**File**: `rec/nodes/recovery_system.py`

Manages executor health and job reassignment.

**Key Methods**:
- `register_executor(executor_id)` - Add executor to tracking
- `mark_executor_failed(executor_id, failed_jobs)` - Handle executor failure
- `declare_system_emergency(emergency_type, level)` - System-wide emergency
- `get_system_status()` - Get recovery system status

**Example**:
```python
from rec.nodes.recovery_system import SimpleRecoveryManager

recovery = SimpleRecoveryManager("recovery_manager")
recovery.register_executor("exec_1")
recovery.mark_executor_failed("exec_1", ["job_1", "job_2"])
```

### SimpleEmergencySystem
**File**: `rec/nodes/emergency_integration.py`

Complete integrated system bringing everything together.

**Key Methods**:
- `add_executor(executor_id)` - Add executor to system
- `submit_normal_job(job_info, target_executor)` - Submit normal job
- `submit_emergency_job(emergency_type, job_info)` - Submit emergency job
- `declare_system_emergency(emergency_type, level)` - System emergency
- `get_system_overview()` - Complete system status

## Emergency Levels

- **LOW**: Normal operation, emergency jobs have slight priority
- **MEDIUM**: Emergency jobs prioritized, normal jobs still process
- **HIGH**: Only emergency jobs process, normal jobs paused
- **CRITICAL**: Only emergency jobs process, normal jobs paused

## Testing

Run the complete test suite:
```bash
python -m pytest tests/test_emergency_simple.py -v
```

Run individual demos:
```python
# Complete system demo
from rec.nodes.emergency_integration import demo_complete_emergency
demo_complete_emergency()

# Individual component demos
from rec.nodes.emergency_executor import demo_emergency_executor
demo_emergency_executor()

from rec.nodes.recovery_system import demo_recovery_system
demo_recovery_system()
```

## Code Design Principles

### ✅ Student-Friendly
- **Simple Classes**: Clear, focused classes with single responsibilities
- **Descriptive Names**: Method and variable names that explain what they do
- **Minimal Complexity**: Avoided advanced patterns that might confuse students
- **Lots of Comments**: Clear explanations of what each part does

### ✅ Easy to Extend
- **Modular Design**: Each component can be used independently
- **Simple Interfaces**: Methods have clear inputs and outputs
- **Helper Functions**: Factory functions make it easy to create objects
- **Demo Functions**: Show how to use each component

### ✅ Practical Focus
- **Real-World Scenarios**: Emergency response, failure handling, job distribution
- **Observable Behavior**: Easy to see what's happening with status methods
- **Simple Testing**: Tests show how components work together

## Integration with Previous Tasks

### Vector Clock Foundation
- Uses `VectorClock` for all timing coordination
- Uses `EmergencyLevel` and `EmergencyContext` for emergency handling
- Integrates with serverless and capability-aware features

### Broker Integration
- Can work with `VectorClockBroker` for distributed coordination
- Uses same vector clock synchronization patterns
- Compatible with existing broker job submission

## Next Steps

After understanding the emergency response system, students can:

1. **Extend Emergency Types**: Add new emergency types with custom handling
2. **Improve Scheduling**: Add more sophisticated job scheduling algorithms  
3. **Add Persistence**: Store job state and recovery information
4. **Network Integration**: Connect with real network services
5. **Performance Monitoring**: Add metrics and performance tracking

## File Summary

**Emergency Response Files**:
- `rec/nodes/emergency_executor.py` - Emergency-aware executor
- `rec/nodes/recovery_system.py` - Recovery and coordination
- `rec/nodes/emergency_integration.py` - Complete integrated system
- `tests/test_emergency_simple.py` - Tests and examples

**Supporting Files** (from previous implementations):
- `rec/replication/core/vector_clock.py` - Vector clock foundation
- `rec/nodes/brokers/vector_clock_broker.py` - Broker integration
