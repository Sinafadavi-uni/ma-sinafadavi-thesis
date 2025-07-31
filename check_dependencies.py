#!/usr/bin/env python3
"""
Dependency verification script for Vector Clock implementation
"""
import sys
import importlib
from typing import List, Tuple

# Required dependencies for vector clock implementation
REQUIRED_DEPENDENCIES = [
    # Core serialization
    ("msgpack", "Message serialization"),
    ("numpy", "Mathematical operations"),
    ("cryptography", "Security features"),
    
    # Testing
    ("pytest", "Testing framework"),
    ("hypothesis", "Property-based testing"),
    
    # Logging
    ("structlog", "Structured logging"),
    
    # Existing UCP dependencies
    ("fastapi", "REST API framework"),
    ("pydantic", "Data validation"),
    ("wasmtime", "WebAssembly runtime"),
    ("zeroconf", "Service discovery"),
]

OPTIONAL_DEPENDENCIES = [
    # Analysis and visualization
    ("pandas", "Data analysis"),
    ("matplotlib", "Plotting"),
    ("scipy", "Scientific computing"),
    
    # Performance monitoring
    ("memory_profiler", "Memory profiling"),
    ("prometheus_client", "Metrics collection"),
]

def check_dependency(module_name: str, description: str) -> Tuple[bool, str]:
    """Check if a dependency is available."""
    try:
        importlib.import_module(module_name)
        return True, f"✅ {module_name}: {description}"
    except ImportError as e:
        return False, f"❌ {module_name}: {description} - {str(e)}"

def main():
    """Check all dependencies and report status."""
    print("🔍 Checking Vector Clock Implementation Dependencies\n")
    
    print("📦 Required Dependencies:")
    required_missing = []
    for module, desc in REQUIRED_DEPENDENCIES:
        success, message = check_dependency(module, desc)
        print(f"  {message}")
        if not success:
            required_missing.append(module)
    
    print("\n📦 Optional Dependencies:")
    optional_missing = []
    for module, desc in OPTIONAL_DEPENDENCIES:
        success, message = check_dependency(module, desc)
        print(f"  {message}")
        if not success:
            optional_missing.append(module)
    
    print("\n" + "="*60)
    
    if required_missing:
        print(f"❌ Missing {len(required_missing)} required dependencies:")
        for dep in required_missing:
            print(f"   pip install {dep}")
        print("\nInstall command:")
        print(f"pip install {' '.join(required_missing)}")
        sys.exit(1)
    else:
        print("✅ All required dependencies are installed!")
    
    if optional_missing:
        print(f"\n⚠️  Missing {len(optional_missing)} optional dependencies:")
        for dep in optional_missing:
            print(f"   pip install {dep}")
        print("\nOptional install command:")
        print(f"pip install {' '.join(optional_missing)}")
    else:
        print("✅ All optional dependencies are installed!")
    
    print("\n🚀 Ready to start Vector Clock implementation!")

if __name__ == "__main__":
    main()
