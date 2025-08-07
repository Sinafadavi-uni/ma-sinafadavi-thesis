# GitHub Copilot Instructions for Urban Computing Platform (UCP) Thesis Project

## Project Overview

This is a **master's thesis project** implementing **distributed vector clock-based data replication** for the **Urban Computing Platform (UCP)**. The system focuses on **emergency response scenarios** with **causal consistency** guarantees and **FCFS (First-Come-First-Serve) policies**.

### Core Architecture
- **Python 3.12.3** project with virtual environment
- **UCP Integration**: Extends existing Urban Computing Platform
- **Vector Clock Foundation**: Distributed consistency algorithms
- **Emergency Response**: Specialized handling for emergency scenarios
- **Multi-Node Coordination**: Broker-executor architecture
- **WASM Support**: WebAssembly job execution capabilities

## Task Structure & File Organization

### Task 1: Vector Clock Foundation
**File**: `rec/replication/core/vector_clock.py`
- **Purpose**: Core vector clock algorithms for distributed consistency
- **Key Classes**: `VectorClock`, `EmergencyLevel`, `Emergency`
- **Methods**: `tick()`, `update()`, `compare()`, `create_emergency()`
- **Testing**: Complete with causal consistency validation

### Task 2: Emergency Detection and Response (Broker-level)
**Files**: 
- `rec/replication/core/vector_clock.py` (emergency types)
- **Key Components**: Emergency classification, priority handling
- **Integration**: Broker-level emergency detection patterns

### Task 3: Emergency Response System (Executor-level)
**Files**:
- `rec/nodes/emergency_executor.py` - SimpleEmergencyExecutor
- `rec/nodes/emergency_integration.py` - SimpleEmergencySystem
- `rec/nodes/recovery_system.py` - SimpleRecoveryManager
- **Purpose**: Educational emergency handling at executor level
- **Key Features**: Job prioritization, recovery management

### Task 3.5: UCP Executor Enhancement
**File**: `rec/nodes/vector_clock_executor.py`
- **Purpose**: Enhanced UCP executor with vector clock coordination
- **Class**: `VectorClockExecutor` (extends base UCP Executor)
- **Integration**: Production UCP architecture compliance
- **Requirements**: host, port, rootdir, executor_id parameters

### Task 4: ~~Multi-Broker Coordination~~ (REMOVED per UCP Part B requirements)
**Files**: `rec/nodes/brokers/multi_broker_coordinator.py`
- **Status**: Core components exist but full datastore removed
- **Classes**: `BrokerMetadata`, `PeerBroker` (foundation only)

### Task 5: Enhanced FCFS Executor
**File**: `rec/nodes/enhanced_vector_clock_executor.py`
- **Class**: `VectorClockFCFSExecutor`
- **Purpose**: FCFS policy implementation with vector clock coordination
- **Key Methods**: `submit_job()`, `handle_result_submission()`
- **Policy**: First result wins, subsequent results rejected

### Task 6: Performance Optimization Framework
**Files**:
- `rec/performance/vector_clock_optimizer.py` - VectorClockOptimizer
- `rec/performance/benchmark_suite.py` - PerformanceBenchmarkSuite
- `rec/performance/scalability_tester.py` - UrbanScalabilityTester
- **Purpose**: Production-grade performance optimization for vector clock operations
- **Key Classes**: `SimpleVCOptimizer`, `SimpleBenchmarkSuite`, `SimpleUrbanTester`
- **Features**: Performance metrics, resource monitoring, urban scenario testing

## Development Guidelines

### Testing Strategy
- **Framework**: PyTest with comprehensive validation
- **Files**: 
  - `tests/test_installation.py` - Basic installation tests
  - `tests/test_performance_optimization.py` - Task 6 performance tests
  - `comprehensive_validation_corrected.py` - Full system validation
- **Coverage**: 30+ tests (20 unit + 10 comprehensive) - 100% pass rate
- **Command**: `python -m pytest tests/ -v`

### Code Patterns

