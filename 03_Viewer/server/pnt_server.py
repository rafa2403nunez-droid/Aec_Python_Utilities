# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

"""
pnt_server.py — BIM Coordination Dashboard (standalone)

Usage:
    python pnt_server.py                   # opens file picker in PyWebView window
    python pnt_server.py project.pnt       # opens a specific package directly
    python pnt_server.py --port 8096       # custom port

Package as .exe (from 03_Viewer/server/):
    pyinstaller pnt_server.py --onefile --noconsole ^
        --add-data "../dashboard;dashboard" ^
        --add-data "../dist;dist"
"""

import atexit
import io
import json
import os
import queue
import sys
import time
import threading
import zipfile
from pathlib import Path

PORT = 8095

# Discovery endpoint — the MCP bridge reads this to find the viewer's port and the data dir
# (the extracted .pnt with clashes.json/properties.json). Bridge reads DATA from those JSONs;
# it only uses the port to drive the viewer via /api/control.
ENDPOINT_PATH = Path.home() / ".pynet_viewer" / "endpoint.json"


def _write_endpoint(port: int) -> None:
    """Publish the running viewer's endpoint so the MCP bridge can attach to it."""
    try:
        ENDPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
        info = {
            "kind": "pynet-viewer",
            "port": port,
            "pid": os.getpid(),
            "dataDir": str(_state["dir"]) if _state.get("dir") else None,
            "package": _state.get("package"),
        }
        ENDPOINT_PATH.write_text(json.dumps(info), "utf-8")
    except Exception:
        pass  # discovery is best-effort; never block serving


def _clear_endpoint() -> None:
    try:
        if ENDPOINT_PATH.is_file():
            ENDPOINT_PATH.unlink()
    except Exception:
        pass

# Resolve base paths — works both from source and PyInstaller frozen exe
if getattr(sys, "frozen", False):
    _BASE = Path(sys._MEIPASS)
else:
    _BASE = Path(__file__).resolve().parent.parent  # 03_Viewer/

_DASHBOARD_DIR = _BASE / "dashboard"
_VIEWER_DIR    = _BASE / "dist"

_MIME = {
    "css":  "text/css",
    "js":   "application/javascript",
    "mjs":  "application/javascript",
    "wasm": "application/wasm",
    "json": "application/json",
    "html": "text/html",
    "ifc":  "application/octet-stream",
    "png":  "image/png",
    "svg":  "image/svg+xml",
    "ico":  "image/x-icon",
}

# ── Shared server state ────────────────────────────────────────────────────────
_state: dict = {"dir": None, "port": None, "package": None}

# ── Viewer control channel (MCP ⇄ viewer) ───────────────────────────────────────
# The bridge POSTs commands to /api/control; they are fanned out to every connected
# viewer via Server-Sent Events on /api/events. The viewer POSTs its current state
# (selection, loaded models) to /api/state, which /api/control can read back for
# get_state. No extra dependency required — SSE is plain Flask streaming.
_VIEWER_ACTIONS = {"load_model", "select", "select_ids", "isolate", "isolate_models", "fit", "clear", "get_state"}
_control = {
    "subscribers": [],            # list[queue.Queue] — one per connected viewer (SSE)
    "lock": threading.Lock(),
    "last_state": {},             # last state reported by the viewer
}


def _broadcast(command: dict) -> int:
    """Push a command to every connected viewer. Returns the number of receivers."""
    with _control["lock"]:
        subs = list(_control["subscribers"])
        for q in subs:
            q.put(command)
    return len(subs)


def _extract_pnt(pnt_path: Path) -> dict | None:
    """Extract a .pnt ZIP to ~/.pynet_viewer/<stem>/ and return clashes.json as dict."""
    extract_dir = Path.home() / ".pynet_viewer" / pnt_path.stem
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(str(pnt_path), "r") as zf:
        zf.extractall(str(extract_dir))
    _state["dir"] = extract_dir
    _state["package"] = pnt_path.name
    _write_endpoint(_state.get("port") or PORT)
    clashes = extract_dir / "clashes.json"
    if clashes.is_file():
        return json.loads(clashes.read_text("utf-8"))
    return None


def _extract_pnt_bytes(pnt_bytes: bytes, name: str) -> dict | None:
    """Same as _extract_pnt but from in-memory bytes (browser upload fallback)."""
    stem = Path(name).stem
    extract_dir = Path.home() / ".pynet_viewer" / stem
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(pnt_bytes), "r") as zf:
        zf.extractall(str(extract_dir))
    _state["dir"] = extract_dir
    _state["package"] = name
    _write_endpoint(_state.get("port") or PORT)
    clashes = extract_dir / "clashes.json"
    if clashes.is_file():
        return json.loads(clashes.read_text("utf-8"))
    return None


# ── PyWebView JS API ───────────────────────────────────────────────────────────
class PNTServerAPI:
    """Methods callable from the dashboard JS as window.pywebview.api.*"""

    def open_pnt_dialog(self):
        import webview
        wins = webview.windows
        if not wins:
            return None
        result = wins[0].create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=("PNT Package (*.pnt)",),
        )
        return result[0] if result else None

    def load_pnt(self, path: str):
        if not path:
            return None
        p = Path(path)
        if not p.is_file():
            return None
        return _extract_pnt(p)


