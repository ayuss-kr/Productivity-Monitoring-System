"""
The main entry point for the client-side productivity monitoring application.

This script orchestrates all the individual sensor modules, makes a final
productivity decision, and displays real-time feedback to the user.
"""
import cv2
import time

# Import our custom modules
from timer import ProductivityTimer, TimerState
from input_detector import InputDetector
from screen_detector import ScreenDetector, ScreenActivity
from face_detector import FaceDetector
import config

def draw_ui(frame, timer: ProductivityTimer):
    """Draws the status UI on the video frame."""
    # Get the current state and time from the timer
    status = timer.get_status()
    total_time_str = timer.get_formatted_total_time()

    # Determine color and text for the status
    if status == TimerState.RUNNING:
        status_text = "PRODUCTIVE"
        color = (0, 255, 0)  # Green
    elif status == TimerState.PAUSED:
        status_text = "UNPRODUCTIVE"
        color = (0, 0, 255)  # Red
    else: # IN_GRACE_PERIOD
        status_text = f"GRACE PERIOD ({timer.get_remaining_grace_period()}s)"
        color = (0, 165, 255) # Orange

    # --- UI Drawing ---
    # Draw a semi-transparent background rectangle for the text
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (frame.shape[1], 80), (0, 0, 0), -1)
    alpha = 0.6
    frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    # Draw the status text
    (text_width, text_height), _ = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
    cv2.putText(frame, status_text, (frame.shape[1] - text_width - 20, 55), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)

    # Draw the total productive time
    cv2.putText(frame, f"Time: {total_time_str}", (20, 55), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
    
    return frame

def main():
    """Main function to run the productivity monitoring application."""
    print("Starting Productivity Monitoring System...")

    # --- Initialization ---
    timer = ProductivityTimer(grace_period_seconds=config.GRACE_PERIOD_SECONDS)
    input_detector = InputDetector()
    screen_detector = ScreenDetector()
    face_detector = FaceDetector()

    print("\n--- System is now running. Press 'q' in the video window to quit. ---")

    try:
        while True:
            # --- 1. Gather Data from All Sensors ---
            input_activity = input_detector.get_and_reset_activity()
            screen_classification = screen_detector.get_activity_classification()
            face_focused, frame = face_detector.is_user_present_and_focused()

            if frame is None:
                print("Could not retrieve frame from webcam. Exiting.")
                break

            # --- 2. Core Decision-Making Logic ---
            is_productive = False
            
            # This is a more nuanced logic that balances different work styles.
            if screen_classification == ScreenActivity.UNPRODUCTIVE:
                # Rule 1: Unproductive apps are never productive.
                is_productive = False
            elif screen_classification == ScreenActivity.PRODUCTIVE:
                # Rule 2: For explicitly PRODUCTIVE apps, allow head-down typing.
                # Timer runs if user is focused OR actively using keyboard/mouse.
                is_productive = face_focused or input_activity
            elif screen_classification == ScreenActivity.NEUTRAL:
                # Rule 3: For NEUTRAL apps, require focus. This prevents the timer
                # from running if the user walks away from a generic browser window.
                is_productive = face_focused

            # --- 3. Update Timer ---
            timer.update(is_productive)

            # --- 4. Display Feedback ---
            ui_frame = draw_ui(frame, timer)
            cv2.imshow("Productivity Monitor", ui_frame)

            # --- 5. Handle Exit ---
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n'q' pressed. Shutting down...")
                break
            
            # A small sleep to prevent the loop from running too fast and using 100% CPU
            time.sleep(0.05)

    finally:
        # --- Cleanup ---
        print("Releasing resources...")
        input_detector.stop_listeners()
        face_detector.release()
        print("Shutdown complete.")


if __name__ == "__main__":
    main()

