import sys
import os

# Add the project root to the sys.path so 'backend' can be imported
path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path not in sys.path:
    sys.path.append(path)

from backend.main import app
