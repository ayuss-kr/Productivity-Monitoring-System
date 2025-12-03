# ui_icons.py
# Complete icon manager for CustomTkinter / Tkinter tables
# Supports:
#  - Placeholder initials icons
#  - Google favicon service
#  - /favicon.ico fallback (https + http)
#  - HTML <link rel="icon"> discovery
#  - Async fetching
#  - Disk cache (.png)
#  - Tk PhotoImage references

import os
import threading
import hashlib
from pathlib import Path
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont
import tkinter as tk

# Cache directory
CACHE_DIR = Path.home() / ".prod_monitor_ui" / "icon_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

ICON_SIZE = 20

# Colors used for placeholder icons
PALETTE = [
    "#ef4444", "#f97316", "#f59e0b", "#eab308",
    "#10b981", "#06b6d4", "#3b82f6", "#8b5cf6",
    "#ec4899", "#64748b"
]

# Load a font for initials
def _get_font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        try:
            return ImageFont.load_default()
        except:
            return None

FONT = _get_font(12)


class IconManager:
    def __init__(self, tk_root=None):
        """
        tk_root: Tk root instance.
        If not provided, a hidden root is created (valid but not ideal).
        """
        self._tk_root_provided = tk_root is not None
        self._root = tk_root or tk.Tk()
        if not self._tk_root_provided:
            self._root.withdraw()

        self._photo_cache = {}   # key -> PhotoImage
        self._fetching = set()   # domains currently fetching

    # ------------------------
    # INTERNAL HELPERS
    # ------------------------
    def _hash(self, v: str):
        return hashlib.sha1(v.encode("utf8")).hexdigest()

    def _png_path(self, key: str):
        return CACHE_DIR / f"{self._hash(key)}.png"

    def _ico_path(self, key: str):
        return CACHE_DIR / f"{self._hash(key)}.ico"

    def _make_initials_icon(self, text: str, size=ICON_SIZE) -> Image.Image:
        """
        Generate a circular placeholder icon with initials.
        """
        h = int(self._hash(text)[:8], 16)
        color = PALETTE[h % len(PALETTE)]

        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Circle
        draw.ellipse((0, 0, size, size), fill=color)

        # Text initials (1–2 chars)
        initials = "".join([p[0] for p in text.split() if p])[:2].upper()
        if not initials:
            initials = text[:2].upper()

        if FONT:
            bbox = draw.textbbox((0, 0), initials, font=FONT)
            w = bbox[2] - bbox[0]
            h_text = bbox[3] - bbox[1]
            draw.text(
                ((size - w) / 2, (size - h_text) / 2 - 1),
                initials, fill="white", font=FONT
            )
        else:
            draw.text((size/3, size/4), initials, fill="white")

        return img

    def _pil_to_photo(self, pil_img: Image.Image):
        """
        Convert PIL image to Tk PhotoImage.
        """
        bio = BytesIO()
        pil_img.save(bio, format="PNG")
        bio.seek(0)
        return tk.PhotoImage(data=bio.read())

    def _store_png_and_photo(self, pil_img: Image.Image, key: str):
        """
        Resize PIL image, save PNG to disk, and store PhotoImage in memory cache.
        """
        pil = pil_img.convert("RGBA")
        pil = pil.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)

        png_path = self._png_path(key)
        pil.save(png_path, format="PNG")

        photo = self._pil_to_photo(pil)
        self._photo_cache[key] = photo
        return True

    # ------------------------
    # PUBLIC: SYNC GETTER
    # ------------------------
    def get_icon_sync(self, app_name=None, domain=None, key=None):
        """
        Get icon immediately:
        - Returns cached favicon if exists
        - Otherwise returns placeholder initials icon
        """

        if key is None:
            key = (domain or app_name or "app")

        # 1) Check PNG cache
        png = self._png_path(key)
        if png.exists():
            try:
                pil = Image.open(png).convert("RGBA")
                pil = pil.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
                photo = self._pil_to_photo(pil)
                self._photo_cache[key] = photo
                return photo
            except:
                pass

        # 2) Fallback: initials icon
        name = app_name or (domain or "App")
        pil = self._make_initials_icon(name)
        photo = self._pil_to_photo(pil)

        self._photo_cache[key] = photo
        return photo

    # ------------------------
    # PUBLIC: ASYNC FETCH
    # ------------------------
    def fetch_favicon_async(self, domain: str, key: str, callback=None):
        """
        Improved favicon fetch (Google API + fallback).
        """
        if not domain:
            return
        if domain in self._fetching:
            return

        self._fetching.add(domain)

        def worker():
            try:
                # 1) GOOGLE FAVICON SERVICE
                try:
                    google = f"https://www.google.com/s2/favicons?domain={domain}&sz={ICON_SIZE}"
                    r = requests.get(google, timeout=3)
                    if r.status_code == 200 and r.content:
                        try:
                            pil = Image.open(BytesIO(r.content))
                            if self._store_png_and_photo(pil, key):
                                return
                        except:
                            pass
                except:
                    pass

                # 2) DIRECT /favicon.ico (https + http)
                for url in [
                    f"https://{domain}/favicon.ico",
                    f"http://{domain}/favicon.ico"
                ]:
                    try:
                        r = requests.get(url, timeout=3)
                        if r.status_code == 200 and r.content:
                            try:
                                pil = Image.open(BytesIO(r.content))
                                if self._store_png_and_photo(pil, key):
                                    return
                            except:
                                # save .ico file for fallback
                                ico = self._ico_path(key)
                                ico.write_bytes(r.content)
                                try:
                                    pil = Image.open(ico)
                                    if self._store_png_and_photo(pil, key):
                                        return
                                except:
                                    pass
                    except:
                        pass

                # 3) HTML PARSE fallback
                try:
                    r = requests.get(f"https://{domain}", timeout=3)
                    if r.status_code == 200 and r.text:
                        from html.parser import HTMLParser

                        class IconFinder(HTMLParser):
                            def __init__(self):
                                super().__init__()
                                self.links = []

                            def handle_starttag(self, tag, attrs):
                                if tag.lower() == "link":
                                    d = dict(attrs)
                                    rel = d.get("rel", "").lower()
                                    if "icon" in rel:
                                        href = d.get("href")
                                        if href:
                                            self.links.append(href)

                        parser = IconFinder()
                        parser.feed(r.text)

                        for href in parser.links:
                            if href.startswith("//"):
                                href = "https:" + href
                            elif href.startswith("/"):
                                href = f"https://{domain}{href}"
                            elif not href.startswith("http"):
                                href = f"https://{domain}/{href}"

                            try:
                                r2 = requests.get(href, timeout=3)
                                if r2.status_code == 200 and r2.content:
                                    try:
                                        pil = Image.open(BytesIO(r2.content))
                                        if self._store_png_and_photo(pil, key):
                                            return
                                    except:
                                        pass
                            except:
                                pass
                except:
                    pass

            finally:
                self._fetching.discard(domain)
                if callback:
                    try:
                        self._root.after(0, lambda: callback(key))
                    except:
                        try:
                            callback(key)
                        except:
                            pass

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------
    # PUBLIC: internal photo lookup
    # ------------------------
    def get_cached_photo(self, key: str):
        return self._photo_cache.get(key)

    # ------------------------
    # INTERNAL: cleanup
    # ------------------------
    def ensure_root_destroyed(self):
        if not self._tk_root_provided:
            try:
                self._root.destroy()
            except:
                pass
