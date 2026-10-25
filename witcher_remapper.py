"""
Witcher Remapper – Local Input Interception System for GeForce NOW
==================================================================
Captures raw inputs from a physical controller (Cosmic Byte Ares Pro),
translates them through a configurable mapping matrix, and writes the
results to a ViGEmBus virtual Xbox 360 controller that GeForce NOW sees.

Entry point — run this file:
    python witcher_remapper.py
"""

import sys
from PyQt6.QtWidgets import QApplication
from ui import WitcherRemapperUI


def main():
    app = QApplication(sys.argv)
    window = WitcherRemapperUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
