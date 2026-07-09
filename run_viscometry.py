#!/usr/bin/env python3
"""Run the automated viscometry platform (hardware + web UI)."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))

from viscometry.run.controller import main

if __name__ == "__main__":
    main()
