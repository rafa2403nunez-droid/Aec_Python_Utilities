# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

"""
Export Clash Dashboard Data & Launch Viewer
Extracts clash test results, exports clashes.json,
launches a Dash server and opens the BIM Coordination Dashboard.
"""

import clr
import sys
import json
import re
import threading
import webbrowser
import zipfile
from pathlib import Path
from collections import defaultdict

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import Application

clr.AddReference("Autodesk.Navisworks.Clash")
from Autodesk.Navisworks.Api.Clash import DocumentClash
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")

from System.Windows.Forms import (
    Form, Button, GroupBox, DataGridView, AnchorStyles,
    FormBorderStyle, FormStartPosition,
    DataGridViewAutoSizeColumnMode, DataGridViewSelectionMode,
    DataGridViewColumnHeadersHeightSizeMode,
)
from System.Drawing import Point, Size, Color, Icon

bundlePath = (Path.home() / "AppData" / "Roaming" / "Autodesk" / "ApplicationPlugins" / "RAEN.Navisworks.PyNET.bundle" / "Contents" / "2024")
NavisworksIconPath = (Path.home() / "AppData" / "Roaming" / "Autodesk" / "ApplicationPlugins" / "Raen.Navisworks.Pynet.bundle" / "manage.ico")
sys.path.append(str(bundlePath))
clr.AddReference("Raen.Core.Pynet.Resources")
from Raen.Core.Pynet.Resources import CastUtils #type:ignore

from Autodesk.Navisworks.Api import Application
doc = Application.ActiveDocument

user_home = Path.home()
repo_base = user_home / "source" / "repos" / "GithubRNM" / "PyNetLibrary" / "03_Viewer"
VIEWER_DIR = repo_base / "dist"
DASHBOARD_DIR = repo_base / "dashboard"
PORT = 8095

sys.path.append(str(Path.home() / "AppData" / "Roaming" / "Pynet" / "Library" / "01_Scripts" / "00_utils"))
from pynet_clash import get_clash_tests


class ClashExtractor:
    """Extracts clash data from the active document."""

    @staticmethod
    def GetElementId(item):
        if item is None:
            return None
        try:
            for cat in item.PropertyCategories:
                if "Element" in cat.DisplayName:
                    for prop in cat.Properties:
                        if prop.DisplayName in ("Value", "Id") or "id" in prop.DisplayName.lower():
                            return str(prop.Value.ToDisplayString())
            for cat in item.PropertyCategories:
                for prop in cat.Properties:
                    if prop.DisplayName.lower() in ("id", "guid", "ifcguid"):
                        return str(prop.Value.ToDisplayString())
        except:
            pass
        return str(item.InstanceGuid)

    @staticmethod
    def GetProperty(item, catName, propName):
        if item is None:
            return None
        try:
            for cat in item.PropertyCategories:
                if cat.DisplayName == catName:
                    for prop in cat.Properties:
                        if prop.DisplayName == propName:
                            return str(prop.Value.ToDisplayString())
        except:
            pass
        return None

    @staticmethod
    def ExtractDiscipline(testName):
        m = re.search(r'Instalaciones_([^_]+)', testName)
        return m.group(1) if m else "Estructura"

    @staticmethod
    def IterResults(test):
        """Yield ClashResult objects under a test, entering groups if present."""
        for child in test.Children:
            if child.IsGroup:
                for r in child.Children:
                    yield r
            else:
                yield child

    @staticmethod
    def Run(document):
        models = []
        for model in document.Models:
            fname = model.FileName.replace("\\", "/")
            models.append({
                "name": model.RootItem.DisplayName.replace(".ifc", ""),
                "fileName": fname.split("/")[-1],
                "fullPath": fname
            })

        clashDocument = CastUtils.CastTo[DocumentClash](document.Clash)
        testsData = clashDocument.TestsData

        testsData.TestsRunAllTests()

        allClashes = []
        testsSummary = []

        for test in get_clash_tests(clashDocument):
            results = list(ClashExtractor.IterResults(test))
            count = len(results)
            status_counts = {}
            for r in results:
                s = str(r.Status)
                status_counts[s] = status_counts.get(s, 0) + 1
            dominant_status = max(status_counts, key=status_counts.get) if status_counts else "New"
            testsSummary.append({"name": test.DisplayName, "clashes": count, "status": dominant_status})
            if count == 0:
                continue
            testName = test.DisplayName
            discipline = ClashExtractor.ExtractDiscipline(testName)
            for result in results:
                itemA = result.Item1
                itemB = result.Item2
                point = result.Center
                try:
                    guid = str(result.DisplayName)
                except:
                    guid = ""
                allClashes.append({
                    "Test": testName, "Discipline": discipline,
                    "Clash": result.DisplayName, "Status": str(result.Status),
                    "Distance (m)": round(result.Distance, 4) if result.Distance else 0,
                    "X": round(point.X, 3) if point else None,
                    "Y": round(point.Y, 3) if point else None,
                    "Z": round(point.Z, 3) if point else None,
                    "Element A": itemA.DisplayName if itemA else "",
                    "ID A": ClashExtractor.GetElementId(itemA),
                    "Source A": ClashExtractor.GetProperty(itemA, "Item", "Source File") or "",
                    "Type A": ClashExtractor.GetProperty(itemA, "Item", "Type") or "",
                    "Element B": itemB.DisplayName if itemB else "",
                    "ID B": ClashExtractor.GetElementId(itemB),
                    "Source B": ClashExtractor.GetProperty(itemB, "Item", "Source File") or "",
                    "Type B": ClashExtractor.GetProperty(itemB, "Item", "Type") or "",
                    "GUID": guid
                })

        return models, testsSummary, allClashes