# ── Flask / Dash server ────────────────────────────────────────────────────────
def _start_flask(port: int) -> None:
    _state["port"] = port
    _write_endpoint(port)
    atexit.register(_clear_endpoint)

    from dash import Dash, html
    import flask as fk

    app = Dash("pnt_dashboard", url_base_pathname="/_app/")
    app.layout = html.Div("OK")
    server = app.server

    def _send(path, mime=None):
        p = Path(path)
        m = mime or _MIME.get(p.suffix.lstrip("."), "application/octet-stream")
        return fk.send_file(str(p), mimetype=m)

    @server.route("/")
    def root():
        return _send(_DASHBOARD_DIR / "index.html")

    @server.route("/dashboard.css")
    def css():
        return _send(_DASHBOARD_DIR / "dashboard.css")

    @server.route("/dashboard.js")
    def js():
        return _send(_DASHBOARD_DIR / "dashboard.js")

    @server.route("/viewer/")
    def viewer_root():
        return _send(_VIEWER_DIR / "index.html")

    @server.route("/viewer/<path:fp>")
    def viewer_file(fp):
        f = _VIEWER_DIR / fp
        return _send(f) if f.is_file() else ("Not found", 404)

    @server.route("/models/<fn>")
    def model_file(fn):
        if _state["dir"] is None:
            return "Not ready", 503
        # Check root first (flat layout), then models/ subdir (PNT layout)
        f = _state["dir"] / fn
        if not f.exists():
            f = _state["dir"] / "models" / fn
        return _send(f) if f.is_file() else ("Not found", 404)

    @server.route("/data/<fn>")
    def data_file(fn):
        if _state["dir"] is None:
            return "Not ready", 503
        f = _state["dir"] / fn
        return _send(f) if f.is_file() else ("Not found", 404)

    @server.route("/api/upload-pnt", methods=["POST"])
    def upload_pnt():
        f = fk.request.files.get("file")
        if not f:
            return fk.jsonify({"status": "error", "message": "No file"}), 400
        data = _extract_pnt_bytes(f.read(), f.filename)
        if data is None:
            return fk.jsonify({"status": "error", "message": "No clashes.json found"}), 400
        return fk.jsonify(data)

    @server.route("/api/load-pnt-path", methods=["POST"])
    def load_pnt_path():
        """Load a .pnt from a local path (used by the VS Code host's native file dialog)."""
        body = fk.request.get_json(silent=True) or {}
        p = Path(body.get("path", ""))
        if not p.is_file():
            return fk.jsonify({"status": "error", "message": "File not found"}), 400
        data = _extract_pnt(p)
        models = (data or {}).get("models", [])
        return fk.jsonify({"status": "ok", "models": models})

    # ── Viewer control API ──────────────────────────────────────────────────────
    @server.route("/api/control", methods=["POST"])
    def control():
        """Enqueue a command for connected viewers. Used by the MCP bridge (phase 2)."""
        cmd = fk.request.get_json(silent=True) or {}
        action = cmd.get("action")
        if action not in _VIEWER_ACTIONS:
            return fk.jsonify({"status": "error", "message": f"Unknown action: {action}"}), 400
        if action == "get_state":
            return fk.jsonify({"status": "ok", "state": _control["last_state"]})
        receivers = _broadcast(cmd)
        return fk.jsonify({"status": "ok", "receivers": receivers})

    @server.route("/api/state", methods=["POST"])
    def report_state():
        """Viewer reports its current state (selection, loaded models)."""
        _control["last_state"] = fk.request.get_json(silent=True) or {}
        return fk.jsonify({"status": "ok"})

    @server.route("/api/events")
    def events():
        """SSE stream — the viewer subscribes here to receive control commands."""
        q: queue.Queue = queue.Queue()
        with _control["lock"]:
            _control["subscribers"].append(q)

        def _stream():
            try:
                yield "retry: 2000\n\n"  # client reconnect hint
                while True:
                    try:
                        cmd = q.get(timeout=20)
                        yield f"data: {json.dumps(cmd)}\n\n"
                    except queue.Empty:
                        yield ": keep-alive\n\n"  # comment frame keeps the connection open
            finally:
                with _control["lock"]:
                    if q in _control["subscribers"]:
                        _control["subscribers"].remove(q)

        return fk.Response(_stream(), mimetype="text/event-stream",
                           headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    app.run(port=port, debug=False, use_reloader=False, threaded=True)


# ── Entry point ────────────────────────────────────────────────────────────────
def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="BIM Coordination Dashboard")
    ap.add_argument("pnt_file", nargs="?", help="Path to a .pnt file to open directly")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--headless", action="store_true",
                    help="Run Flask only, without the PyWebView window (used when hosted in a "
                         "VS Code Webview).")
    args = ap.parse_args()

    # Pre-load if a .pnt was provided as argument (done before serving so it's ready).
    def _preload():
        if args.pnt_file:
            pnt_path = Path(args.pnt_file)
            if pnt_path.is_file():
                print(f"Loading {pnt_path.name}...")
                _extract_pnt(pnt_path)
            else:
                print(f"Warning: file not found — {pnt_path}", file=sys.stderr)

    # Headless: Flask owns the main thread, no desktop window. The VS Code Webview is the UI.
    if args.headless:
        _preload()
        print(f"PyNET viewer server (headless) listening on http://127.0.0.1:{args.port}",
              flush=True)
        _start_flask(args.port)
        return

    # Windowed: Flask in background thread — PyWebView must own the main thread.
    threading.Thread(target=_start_flask, args=(args.port,), daemon=True).start()
    time.sleep(1.5)
    _preload()

    import webview
    webview.create_window(
        "BIM Coordination Dashboard",
        f"http://localhost:{args.port}",
        width=1440,
        height=900,
        resizable=True,
        min_size=(800, 600),
        js_api=PNTServerAPI(),
    )
    webview.start()


if __name__ == "__main__":
    main()
