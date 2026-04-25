import sys
sys.path.insert(0, '.')

try:
    from app import models
    print("✓ models imported successfully")
except Exception as e:
    print(f"✗ models import failed: {e}")

try:
    from app import schemas
    print("✓ schemas imported successfully")
except Exception as e:
    print(f"✗ schemas import failed: {e}")

try:
    from app import crud
    print("✓ crud imported successfully")
except Exception as e:
    print(f"✗ crud import failed: {e}")

try:
    from app import main
    print("✓ main imported successfully")
except Exception as e:
    print(f"✗ main import failed: {e}")

print("\nAll imports checked!")
