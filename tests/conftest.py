"""
conftest.py

Adds src/ to the Python path so test files can import pipeline
modules directly (e.g. `from data_quality import validate_transactions`)
regardless of what directory pytest is run from.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
