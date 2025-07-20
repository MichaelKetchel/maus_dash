#!/usr/bin/env python3
"""
Test runner script for maus_dash project.
Provides convenient commands for running different types of tests.
"""
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent, check=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False


def main():
    """Main test runner"""
    if len(sys.argv) < 2:
        print("""
Usage: python run_tests.py [command]

Available commands:
  all          - Run all tests
  unit         - Run unit tests only
  integration  - Run integration tests only
  module       - Run module-related tests only
  api          - Run API endpoint tests only
  quick        - Run quick unit tests (no integration)
  coverage     - Run all tests with coverage report
  lint         - Run code linting
  format       - Format code
  check        - Run lint + unit tests

Examples:
  python run_tests.py all
  python run_tests.py unit
  python run_tests.py coverage
""")
        return

    command = sys.argv[1].lower()
    success = True
    
    if command == "all":
        success &= run_command(["pytest", "tests/", "-v"], "All tests")
        
    elif command == "unit":
        success &= run_command(["pytest", "tests/unit/", "-v"], "Unit tests")
        
    elif command == "integration":
        success &= run_command(["pytest", "tests/integration/", "-v"], "Integration tests")
        
    elif command == "module":
        success &= run_command(["pytest", "tests/unit/core/test_module_loader.py", "tests/unit/core/test_base_module.py", "-v"], "Module tests")
        
    elif command == "api":
        success &= run_command(["pytest", "tests/integration/test_api_endpoints.py", "-v"], "API tests")
        
    elif command == "quick":
        success &= run_command(["pytest", "tests/unit/", "-v", "--tb=short"], "Quick unit tests")
        
    elif command == "coverage":
        success &= run_command(["pytest", "tests/", "--cov=backend", "--cov-report=html", "--cov-report=term"], "Tests with coverage")
        if success:
            print(f"\n📊 Coverage report generated in htmlcov/index.html")
            
    elif command == "lint":
        success &= run_command(["ruff", "check", "backend/"], "Ruff linting")
        
    elif command == "format":
        success &= run_command(["black", "backend/", "--line-length=100"], "Code formatting")
        
    elif command == "check":
        success &= run_command(["ruff", "check", "backend/"], "Linting")
        success &= run_command(["pytest", "tests/unit/", "-v"], "Unit tests")
        
    else:
        print(f"❌ Unknown command: {command}")
        success = False
    
    if success:
        print(f"\n🎉 All operations completed successfully!")
        sys.exit(0)
    else:
        print(f"\n💥 Some operations failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()