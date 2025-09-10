"""
Monitors the user's screen to identify the active application and classify its productivity.
"""
import pygetwindow as gw
import time
from enum import Enum, auto

# Import settings from our central configuration file
import config

class ScreenActivity(Enum):
    """Enumeration for the different classification results."""
    PRODUCTIVE = auto()
    UNPRODUCTIVE = auto()
    NEUTRAL = auto()

class ScreenDetector:
    """A class to detect and classify screen activity based on the active window title."""

    def __init__(self):
        # We can add state here later, e.g., for motion detection
        pass

    def _get_active_window_title(self) -> str | None:
        """
        Gets the title of the currently active window in lowercase.
        
        Returns:
            str: The title of the active window, or None if not found or an error occurs.
        """
        try:
            active_window = gw.getActiveWindow()
            if active_window:
                return active_window.title.lower()
        except Exception:
            # Can happen if no window is active or on certain OS pop-ups
            pass
        return None

    def get_activity_classification(self) -> ScreenActivity:
        """
        Analyzes the active window title to classify the current screen activity.

        Returns:
            ScreenActivity: The classification of the current activity.
        """
        title = self._get_active_window_title()

        if title is None:
            return ScreenActivity.NEUTRAL

        # Check for unproductive keywords first
        for keyword in config.UNPRODUCTIVE_KEYWORDS:
            if keyword in title:
                return ScreenActivity.UNPRODUCTIVE

        # Then check for productive keywords
        for keyword in config.PRODUCTIVE_KEYWORDS:
            if keyword in title:
                return ScreenActivity.PRODUCTIVE

        # If no keywords match, it's neutral
        return ScreenActivity.NEUTRAL

if __name__ == '__main__':
    # A simple test block to demonstrate the class functionality.
    # Run this file directly (`python client/screen_detector.py`) to test.
    
    print("--- Testing ScreenDetector ---")
    print("This will check your active window's classification every 2 seconds for the next 20 seconds.")
    print("Click on different windows (e.g., your browser, VS Code, a file explorer) to see the output change.")
    
    detector = ScreenDetector()
    
    end_time = time.time() + 20
    while time.time() < end_time:
        classification = detector.get_activity_classification()
        active_title = detector._get_active_window_title() or "No Active Window"
        
        print(f"[{time.strftime('%H:%M:%S')}] Active Window: '{active_title[:70]}...' -> Classification: {classification.name}")
        
        time.sleep(2)

    print("\n--- Test Complete ---")
