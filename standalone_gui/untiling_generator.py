#!/usr/bin/env python3
"""Untiling / Aperiodic Generator — basic desktop client.

Classic small-app UI: pick a mask, formats, depth (default 0), hit Generate,
files land in a folder. Talks to the hosted API. No fancy chrome.
"""

from __future__ import annotations

import json
import os
import threading
import time
import traceback
import urllib.error
import urllib.request
import uuid
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME = "Aperiodic Generator"
API_DEFAULT = "https://api.aperiodicgenerator.com"
FALLBACK_API = "https://aperiodic-monotile-api.onrender.com"
CONFIG_NAME = "untiling_generator_settings.json"


def _config_path() -> Path:
    base = Path(os.environ.get("APPDATA") or Path.home() / ".config")
    folder = base / "Untiling"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / CONFIG_NAME


def load_settings() -> dict:
    path = _config_path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_settings(data: dict) -> None:
    try:
        _config_path().write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


class ApiClient:
    def __init__(self, base: str, api_key: str) -> None:
        primary = (base or API_DEFAULT).rstrip("/")
        self.bases = [primary]
        if FALLBACK_API.rstrip("/") not in self.bases:
            self.bases.append(FALLBACK_API.rstrip("/"))
        self.api_key = api_key.strip()
        self.active_base = primary

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        last_err: Exception | None = None
        for base in self.bases:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-API-Key": self.api_key,
                "User-Agent": "UntilingDesktop/1.0",
            }
            if method == "POST":
                headers["Idempotency-Key"] = str(uuid.uuid4())
            req = urllib.request.Request(
                f"{base}{path}",
                data=payload,
                method=method,
                headers=headers,
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    raw = resp.read().decode("utf-8")
                    self.active_base = base
                    return json.loads(raw) if raw else {}
            except Exception as err:  # noqa: BLE001
                last_err = err
                continue
        assert last_err is not None
        raise last_err

    def create_patch(self, body: dict) -> dict:
        return self._request("POST", "/v1/patch", body)

    def job(self, job_id: str) -> dict:
        return self._request("GET", f"/v1/jobs/{job_id}")

    def urls(self, job_id: str) -> dict:
        return self._request("GET", f"/v1/jobs/{job_id}/urls")

    def absolute(self, url: str) -> str:
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return f"{self.active_base}{url}"


def download_file(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "UntilingDesktop/1.0"})
    with urllib.request.urlopen(req, timeout=300) as resp, dest.open("wb") as out:
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            out.write(chunk)


