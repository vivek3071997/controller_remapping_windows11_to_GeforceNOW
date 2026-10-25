"""
main.py / witcher_remapper.py – Dual UI Universal Entry Point
=============================================================
Supports:
  1. Desktop Native GUI (PyQt6) -> Default or via: `python witcher_remapper.py --desktop`
  2. Browser Web Dashboard (Flask) -> via: `python witcher_remapper.py --web`
  3. Combined Dual UI Mode (Runs Web Server in background + launches Desktop GUI) -> via: `python witcher_remapper.py --all`
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
