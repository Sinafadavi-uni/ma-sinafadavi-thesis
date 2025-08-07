# 🛡️ Fault Tolerance Module

This module provides comprehensive fault tolerance capabilities for the distributed computing platform.

## Structure

```
rec/nodes/fault_tolerance/
├── __init__.py                    # Module exports and organization
├── advanced_fault_tolerance.py   # Multi-level fault detection and recovery
├── byzantine_tolerance.py        # Byzantine fault tolerance and consensus
└── integration_system.py         # Complete system integration
```

## Components

### Advanced Fault Tolerance (`advanced_fault_tolerance.py`)
- **SimpleFaultDetector**: Heartbeat-based health monitoring
- **SimplePartitionDetector**: Network partition detection
- **AdvancedRecoveryManager**: Job backup and recovery system

### Byzantine Tolerance (`byzantine_tolerance.py`) 
- **SimpleByzantineDetector**: Reputation-based Byzantine node detection
- **SimpleConsensusManager**: Voting-based consensus for critical decisions

### Integration System (`integration_system.py`)
- **Task7FaultToleranceSystem**: Complete fault tolerance integration
- **SystemHealth**: Health monitoring and trend analysis
- **demo_complete_fault_tolerance()**: Demonstration function

## Usage

```python
from rec.nodes.fault_tolerance import (
    Task7FaultToleranceSystem,
    SimpleFaultDetector,
    SimpleByzantineDetector
)

# Create complete fault tolerance system
system = Task7FaultToleranceSystem("my_system")

# Register nodes and start monitoring
system.register_node("node_1")
system.perform_health_check()
```

## Features

- ✅ Multi-level fault detection (heartbeat, partition, Byzantine)
- ✅ Automatic recovery and job backup systems  
- ✅ Emergency protocol activation/deactivation
- ✅ Consensus-based critical decision making
- ✅ System health trend analysis
- ✅ Student-friendly, educational code structure

## Integration

This module integrates seamlessly with:
- Vector Clock Foundation (Task 1)
- Emergency Response System (Tasks 2-3)
- FCFS Executor (Task 5)
- Performance Framework (Task 6)
