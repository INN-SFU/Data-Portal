#!/usr/bin/env python3
"""
Smoke Test Runner

Runs smoke tests for backend services after deployment/startup.
Can be run manually or automatically from entrypoint.sh.

Usage:
    python tests/run_smoke_tests.py              # Run all smoke tests
    python tests/run_smoke_tests.py --auth       # Run only auth tests
    python tests/run_smoke_tests.py --users      # Run only user CRUD tests
    python tests/run_smoke_tests.py --verbose    # Show full output
"""

import sys
import subprocess
from pathlib import Path
from typing import List


def run_pytest(test_files: List[str], verbose: bool = False) -> tuple[int, str]:
    """
    Run pytest with specified test files.

    Args:
        test_files: List of test file paths relative to tests/ directory
        verbose: If True, show full pytest output

    Returns:
        Tuple of (return_code, output)
    """
    tests_dir = Path(__file__).parent

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--tb=line",
        "--no-header",
    ]

    if verbose:
        cmd.append("-v")
    else:
        cmd.extend(["-q", "--tb=no"])

    # Add test files
    for test_file in test_files:
        test_path = tests_dir / test_file
        if test_path.exists():
            cmd.append(str(test_path))
        else:
            print(f"⚠️  Warning: Test file not found: {test_file}")

    # Set PYTHONPATH to include backend directory
    import os
    env = os.environ.copy()
    backend_dir = tests_dir.parent
    env["PYTHONPATH"] = f"{backend_dir}:{env.get('PYTHONPATH', '')}"

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=120  # 2 minute timeout for all tests
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return 1, "ERROR: Tests timed out after 120 seconds"
    except Exception as e:
        return 1, f"ERROR: Failed to run tests: {e}"


def format_output(output: str, verbose: bool = False) -> str:
    """Format test output for display."""
    if verbose:
        return output

    # Extract summary line and test results
    lines = output.split("\n")
    formatted = []

    for line in lines:
        # Show passed/failed indicators
        if "PASSED" in line or "passed" in line:
            formatted.append(f"  ✓ {line}")
        elif "FAILED" in line or "failed" in line or "ERROR" in line:
            formatted.append(f"  ✗ {line}")
        # Show summary line
        elif " passed" in line or " failed" in line:
            formatted.append(line)

    return "\n".join(formatted) if formatted else output


def main():
    """Main entry point for smoke test runner."""
    import argparse

    parser = argparse.ArgumentParser(description="Run backend smoke tests")
    parser.add_argument(
        "--auth",
        action="store_true",
        help="Run only authentication smoke tests"
    )
    parser.add_argument(
        "--users",
        action="store_true",
        help="Run only user CRUD smoke tests"
    )
    parser.add_argument(
        "--policies",
        action="store_true",
        help="Run only policy CRUD smoke tests"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output"
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Exit on first test failure"
    )

    args = parser.parse_args()

    # Determine which tests to run
    test_files = []
    if args.auth:
        test_files = ["test_auth_smoke.py"]
    elif args.users:
        test_files = ["test_user_crud_smoke.py"]
    elif args.policies:
        test_files = ["test_policy_crud_smoke.py"]
    else:
        # Run all smoke tests
        test_files = [
            "test_auth_smoke.py",
            "test_user_crud_smoke.py",
            "test_policy_crud_smoke.py",
        ]

    # Check if pytest is available
    try:
        import pytest
    except ImportError:
        print("ERROR: pytest not installed. Install with: pip install pytest")
        return 1

    print("🧪 Running smoke tests...")
    if not args.verbose:
        print("   (Use --verbose for full output)")
    print()

    # Run tests
    return_code, output = run_pytest(test_files, verbose=args.verbose)

    # Display results
    formatted = format_output(output, verbose=args.verbose)
    print(formatted)

    # Summary
    if return_code == 0:
        print("\n✅ All smoke tests passed!")
    else:
        print("\n❌ Some smoke tests failed.")
        if not args.verbose:
            print("   Run with --verbose for detailed output")

    return return_code


if __name__ == "__main__":
    sys.exit(main())
