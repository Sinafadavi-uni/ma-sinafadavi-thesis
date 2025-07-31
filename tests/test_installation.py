"""
Basic test to verify that all dependencies are working correctly
and the core application components can be imported and instantiated.
"""
import pytest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that all critical dependencies can be imported."""
    import fastapi
    import pydantic
    import psutil
    import zeroconf
    import wasmtime
    import uvicorn
    assert True

def test_rec_models():
    """Test that REC model classes can be imported and instantiated."""
    from rec.model import Capabilities, JobInfo, ExecutionPlan, NodeRole
    
    # Test Capabilities
    caps = Capabilities()
    assert caps is not None
    
    # Test JobInfo
    job = JobInfo(wasm_bin="test.wasm")
    assert job.wasm_bin == "test.wasm"
    
    # Test ExecutionPlan
    plan = ExecutionPlan(exec=[], cmds={})
    assert plan.exec == []
    assert plan.cmds == {}
    
    # Test NodeRole enum
    assert NodeRole.BROKER.value == (1,)
    assert NodeRole.EXECUTOR.value == (2,)
    assert NodeRole.DATASTORE.value == (3,)

def test_rec_nodes():
    """Test that REC node classes can be imported."""
    from rec.nodes.node import Node
    from rec.nodes.broker import Broker
    from rec.nodes.executor import Executor
    from rec.nodes.datastore import Datastore
    
    assert Node is not None
    assert Broker is not None
    assert Executor is not None
    assert Datastore is not None

def test_application_entry_point():
    """Test that the main application module can be imported."""
    from rec import run
    assert run is not None
    assert hasattr(run, 'main')
