"""Entry point for PyInstaller packaging."""
import sys
import os

# PyInstaller sets sys._MEIPASS to the extracted bundle path
if getattr(sys, 'frozen', False):
    _root = sys._MEIPASS
else:
    _root = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, _root)

from src.app import GPUPetApp


def main():
    app = GPUPetApp()
    app.run()


if __name__ == "__main__":
    main()
