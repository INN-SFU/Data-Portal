#!/usr/bin/env python3
"""
Test runner for authentication functionality tests.

This script runs both unit and integration tests for the authentication
system improvements including:
- Token validation
- Cookie security
- Login/logout flows  
- Refresh token functionality
- Landing page authentication detection

Usage:
    python tests/run_auth_tests.py [--unit] [--integration] [--verbose]
"""

import sys
import subprocess
import argparse
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_tests(test_type="all", verbose=False):
    """
    Run authentication tests.
    
    Args:
        test_type (str): Type of tests to run ("unit", "integration", or "all")
        verbose (bool): Whether to run in verbose mode
    """
    test_files = []
    
    if test_type in ["unit", "all"]:
        test_files.append("tests/unit/test_auth_security_improvements.py")
    
    if test_type in ["integration", "all"]:
        test_files.append("tests/integration/test_auth_endpoints.py")
    
    if not test_files:
        print("No test files specified")
        return 1
    
    # Build pytest command
    cmd = [sys.executable, '-m', 'pytest']
    
    if verbose:
        cmd.append('-v')
    else:
        cmd.append('-q')
    
    cmd.extend(test_files)
    
    print(f"Running {test_type} authentication tests...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, cwd=project_root, timeout=300)
        return result.returncode
    except subprocess.TimeoutExpired:
        print("Tests timed out after 5 minutes")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run authentication tests")
    parser.add_argument(
        "--unit", 
        action="store_true", 
        help="Run only unit tests"
    )
    parser.add_argument(
        "--integration", 
        action="store_true", 
        help="Run only integration tests"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true", 
        help="Run in verbose mode"
    )
    
    args = parser.parse_args()
    
    # Determine test type
    if args.unit and args.integration:
        test_type = "all"
    elif args.unit:
        test_type = "unit"
    elif args.integration:
        test_type = "integration"
    else:
        test_type = "all"
    
    return run_tests(test_type, args.verbose)


if __name__ == "__main__":
    exit(main())