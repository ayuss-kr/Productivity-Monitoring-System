
import keyboard
import mouse
import threading
import time

class InputDetector:
    """
    A class to detect keyboard and mouse activity using background listeners.
    
    This class is designed to be thread-safe. The listeners run in separate
    threads and update a shared flag, which is protected by a lock.
    """
    def __init__(self):
        self._activity_detected = False
        self._lock = threading.Lock()
        
        # Start the listeners in the background
        self._start_listeners()

    def _on_activity(self, event):
        """Callback function that sets the activity flag."""
        with self._lock:
            self._activity_detected = True

    def _start_listeners(self):
        """Initializes and starts the keyboard and mouse listeners."""
        # The keyboard and mouse libraries run their own background threads.
        keyboard.hook(self._on_activity)
        mouse.hook(self._on_activity)
        print("Input listeners started.")

    def get_and_reset_activity(self) -> bool:
        """
        Checks if any activity has been detected since the last call and resets the flag.
        This is the main method to be called from the application's main loop.

        Returns:
            bool: True if activity was detected, False otherwise.
        """
        with self._lock:
            activity_status = self._activity_detected
            self._activity_detected = False  # Reset the flag after checking
            return activity_status

    def stop_listeners(self):
        """Stops the listeners to allow for a clean shutdown."""
        keyboard.unhook_all()
        mouse.unhook_all()
        print("Input listeners stopped.")

if __name__ == '__main__':
    # A simple test block to demonstrate the class functionality.
    # Run this file directly (`python client/input_detector.py`) to test.
    
    print("--- Testing InputDetector ---")
    print("Monitoring keyboard and mouse activity for 10 seconds...")
    print("Try typing or moving your mouse.")
    
    detector = InputDetector()
    
    end_time = time.time() + 10
    while time.time() < end_time:
        if detector.get_and_reset_activity():
            print(f"[{time.strftime('%H:%M:%S')}] Activity Detected!")
        time.sleep(1) # Check for activity once per second

    detector.stop_listeners()
    print("\n--- Test Complete ---")
