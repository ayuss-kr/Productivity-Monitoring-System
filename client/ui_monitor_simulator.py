# ui_monitor_simulator.py
# Simulator that pushes periodic (fake) session + app-usage updates
# into the TimerCard and AppUsageTable UI components, and requests favicons.

import threading
import time
from datetime import datetime, timezone, timedelta
import random

BROWSER_SAMPLE_DOMAINS = [
    "openai.com", "github.com", "stackoverflow.com", "news.ycombinator.com",
    "google.com", "medium.com", "docs.python.org"
]

class MonitorSimulator:
    def __init__(self, timer_card, app_table, tick_interval=1.0):
        """
        timer_card: instance of TimerCard (ui_timer_card.TimerCard)
        app_table: instance of AppUsageTable (ui_app_usage.AppUsageTable)
        tick_interval: seconds between updates
        """
        self.timer_card = timer_card
        self.app_table = app_table
        self.tick = tick_interval

        self._running = False
        self._thread = None

        # small internal state: app rows (list of dicts)
        now = datetime.now(timezone.utc)
        self._rows = [
            {
                "usage_id": 101,
                "app_name": "Google Chrome",
                "window_title": "ChatGPT — OpenAI",
                "domain": "openai.com",
                "category": "productive",
                "productive_sec": 120,
                "duration_sec": 150,
                "start_time": now,
                "end_time": None,
            },
            {
                "usage_id": 102,
                "app_name": "Visual Studio Code",
                "window_title": "main.py — Productivity App",
                "domain": None,
                "category": "productive",
                "productive_sec": 600,
                "duration_sec": 720,
                "start_time": now - timedelta(minutes=10),
                "end_time": None,
            },
            {
                "usage_id": 103,
                "app_name": "Spotify",
                "window_title": "Your Playlist",
                "domain": None,
                "category": "unproductive",
                "productive_sec": 0,
                "duration_sec": 300,
                "start_time": now - timedelta(minutes=5),
                "end_time": None,
            },
        ]

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _loop(self):
        """
        Each tick:
         - increments durations for rows
         - randomly adds productive seconds to 'productive' rows
         - occasionally switches active app (small simulation)
         - writes updates into the UI via thread-safe methods and triggers favicon fetches
        """
        while self._running:
            # update rows
            for r in self._rows:
                # every tick, duration increments
                r["duration_sec"] = r.get("duration_sec", 0) + int(self.tick)

                # probabilistically increment productive_sec for productive rows
                if r.get("category") == "productive":
                    # simulate that most ticks are productive, but sometimes not
                    r["productive_sec"] = r.get("productive_sec", 0) + (1 if random.random() < 0.9 else 0)
                else:
                    # unproductive rows rarely increase productive time
                    r["productive_sec"] = r.get("productive_sec", 0)

            # Occasionally add a new short row to simulate switching to a website
            if random.random() < 0.18:  # increase chance so you see favicons more frequently
                newid = max(r["usage_id"] for r in self._rows) + 1
                now = datetime.now(timezone.utc)
                app_choice = random.choice(["Chrome", "Edge", "Firefox", "Notepad", "Slack"])
                # choose domain only for browsers
                domain = random.choice(BROWSER_SAMPLE_DOMAINS) if app_choice in ("Chrome", "Edge", "Firefox") else None
                title_choice = {
                    "Chrome": random.choice(["ChatGPT", "OpenAI Blog", "GitHub"]),
                    "Edge": random.choice(["News", "Docs", "Gmail"]),
                    "Firefox": random.choice(["Stack Overflow", "Medium", "Hacker News"]),
                    "Notepad": "notes.txt",
                    "Slack": "General — Workspace"
                }.get(app_choice, "Window")
                newrow = {
                    "usage_id": newid,
                    "app_name": app_choice,
                    "window_title": title_choice,
                    "domain": domain,
                    "category": random.choice(["productive", "unproductive"]),
                    "productive_sec": 0,
                    "duration_sec": random.randint(5, 20),
                    "start_time": now,
                    "end_time": None,
                }
                self._rows.insert(0, newrow)
                # keep list small
                if len(self._rows) > 18:
                    self._rows = self._rows[:18]

            # Compute aggregate productive/unproductive for timer_card
            total_prod = sum(r.get("productive_sec", 0) for r in self._rows)
            total_dur = sum(r.get("duration_sec", 0) for r in self._rows)
            total_unp = max(0, total_dur - total_prod)

            # Update timer_card counters on the main thread
            try:
                def apply_counts():
                    self.timer_card.productive_seconds = int(total_prod)
                    self.timer_card.unproductive_seconds = int(total_unp)
                self.timer_card.session_time_label.after(0, apply_counts)
            except Exception:
                pass

            # Update table rows on UI: convert to strings expected by AppUsageTable
            try:
                def push_table():
                    tree = self.app_table.table
                    # clear table
                    for iid in tree.get_children():
                        tree.delete(iid)
                    # insert new rows with images
                    for idx, r in enumerate(self._rows):
                        app = r.get("app_name", "")
                        title = r.get("window_title", "")
                        dur = r.get("duration_sec", 0)
                        hh = dur // 3600
                        mm = (dur % 3600) // 60
                        ss = dur % 60
                        dur_str = f"{hh:02d}:{mm:02d}:{ss:02d}"

                        # use usage_id if present so keys are stable; fallback to idx
                        uid = r.get("usage_id", None)
                        key = f"row_{uid}" if uid is not None else f"row_{idx}"

                        # get immediate icon (placeholder or cached favicon)
                        try:
                            photo = self.app_table.icon_manager.get_icon_sync(
                                app_name=app, domain=r.get("domain"), key=key
                            )
                            # keep a reference so PhotoImage isn't GC'd
                            self.app_table._item_image_refs[key] = photo
                        except Exception:
                            photo = None

                        # insert item into tree: image in #0 (tree column), text is app name
                        try:
                            tree.insert("", "end", iid=key, text=app, image=photo, values=(title, dur_str))
                        except Exception:
                            # fallback: insert without image
                            tree.insert("", "end", iid=key, text=app, values=(title, dur_str))

                        # If this row has a domain, kick off favicon fetch (async)
                        domain = r.get("domain")
                        if domain:
                            try:
                                # request async favicon; when ready, AppUsageTable._on_favicon_ready will update
                                self.app_table.icon_manager.fetch_favicon_async(domain, key, callback=self.app_table._on_favicon_ready)
                            except Exception:
                                pass

                # schedule the push on the Tk main loop
                self.app_table.table.after(0, push_table)
            except Exception:
                pass

            time.sleep(self.tick)
