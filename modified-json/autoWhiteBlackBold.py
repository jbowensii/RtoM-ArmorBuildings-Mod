"""
autoWhiteBlackBold.py — Legacy CLI wrapper.

Delegates to :mod:`src.recipes.colour_variants`.  Kept at this path so
existing workflows still work.
"""

import os
import sys

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.recipes.colour_variants import main  # noqa: E402

if __name__ == "__main__":
    main()
