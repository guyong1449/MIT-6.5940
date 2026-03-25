#!/usr/bin/env python3
"""
Windows build script for TinyChatEngine
Usage: python build.py [implementation]
  implementation: reference, loop_unrolling, multithreading, simd_programming, multithreading_loop_unrolling, all_techniques
"""

import os
import sys
import subprocess
import glob
from pathlib import Path

# Map implementation names to numbers
IMP_MAP = {
    "reference": 0,
    "loop_unrolling": 1,
    "multithreading": 2,
    "simd_programming": 3,
    "multithreading_loop_unrolling": 4,
    "all_techniques": 5,
}

def get_imp_number(impl_name):
    """Get IMP number from implementation name."""
    return IMP_MAP.get(impl_name, 0)

def main():
    # Parse arguments
    impl_name = sys.argv[1] if len(sys.argv) > 1 else "reference"
    imp_num = get_imp_number(impl_name)

    print(f"Building {impl_name} (IMP={imp_num})...")

    # Compiler and flags
    CXX = "g++"
    CXXFLAGS = [
        "-std=c++11",
        "-pthread",
        "-g",
        "-O0",
        "-w",
        f"-DIMP={imp_num}",
        "-mavx2",
        "-mfma",
        "-ffast-math",
        "-fpermissive",
        "-DQM_x86",
    ]

    # Directories
    transformer_dir = Path(__file__).parent
    lib_dir = transformer_dir / ".." / "kernels"
    src_dir = transformer_dir / "src"
    build_dir = transformer_dir / "build" / "transformer"
    test_target = transformer_dir / "test_linear.exe"
    app_target = transformer_dir / "chat.exe"

    # Include directories
    include_dirs = [
        str(lib_dir),
        str(transformer_dir / "include"),
        str(transformer_dir / "include" / "nn_modules"),
        str(transformer_dir / "json" / "single_include"),
    ]

    include_flags = [f"-I{d}" for d in include_dirs]

    # Clean build
    if build_dir.exists():
        for f in build_dir.glob("*.o"):
            f.unlink()

    build_dir.mkdir(parents=True, exist_ok=True)

    # Clean old executables
    if test_target.exists():
        test_target.unlink()
    if app_target.exists():
        app_target.unlink()

    # Collect source files
    source_files = []

    # Library source files
    source_files.extend(lib_dir.glob("*.cc"))
    source_files.extend(lib_dir.glob("avx/*.cc"))
    source_files.extend(lib_dir.glob("starter_code/*.cc"))

    # Main source files
    source_files.extend(src_dir.glob("*.cc"))
    source_files.extend(src_dir.glob("nn_modules/*.cc"))
    source_files.extend((src_dir / "ops").glob("*.cc"))

    # Compile source files
    obj_files = []
    for src in source_files:
        obj = build_dir / f"{src.parent.name}_{src.stem}.o"
        obj_files.append(obj)

        cmd = [CXX] + CXXFLAGS + include_flags + ["-c", str(src), "-o", str(obj)]

        print(f"Compiling {src.name}...")
        result = subprocess.run(cmd, capture_output=True)

        if result.returncode != 0:
            print(f"Error compiling {src}:")
            print(result.stderr.decode())
            return 1

    # Link test_linear
    test_src = transformer_dir / "tests" / "test_linear.cc"
    cmd = [CXX] + CXXFLAGS + include_flags + ["-o", str(test_target), str(test_src)] + [str(f) for f in obj_files]

    print("Linking test_linear.exe...")
    result = subprocess.run(cmd, capture_output=True)

    if result.returncode != 0:
        print("Error linking test_linear:")
        print(result.stderr.decode())
        return 1

    # Link chat application
    app_src = transformer_dir / "application" / "chat.cc"
    cmd = [CXX] + CXXFLAGS + include_flags + ["-o", str(app_target), str(app_src)] + [str(f) for f in obj_files]

    print("Linking chat.exe...")
    result = subprocess.run(cmd, capture_output=True)

    if result.returncode != 0:
        print("Error linking chat:")
        print(result.stderr.decode())
        return 1

    print()
    print("=" * 50)
    print("Build completed successfully!")
    print(f"Executables: {test_target.name}, {app_target.name}")
    print("=" * 50)

    return 0

if __name__ == "__main__":
    sys.exit(main())
