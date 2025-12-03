# ui_monitor_bridge.py
# Safe wrapper to start/stop the real ProductivityMonitor and provide polling helpers
#
# Usage:
#   from ui_monitor_bridge import MonitorBridge
#   bridge = MonitorBridge()
#   bridge.start_monitor(user_id=<int>)   # starts monitor thread and DB session
#   bridge.stop_monitor()                 # stops monitor and closes session
#   bridge.get_status() -> dict           # {running: bool, status_text: str, total_time: str}
#   bridge.get_recent_app_rows(limit=10)  # returns list of dicts from DB (if DB configured)
#
# IMPORTANT: This wrapper will only run detectors when you explicitly call start_monitor().
# It sets show_window=False by default (no OpenCV window). Change only if you want the webcam preview.

import threading
import time
from typing import Optional, List, Dict

# Import the real monitor class and DB helpers from your project
from monitor import ProductivityMonitor  # the thread-based monitor. See monitor.py. :contentReference[oaicite:2]{index=2}
import db  # DB helpers in your repo for sessions and app_usage. :contentReference[oaicite:3]{index=3}

class MonitorBridge:
    def __init__(self, show_window: bool = False):
        """
        show_window: pass True if you want the OpenCV monitor window to appear.
                     Default False to run headless while testing the UI.
        """
        self.show_window = show_window
        self._monitor: Optional[ProductivityMonitor] = None
        self._session_id: Optional[int] = None
        self._lock = threading.Lock()

    def start_monitor(self, user_id: int) -> int:
        """
        Start a new monitoring session for the given user_id.
        Returns the session_id (DB id) used by the monitor.
        If a session is already running, returns the existing session_id.
        """
        with self._lock:
            if self._monitor and self._monitor.is_alive():
                # already running; return existing session id
                return self._session_id

            # Create a DB session entry (safe wrapper) — uses db.start_session()
            try:
                session_id = db.start_session(user_id)
            except Exception as e:
                # If DB is not configured or fails, we still allow monitoring but session_id is None
                print(f"[MonitorBridge] Warning: could not create DB session: {e}")
                session_id = None

            # Instantiate and start the thread-based monitor.
            # ProductivityMonitor expects a session_id int (monitor.py) — if None, pass 0
            mon = ProductivityMonitor(session_id if session_id is not None else 0, show_window=self.show_window)
            mon.start()

            self._monitor = mon
            self._session_id = session_id
            print(f"[MonitorBridge] Monitor started (session_id={self._session_id})")
            return self._session_id

    def stop_monitor(self):
        """
        Stop the running monitor (if any) and close the DB session (if present).
        """
        with self._lock:
            if not self._monitor:
                return

            try:
                self._monitor.stop()
            except Exception:
                pass

            # Wait briefly for thread to finish (non-blocking long wait)
            if self._monitor.is_alive():
                # give it a short time to exit gracefully
                self._monitor.join(timeout=2.0)

            # If DB session exists, mark it ended safely
            if self._session_id:
                try:
                    db.end_session(self._session_id)
                except Exception as e:
                    print(f"[MonitorBridge] Warning: could not end DB session: {e}")

            print(f"[MonitorBridge] Monitor stopped (session_id={self._session_id})")
            self._monitor = None
            self._session_id = None

    def is_running(self) -> bool:
        with self._lock:
            return bool(self._monitor and self._monitor.is_alive())

    def get_status(self) -> Dict[str, Optional[str]]:
        """
        Returns a small status dict:
          { running: bool, status_text: str | None, total_time: str | None, session_id: int | None }
        These fields are read from the running monitor if present; otherwise None.
        """
        with self._lock:
            if not self._monitor:
                return {"running": False, "status_text": None, "total_time": None, "session_id": None}
            try:
                return {
                    "running": True,
                    "status_text": getattr(self._monitor, "current_status_text", None),
                    "total_time": getattr(self._monitor, "current_total_time_str", None),
                    "session_id": self._session_id
                }
            except Exception:
                return {"running": True, "status_text": None, "total_time": None, "session_id": self._session_id}

    def get_recent_app_rows(self, limit: int = 20) -> List[Dict]:
        """
        Safely query the DB to return recent app usage rows for the active session.
        Returns a list of dicts with keys: id, app_name, window_title, duration_sec, start_time, end_time
        If DB is not configured or session missing, returns an empty list.
        """
        with self._lock:
            if not self._session_id:
                return []

            try:
                conn = db.get_connection()
                cur = conn.cursor(dictionary=True)
                cur.execute(
                    "SELECT id, app_name, window_title, duration_sec, start_time, end_time "
                    "FROM app_usage WHERE session_id = %s ORDER BY start_time DESC LIMIT %s",
                    (self._session_id, limit)
                )
                rows = cur.fetchall()
                cur.close()
                conn.close()
                return rows or []
            except Exception as e:
                print(f"[MonitorBridge] DB query failed: {e}")
                return []

    # Convenience: stop monitor when bridge is garbage-collected
    def __del__(self):
        try:
            self.stop_monitor()
        except Exception:
            pass
