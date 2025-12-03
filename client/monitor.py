import cv2
import time
import threading

from timer import ProductivityTimer, TimerState
from input_detector import InputDetector
from screen_detector import ScreenDetector, ScreenActivity
from face_detector import FaceDetector
import config

from db import update_session_productivity, log_activity  # log_activity is optional; remove if not using


class ProductivityMonitor(threading.Thread):
    """
    Runs the productivity monitoring loop in a background thread.
    It can be started when the user Punches In, and stopped on Punch Out.
    """

    def __init__(self, session_id: int, show_window: bool = True):
        super().__init__(daemon=True)
        self.session_id = session_id
        self.show_window = show_window

        self._stop_event = threading.Event()

        # detectors and timer will be initialized in run()
        self.timer = None
        self.input_detector = None
        self.screen_detector = None
        self.face_detector = None

        # for UI / dashboard polling (optional)
        self.current_status_text = "Not started"
        self.current_total_time_str = "00:00:00"

    def stop(self):
        """Request the monitoring loop to stop."""
        self._stop_event.set()

    def run(self):
        print(f"[Monitor] Starting Productivity Monitoring for session {self.session_id}...")

        # --- Initialization ---
        self.timer = ProductivityTimer(grace_period_seconds=config.GRACE_PERIOD_SECONDS)
        self.input_detector = InputDetector()
        self.screen_detector = ScreenDetector()
        self.face_detector = FaceDetector()

        last_time = time.time()
        # accumulator to collect fractional seconds and publish whole-second increments
        productive_accum = 0.0

        try:
            while not self._stop_event.is_set():
                now = time.time()
                dt = now - last_time
                last_time = now

                # --- 1. Gather Data from All Sensors ---
                input_activity = self.input_detector.get_and_reset_activity()
                screen_classification = self.screen_detector.get_activity_classification()
                face_focused, frame = self.face_detector.is_user_present_and_focused()

                if frame is None:
                    print("[Monitor] Could not retrieve frame from webcam. Stopping monitor.")
                    break

                # --- 2. Core Decision-Making Logic ---
                is_productive = False

                if screen_classification == ScreenActivity.UNPRODUCTIVE:
                    # Rule 1: Unproductive apps are never productive.
                    is_productive = False
                elif screen_classification == ScreenActivity.PRODUCTIVE:
                    # Rule 2: For explicitly PRODUCTIVE apps, allow head-down typing.
                    is_productive = face_focused or input_activity
                elif screen_classification == ScreenActivity.NEUTRAL:
                    # Rule 3: For NEUTRAL apps, require focus.
                    is_productive = face_focused

                # --- 3. Update Timer ---
                self.timer.update(is_productive)

                # -----------------------
                # Publish classifier decision to shared_state (UI bridge)
                # - accumulate dt so we add only whole seconds
                # - set an instantaneous productive flag for UI
                # -----------------------
                try:
                    import shared_state
                    # set transient flag for UI (True if this tick judged productive)
                    try:
                        shared_state.set_productive_flag(bool(is_productive))
                    except Exception:
                        pass

                    # accumulate productive seconds and publish whole-second increments
                    if is_productive:
                        productive_accum += dt
                        if productive_accum >= 1.0:
                            # add whole seconds to shared state
                            to_add = int(productive_accum)
                            for _ in range(to_add):
                                try:
                                    shared_state.add_productive_seconds(1)
                                except Exception:
                                    pass
                            productive_accum -= to_add
                    else:
                        # when not productive, we do not add; keep accumulator as-is
                        pass
                except Exception as e:
                    # non-fatal: if shared_state isn't available, continue running monitor
                    print(f"[Monitor] shared_state publish failed: {e}")

                # store formatted time & status for GUI polling
                status = self.timer.get_status()
                total_time_str = self.timer.get_formatted_total_time()
                self.current_total_time_str = total_time_str

                if status == TimerState.RUNNING:
                    status_text = "PRODUCTIVE"
                elif status == TimerState.PAUSED:
                    status_text = "UNPRODUCTIVE"
                else:
                    status_text = f"GRACE PERIOD ({self.timer.get_remaining_grace_period()}s)"

                self.current_status_text = status_text

                # --- 4. Update DB with time deltas ---
                # NOTE: this uses raw dt from loop. If you want exact equality with timer,
                # you can modify your ProductivityTimer to expose numeric total seconds.
                productive_delta = int(dt) if is_productive else 0
                unproductive_delta = int(dt) if not is_productive else 0

                if productive_delta or unproductive_delta:
                    update_session_productivity(
                        self.session_id,
                        productive_delta,
                        unproductive_delta
                    )

                # --- 5. Optional: log raw activity (if you created activity_log table) ---
                try:
                    log_activity(
                        self.session_id,
                        int(bool(face_focused)),
                        int(bool(input_activity)),
                        int(screen_classification == ScreenActivity.PRODUCTIVE),
                        "productive" if is_productive else "unproductive"
                    )
                except Exception:
                    # If you haven't implemented log_activity, you can ignore this.
                    pass

                # --- 6. Display Feedback with OpenCV (if enabled) ---
                if self.show_window:
                    ui_frame = self._draw_ui(frame, status_text, total_time_str)
                    cv2.imshow("Productivity Monitor", ui_frame)

                    # Allow user to close window with 'q'
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("[Monitor] 'q' pressed. Stopping monitor.")
                        self.stop()

                # A small sleep to prevent the loop from running too fast
                time.sleep(0.05)

        finally:
            print("[Monitor] Releasing resources...")
            if self.input_detector:
                self.input_detector.stop_listeners()
            if self.face_detector:
                self.face_detector.release()
            if self.show_window:
                cv2.destroyAllWindows()
            print("[Monitor] Shutdown complete.")

    @staticmethod
    def _draw_ui(frame, status_text: str, total_time_str: str):
        """Draw the status UI on the video frame (adapted from your draw_ui())."""
        # semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], 80), (0, 0, 0), -1)
        alpha = 0.6
        frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

        # status text color
        if status_text.startswith("PRODUCTIVE"):
            color = (0, 255, 0)
        elif status_text.startswith("UNPRODUCTIVE"):
            color = (0, 0, 255)
        else:
            color = (0, 165, 255)

        # status text
        (text_width, text_height), _ = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
        cv2.putText(frame, status_text,
                    (frame.shape[1] - text_width - 20, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)

        # total productive time
        cv2.putText(frame, f"Time: {total_time_str}",
                    (20, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)

        return frame