#### Vector Clock Usage
```python
from rec.replication.core.vector_clock import VectorClock

# Always initialize with node_id
clock = VectorClock("node_name")

# Tick for local events
clock.tick()

# Update with other clocks (pass .clock dict, not object)
clock.update(other_clock.clock)

# Compare for causal relationships
result = clock.compare(other_clock)  # "before", "after", "concurrent"
```

#### UCP Integration Patterns
```python
from rec.nodes.vector_clock_executor import VectorClockExecutor

# Always provide required UCP parameters
executor = VectorClockExecutor(
    host=["127.0.0.1"], 
    port=9999, 
    rootdir="/tmp", 
    executor_id="unique_id"
)
```

#### FCFS Implementation Pattern
```python
from rec.nodes.enhanced_vector_clock_executor import VectorClockFCFSExecutor

executor = VectorClockFCFSExecutor(node_id="node_name")
job_id = uuid4()

# Submit job
executor.submit_job(job_id, job_data)

# Handle results (FCFS policy)
first_result = executor.handle_result_submission(job_id, result_data)   # True
second_result = executor.handle_result_submission(job_id, result_data)  # False
```

#### Performance Optimization Pattern
```python
from rec.performance.vector_clock_optimizer import VectorClockOptimizer
from rec.performance.benchmark_suite import PerformanceBenchmarkSuite
from rec.performance.scalability_tester import UrbanScalabilityTester

# Performance optimization
optimizer = VectorClockOptimizer("node_id", optimization_level="standard")
optimizer.optimized_tick()  # Measured tick operation
summary = optimizer.get_performance_summary()

# Benchmarking
benchmark = PerformanceBenchmarkSuite()
results = benchmark.run_all()

# Urban scalability testing
tester = UrbanScalabilityTester()
metrics = tester.run_all()
```

### Architectural Constraints

#### UCP Part B Compliance
- **No full datastore implementation** (removed per requirements)
- **Broker metadata synchronization** required
- **FCFS policy enforcement** mandatory
- **Vector clock integration** throughout all components

#### Emergency Response Requirements
- **Priority-based job handling** (emergency vs normal)
- **Causal consistency** for emergency events
- **Recovery mechanisms** for failed executors
- **Educational implementation** (not production emergency system)

### Dependencies & Environment

#### Required Packages
```toml
# pyproject.toml dependencies
wasmtime = "^24.0.0"
fastapi = "^0.115.4"
numpy = "^2.1.3"
pytest = "^8.4.1"
```

#### Environment Setup
```bash
# Virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -e .
```

### Testing Workflows

#### Full System Validation
```bash
# Run comprehensive tests
python comprehensive_validation_corrected.py

# Expected output: All tasks ✅ WORKING
# UCP Part B Compliance ✅ VERIFIED
```

#### Unit Testing
```bash
# PyTest for specific components
python -m pytest tests/test_installation.py -v
python -m pytest tests/test_performance_optimization.py -v
python -m pytest tests/ -v
```

#### Performance Testing
```bash
# Run performance benchmarks
python -c "from rec.performance.benchmark_suite import PerformanceBenchmarkSuite; PerformanceBenchmarkSuite().run_all()"

# Urban scalability tests
python -c "from rec.performance.scalability_tester import UrbanScalabilityTester; UrbanScalabilityTester().run_all()"
```

#### Manual Testing Pattern
```python
# Always test vector clock operations
def test_component():
    clock = VectorClock("test_node")
    clock.tick()
    assert clock.clock["test_node"] == 1
```

## Common Pitfalls & Solutions

### Vector Clock Integration
- **❌ WRONG**: `clock.update(other_clock)` (passing object)
- **✅ CORRECT**: `clock.update(other_clock.clock)` (passing dict)

### UCP Executor Parameters
- **❌ WRONG**: Missing required parameters in VectorClockExecutor
- **✅ CORRECT**: Always provide host, port, rootdir, executor_id

### FCFS Policy Testing
- **❌ WRONG**: Expecting all results to be accepted
- **✅ CORRECT**: First result True, subsequent False

### Performance Optimization Testing
- **❌ WRONG**: Running performance tests without baseline
- **✅ CORRECT**: Establish baseline before optimization with `benchmark.run_all()`