class ClassificationAnalyzer:
    """Validates PYNET_Classification coverage at TYPE node level per model."""

    PARAM_NAME = "PYNET_Classification"
    PARAM_CAT  = "lcldrevit_tab_type"

    @staticmethod
    def Run(document) -> list:
        results = []
        for model in document.Models:
            model_name = Path(model.FileName).stem
            classified_types   = {}
            unclassified_types = []

            for item in model.RootItem.Descendants:
                if item.ClassDisplayName != "Tipo":
                    continue
                code = None
                for cat in item.PropertyCategories:
                    if cat.Name != ClassificationAnalyzer.PARAM_CAT:
                        continue
                    for prop in cat.Properties:
                        if prop.DisplayName != ClassificationAnalyzer.PARAM_NAME:
                            continue
                        try:
                            val = prop.Value.ToDisplayString()
                            if val:
                                code = val
                        except:
                            pass
                if code:
                    classified_types[hash(item)] = code
                else:
                    if len(unclassified_types) < 20:
                        unclassified_types.append(item.DisplayName or "(sin nombre)")

            code_counts        = defaultdict(int)
            covered_geo_hashes = set()
            for item in model.RootItem.Descendants:
                if item.ClassDisplayName != "Tipo":
                    continue
                h = hash(item)
                if h not in classified_types:
                    continue
                code = classified_types[h]
                for desc in item.Descendants:
                    if desc.HasGeometry:
                        dh = hash(desc)
                        if dh not in covered_geo_hashes:
                            covered_geo_hashes.add(dh)
                            code_counts[code] += 1

            total_geo      = sum(1 for it in model.RootItem.Descendants if it.HasGeometry)
            classified_geo = sum(code_counts.values())
            coverage_pct   = round(classified_geo / total_geo * 100, 1) if total_geo > 0 else 0.0

            results.append({
                "model":                   model_name,
                "total_geometry_elements": total_geo,
                "classified_geo":          classified_geo,
                "unclassified_geo":        total_geo - classified_geo,
                "coverage_pct":            coverage_pct,
                "unclassified_type_count": len(unclassified_types),
                "unclassified_type_names": unclassified_types,
                "elements_per_code":       dict(sorted(code_counts.items())),
            })
        return results


