# db.py
import mysql.connector
import hashlib
from datetime import datetime

# ---- DB CONNECTION ----

def get_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user="root",                 
        password="Ayush@2005",    
        database="productivity_monitor"  # CHANGE THIS IF NAME DIFFERENT
    )

# ---- PASSWORD HELPERS ----

def hash_pass(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ---- USER FUNCTIONS ----

def create_user(username: str, password: str, full_name: str = "", role: str = "user"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, password_hash, full_name, role) VALUES (%s, %s, %s, %s)",
        (username, hash_pass(password), full_name, role)
    )
    conn.commit()
    conn.close()


def get_user_by_username(username: str):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    conn.close()
    return user


def verify_user(username: str, password: str):
    user = get_user_by_username(username)
    if not user:
        return None
    if user["password_hash"] == hash_pass(password):
        return user
    return None

# ---- SESSION (PUNCH IN / OUT) ----

def start_session(user_id: int) -> int:
    """Create new active session and return its ID."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now()

    # close any previously active sessions (safe-guard)
    cur.execute(
        "UPDATE sessions SET is_active = FALSE, punch_out = %s WHERE user_id = %s AND is_active = TRUE",
        (now, user_id)
    )

    cur.execute(
        "INSERT INTO sessions (user_id, punch_in, is_active) VALUES (%s, %s, TRUE)",
        (user_id, now)
    )
    conn.commit()
    session_id = cur.lastrowid
    conn.close()
    return session_id


def end_session(session_id: int):
    """Mark session as ended."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now()
    cur.execute(
        "UPDATE sessions SET punch_out = %s, is_active = FALSE WHERE id = %s",
        (now, session_id)
    )
    conn.commit()
    conn.close()


def update_session_productivity(session_id: int, productive_delta: int, unproductive_delta: int):
    """Add seconds to productive/unproductive counters. Call this from your timer/model logic."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE sessions
        SET total_productive_sec = total_productive_sec + %s,
            total_unproductive_sec = total_unproductive_sec + %s
        WHERE id = %s
    """, (productive_delta, unproductive_delta, session_id))
    conn.commit()
    conn.close()

# ---- APP USAGE LOGGING ----

def log_app_start(session_id: int, app_name: str, window_title: str,
                  category: str, productive: bool) -> int:
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now()
    cur.execute("""
        INSERT INTO app_usage (session_id, app_name, window_title, category,
                               productive, start_time)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (session_id, app_name, window_title, category, int(productive), now))
    conn.commit()
    usage_id = cur.lastrowid
    conn.close()
    return usage_id


def log_app_end(usage_id: int):
    conn = get_connection()
    cur = conn.cursor()

    # get start_time
    cur.execute("SELECT start_time FROM app_usage WHERE id = %s", (usage_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return

    start_time = row[0]
    now = datetime.now()
    duration_sec = int((now - start_time).total_seconds())

    cur.execute("""
        UPDATE app_usage
        SET end_time = %s, duration_sec = %s
        WHERE id = %s
    """, (now, duration_sec, usage_id))
    conn.commit()
    conn.close()

# --------- Activity log (optional) ----------

def log_activity(session_id: int, face_present: int, input_active: int,
                 screen_productive: int, overall_status: str):
    """
    Insert a single activity snapshot for the given session.
    Requires activity_log table in MySQL:
        session_id INT, timestamp DATETIME, face_present BOOL,
        input_active BOOL, screen_productive BOOL, overall_status VARCHAR
    """
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now()
    cur.execute("""
        INSERT INTO activity_log (session_id, timestamp, face_present,
                                  input_active, screen_productive, overall_status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (session_id, now, face_present, input_active, screen_productive, overall_status))
    conn.commit()
    conn.close()