### Urban Scalability Testing
- **❌ WRONG**: Testing only single-node scenarios
- **✅ CORRECT**: Use `UrbanScalabilityTester` for multi-zone city simulations

## File Import Patterns

```python
# Vector Clock Foundation
from rec.replication.core.vector_clock import VectorClock, EmergencyLevel, create_emergency

# Emergency Systems
from rec.nodes.emergency_executor import SimpleEmergencyExecutor
from rec.nodes.emergency_integration import SimpleEmergencySystem
from rec.nodes.recovery_system import SimpleRecoveryManager

# UCP Integration
from rec.nodes.vector_clock_executor import VectorClockExecutor

# FCFS Implementation
from rec.nodes.enhanced_vector_clock_executor import VectorClockFCFSExecutor

# Broker Components
from rec.nodes.brokers.multi_broker_coordinator import BrokerMetadata, PeerBroker

# Performance Optimization (Task 6)
from rec.performance.vector_clock_optimizer import VectorClockOptimizer, MultiNodeOptimizer
from rec.performance.benchmark_suite import PerformanceBenchmarkSuite, SimpleBenchmarkSuite
from rec.performance.scalability_tester import UrbanScalabilityTester, SimpleUrbanTester
```

## Thesis Context

This codebase represents a **complete implementation** of distributed vector clock-based data replication for emergency response scenarios. The focus is on **causal consistency**, **FCFS policies**, and **UCP integration** rather than production emergency systems.

**All Tasks 1, 2, 3, 3.5, 5, and 6 are COMPLETE and VALIDATED**. Task 4 was removed per UCP Part B requirements. The system demonstrates distributed computing concepts for academic evaluation.

When working with this codebase:
1. **Maintain causal consistency** in all distributed operations
2. **Follow FCFS policies** for result handling
3. **Respect UCP integration patterns** for production compatibility
4. **Use comprehensive testing** before any modifications
5. **Focus on thesis requirements** rather than production features

## Project Status & Implementation Progress

### Completed Tasks ✅
1. **Task 1**: Vector Clock Foundation - COMPLETE
2. **Task 2**: Emergency Detection (Broker) - COMPLETE  
3. **Task 3**: Emergency Response System (Executor) - COMPLETE
4. **Task 3.5**: UCP Executor Enhancement - COMPLETE
5. **Task 5**: Enhanced FCFS Executor - COMPLETE
6. **Task 6**: Performance Optimization Framework - COMPLETE

### Implementation Metrics ✅
- **Total Code**: 2,000+ lines production-quality implementation
- **Test Coverage**: 30+ tests with 100% pass rate (6 Task 6 performance tests added)
- **UCP Part B Compliance**: 100% requirements fulfilled
- **Performance Framework**: Complete with benchmarking and scalability testing
- **Documentation**: Comprehensive technical and thesis documentation

### Task 6 Performance Components
- **Vector Clock Optimizer**: `rec/performance/vector_clock_optimizer.py`
  - `SimpleVCOptimizer` with performance tracking
  - `VectorClockOptimizer` with advanced caching and metrics
  - `MultiNodeOptimizer` for distributed coordination
- **Benchmark Suite**: `rec/performance/benchmark_suite.py`
  - `SimpleBenchmarkSuite` for resource monitoring
  - `PerformanceBenchmarkSuite` for comprehensive testing
  - Real-time CPU and memory tracking
- **Scalability Tester**: `rec/performance/scalability_tester.py`
  - `SimpleUrbanTester` for city-scale simulations
  - Multi-zone scenario testing with configurable parameters
  - Emergency and normal job processing simulation

### Next Phase 🚀
- **Task 7**: Advanced Fault Tolerance & Recovery
- **Task 8**: Academic Validation & Benchmarking
- **Task 9**: Demonstration & Visualization
- **Task 10**: Thesis Documentation & Final Delivery

### Academic Timeline
- **Current Progress**: 60% complete (6/10 tasks)
- **Thesis Writing**: Can proceed in parallel
- **Expected Completion**: End of August 2025
