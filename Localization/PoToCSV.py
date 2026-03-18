"""
PoToCSV.py — Legacy CLI wrapper.

Delegates to :mod:`src.localization.po_to_csv`.  Kept at this path so
existing workflows (batch scripts, muscle memory) still work.
"""

import os
import sys

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.localization.po_to_csv import main  # noqa: E402

if __name__ == "__main__":
    main()
