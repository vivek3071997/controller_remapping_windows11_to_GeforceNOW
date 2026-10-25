"""
witcher_remapper.py – GeForce NOW Controller Remapper PC Entry Point
=====================================================================
Local Input Interception & Macro System for GeForce NOW on PC.
"""

import sys
import threading
from PyQt6.QtWidgets import QApplication
from ui import WitcherRemapperUI
import web_server

def run_desktop():
    app = QApplication(sys.argv)
    window = WitcherRemapperUI()
    window.show()
    sys.exit(app.exec())

def run_web():
    web_server.start_web_server(port=5000)

def main():
    if "--web" in sys.argv:
        run_web()
    elif "--all" in sys.argv:
        # Launch web server in a background thread and desktop GUI on main thread
        web_thread = threading.Thread(target=run_web, daemon=True)
        web_thread.start()
        run_desktop()
    else:
        # Default to Native Desktop GUI
        run_desktop()

if __name__ == "__main__":
    main()
