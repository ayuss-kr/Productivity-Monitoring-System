# ui_timer_card.py
# Timer Card using CustomTkinter that reads productive seconds from shared_state.
# Run via the dashboard (ui_dashboard.py)

import customtkinter as ctk
import time
import threading
from datetime import datetime, timezone

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class TimerCard(ctk.CTkFrame):
    def __init__(self, master=None, poll_interval=1):
        super().__init__(master, corner_radius=12, fg_color="#1f2937")
        self.poll_interval = poll_interval  # seconds

        # Session state
        self.session_active = False
        self.punch_in_ts = None
        self.punch_out_ts = None

        # UI counters (kept for fallback & display)
        self.productive_seconds = 0
        self.unproductive_seconds = 0
        self.simulate_productive = False

        # UI elements
        self._build_ui()

        # Start updater
        self._running = True
        self._start_updater()

    def _build_ui(self):
        self.status_label = ctk.CTkLabel(self, text="INACTIVE", width=140, anchor="center")
        self.status_label.configure(font=("Helvetica", 11, "bold"))
        self.status_label.pack(pady=(6, 10))

        self.session_time_label = ctk.CTkLabel(self, text="Session: 00:00:00", font=("Helvetica", 24, "bold"))
        self.session_time_label.pack(pady=(0, 8))

        self.productive_label = ctk.CTkLabel(self, text="Productive: 00:00:00 (0%)", font=("Helvetica", 12))
        self.productive_label.pack(pady=(0, 8))

        self.progress = ctk.CTkProgressBar(self, width=220)
        self.progress.set(0.0)
        self.progress.pack(pady=(0, 12))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=(0, 6))

        self.punch_btn = ctk.CTkButton(btn_row, text="Punch In", width=120, command=self.on_punch)
        self.punch_btn.grid(row=0, column=0, padx=6)

        self.toggle_btn = ctk.CTkButton(btn_row, text="Simulate Productive: OFF", width=180, command=self.toggle_productive)
        self.toggle_btn.grid(row=0, column=1, padx=6)

    def on_punch(self):
        # lazy import MonitorBridge if present (defensive)
        if not self.session_active:
            # start session
            self.punch_in_ts = datetime.now(timezone.utc)
            self.punch_out_ts = None
            self.session_active = True
            self.productive_seconds = 0
            self.unproductive_seconds = 0
            self.punch_btn.configure(text="Punch Out")
            # reset shared state for new session if available
            try:
                import shared_state
                shared_state.reset_total_productive_seconds()
            except Exception:
                pass
            # optionally start the real monitor bridge if you wired it (handled elsewhere)
        else:
            # end session
            self.punch_out_ts = datetime.now(timezone.utc)
            self.session_active = False
            self.punch_btn.configure(text="Punch In")
            # optionally stop monitor bridge (handled elsewhere)

    def toggle_productive(self):
        self.simulate_productive = not self.simulate_productive
        label = "ON" if self.simulate_productive else "OFF"
        self.toggle_btn.configure(text=f"Simulate Productive: {label}")

    def _start_updater(self):
        def loop():
            while self._running:
                self._tick()
                time.sleep(self.poll_interval)
        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def stop(self):
        self._running = False

    def _tick(self):
        # Update session duration (wall clock)
        if self.session_active and self.punch_in_ts:
            now = datetime.now(timezone.utc)
            total_seconds = int((now - self.punch_in_ts).total_seconds())
            session_str = self._format_hhmmss(total_seconds)
        elif self.punch_in_ts and self.punch_out_ts:
            total_seconds = int((self.punch_out_ts - self.punch_in_ts).total_seconds())
            session_str = self._format_hhmmss(total_seconds)
        else:
            total_seconds = 0
            session_str = self._format_hhmmss(0)

        # -------------------------
        # Authoritative productive total from shared_state (if available)
        # -------------------------
        try:
            import shared_state
            total_prod = shared_state.get_total_productive_seconds()
            # set UI counter to authoritative value
            self.productive_seconds = int(total_prod)
            # compute counted time for pct: we consider only counted seconds = productive + unproductive
            # keep unproductive as total_seconds - productive (fallback)
            self.unproductive_seconds = max(0, total_seconds - self.productive_seconds)
        except Exception:
            # fallback to simulation behaviour when shared_state unavailable
            if self.session_active:
                if self.simulate_productive:
                    self.productive_seconds += 1
                else:
                    self.unproductive_seconds += 1

        # compute productive percentage (of counted time)
        counted = self.productive_seconds + self.unproductive_seconds
        pct = int(round((self.productive_seconds / counted) * 100)) if counted > 0 else 0

        # Update UI via .after to ensure main-thread-safe updates
        try:
            self.session_time_label.after(0, lambda: self.session_time_label.configure(text=f"Session: {session_str}"))
            self.productive_label.after(0, lambda: self.productive_label.configure(
                text=f"Productive: {self._format_hhmmss(self.productive_seconds)} ({pct}%)"
            ))
            self.progress.after(0, lambda: self.progress.set(pct / 100.0))
            # status pill
            if self.session_active:
                self.status_label.after(0, lambda: self.status_label.configure(text="ACTIVE", text_color="#16a34a"))
            else:
                self.status_label.after(0, lambda: self.status_label.configure(text="INACTIVE", text_color="#94a3b8"))
        except Exception:
            pass

    @staticmethod
    def _format_hhmmss(seconds):
        s = int(seconds or 0)
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        return f"{h:02d}:{m:02d}:{sec:02d}"


# quick-run demo
if __name__ == "__main__":
    root = ctk.CTk()
    root.title("Timer Card - Demo")
    root.geometry("420x280")
    frame = ctk.CTkFrame(root)
    frame.pack(expand=True, fill="both", padx=12, pady=12)
    card = TimerCard(frame)
    card.pack(expand=True, fill="both", padx=8, pady=8)

    def on_close():
        card.stop()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
