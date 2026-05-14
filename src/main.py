"""GPU Pet Monitor - A cute desktop pet that monitors your NVIDIA GPU."""

import sys
import os

# Ensure src is on path when running directly
_src_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_src_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from src.app import GPUPetApp


def main():
    app = GPUPetApp()
    app.run()


if __name__ == "__main__":
    main()
