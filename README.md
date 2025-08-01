# Vector Clock Emergency System

A simple implementation of vector clocks for emergency computing systems.

## What This Project Does

This project helps computers coordinate during emergencies by combining:
- **Vector clocks** (for event ordering)
- **Capability assessment** (for node prioritization)  
- **Emergency context** (for adaptive behavior)

## Quick Start

### Requirements
- Python 3.8+
- Basic packages: `pydantic`, `pytest`

### Running the Demo
```bash
# Clone or download the project
cd ma-sinafadavi

# Set up environment
python3 -m venv .venv
source .venv/bin/activate
pip install pydantic pytest

# Run demonstrations
PYTHONPATH=. python3 rec/replication/simple_demo.py
```

## Project Structure

```
rec/replication/
├── core/
│   ├── vector_clock_simple.py      # Main vector clock implementation
│   └── causal_message_simple.py    # Message handling with priorities
├── simple_demo.py                  # Working demonstrations
docs/
├── project-documentation-simple.md # Complete project documentation
reports/
├── literature-review-simple.md     # Research background
└── day-1-progress-simple.md       # Progress report
```

## Key Features

### 1. Basic Vector Clocks
```python
clock = VectorClock(node_id)
clock.tick()  # increment time
clock.update(other_clock)  # merge timestamps
relation = clock.compare(other_clock)  # 'before', 'after', or 'concurrent'
```

### 2. Emergency Prioritization
```python
# Node with medical equipment gets priority during medical emergencies
caps = Capabilities(cpu_cores=8, memory=16384, has_medical_equipment=True)
clock = CapabilityAwareVectorClock(node_id, caps)
emergency = create_emergency("medical", "critical")
score = clock.get_capability_score(emergency)  # Higher = better
```

### 3. Message Ordering
```python
handler = MessageHandler(node_id, capabilities)

# Normal message
msg1 = handler.send_message("Status update", recipient_id)

# Emergency message (gets priority)
msg2 = handler.send_message("FIRE DETECTED!", recipient_id, is_emergency=True)
```

## Demonstrations

The `simple_demo.py` file shows 5 working scenarios:

1. **Basic Vector Clock Operations** - Event ordering between nodes
2. **Emergency Prioritization** - Medical equipment priority in medical emergencies
3. **Message Ordering** - Emergency messages processed first
4. **Node Ranking** - Different rankings for normal vs. emergency situations
5. **Emergency Alert System** - Complete emergency detection and response

## Research Background

This project addresses a gap in current research:
- **Vector clocks** work great for event ordering but don't consider node capabilities
- **Emergency systems** often ignore proper event ordering and causality
- **My approach** combines both for better emergency coordination

## Technical Details

### Vector Clock Algorithm
Based on Lamport (1978) and Fidge (1988) papers:
- Each node maintains vector of timestamps for all known nodes
- Increment own timestamp before sending messages
- Take maximum of both clocks when receiving messages
- Compare vectors to determine event ordering

### Emergency Extensions
- **Capability scoring**: Rank nodes by hardware and emergency equipment
- **Priority messaging**: Emergency messages processed before normal ones
- **Context awareness**: Adapt behavior based on emergency type and severity

### Performance
- Time complexity: O(n) for vector operations where n = number of nodes
- Space complexity: O(n) for storing vector clocks
- Message overhead: Small (just the timestamp vector)

## Code Style

The code is written in simple student style:
- Clear variable names and function names
- Comments explaining the algorithms and reasoning
- No overly complex patterns or advanced techniques
- Focus on readability and understanding

## Future Work

Possible extensions:
- Geographic awareness for location-based emergencies
- Machine learning for adaptive capability assessment
- Integration with real emergency response systems
- Performance optimization for larger networks

## Academic Context

This work contributes to research in:
- **Distributed systems**: Novel capability-aware vector clocks
- **Emergency computing**: Practical coordination algorithms
- **System design**: Simple, implementable solutions to complex problems

## License

Educational/research project - feel free to use for learning and research purposes.

## Author

Sina Fadavi - Master's Thesis Project, August 2025

---

**Status**: Working prototype with successful demonstrations  
**Research Value**: Novel approach to emergency system coordination  
**Next Steps**: Geographic awareness, performance optimization, real-world testing
