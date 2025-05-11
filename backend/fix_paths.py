import sys
import os

# Get the absolute path to the backend directory
backend_dir = os.path.abspath(os.path.dirname(__file__))

# Add backend to the Python path if it's not already there
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
    print(f"Added {backend_dir} to Python path")
