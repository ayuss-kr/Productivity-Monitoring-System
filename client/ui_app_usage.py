# ui_app_usage.py
# App Usage Table using CustomTkinter + small icons support + Export CSV
# Run: python ui_app_usage.py or run via the dashboard

import customtkinter as ctk
from ui_icons import IconManager
from tkinter import ttk, filedialog, messagebox
import csv
from datetime import datetime

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AppUsageTable(ctk.CTkFrame):
    def __init__(self, master=None):
        super().__init__(master, fg_color="#1f2937", corner_radius=12)

        self._build_ui()

        # icon manager (use the existing Tk root)
        self.icon_manager = IconManager(tk_root=self.winfo_toplevel())
        self._item_image_refs = {}  # keep PhotoImage refs to avoid GC

        self._populate_fake_data()

    def _build_ui(self):
        # Top row: title + export button
        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", pady=(8, 6), padx=10)

        title = ctk.CTkLabel(top_row, text="App Usage", font=("Arial", 18, "bold"))
        title.pack(side="left")

        self.export_btn = ctk.CTkButton(top_row, text="Export CSV", width=100, command=self.export_csv)
        self.export_btn.pack(side="right")

        # Table container
        table_frame = ctk.CTkFrame(self, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Treeview: use the tree column (#0) for icon+app name so images render reliably
        style = ttk.Style()
        style.theme_use("default")

        style.configure(
            "Treeview",
            background="#1f2937",
            foreground="white",
            rowheight=40,          # make room for icons
            fieldbackground="#1f2937",
            borderwidth=0
        )
        style.map("Treeview", background=[("selected", "#374151")])

        # use show='tree headings' so #0 is visible and usable for icon+app
        self.table = ttk.Treeview(
            table_frame,
            columns=("title", "time"),
            show="tree headings",
            height=10
        )

        # Configure the special #0 column for App (icon + name)
        self.table.heading("#0", text="App")
        self.table.column("#0", width=220, anchor="w")

        # Other columns
        self.table.heading("title", text="Window Title")
        self.table.heading("time", text="Duration")

        self.table.column("title", width=340, anchor="w")
        self.table.column("time", width=100, anchor="center")

        # Enable single row selection
        self.table.bind("<<TreeviewSelect>>", self._on_row_selected)

        self.table.pack(fill="both", expand=True)

        # bottom small status
        self.status_label = ctk.CTkLabel(self, text="", font=("Arial", 10))
        self.status_label.pack(fill="x", padx=10, pady=(6, 8))

    def _populate_fake_data(self):
        fake_rows = [
            ("Chrome", "ChatGPT – OpenAI", "00:45:12", "openai.com"),
            ("VS Code", "main.py – Productivity App", "01:12:38", None),
            ("Spotify", "Your Playlist", "00:23:08", None),
            ("Figma", "Design Board", "00:33:41", None),
        ]

        # clear any existing items
        for iid in self.table.get_children():
            self.table.delete(iid)

        for idx, row in enumerate(fake_rows):
            app = row[0]
            title = row[1]
            dur = row[2]
            domain = row[3]  # None in fake data; real rows can set domain

            # unique key for this row
            key = f"row_{idx}"

            # immediate icon (placeholder or cached favicon)
            photo = self.icon_manager.get_icon_sync(app_name=app, domain=domain, key=key)
            self._item_image_refs[key] = photo  # keep ref

            # insert item into tree: image in #0 (tree column), text is app name
            self.table.insert("", "end", iid=key, text=app, image=photo, values=(title, dur))

            # if domain known, fetch favicon async and update when ready
            if domain:
                self.icon_manager.fetch_favicon_async(domain, key, callback=self._on_favicon_ready)

        self.status_label.configure(text=f"{len(fake_rows)} items")

    def _on_favicon_ready(self, key):
        # called when IconManager fetched a favicon and stored PhotoImage in cache
        photo = self.icon_manager.get_cached_photo(key)
        if photo:
            try:
                self._item_image_refs[key] = photo
                self.table.item(key, image=photo)
            except Exception:
                pass

    def _on_row_selected(self, event):
        # show a tiny contextual status with selected row info
        sel = self.table.selection()
        if not sel:
            self.status_label.configure(text="")
            return
        iid = sel[0]
        vals = self.table.item(iid)
        app = vals.get("text", "")
        title = vals.get("values", ["", ""])[0] if vals.get("values") else ""
        self.status_label.configure(text=f"Selected: {app} — {title}")

    # --------------------
    # Export CSV feature
    # --------------------
    def export_csv(self):
        """
        Export current visible rows to CSV.
        Columns: App, Window Title, Duration
        """
        # Default filename with timestamp
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"session_{ts}.csv"

        # Ask user where to save
        try:
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                initialfile=default_name,
                title="Export App Usage to CSV"
            )
            if not path:
                return  # user cancelled

            rows = []
            for iid in self.table.get_children():
                item = self.table.item(iid)
                app = item.get("text", "")
                values = item.get("values", ["", ""])
                title = values[0] if len(values) > 0 else ""
                duration = values[1] if len(values) > 1 else ""
                rows.append((app, title, duration))

            # Write CSV
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["App", "Window Title", "Duration"])
                for r in rows:
                    writer.writerow(r)

            messagebox.showinfo("Export complete", f"Exported {len(rows)} rows to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export failed", f"Could not export CSV:\n{e}")

    # --------------------
    # Utilities for external updates
    # --------------------
    def replace_rows_from_list(self, rows):
        """
        Accept rows as list of tuples: (app_name, window_title, duration_str, domain?, exe_path?)
        Rebuilds the table (used by simulator or real monitor).
        """
        # clear
        for iid in self.table.get_children():
            self.table.delete(iid)

        for idx, r in enumerate(rows):
            # r may be tuple or dict-like
            if isinstance(r, dict):
                app = r.get("app_name", "")
                title = r.get("window_title", "")
                dur = r.get("duration_str", r.get("duration", "00:00:00"))
                domain = r.get("domain")
                exe = r.get("exe_path")
            else:
                app, title, dur = r[0], r[1], r[2]
                domain = r[3] if len(r) > 3 else None
                exe = r[4] if len(r) > 4 else None

            key = f"row_{idx}"
            photo = self.icon_manager.get_icon_sync(app_name=app, domain=domain, exe_path=exe, key=key)
            self._item_image_refs[key] = photo
            self.table.insert("", "end", iid=key, text=app, image=photo, values=(title, dur))
            if domain:
                self.icon_manager.fetch_favicon_async(domain, key, callback=self._on_favicon_ready)

        self.status_label.configure(text=f"{len(rows)} items")


def main():
    root = ctk.CTk()
    root.title("App Usage Table – Demo")
    root.geometry("650x350")

    table = AppUsageTable(root)
    table.pack(fill="both", expand=True, padx=16, pady=16)

    root.mainloop()


if __name__ == "__main__":
    main()
