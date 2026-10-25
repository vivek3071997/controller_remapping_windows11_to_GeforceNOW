"""
Witcher Remapper / Apex Universal Controller Remapper
=====================================================
Local Input Interception & Macro System for GeForce NOW & PC Games.
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
