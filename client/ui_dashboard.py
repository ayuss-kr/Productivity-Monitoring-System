# ui_dashboard.py
# Dashboard wired to MonitorBridge (real monitor) and DB polling.
# Overwrites previous safe-mode file. Run: python ui_dashboard.py

import customtkinter as ctk
from tkinter import LEFT, BOTH, RIGHT, YES
import ui_timer_card   # your TimerCard file
import ui_app_usage    # your AppUsageTable file

# MonitorBridge wrapper (starts/stops ProductivityMonitor and DB sessions)
from ui_monitor_bridge import MonitorBridge

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def main():
    root = ctk.CTk()
    root.title("Productivity Dashboard - Live Mode")
    root.geometry("1000x640")
    root.minsize(900, 520)

    # create a single MonitorBridge instance (headless by default)
    bridge = MonitorBridge(show_window=False)
    # attach to root for debugging access if needed
    root._monitor_bridge = bridge

    # Outer padding frame
    outer = ctk.CTkFrame(root)
    outer.pack(expand=True, fill="both", padx=16, pady=16)

    # Left: Timer card (fixed width-ish)
    left_container = ctk.CTkFrame(outer, fg_color="transparent")
    left_container.pack(side=LEFT, fill="y", padx=(0, 12))

    timer_card = ui_timer_card.TimerCard(left_container)
    timer_card.pack(expand=False, fill=None, padx=8, pady=8)

    # Right: App usage table (expands)
    right_container = ctk.CTkFrame(outer, fg_color="transparent")
    right_container.pack(side=RIGHT, fill=BOTH, expand=YES)

    app_table = ui_app_usage.AppUsageTable(right_container)
    app_table.pack(fill=BOTH, expand=True, padx=8, pady=8)

    # ---- Polling loop: update UI from MonitorBridge every 1s ----
    def poll_bridge():
        try:
            st = bridge.get_status()
        except Exception as e:
            # Defensive: if bridge fails, print and retry next tick
            print(f"[UI Poll] Bridge.get_status() failed: {e}")
            st = {"running": False, "status_text": None, "total_time": None, "session_id": None}

        # 1) Update TimerCard display from monitor if running
        try:
            if st.get("running"):
                # display monitor provided time/status non-invasively
                total = st.get("total_time") or "00:00:00"
                status_text = st.get("status_text") or ""
                try:
                    # Prefer updating a dedicated label if TimerCard exposes it
                    timer_card.update_from_monitor(total_time_str=total, status_text=status_text)
                except Exception:
                    # fallback: set productive_label text
                    try:
                        timer_card.productive_label.configure(text=f"Productive: {total}")
                    except Exception:
                        pass
            else:
                # if not running, leave TimerCard as-is
                pass
        except Exception as e:
            print(f"[UI Poll] TimerCard update failed: {e}")

        # 2) If monitor running and has a session, pull recent DB app rows and show in table
        try:
            if st.get("running") and st.get("session_id"):
                rows = bridge.get_recent_app_rows(limit=30)
                # convert DB rows (dicts) into the structure expected by replace_rows_from_list
                app_rows = []
                for r in rows:
                    # DB columns: id, app_name, window_title, duration_sec, start_time, end_time
                    dur = r.get("duration_sec") or 0
                    hh = dur // 3600
                    mm = (dur % 3600) // 60
                    ss = dur % 60
                    dur_str = f"{hh:02d}:{mm:02d}:{ss:02d}"
                    app_rows.append({
                        "app_name": r.get("app_name") or "",
                        "window_title": r.get("window_title") or "",
                        "duration_str": dur_str,
                        "domain": None,
                        "exe_path": None
                    })
                if app_rows:
                    app_table.replace_rows_from_list(app_rows)
        except Exception as e:
            # DB or bridge may fail; print and continue
            print(f"[UI Poll] Fetching recent app rows failed: {e}")

        # schedule next poll
        root.after(1000, poll_bridge)

    # start polling after a short delay
    root.after(1000, poll_bridge)

    # Close handling: ensure monitor stops
    def on_close():
        try:
            # stop monitor if running
            if hasattr(root, "_monitor_bridge"):
                try:
                    root._monitor_bridge.stop_monitor()
                except Exception:
                    pass
        except Exception:
            pass

        try:
            timer_card.stop()
        except Exception:
            pass
        # ensure icon manager cleanup if present
        try:
            if hasattr(app_table, "icon_manager"):
                app_table.icon_manager.ensure_root_destroyed()
        except Exception:
            pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
