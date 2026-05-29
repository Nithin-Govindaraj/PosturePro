# ─────────────────────────────────────────────
#  logger.py  —  Terminal logger with timestamps
# ─────────────────────────────────────────────

import logging
import sys
from datetime import datetime
from config import LOG_LEVEL

# ANSI color codes (work on Windows 10+ with ANSI enabled, and Linux/Mac)
class Colors:
    RESET   = "\033[0m"
    GREY    = "\033[90m"
    CYAN    = "\033[96m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    BOLD    = "\033[1m"

LEVEL_COLORS = {
    "DEBUG":    Colors.GREY,
    "INFO":     Colors.CYAN,
    "WARNING":  Colors.YELLOW,
    "ERROR":    Colors.RED,
    "CRITICAL": Colors.RED + Colors.BOLD,
    "STATE":    Colors.GREEN + Colors.BOLD,
    "ALERT":    Colors.RED  + Colors.BOLD,
}


class FallDetectionLogger:
    def __init__(self, name="FallDetect"):
        self.name = name
        self._enable_windows_ansi()

    def _enable_windows_ansi(self):
        """Enable ANSI escape codes on Windows terminals."""
        import os
        if os.name == "nt":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except Exception:
                pass  # Fallback: colors won't show but won't crash either

    def _log(self, level: str, msg: str):
        if LOG_LEVEL == "WARNING" and level in ("DEBUG", "INFO"):
            return
        if LOG_LEVEL == "INFO" and level == "DEBUG":
            return

        ts    = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        color = LEVEL_COLORS.get(level, Colors.RESET)
        tag   = f"[{level:<8}]"
        print(f"{Colors.GREY}{ts}{Colors.RESET}  {color}{tag}{Colors.RESET}  {msg}")

    # ── Public methods ────────────────────────
    def debug(self, msg):    self._log("DEBUG",    msg)
    def info(self, msg):     self._log("INFO",     msg)
    def warning(self, msg):  self._log("WARNING",  msg)
    def error(self, msg):    self._log("ERROR",    msg)

    def state(self, msg):
        """Use for state machine transitions — always visible."""
        self._log("STATE", msg)

    def alert(self, msg):
        """Use for final SOS alert — always visible, stands out."""
        print()
        self._log("ALERT", f"{'─'*10} {msg} {'─'*10}")
        print()


# Singleton — import and use directly
log = FallDetectionLogger()