class DataExporter:
    """Exports clash data to JSON."""

    @staticmethod
    def Export(models, testsSummary, allClashes, classification=None, project=None):
        ifc_dir = Path(models[0]["fullPath"]).parent if models else Path.home() / "Desktop"
        export_data = {
            "project": project or "Project",
            "models": models, "tests": testsSummary, "clashes": allClashes,
            "classification": classification or [],
            "summary": {
                "totalClashes": len(allClashes),
                "activeTests": sum(1 for t in testsSummary if t["clashes"] > 0),
                "totalModels": len(models)
            }
        }
        output_path = ifc_dir / "clashes.json"
        output_path.write_text(json.dumps(export_data, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path, ifc_dir

class DashboardServer:
    """Launches a Dash/Flask server to serve the viewer and dashboard."""
    _dir = [None]

    @staticmethod
    def Run(ifc_dir):
        DashboardServer._dir[0] = ifc_dir
        from dash import Dash, html

        app = Dash("pynet_dashboard", url_base_pathname="/_app/")
        fk = sys.modules.get("flask")
        app.layout = html.Div("OK")

        @app.server.route("/")
        def idx():
            return fk.send_file(str(DASHBOARD_DIR / "index.html"), mimetype="text/html")

        @app.server.route("/dashboard.css")
        def css():
            return fk.send_file(str(DASHBOARD_DIR / "dashboard.css"), mimetype="text/css")

        @app.server.route("/dashboard.js")
        def js():
            return fk.send_file(str(DASHBOARD_DIR / "dashboard.js"), mimetype="application/javascript")

        @app.server.route("/viewer/")
        def vi():
            return fk.send_file(str(VIEWER_DIR / "index.html"), mimetype="text/html")

        @app.server.route("/viewer/<path:fp>")
        def vf(fp):
            f = VIEWER_DIR / fp
            if f.exists() and f.is_file():
                mt = {"css": "text/css", "js": "application/javascript", "mjs": "application/javascript",
                      "wasm": "application/wasm", "json": "application/json", "html": "text/html"}
                return fk.send_file(str(f), mimetype=mt.get(f.suffix.lstrip("."), "application/octet-stream"))
            return "Not found", 404

        @app.server.route("/api/set-data-dir", methods=["POST"])
        def set_data_dir():
            body = fk.request.get_json(silent=True) or {}
            new_dir = Path(body.get("dir", ""))
            if new_dir.is_dir():
                DashboardServer._dir[0] = new_dir
                return fk.jsonify({"status": "ok"})
            return fk.jsonify({"status": "error", "message": "Directory not found"}), 400

        @app.server.route("/api/upload-pnt", methods=["POST"])
        def upload_pnt():
            import io
            f = fk.request.files.get("file")
            if not f:
                return fk.jsonify({"status": "error", "message": "No file"}), 400
            pnt_name = Path(f.filename).stem
            extract_dir = Path.home() / ".pynet_viewer" / pnt_name
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(f.read()), 'r') as zf:
                zf.extractall(str(extract_dir))
            DashboardServer._dir[0] = extract_dir
            clashes_path = extract_dir / "clashes.json"
            if clashes_path.exists():
                return fk.send_file(str(clashes_path), mimetype="application/json")
            return fk.jsonify({"status": "error", "message": "No clashes.json in package"}), 400

        @app.server.route("/models/<fn>")
        def mi(fn):
            f = DashboardServer._dir[0] / fn
            if not f.exists():
                f = DashboardServer._dir[0] / "models" / fn
            if f.exists():
                return fk.send_file(str(f), mimetype="application/octet-stream")
            return "Not found", 404

        @app.server.route("/data/<fn>")
        def di(fn):
            f = DashboardServer._dir[0] / fn
            if f.exists():
                return fk.send_file(str(f), mimetype="application/json")
            return "Not found", 404

        app.run(port=PORT, debug=False, use_reloader=False)

class WebViewAPI:
    """Python API exposed to the pywebview dashboard as window.pywebview.api"""

    def open_pnt_dialog(self):
        import webview
        wins = webview.windows
        if not wins:
            return None
        result = wins[0].create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=('PNT Package (*.pnt)',)
        )
        return result[0] if result else None

    def load_pnt(self, path):
        if not path:
            return None
        pnt_path = Path(path)
        if not pnt_path.exists():
            return None
        extract_dir = Path.home() / ".pynet_viewer" / pnt_path.stem
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(str(pnt_path), 'r') as zf:
            zf.extractall(str(extract_dir))
        DashboardServer._dir[0] = extract_dir
        clashes_path = extract_dir / "clashes.json"
        if clashes_path.exists():
            return json.loads(clashes_path.read_text(encoding='utf-8'))
        return None


