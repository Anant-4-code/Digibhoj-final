import sys
import os

# Add the project root to the sys.path so 'backend' can be imported
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from backend.main import app
