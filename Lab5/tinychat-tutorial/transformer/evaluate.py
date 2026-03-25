#!/usr/bin/env python3
"""
Windows evaluation script for TinyChatEngine
Usage: python evaluate.py [implementation]
  If no implementation is specified, all implementations will be tested.
"""

import sys
import subprocess
from pathlib import Path

# List of implementations in order
IMPLEMENTATIONS = [
    "reference",
    "loop_unrolling",
    "multithreading",
    "simd_programming",
    "multithreading_loop_unrolling",
    "all_techniques",
]

def run_build(impl):
    """Run the build script for a specific implementation."""
    build_script = Path(__file__).parent / "build.py"
    result = subprocess.run([sys.executable, str(build_script), impl],
                          capture_output=True, text=True)
    return result

def run_test():
    """Run the test_linear executable."""
    exe = Path(__file__).parent / "test_linear.exe"
    result = subprocess.run([str(exe)], capture_output=True, text=True)
    return result

def main():
    # Parse arguments
    if len(sys.argv) > 1:
        impl = sys.argv[1]
        if impl not in IMPLEMENTATIONS:
            print(f"Invalid implementation: {impl}")
            print(f"Valid implementations: {', '.join(IMPLEMENTATIONS)}")
            return 1
        test_impls = [impl]
    else:
        test_impls = IMPLEMENTATIONS

    print(f"Running evaluation for: {', '.join(test_impls)}")
    print()

    for impl in test_impls:
        print("=" * 50)
        print(f"Testing: {impl}")
        print("=" * 50)

        # Build
        build_result = run_build(impl)
        if build_result.returncode != 0:
            print("Build output:")
            print(build_result.stdout)
            print(build_result.stderr)
            print(f"Compilation failed for {impl}")
            return 1

        # Run test
        print("Running test_linear.exe...")
        test_result = run_test()

        print(test_result.stdout)
        if test_result.stderr:
            print("Errors:")
            print(test_result.stderr)

        if test_result.returncode != 0:
            print(f"Test failed for {impl}")
            return 1

        print()

    print("=" * 50)
    print("All tests completed!")
    print("=" * 50)

    return 0

if __name__ == "__main__":
    sys.exit(main())
