#!/usr/bin/env python3
"""
Test runner for dual observability system tests.

Provides various test execution options for the dual observability implementation.
"""

import sys
import os
import subprocess
from pathlib import Path
import argparse


def run_tests(test_type="all", verbose=True, coverage=False, markers=None):
    """
    Run tests with specified options.
    
    Args:
        test_type: Type of tests to run (all, unit, integration, compatibility)
        verbose: Enable verbose output
        coverage: Enable coverage reporting
        markers: Additional pytest markers to filter by
    """
    # Ensure we're in the correct directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Add src to Python path
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test type filter
    if test_type != "all":
        cmd.extend(["-m", test_type])
    
    # Add additional markers if specified
    if markers:
        for marker in markers:
            cmd.extend(["-m", marker])
    
    # Add verbosity
    if verbose:
        cmd.append("-v")
    
    # Add coverage if requested
    if coverage:
        cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term-missing"])
    
    # Add test directory
    cmd.append("tests/")
    
    print(f"Running command: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n\nTest execution interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(description="Run dual observability tests")
    
    parser.add_argument(
        "--type", 
        choices=["all", "unit", "integration", "compatibility"],
        default="all",
        help="Type of tests to run (default: all)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--coverage", "-c",
        action="store_true", 
        help="Enable coverage reporting"
    )
    
    parser.add_argument(
        "--markers", "-m",
        nargs="*",
        help="Additional pytest markers to filter by"
    )
    
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Run only fast tests (exclude slow marker)"
    )
    
    parser.add_argument(
        "--telemetry-only",
        action="store_true",
        help="Run only telemetry-related tests"
    )
    
    parser.add_argument(
        "--application-only", 
        action="store_true",
        help="Run only application logging tests"
    )
    
    parser.add_argument(
        "--chat-only",
        action="store_true",
        help="Run only chat observability tests"
    )
    
    args = parser.parse_args()
    
    # Handle special test selection options
    markers = args.markers or []
    
    if args.fast:
        markers.append("not slow")
    
    if args.telemetry_only:
        markers.append("telemetry")
    
    if args.application_only:
        markers.append("application")
    
    if args.chat_only:
        markers.append("chat")
    
    # Run tests
    exit_code = run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=args.coverage,
        markers=markers
    )
    
    # Print summary
    print("-" * 50)
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()