class DashboardForm(Form):
    """Main form for the Clash Dashboard workflow."""
    _webview_active = [False]

    def __init__(self):
        Form.__init__(self)
        self.ExportResult = None
        self.IFCDir = None
        self.ServerRunning = False
        self.ConfigureForm()     

    def ConfigureForm(self):
        self.Text = "BIM Coordination Dashboard"
        if Path(str(NavisworksIconPath)).exists():
            self.Icon = Icon(str(NavisworksIconPath))
        self.Width = 990
        self.Height = 700
        self.MinimumSize = Size(480, 340)
        self.FormBorderStyle = FormBorderStyle.FixedDialog
        self.MaximizeBox = False
        self.StartPosition = FormStartPosition.CenterScreen
        self.TopMost = True       
        self.GenerateUI()
        self.GenerateFormGroups()
        self.GenerateFormSelectionList()
        self.ExportData()

    def GenerateUI(self):
        self.LaunchBtn = Button()
        self.LaunchBtn.Text = "Launch"
        self.LaunchBtn.Width = 120
        self.LaunchBtn.Location = Point(710, 590)
        self.LaunchBtn.Enabled = False
        self.LaunchBtn.Click += self.OnLaunch
        self.Controls.Add(self.LaunchBtn)

        closeBtn = Button()
        closeBtn.Text = "Cancel"
        closeBtn.Width = 120
        closeBtn.Location = Point(840, 590)
        closeBtn.Click += self.OnClose
        self.Controls.Add(closeBtn)

    def GenerateFormGroups(self):
        groupBoxViews = GroupBox()
        groupBoxViews.Text = "Clash Detection Results generated"
        groupBoxViews.Size = Size(940, 550)
        groupBoxViews.Location = Point(20, 20)
        groupBoxViews.Anchor = AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Top
        groupBoxViews.Parent = self

    def GenerateFormSelectionList(self):
        self.dataGrid = DataGridView()
        self.dataGrid.Name = "ModelsList"
        self.dataGrid.BackgroundColor = Color.White
        self.dataGrid.Location = Point(40, 60)
        self.dataGrid.Size = Size(900, 480)
        self.dataGrid.Anchor = AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Top
        
        self.dataGrid.ColumnCount = 3
        self.dataGrid.Columns[0].Name = "ClashTest Name"
        self.dataGrid.Columns[1].Name = "Clashes Count"
        self.dataGrid.Columns[2].Name = "Clashtest Status"
        
        for i in range(3):
            self.dataGrid.Columns[i].AutoSizeMode = DataGridViewAutoSizeColumnMode.Fill

        self.dataGrid.AllowUserToAddRows = False
        self.dataGrid.AllowUserToDeleteRows = False
        self.dataGrid.RowHeadersVisible = False
        self.dataGrid.ReadOnly = True
        self.dataGrid.AllowUserToResizeRows = False
        self.dataGrid.SelectionMode = DataGridViewSelectionMode.FullRowSelect
        self.dataGrid.ColumnHeadersHeight = 40
        self.dataGrid.ColumnHeadersHeightSizeMode = DataGridViewColumnHeadersHeightSizeMode.DisableResizing
        
        self.Controls.Add(self.dataGrid)
        self.dataGrid.BringToFront()

    def ExportData(self):
        print("Running clash tests")
        self.Refresh()

        try:
            models, testsSummary, allClashes = ClashExtractor.Run(doc)
            print("Exporting data and updating UI")

            self.dataGrid.Rows.Clear()
            for test in testsSummary:
                self.dataGrid.Rows.Add(test["name"], test["clashes"], test["status"])

            classification = ClassificationAnalyzer.Run(doc)
            project_name = Path(doc.FileName).stem if doc.FileName else "Project"
            output_path, ifc_dir = DataExporter.Export(models, testsSummary, allClashes, classification, project_name)
            self.IFCDir = ifc_dir

            total = len(allClashes)
            active = sum(1 for t in testsSummary if t["clashes"] > 0)
            print(f"Exported: {total} clashes from {active} tests.")

            self.LaunchBtn.Enabled = True
        except Exception as e:
            print(f"Error: {e}")

    @staticmethod
    def CheckPort(port):
        """Returns (owner_pid, is_own_process) for a port, or (None, False) if free."""
        import psutil
        my_pid = psutil.Process().pid
        for conn in psutil.net_connections(kind='tcp'):
            if conn.laddr.port == port and conn.status == 'LISTEN':
                return conn.pid, conn.pid == my_pid
        return None, False

    @staticmethod
    def KillPort(port):
        """Kill process on port ONLY if it's external (never kill Navisworks)."""
        import psutil
        my_pid = psutil.Process().pid
        for conn in psutil.net_connections(kind='tcp'):
            if conn.laddr.port == port and conn.status == 'LISTEN':
                if conn.pid == my_pid:
                    return False
                try:
                    proc = psutil.Process(conn.pid)
                    proc.terminate()
                    proc.wait(timeout=3)
                    return True
                except:
                    pass
        return False

    def OnLaunch(self, sender, args):
        import time

        owner_pid, is_self = DashboardForm.CheckPort(PORT)

        # Server already running inside Navisworks — just open webview
        if owner_pid is not None and is_self:
            DashboardForm._OpenWebView()
            self.ServerRunning = True
            return

        self.LaunchBtn.Enabled = False
        self.Refresh()

        # Port occupied by external process — kill it safely
        if owner_pid is not None:
            print(f"Port {PORT} busy (external PID {owner_pid}) — stopping...")
            DashboardForm.KillPort(PORT)
            time.sleep(1)

        print("Starting dashboard server...")
        self.Refresh()

        dash_thread = threading.Thread(
            target=DashboardServer.Run,
            args=(self.IFCDir,),
            daemon=False
        )
        dash_thread.start()
        self.ServerRunning = True

        time.sleep(2)
        DashboardForm._OpenWebView()

        self.LaunchBtn.Enabled = True

    @staticmethod
    def _OpenWebView():
        if DashboardForm._webview_active[0]:
            return
        def _run():
            import webview
            DashboardForm._webview_active[0] = True
            try:
                webview.create_window(
                    "BIM Coordination Dashboard",
                    f"http://localhost:{PORT}",
                    width=1440,
                    height=900,
                    resizable=True,
                    min_size=(800, 600),
                    js_api=WebViewAPI(),
                )
                webview.start()
            finally:
                DashboardForm._webview_active[0] = False
        threading.Thread(target=_run, daemon=True).start()

    def OnClose(self, sender, args):
        self.Close()

DashboardForm().ShowDialog()