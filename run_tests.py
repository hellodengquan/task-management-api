import subprocess
import sys
import os

print("=" * 60)
print("Running Tests for Tag Functionality")
print("=" * 60)
print()

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try to import pytest
try:
    import pytest
    print("✓ pytest imported successfully")
except ImportError as e:
    print(f"✗ pytest not found: {e}")
    sys.exit(1)

# Run the tests
print()
print("Running tests/test_tags.py...")
print("-" * 60)

# Run pytest programmatically
exit_code = pytest.main([
    "tests/test_tags.py",
    "-v",
    "--tb=short"
])

print()
print("-" * 60)
if exit_code == 0:
    print("✓ All tests passed!")
else:
    print(f"✗ Some tests failed (exit code: {exit_code})")

sys.exit(exit_code)
