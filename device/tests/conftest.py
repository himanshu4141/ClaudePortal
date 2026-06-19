import sys
from pathlib import Path

# Make the device/ modules importable on a host (CPython) without hardware libs.
# Append (don't prepend): device/code.py is the CircuitPython entrypoint and would
# otherwise shadow Python's stdlib `code` module (which pdb/pytest import).
sys.path.append(str(Path(__file__).parent.parent))
