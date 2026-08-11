# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

"""
PyNET Viewer — LEGACY standalone HTTP server (dev/troubleshooting only).
Serves a directory of loose IFC files + Viewer + Dashboard from the Python stdlib.
For the current product flow (.pnt package + desktop window + .exe) use pnt_server.py.

Run from a terminal (NOT from Navisworks):

    python 03_Viewer/server/legacy_server.py --ifc-dir "C:/ruta/a/ifcs" --port 8080
"""

import argparse
import json
import mimetypes
import sys
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs

# MIME types correctos para archivos BIM/web
mimetypes.add_type("application/wasm", ".wasm")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/octet-stream", ".ifc")


class PyNetViewerHandler(SimpleHTTPRequestHandler):
    """Handler que sirve viewer, dashboard, IFCs y datos de clashes."""

    def __init__(self, *args, ifc_dir: Path, viewer_dir: Path, dashboard_dir: Path, data_dir: Path, **kwargs):
        self.ifc_dir = ifc_dir
        self.viewer_dir = viewer_dir
        self.dashboard_dir = dashboard_dir
        self.data_dir = data_dir
        super().__init__(*args, **kwargs)

    def end_headers(self):
        # CORS para desarrollo local
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        # /models/<filename> → archivos IFC
        if path.startswith("/models/"):
            filename = path[len("/models/"):]
            self._serve_file(self.ifc_dir / filename)
            return

        # /data/<filename> → datos JSON (clashes, etc.)
        if path.startswith("/data/"):
            filename = path[len("/data/"):]
            self._serve_file(self.data_dir / filename)
            return

        # /viewer/ → app viewer buildeada
        if path.startswith("/viewer/") or path == "/viewer":
            rel = path[len("/viewer/"):] or "index.html"
            self._serve_file(self.viewer_dir / rel)
            return

        # / → dashboard
        if path == "/" or path == "/index.html":
            self._serve_file(self.dashboard_dir / "index.html")
            return

        # /dashboard/* → assets del dashboard
        if path.startswith("/dashboard/"):
            rel = path[len("/dashboard/"):]
            self._serve_file(self.dashboard_dir / rel)
            return

        # Fallback: intentar servir desde dashboard
        candidate = self.dashboard_dir / path.lstrip("/")
        if candidate.exists() and candidate.is_file():
            self._serve_file(candidate)
            return

        self.send_error(404, f"Not found: {path}")

    def _serve_file(self, filepath: Path):
        filepath = filepath.resolve()
        if not filepath.exists() or not filepath.is_file():
            self.send_error(404, f"Not found: {filepath.name}")
            return

        content_type, _ = mimetypes.guess_type(str(filepath))
        if content_type is None:
            content_type = "application/octet-stream"

        try:
            data = filepath.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(500, str(e))

    def log_message(self, format, *args):
        print(f"[PyNET Server] {args[0]}")


def main():
    parser = argparse.ArgumentParser(description="PyNET Viewer HTTP Server")
    parser.add_argument("--ifc-dir", required=True, help="Directorio con archivos IFC")
    parser.add_argument("--port", type=int, default=8080, help="Puerto (default: 8080)")
    parser.add_argument("--viewer-dir", default=None, help="Directorio del viewer buildeado (default: ../dist)")
    parser.add_argument("--dashboard-dir", default=None, help="Directorio del dashboard (default: ../dashboard)")

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    ifc_dir = Path(args.ifc_dir).resolve()
    viewer_dir = Path(args.viewer_dir).resolve() if args.viewer_dir else (script_dir.parent / "dist").resolve()
    dashboard_dir = Path(args.dashboard_dir).resolve() if args.dashboard_dir else (script_dir.parent / "dashboard").resolve()
    data_dir = ifc_dir  # clashes.json se guarda junto a los IFCs

    print(f"[PyNET Server] IFC dir:       {ifc_dir}")
    print(f"[PyNET Server] Viewer dir:    {viewer_dir}")
    print(f"[PyNET Server] Dashboard dir: {dashboard_dir}")
    print(f"[PyNET Server] Data dir:      {data_dir}")
    print(f"[PyNET Server] Starting on http://localhost:{args.port}")
    print(f"[PyNET Server] Dashboard:     http://localhost:{args.port}/")
    print(f"[PyNET Server] Viewer only:   http://localhost:{args.port}/viewer/")
    print()

    handler = partial(
        PyNetViewerHandler,
        ifc_dir=ifc_dir,
        viewer_dir=viewer_dir,
        dashboard_dir=dashboard_dir,
        data_dir=data_dir,
    )

    server = HTTPServer(("0.0.0.0", args.port), handler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[PyNET Server] Stopped")
        server.server_close()


if __name__ == "__main__":
    main()
