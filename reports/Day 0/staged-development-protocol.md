# **Staged Development & Testing Protocol**

## **🎯 Development Philosophy**

**"No code advances without passing tests"**

Every piece of code must be developed in small, testable stages with mandatory testing gates between stages.

## **📋 Stage Development Rules**

### **Rule 1: Small, Focused Stages**
- Each stage should accomplish ONE clear objective
- Maximum 2-3 hours of coding per stage
- Each stage should be independently testable

### **Rule 2: Mandatory Testing Gates**
- **STOP RULE**: Cannot proceed to next stage until current stage passes ALL tests
- **NO EXCEPTIONS**: Even small changes require test validation
- **REGRESSION RULE**: Previous stages must still pass when new stages are added

### **Rule 3: Quality Gates**
- Linting must pass before testing
- Type checking must pass before testing  
- Documentation must be updated during development
- All tests must pass before Git commit

## **🔄 Stage Development Workflow**

### **Stage Planning (5 minutes)**
```
1. Define stage objective clearly
2. Identify what will be tested
3. Plan test cases before coding
4. Estimate time needed (max 3 hours)
```

### **Stage Implementation (1-3 hours)**
```
1. Write failing tests first (TDD approach)
2. Implement minimal code to pass tests
3. Refactor while keeping tests green
4. Add edge case tests as needed
```

### **Stage Validation (15-30 minutes)**
```
1. Run linting: flake8, isort
2. Run type checking: mypy
3. Run unit tests: pytest
4. Run integration tests (if applicable)
5. Manual testing for complex behavior
6. Update documentation
```

### **Stage Completion Checklist**
- [ ] **Functionality**: Feature works as designed
- [ ] **Testing**: All tests pass (unit + integration)
- [ ] **Quality**: Linting and type checking pass
- [ ] **Documentation**: Code is properly documented
- [ ] **Regression**: Previous stages still work
- [ ] **Ready**: Stage is ready for next stage to build upon

## **🧪 Testing Strategy per Implementation Phase**

### **Phase 1-2: Foundation & Research (Weeks 1-2)**

#### **Week 1 Stages:**
- **Stage 1**: Basic vector clock data structure
  - **Tests**: Clock creation, increment, comparison
- **Stage 2**: Capability integration  
  - **Tests**: Capability scoring, weight calculation
- **Stage 3**: Serialization support
  - **Tests**: msgpack serialization/deserialization

#### **Week 2 Stages:**
- **Stage 1**: Conflict resolution algorithm
  - **Tests**: Concurrent update scenarios, capability weighting
- **Stage 2**: Energy-aware synchronization
  - **Tests**: Battery simulation, adaptive sync frequency  
- **Stage 3**: Message protocol
  - **Tests**: Message creation, processing, validation

### **Phase 3-4: Broker & Executor (Weeks 3-6)**

#### **Typical Daily Stages:**
- **Stage 1**: Core integration (2-3 hours)
  - **Tests**: Basic functionality with existing UCP code
- **Stage 2**: Causal consistency (2-3 hours)  
  - **Tests**: Causal ordering, dependency satisfaction
- **Stage 3**: Error handling & edge cases (1-2 hours)
  - **Tests**: Failure scenarios, recovery mechanisms

### **Phase 5-6: Datastore & Integration (Weeks 7-12)**

#### **Advanced Stage Strategy:**
- **Stage 1**: New feature implementation
- **Stage 2**: Integration with existing components
- **Stage 3**: Performance optimization
- **Stage 4**: Comprehensive testing

## **🔬 Testing Categories by Stage Type**

### **Foundation Stages**
```python
# Unit Tests (isolated component testing)
def test_vector_clock_increment():
    clock = VectorClock(node_id)
    initial_value = clock.get_local_time()
    clock.increment()
    assert clock.get_local_time() == initial_value + 1

# Property Tests (correctness guarantees)  
@given(st.lists(st.integers()))
def test_vector_clock_ordering(events):
    # Test happens-before relationship properties
```

### **Integration Stages**
```python
# Integration Tests (component interaction)
def test_broker_executor_communication():
    broker = CausalBroker()
    executor = CausalExecutor()
    # Test causal message exchange

# System Tests (end-to-end behavior)
def test_complete_job_lifecycle():
    # Test full job flow with causal consistency
```

### **Performance Stages**
```python
# Performance Tests (timing and resource usage)
def test_vector_clock_performance():
    start_time = time.time()
    # Perform operations
    duration = time.time() - start_time
    assert duration < expected_threshold
```

## **⚠️ Common Stage Failure Patterns**

### **Anti-Pattern 1: "Big Bang" Implementation**
❌ **Wrong**: Implement entire vector clock system in one stage
✅ **Right**: Stage 1: Basic clock, Stage 2: Capabilities, Stage 3: Serialization

### **Anti-Pattern 2: "Test Later" Mentality**  
❌ **Wrong**: Write all code first, then write tests
✅ **Right**: Write tests for each stage before/during implementation

### **Anti-Pattern 3: "Integration Rush"**
❌ **Wrong**: Integrate with UCP before basic functionality is tested
✅ **Right**: Thoroughly test vector clock in isolation first

## **🚨 Emergency Protocols**

### **When Tests Fail:**
1. **STOP**: Do not proceed to next stage
2. **ANALYZE**: Understand why tests are failing
3. **FIX**: Correct the implementation or tests
4. **VERIFY**: Ensure fix doesn't break other tests
5. **DOCUMENT**: Record the issue and solution

### **When Behind Schedule:**
1. **SIMPLIFY**: Reduce stage scope, not testing requirements
2. **PARALLEL**: Some testing can be done in parallel with coding
3. **HELP**: Document blockers for assistance
4. **ADJUST**: Update timeline rather than skip testing

## **📊 Success Metrics**

### **Daily Success Criteria:**
- **All planned stages completed**: ✅/❌
- **All tests passing**: ✅/❌  
- **No regressions introduced**: ✅/❌
- **Code quality maintained**: ✅/❌
- **Documentation updated**: ✅/❌

### **Weekly Success Criteria:**
- **Weekly objectives met**: ✅/❌
- **Integration tests passing**: ✅/❌
- **Performance benchmarks met**: ✅/❌
- **No technical debt accumulated**: ✅/❌

## **🎯 Stage Development Examples**

### **Example: Day 6 - Core Vector Clock Implementation**

#### **Stage 1: Basic Data Structure (2 hours)**
```python
# Objective: Create basic VectorClock class with increment/compare
class VectorClock:
    def __init__(self, node_id: UUID): pass
    def increment(self) -> None: pass  
    def compare(self, other: 'VectorClock') -> ClockRelation: pass

# Tests: 5 unit tests for basic operations
# Quality Gate: All tests pass, linting clean
```

#### **Stage 2: Capability Integration (2 hours)**  
```python
# Objective: Add capability awareness to vector clock
class CapabilityAwareVectorClock(VectorClock):
    def __init__(self, node_id: UUID, capabilities: Capabilities): pass
    def get_capability_weight(self) -> float: pass

# Tests: 8 unit tests including capability scenarios
# Quality Gate: All Stage 1 + Stage 2 tests pass
```

#### **Stage 3: Serialization Support (1 hour)**
```python
# Objective: Add msgpack serialization
def serialize(self) -> bytes: pass
def deserialize(data: bytes) -> 'CapabilityAwareVectorClock': pass

# Tests: 4 unit tests for serialization round-trips
# Quality Gate: ALL tests pass, ready for Day 7
```

This staged approach ensures solid, tested progress every single day! 🎯
