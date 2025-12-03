# ui_dashboard.py
# Combines the Timer Card and App Usage Table into one clean dashboard.
# Run: python ui_dashboard.py

import customtkinter as ctk
from tkinter import LEFT, BOTH, RIGHT, YES
import ui_timer_card   # your TimerCard file
import ui_app_usage    # your AppUsageTable file

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def main():
    root = ctk.CTk()
    root.title("Productivity Dashboard - Demo")
    root.geometry("1000x640")
    # Minimum size to keep layout sane
    root.minsize(900, 520)

    # Outer padding frame
    outer = ctk.CTkFrame(root)
    outer.pack(expand=True, fill="both", padx=16, pady=16)

    # Left: Timer card (fixed width-ish)
    left_container = ctk.CTkFrame(outer, fg_color="transparent")
    left_container.pack(side=LEFT, fill="y", padx=(0, 12))

    timer_card = ui_timer_card.TimerCard(left_container)
    # pack with padding (TimerCard removed internal padx/pady earlier)
    timer_card.pack(expand=False, fill=None, padx=8, pady=8)

    # Right: App usage table (expands)
    right_container = ctk.CTkFrame(outer, fg_color="transparent")
    right_container.pack(side=RIGHT, fill=BOTH, expand=YES)

    app_table = ui_app_usage.AppUsageTable(right_container)
    app_table.pack(fill=BOTH, expand=True, padx=8, pady=8)

    # --- Start the simulator that will update both components ---
    from ui_monitor_simulator import MonitorSimulator
    sim = MonitorSimulator(timer_card, app_table)
    sim.start()

    # Properly stop background threads on close
    def on_close():
        try:
            sim.stop()
        except Exception:
            pass
        try:
            timer_card.stop()
        except Exception:
            pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
