# test_icons.py
# Quick test for IconManager to confirm PhotoImages are generated and usable.

import tkinter as tk
from ui_icons import IconManager
import time

def main():
    root = tk.Tk()
    root.title("Icon Test")
    root.geometry("240x120")

    mgr = IconManager(tk_root=root)

    # Request two icons
    photo1 = mgr.get_icon_sync(app_name="Chrome", domain=None, key="t1")
    photo2 = mgr.get_icon_sync(app_name="VS Code", domain=None, key="t2")

    print("photo1:", type(photo1), bool(photo1))
    print("photo2:", type(photo2), bool(photo2))
    print("cached t1:", bool(mgr.get_cached_photo("t1")))
    print("cached t2:", bool(mgr.get_cached_photo("t2")))

    # Show them in labels so Tk displays them
    lbl1 = tk.Label(root, image=photo1, text=" Chrome", compound="left", padx=8)
    lbl1.pack(pady=6)
    lbl2 = tk.Label(root, image=photo2, text=" VS Code", compound="left", padx=8)
    lbl2.pack(pady=6)

    # Keep references in case they might be garbage-collected (defensive)
    root._photos = {"t1": photo1, "t2": photo2}

    root.mainloop()

if __name__ == "__main__":
    main()
