# shared_state.py
# Simple thread-safe shared state for UI <-> classifier communication.

import threading
import time
from typing import Optional

_lock = threading.Lock()

_total_productive_seconds = 0       # authoritative cumulative productive seconds
_last_productive_ts: Optional[float] = None
_current_productive_flag = False

def add_productive_seconds(sec: int = 1):
    global _total_productive_seconds, _last_productive_ts
    with _lock:
        _total_productive_seconds += int(sec)
        _last_productive_ts = time.time()

def get_total_productive_seconds() -> int:
    with _lock:
        return int(_total_productive_seconds)

def reset_total_productive_seconds():
    global _total_productive_seconds, _last_productive_ts
    with _lock:
        _total_productive_seconds = 0
        _last_productive_ts = None

def set_productive_flag(flag: bool):
    global _current_productive_flag
    with _lock:
        _current_productive_flag = bool(flag)

def get_productive_flag() -> bool:
    with _lock:
        return bool(_current_productive_flag)

def last_productive_ts() -> Optional[float]:
    with _lock:
        return _last_productive_ts
