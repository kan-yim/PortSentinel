"""
Pytest configuration file to set up test environment.
This ensures the src directory is in the Python path for imports.
"""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))
