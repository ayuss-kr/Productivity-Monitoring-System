"""
Manages the state of the productivity timer, including running, paused, and grace period logic.
"""
import time
from enum import Enum, auto

class TimerState(Enum):
    """Enumeration for the different states of the timer."""
    RUNNING = auto()
    PAUSED = auto()
    IN_GRACE_PERIOD = auto()

class ProductivityTimer:
    """A class to manage a productivity timer with a grace period."""

    def __init__(self, grace_period_seconds: int):
        """
        Initializes the ProductivityTimer.

        Args:
            grace_period_seconds (int): The duration in seconds to wait before pausing.
        """
        self.total_productive_seconds = 0.0
        self.state = TimerState.PAUSED
        self.last_state_change_time = time.time()
        
        self.grace_period_seconds = grace_period_seconds
        self.grace_period_end_time = 0.0

    def update(self, is_user_productive: bool):
        """
        Updates the timer's state based on whether the user is currently productive.
        This method should be called repeatedly in the main application loop.
        """
        current_time = time.time()

        if self.state == TimerState.RUNNING:
            elapsed = current_time - self.last_state_change_time
            if not is_user_productive:
                # User was productive, but now is not. Start grace period.
                self.total_productive_seconds += elapsed
                self.state = TimerState.IN_GRACE_PERIOD
                self.grace_period_end_time = current_time + self.grace_period_seconds
                self.last_state_change_time = current_time
        
        elif self.state == TimerState.PAUSED:
            if is_user_productive:
                # User was paused, now is productive. Start running.
                self.state = TimerState.RUNNING
                self.last_state_change_time = current_time

        elif self.state == TimerState.IN_GRACE_PERIOD:
            if is_user_productive:
                # User became productive again during the grace period. Go back to running.
                self.state = TimerState.RUNNING
                # No time is added, as the grace period is "forgiven".
                self.last_state_change_time = current_time
            elif current_time > self.grace_period_end_time:
                # Grace period expired. Move to paused state.
                self.state = TimerState.PAUSED
                self.last_state_change_time = current_time

    def get_status(self) -> TimerState:
        """Returns the current state of the timer."""
        return self.state

    def get_remaining_grace_period(self) -> int:
        """Returns the remaining seconds in the grace period, or 0."""
        if self.state == TimerState.IN_GRACE_PERIOD:
            remaining = self.grace_period_end_time - time.time()
            return max(0, int(remaining))
        return 0

    def get_formatted_total_time(self) -> str:
        """
        Calculates and returns the total productive time as a formatted string (HH:MM:SS).
        """
        current_time = time.time()
        total_seconds = self.total_productive_seconds

        # If the timer is currently running, add the time since the last state change
        if self.state == TimerState.RUNNING:
            total_seconds += current_time - self.last_state_change_time

        # Format into HH:MM:SS
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

if __name__ == '__main__':
    # A simple test block to demonstrate the class functionality.
    # Run this file directly (`python client/timer.py`) to test.
    print("--- Testing ProductivityTimer ---")
    timer = ProductivityTimer(grace_period_seconds=5)
    print("Timer started. Simulating 15 seconds of activity.")
    
    # Simulate some activity
    is_active = True
    for i in range(15):
        if i == 4:
            print("\n>>> Simulating distraction...")
            is_active = False
        if i == 12:
            print("\n>>> Simulating productivity again...")
            is_active = True
            
        timer.update(is_active)
        print(f"Second {i+1}: Status = {timer.get_status().name}, Total Time = {timer.get_formatted_total_time()}")
        time.sleep(1)
        
    print("\n--- Test Complete ---")