def build_mask(kind: str, values: dict) -> dict:
    if kind == "circle":
        return {"type": "circle", "radius": float(values["radius"])}
    if kind == "square":
        return {"type": "square", "half_side": float(values["half_side"])}
    if kind == "triangle":
        return {"type": "triangle", "side_length": float(values["side"])}
    if kind == "regular_hexagon":
        return {"type": "regular_hexagon", "circumradius": float(values["radius"])}
    if kind == "rounded_rect":
        return {
            "type": "rounded_rect",
            "width": float(values["width"]),
            "height": float(values["height"]),
            "corner_radius": float(values["corner"]),
        }
    return {
        "type": "rectangle",
        "width": float(values["width"]),
        "height": float(values["height"]),
    }


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("540x680")
        self.minsize(500, 580)

        saved = load_settings()
        self.api_url = tk.StringVar(value=saved.get("api_url", API_DEFAULT))
        self.api_key = tk.StringVar(value=saved.get("api_key", ""))
        self.mask = tk.StringVar(value=saved.get("mask", "rectangle"))
        self.width = tk.StringVar(value=str(saved.get("width", 40)))
        self.height = tk.StringVar(value=str(saved.get("height", 24)))
        self.radius = tk.StringVar(value=str(saved.get("radius", 20)))
        self.half_side = tk.StringVar(value=str(saved.get("half_side", 20)))
        self.side = tk.StringVar(value=str(saved.get("side", 40)))
        self.corner = tk.StringVar(value=str(saved.get("corner", 3)))
        self.scale = tk.StringVar(value=str(saved.get("scale", 1)))
        self.depth = tk.StringVar(value=str(saved.get("depth", 0)))
        self.out_dir = tk.StringVar(
            value=saved.get("out_dir", str(Path.home() / "Documents" / "Untiling"))
        )
        self.status = tk.StringVar(value="Ready.")
        self._busy = False

        formats_saved = set(saved.get("formats", ["png"]))
        self.fmt_vars = {
            name: tk.BooleanVar(value=name in formats_saved)
            for name in ("png", "jpg", "svg", "json", "csv", "stl", "glb")
        }

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _labeled_entry(
        self, parent: ttk.Frame, row: int, label: str, var: tk.StringVar, show: str = ""
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(parent, textvariable=var, width=44, show=show).grid(
            row=row, column=1, sticky="ew", pady=2
        )
        parent.columnconfigure(1, weight=1)

    def _build(self) -> None:
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text=APP_NAME, font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(
            root,
            text="Free JPG/PNG · Paid SVG/3D · Depth defaults to 0 (flat)",
        ).pack(anchor="w", pady=(0, 8))

        auth = ttk.LabelFrame(root, text="API", padding=8)
        auth.pack(fill="x", pady=4)
        self._labeled_entry(auth, 0, "Base URL", self.api_url)
        self._labeled_entry(auth, 1, "API key", self.api_key, show="*")

        shape = ttk.LabelFrame(root, text="Mask", padding=8)
        shape.pack(fill="x", pady=4)
        ttk.Label(shape, text="Type").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            shape,
            textvariable=self.mask,
            values=(
                "rectangle",
                "circle",
                "square",
                "triangle",
                "regular_hexagon",
                "rounded_rect",
            ),
            state="readonly",
            width=22,
        ).grid(row=0, column=1, sticky="w", pady=2)
        self._labeled_entry(shape, 1, "Width", self.width)
        self._labeled_entry(shape, 2, "Height", self.height)
        self._labeled_entry(shape, 3, "Radius", self.radius)
        self._labeled_entry(shape, 4, "Half side", self.half_side)
        self._labeled_entry(shape, 5, "Side", self.side)
        self._labeled_entry(shape, 6, "Corner", self.corner)

        opts = ttk.LabelFrame(root, text="Options", padding=8)
        opts.pack(fill="x", pady=4)
        self._labeled_entry(opts, 0, "Tile scale", self.scale)
        self._labeled_entry(opts, 1, "Depth (mm)", self.depth)
        ttk.Label(opts, text="0 = flat (default)").grid(row=1, column=2, sticky="w", padx=6)

        fmts = ttk.LabelFrame(root, text="Formats", padding=8)
        fmts.pack(fill="x", pady=4)
        for i, name in enumerate(self.fmt_vars):
            ttk.Checkbutton(fmts, text=name.upper(), variable=self.fmt_vars[name]).grid(
                row=i // 4, column=i % 4, sticky="w", padx=6, pady=2
            )

        out = ttk.LabelFrame(root, text="Output folder", padding=8)
        out.pack(fill="x", pady=4)
        ttk.Entry(out, textvariable=self.out_dir).grid(row=0, column=0, sticky="ew")
        ttk.Button(out, text="Browse…", command=self._browse).grid(row=0, column=1, padx=6)
        out.columnconfigure(0, weight=1)

        actions = ttk.Frame(root)
        actions.pack(fill="x", pady=8)
        self.gen_btn = ttk.Button(actions, text="Generate", command=self._generate)
        self.gen_btn.pack(side="left")
        ttk.Button(actions, text="Open folder", command=self._open_folder).pack(
            side="left", padx=8
        )

        ttk.Label(root, textvariable=self.status, wraplength=500).pack(anchor="w", fill="x")
        self.log = tk.Text(root, height=10, wrap="word", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, pady=(6, 0))

    def _browse(self) -> None:
        path = filedialog.askdirectory(initialdir=self.out_dir.get() or None)
        if path:
            self.out_dir.set(path)

    def _open_folder(self) -> None:
        path = Path(self.out_dir.get())
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)  # type: ignore[attr-defined]

    def _log(self, msg: str) -> None:
        self.log.insert("end", msg + "\n")
        self.log.see("end")

    def _set_status(self, msg: str) -> None:
        self.status.set(msg)
        self._log(msg)

    def _snapshot(self) -> dict:
        formats = [name for name, var in self.fmt_vars.items() if var.get()]
        return {
            "api_url": self.api_url.get().strip(),
            "api_key": self.api_key.get().strip(),
            "mask": self.mask.get(),
            "width": self.width.get(),
            "height": self.height.get(),
            "radius": self.radius.get(),
            "half_side": self.half_side.get(),
            "side": self.side.get(),
            "corner": self.corner.get(),
            "scale": self.scale.get(),
            "depth": self.depth.get(),
            "out_dir": self.out_dir.get(),
            "formats": formats,
        }

    def _on_close(self) -> None:
        save_settings(self._snapshot())
        self.destroy()

    def _generate(self) -> None:
        if self._busy:
            return
        snap = self._snapshot()
        if not snap["api_key"]:
            messagebox.showwarning(APP_NAME, "Paste an API key first (Get started on the site).")
            return
        if not snap["formats"]:
            messagebox.showwarning(APP_NAME, "Pick at least one format.")
            return
        save_settings(snap)
        self._busy = True
        self.gen_btn.state(["disabled"])
        threading.Thread(target=self._run_job, args=(snap,), daemon=True).start()

    def _run_job(self, snap: dict) -> None:
        try:
            self.after(0, lambda: self._set_status("Submitting patch…"))
            client = ApiClient(snap["api_url"], snap["api_key"])
            mask = build_mask(
                snap["mask"],
                {
                    "width": snap["width"],
                    "height": snap["height"],
                    "radius": snap["radius"],
                    "half_side": snap["half_side"],
                    "side": snap["side"],
                    "corner": snap["corner"],
                },
            )
            body = {
                "mask": mask,
                "formats": snap["formats"],
                "scale": float(snap["scale"]),
                "stl_extrusion_mm": float(snap["depth"]),
                "png_width_px": 1200,
                "png_height_px": 1200,
                "jpg_width_px": 1200,
                "jpg_height_px": 1200,
            }
            created = client.create_patch(body)
            job_id = created.get("job_id")
            if not job_id:
                raise RuntimeError(f"No job_id in response: {created}")
            self.after(0, lambda: self._set_status(f"Job {job_id} queued…"))

            deadline = time.time() + 600
            status = created.get("status", "queued")
            while time.time() < deadline:
                self.after(0, lambda s=status: self.status.set(f"Status: {s}"))
                if status in {"completed", "failed", "cancelled", "canceled"}:
                    break
                time.sleep(1.5)
                info = client.job(job_id)
                status = info.get("status", status)
            if status != "completed":
                raise RuntimeError(f"Job did not complete (status={status})")

            url_payload = client.urls(job_id)
            urls = url_payload.get("urls") or {}
            out_root = Path(snap["out_dir"]) / str(job_id)
            out_root.mkdir(parents=True, exist_ok=True)
            (out_root / "request.json").write_text(json.dumps(body, indent=2), encoding="utf-8")

            saved = 0
            for name, url in urls.items():
                dest = out_root / Path(str(name)).name
                abs_url = client.absolute(str(url))
                self.after(0, lambda d=str(dest.name): self._set_status(f"Downloading {d}…"))
                download_file(abs_url, dest)
                saved += 1

            msg = f"Done. Saved {saved} file(s) to {out_root}"
            self.after(0, lambda: self._set_status(msg))
            self.after(0, lambda: messagebox.showinfo(APP_NAME, msg))
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", errors="replace")
            self.after(0, lambda: self._fail(f"HTTP {err.code}: {detail[:400]}"))
        except Exception as err:  # noqa: BLE001
            self.after(0, lambda: self._fail(f"{err}\n{traceback.format_exc()[-800:]}"))
        finally:
            self.after(0, self._idle)

    def _fail(self, msg: str) -> None:
        self._set_status("Error.")
        self._log(msg)
        messagebox.showerror(APP_NAME, msg[:800])

    def _idle(self) -> None:
        self._busy = False
        self.gen_btn.state(["!disabled"])


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
