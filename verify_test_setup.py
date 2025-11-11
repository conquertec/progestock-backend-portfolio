#!/usr/bin/env python
"""
Quick script to verify testing setup is working correctly.
Run this after installing requirements-dev.txt.

Usage:
    python verify_test_setup.py
"""

import sys
import subprocess
from pathlib import Path


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def check_dependencies():
    """Check if testing dependencies are installed."""
    print_header("Checking Dependencies")

    required_packages = [
        'pytest',
        'pytest-django',
        'pytest-cov',
        'pytest-mock'
    ]

    all_installed = True

    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package:20} - Installed")
        except ImportError:
            print(f"❌ {package:20} - NOT INSTALLED")
            all_installed = False

    return all_installed


def check_test_structure():
    """Check if test directory structure exists."""
    print_header("Checking Test Structure")

    required_paths = [
        'tests',
        'tests/unit',
        'tests/integration',
        'tests/conftest.py',
        'pytest.ini',
        'requirements-dev.txt'
    ]

    all_exist = True
    project_root = Path(__file__).parent

    for path_str in required_paths:
        path = project_root / path_str
        if path.exists():
            print(f"✅ {path_str:30} - Exists")
        else:
            print(f"❌ {path_str:30} - MISSING")
            all_exist = False

    return all_exist


def run_sample_tests():
    """Run the example tests."""
    print_header("Running Example Tests")

    try:
        result = subprocess.run(
            ['pytest', '-v', '--tb=short', 'tests/'],
            capture_output=True,
            text=True,
            timeout=30
        )

        print(result.stdout)

        if result.returncode == 0:
            print("\n✅ All tests passed!")
            return True
        else:
            print("\n⚠️  Some tests failed. This is normal if database isn't set up.")
            print("   Run 'python manage.py migrate' and try again.")
            return False

    except subprocess.TimeoutExpired:
        print("\n❌ Tests timed out")
        return False
    except FileNotFoundError:
        print("\n❌ pytest not found. Install with: pip install -r requirements-dev.txt")
        return False


def main():
    """Main verification function."""
    print("\n" + "🔍 ProGestock Test Setup Verification" + "\n")

    checks = []

    # Check 1: Dependencies
    deps_ok = check_dependencies()
    checks.append(("Dependencies", deps_ok))

    if not deps_ok:
        print("\n⚠️  Install dependencies first:")
        print("   pip install -r requirements-dev.txt")
        print("\nThen run this script again.")
        sys.exit(1)

    # Check 2: Structure
    structure_ok = check_test_structure()
    checks.append(("Structure", structure_ok))

    # Check 3: Run tests
    tests_ok = run_sample_tests()
    checks.append(("Tests", tests_ok))

    # Final summary
    print_header("Summary")

    all_passed = all(status for _, status in checks)

    for name, status in checks:
        symbol = "✅" if status else "❌"
        print(f"{symbol} {name}")

    if all_passed:
        print("\n🎉 SUCCESS! Your testing setup is working perfectly!")
        print("\nNext steps:")
        print("  1. Read: docs/testing-guide.md")
        print("  2. Run: pytest -m smoke")
        print("  3. Before Railway deployment: pytest -v")
    else:
        print("\n⚠️  Some checks failed. See messages above.")
        print("\nCommon fixes:")
        print("  - Install dependencies: pip install -r requirements-dev.txt")
        print("  - Run migrations: python manage.py migrate")
        print("  - Check DATABASE_URL is set")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
