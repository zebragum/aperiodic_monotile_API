#!/usr/bin/env python3
"""Aperiodic Generator — simple desktop client.

Child-simple: pick a shape, a size, a format, Generate.
Paid formats open checkout when there's no API key.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
import traceback
import urllib.error
import urllib.request
import uuid
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME = "Aperiodic Generator"
API_DEFAULT = "https://api.aperiodicgenerator.com"
FALLBACK_API = "https://aperiodic-monotile-api.onrender.com"
SITE_URL = "https://aperiodicgenerator.com"
CONFIG_NAME = "untiling_generator_settings.json"

# Friendly shape → API mask
SHAPES = {
    "Rectangle": "rectangle",
    "Circle": "circle",
    "Square": "square",
    "Triangle": "triangle",
    "Hexagon": "regular_hexagon",
}

# Friendly format → API format list
FORMAT_CHOICES = {
    "Picture (PNG) — free": ["png"],
    "Picture (JPG) — free": ["jpg"],
    "Drawing (SVG) — paid": ["svg"],
    "3D model (GLB) — paid": ["glb"],
}

PAID_FORMATS = {"svg", "glb", "stl", "json", "csv", "stl_zip", "obj_zip", "instance_json"}


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
    def __init__(self, api_key: str = "") -> None:
        self.bases = [API_DEFAULT, FALLBACK_API]
        self.api_key = (api_key or "").strip()
        self.active_base = API_DEFAULT

    def _request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        *,
        need_key: bool = True,
    ) -> dict:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        last_err: Exception | None = None
        for base in self.bases:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "UntilingDesktop/1.1",
            }
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            elif need_key:
                pass
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
            except urllib.error.HTTPError as err:
                last_err = err
                if err.code in {401, 403} and need_key:
                    raise
                # try fallback host for other errors
                continue
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

    def checkout(self, plan: str = "solo_monthly", email: str = "") -> dict:
        body: dict = {"plan": plan}
        if email.strip():
            body["email"] = email.strip()
        return self._request("POST", "/v1/billing/checkout", body, need_key=False)

    def claim_key(self, session_id: str) -> dict:
        return self._request(
            "POST",
            "/v1/billing/claim-key",
            {"session_id": session_id.strip()},
            need_key=False,
        )

    def absolute(self, url: str) -> str:
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return f"{self.active_base}{url}"


def download_file(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "UntilingDesktop/1.1"})
    with urllib.request.urlopen(req, timeout=300) as resp, dest.open("wb") as out:
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            out.write(chunk)


def build_mask(shape_label: str, size: float, width: float, height: float) -> dict:
    kind = SHAPES[shape_label]
    if kind == "circle":
        return {"type": "circle", "radius": size}
    if kind == "square":
        return {"type": "square", "half_side": size}
    if kind == "triangle":
        return {"type": "triangle", "side_length": size}
    if kind == "regular_hexagon":
        return {"type": "regular_hexagon", "circumradius": size}
    return {"type": "rectangle", "width": width, "height": height}


def extract_session_id(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if text.startswith("cs_"):
        return text.split()[0]
    match = re.search(r"(cs_[A-Za-z0-9_]+)", text)
    return match.group(1) if match else ""


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("480x620")
        self.minsize(440, 560)

        saved = load_settings()
        self.api_key = tk.StringVar(value=saved.get("api_key", ""))
        self.shape = tk.StringVar(value=saved.get("shape_label", "Rectangle"))
        self.size = tk.StringVar(value=str(saved.get("size", 20)))
        self.width = tk.StringVar(value=str(saved.get("width", 40)))
        self.height = tk.StringVar(value=str(saved.get("height", 24)))
        self.depth = tk.StringVar(value=str(saved.get("depth", 0)))
        self.format_label = tk.StringVar(
            value=saved.get("format_label", "Picture (PNG) — free")
        )
        self.out_dir = tk.StringVar(
            value=saved.get("out_dir", str(Path.home() / "Documents" / "Untiling"))
        )
        self.status = tk.StringVar(value="Pick a shape, pick a format, press Make it.")
        self._busy = False
        self._last_session_id = saved.get("last_session_id", "")

        self._build()
        self._refresh_fields()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build(self) -> None:
        root = ttk.Frame(self, padding=14)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text=APP_NAME, font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(
            root,
            text="Make a shape that never repeats.\nPictures are free. Drawings and 3D need a key.",
            justify="left",
        ).pack(anchor="w", pady=(2, 12))

        step1 = ttk.LabelFrame(root, text="1. Shape", padding=10)
        step1.pack(fill="x", pady=4)
        shape_box = ttk.Combobox(
            step1,
            textvariable=self.shape,
            values=list(SHAPES.keys()),
            state="readonly",
            width=28,
        )
        shape_box.pack(anchor="w")
        shape_box.bind("<<ComboboxSelected>>", lambda _e: self._refresh_fields())

        self.size_frame = ttk.Frame(step1)
        self.size_label = ttk.Label(self.size_frame, text="Size")
        self.size_label.grid(row=0, column=0, sticky="w")
        self.size_entry = ttk.Entry(self.size_frame, textvariable=self.size, width=12)
        self.size_entry.grid(row=0, column=1, sticky="w", padx=(8, 0))

        self.rect_frame = ttk.Frame(step1)
        ttk.Label(self.rect_frame, text="Width").grid(row=0, column=0, sticky="w")
        ttk.Entry(self.rect_frame, textvariable=self.width, width=10).grid(
            row=0, column=1, sticky="w", padx=(8, 16)
        )
        ttk.Label(self.rect_frame, text="Height").grid(row=0, column=2, sticky="w")
        ttk.Entry(self.rect_frame, textvariable=self.height, width=10).grid(
            row=0, column=3, sticky="w", padx=(8, 0)
        )

        step2 = ttk.LabelFrame(root, text="2. What do you want?", padding=10)
        step2.pack(fill="x", pady=4)
        fmt = ttk.Combobox(
            step2,
            textvariable=self.format_label,
            values=list(FORMAT_CHOICES.keys()),
            state="readonly",
            width=36,
        )
        fmt.pack(anchor="w")
        fmt.bind("<<ComboboxSelected>>", lambda _e: self._refresh_fields())

        self.depth_frame = ttk.Frame(step2)
        self.depth_frame.pack(fill="x", pady=(8, 0))
        self.depth_label = ttk.Label(self.depth_frame, text="Thickness")
        self.depth_label.grid(row=0, column=0, sticky="w")
        self.depth_entry = ttk.Entry(self.depth_frame, textvariable=self.depth, width=12)
        self.depth_entry.grid(row=0, column=1, sticky="w", padx=(8, 0))

        step3 = ttk.LabelFrame(root, text="3. Save to", padding=10)
        step3.pack(fill="x", pady=4)
        ttk.Entry(step3, textvariable=self.out_dir).grid(row=0, column=0, sticky="ew")
        ttk.Button(step3, text="Browse…", command=self._browse).grid(row=0, column=1, padx=(8, 0))
        step3.columnconfigure(0, weight=1)

        key_box = ttk.LabelFrame(root, text="API key (needed for SVG / 3D)", padding=10)
        key_box.pack(fill="x", pady=4)
        ttk.Entry(key_box, textvariable=self.api_key, show="*").grid(row=0, column=0, sticky="ew")
        ttk.Button(key_box, text="Get a key", command=self._get_key_flow).grid(
            row=0, column=1, padx=(8, 0)
        )
        key_box.columnconfigure(0, weight=1)
        ttk.Button(key_box, text="I already paid — paste checkout link", command=self._claim_flow).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0)
        )

        actions = ttk.Frame(root)
        actions.pack(fill="x", pady=12)
        self.gen_btn = ttk.Button(actions, text="Make it", command=self._generate)
        self.gen_btn.pack(side="left")
        ttk.Button(actions, text="Open folder", command=self._open_folder).pack(
            side="left", padx=8
        )

        ttk.Label(root, textvariable=self.status, wraplength=430, justify="left").pack(
            anchor="w", fill="x"
        )

    def _formats(self) -> list[str]:
        return list(FORMAT_CHOICES.get(self.format_label.get(), ["png"]))

    def _needs_depth(self) -> bool:
        return any(f in {"glb", "stl", "stl_zip", "obj_zip"} for f in self._formats())

    def _is_paid_format(self) -> bool:
        return any(f in PAID_FORMATS for f in self._formats())

    def _refresh_fields(self) -> None:
        is_rect = self.shape.get() == "Rectangle"
        if is_rect:
            self.size_frame.pack_forget()
            self.rect_frame.pack(fill="x", pady=(8, 0))
        else:
            self.rect_frame.pack_forget()
            self.size_frame.pack(fill="x", pady=(8, 0))
            label = {
                "Circle": "Radius",
                "Square": "Size",
                "Triangle": "Side length",
                "Hexagon": "Radius",
            }.get(self.shape.get(), "Size")
            self.size_label.configure(text=label)

        if self._needs_depth():
            self.depth_entry.state(["!disabled"])
            self.depth_label.configure(foreground="")
        else:
            self.depth.set("0")
            self.depth_entry.state(["disabled"])
            try:
                self.depth_label.configure(foreground="#888888")
            except tk.TclError:
                pass

    def _browse(self) -> None:
        path = filedialog.askdirectory(initialdir=self.out_dir.get() or None)
        if path:
            self.out_dir.set(path)

    def _open_folder(self) -> None:
        path = Path(self.out_dir.get())
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)  # type: ignore[attr-defined]

    def _snapshot(self) -> dict:
        return {
            "api_key": self.api_key.get().strip(),
            "shape_label": self.shape.get(),
            "size": self.size.get(),
            "width": self.width.get(),
            "height": self.height.get(),
            "depth": self.depth.get() if self._needs_depth() else "0",
            "format_label": self.format_label.get(),
            "out_dir": self.out_dir.get(),
            "last_session_id": self._last_session_id,
        }

    def _on_close(self) -> None:
        save_settings(self._snapshot())
        self.destroy()

    def _set_status(self, msg: str) -> None:
        self.status.set(msg)

    def _get_key_flow(self) -> None:
        email = self._ask_email()
        self._set_status("Opening secure checkout…")
        try:
            client = ApiClient()
            payload = client.checkout(plan="solo_monthly", email=email or "")
            url = payload.get("checkout_url")
            sid = payload.get("session_id") or ""
            if sid:
                self._last_session_id = sid
            if not url:
                raise RuntimeError("No checkout URL returned.")
            webbrowser.open(url)
            messagebox.showinfo(
                APP_NAME,
                "Pay in your browser.\n\n"
                "When you’re done, come back here and click\n"
                "“I already paid — paste checkout link”\n"
                "or paste your API key in the box above.",
            )
            self._set_status("Finish checkout in the browser, then paste your key.")
        except Exception as err:  # noqa: BLE001
            # Fallback: open pricing page
            webbrowser.open(f"{SITE_URL}/docs.html#access")
            messagebox.showinfo(
                APP_NAME,
                "Opened the website so you can get a key.\n\n"
                f"(Checkout helper note: {err})\n\n"
                "Paste the key here when you have it.",
            )
            self._set_status("Get a key on the website, then paste it here.")

    def _ask_email(self) -> str:
        dialog = tk.Toplevel(self)
        dialog.title("Email for receipt")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        ttk.Label(
            dialog,
            text="Optional email for your Stripe receipt:",
            padding=10,
        ).pack(anchor="w")
        email_var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=email_var, width=40)
        entry.pack(padx=10, fill="x")
        entry.focus_set()
        result: dict[str, str] = {"email": ""}

        def ok() -> None:
            result["email"] = email_var.get().strip()
            dialog.destroy()

        def skip() -> None:
            dialog.destroy()

        btns = ttk.Frame(dialog, padding=10)
        btns.pack(fill="x")
        ttk.Button(btns, text="Continue", command=ok).pack(side="right")
        ttk.Button(btns, text="Skip", command=skip).pack(side="right", padx=6)
        dialog.bind("<Return>", lambda _e: ok())
        self.wait_window(dialog)
        return result["email"]

    def _claim_flow(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Paste checkout link or session")
        dialog.transient(self)
        dialog.grab_set()
        ttk.Label(
            dialog,
            text="Paste the checkout success link, or the session id (starts with cs_):",
            padding=10,
            wraplength=360,
        ).pack(anchor="w")
        text = tk.Text(dialog, height=4, width=48)
        text.pack(padx=10, fill="x")
        if self._last_session_id:
            text.insert("1.0", self._last_session_id)
        status = ttk.Label(dialog, text="", padding=10, wraplength=360)
        status.pack(anchor="w")

        def do_claim() -> None:
            raw = text.get("1.0", "end").strip()
            sid = extract_session_id(raw)
            if not sid:
                status.configure(text="Could not find a session id. Paste the whole success URL.")
                return
            status.configure(text="Claiming key…")
            dialog.update_idletasks()
            try:
                client = ApiClient()
                payload = client.claim_key(sid)
                key = payload.get("api_key") or ""
                if key:
                    self.api_key.set(key)
                    self._last_session_id = sid
                    save_settings(self._snapshot())
                    status.configure(text="Key saved. You can close this window.")
                    messagebox.showinfo(APP_NAME, "API key saved. Press Make it.")
                    dialog.destroy()
                    return
                prefix = payload.get("key_prefix") or ""
                status.configure(
                    text=f"Already claimed. {('Prefix: ' + prefix) if prefix else 'Paste the key from your email or docs page.'}"
                )
            except Exception as err:  # noqa: BLE001
                status.configure(text=f"Could not claim yet: {err}")

        ttk.Button(dialog, text="Claim key", command=do_claim).pack(pady=10)

    def _ensure_access(self) -> bool:
        if not self._is_paid_format():
            return True
        if self.api_key.get().strip():
            return True
        answer = messagebox.askyesno(
            APP_NAME,
            "SVG and 3D need an API key.\n\n"
            "Pictures (PNG/JPG) are free without buying.\n\n"
            "Get a key now?",
        )
        if answer:
            self._get_key_flow()
        return bool(self.api_key.get().strip())

    def _generate(self) -> None:
        if self._busy:
            return
        self._refresh_fields()
        if not self._ensure_access():
            return
        try:
            size = float(self.size.get() or "20")
            width = float(self.width.get() or "40")
            height = float(self.height.get() or "24")
            depth = float(self.depth.get() or "0") if self._needs_depth() else 0.0
            if size <= 0 or width <= 0 or height <= 0:
                raise ValueError("Sizes must be positive numbers.")
        except ValueError as err:
            messagebox.showwarning(APP_NAME, str(err))
            return

        formats = self._formats()
        snap = self._snapshot()
        save_settings(snap)
        self._busy = True
        self.gen_btn.state(["disabled"])
        threading.Thread(
            target=self._run_job,
            args=(snap, size, width, height, depth, formats),
            daemon=True,
        ).start()

    def _run_job(
        self,
        snap: dict,
        size: float,
        width: float,
        height: float,
        depth: float,
        formats: list[str],
    ) -> None:
        try:
            self.after(0, lambda: self._set_status("Working…"))
            client = ApiClient(snap.get("api_key", ""))
            mask = build_mask(snap["shape_label"], size, width, height)
            body = {
                "mask": mask,
                "formats": formats,
                "scale": 1.0,
                "stl_extrusion_mm": depth,
                "png_width_px": 1200,
                "png_height_px": 1200,
                "jpg_width_px": 1200,
                "jpg_height_px": 1200,
            }
            created = client.create_patch(body)
            job_id = created.get("job_id")
            if not job_id:
                raise RuntimeError(f"No job_id in response: {created}")

            deadline = time.time() + 600
            status = created.get("status", "queued")
            while time.time() < deadline:
                self.after(0, lambda s=status: self._set_status(f"Status: {s}"))
                if status in {"completed", "failed", "cancelled", "canceled"}:
                    break
                time.sleep(1.5)
                info = client.job(job_id)
                status = info.get("status", status)
            if status != "completed":
                raise RuntimeError(f"Job did not complete (status={status})")

            urls = (client.urls(job_id).get("urls") or {})
            out_root = Path(snap["out_dir"]) / str(job_id)
            out_root.mkdir(parents=True, exist_ok=True)
            (out_root / "request.json").write_text(json.dumps(body, indent=2), encoding="utf-8")
            saved = 0
            for name, url in urls.items():
                dest = out_root / Path(str(name)).name
                download_file(client.absolute(str(url)), dest)
                saved += 1
            msg = f"Done! Saved {saved} file(s) in:\n{out_root}"
            self.after(0, lambda: self._set_status("Done."))
            self.after(0, lambda: messagebox.showinfo(APP_NAME, msg))
            self.after(0, self._open_folder)
        except urllib.error.HTTPError as err:
            try:
                text = err.read().decode("utf-8", errors="replace")
            except Exception:
                text = getattr(err, "msg", "") or str(err)
            code = getattr(err, "code", 0)
            if code in {401, 403} or "api key" in text.lower() or "X-API-Key" in text:
                self.after(
                    0,
                    lambda: self._fail_need_key(
                        "The server needs an API key for that.\n\nGet a key, then try again."
                    ),
                )
            elif code == 422 and any(f in PAID_FORMATS for f in formats):
                self.after(
                    0,
                    lambda: self._fail_need_key(
                        "That format needs a paid key.\n\nGet a key, then try again."
                    ),
                )
            else:
                self.after(0, lambda: self._fail(f"HTTP {code}: {text[:500]}"))
        except Exception as err:  # noqa: BLE001
            self.after(0, lambda: self._fail(f"{err}\n{traceback.format_exc()[-500:]}"))
        finally:
            self.after(0, self._idle)

    def _fail_need_key(self, msg: str) -> None:
        self._set_status("Need an API key.")
        if messagebox.askyesno(APP_NAME, msg + "\n\nGet a key now?"):
            self._get_key_flow()

    def _fail(self, msg: str) -> None:
        self._set_status("Something went wrong.")
        messagebox.showerror(APP_NAME, msg[:900])

    def _idle(self) -> None:
        self._busy = False
        self.gen_btn.state(["!disabled"])


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
