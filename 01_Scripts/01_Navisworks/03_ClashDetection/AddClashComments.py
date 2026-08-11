# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

#region references
import clr
import sys
import re
from pathlib import Path
from datetime import datetime

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import Comment, CommentCollection, CommentStatus

clr.AddReference("Autodesk.Navisworks.Clash")
from Autodesk.Navisworks.Api.Clash import DocumentClash
clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import MessageBox, MessageBoxButtons, MessageBoxIcon, DialogResult

bundlePath = (Path.home() / "AppData" / "Roaming" / "Autodesk" / "ApplicationPlugins" / "RAEN.Navisworks.PyNET.bundle" / "Contents" / "2024")
sys.path.append(str(bundlePath))

clr.AddReference("Raen.Core.Pynet.Resources")
from Raen.Core.Pynet.Resources import CastUtils  # type: ignore

from Autodesk.Navisworks.Api import Application, Assignee
doc = Application.ActiveDocument

#endregion


sys.path.append(str(Path.home() / "AppData" / "Roaming" / "Pynet" / "Library" / "01_Scripts" / "00_utils"))
from pynet_clash import get_clash_tests


class ElementInfoExtractor:
    DIAM_PROPS = ("Diámetro", "Diametro", "Diameter", "Tamaño")

    @staticmethod
    def GetPynetAndDiameter(model_item):
        pynet, diameter = "", ""
        nodes = [model_item] + list(model_item.Ancestors)
        for node in nodes:
            for cat in node.PropertyCategories:
                if cat.Name == "LcRevitData_Element":
                    for prop in cat.Properties:
                        try:
                            v = prop.Value.ToDisplayString()
                        except:
                            v = ""
                        if not diameter and prop.DisplayName in ElementInfoExtractor.DIAM_PROPS and v and v != "0":
                            diameter = v
                if cat.Name in ("LcRevitData_TypeCustom", "LcRevitData_Type", "lcldrevit_tab_type"):
                    for prop in cat.Properties:
                        if prop.DisplayName == "PYNET_Classification" and not pynet:
                            try:
                                pynet = prop.Value.ToDisplayString()
                            except:
                                pass
        return pynet, diameter


class ApprovalRules:
    TUB_MAX_DIAMETER_MM = 175
    CON_PROXIMITY_THRESHOLD_MM = 1000
    STRUCTURAL_CODES = {"PIL"}

    @staticmethod
    def ParseDiameterMm(diam_str):
        if not diam_str:
            return None
        m = re.search(r'(\d+(?:\.\d+)?)', diam_str)
        return float(m.group(1)) if m else None

    @staticmethod
    def GetCenterMm(result):
        c = result.Center
        return (c.X * 304.8, c.Y * 304.8, c.Z * 304.8)

    @staticmethod
    def DistSq3D(c1, c2):
        return (c1[0]-c2[0])**2 + (c1[1]-c2[1])**2 + (c1[2]-c2[2])**2

    @staticmethod
    def GetReason(result, con_clash_centers):
        pa, da = ElementInfoExtractor.GetPynetAndDiameter(result.Item1)
        pb, db = ElementInfoExtractor.GetPynetAndDiameter(result.Item2)
        codes = {pa, pb}

        if codes == {"PIL", "FAC"}:
            return "PIL vs FAC: perimeter column in facade"
        structural_hit = codes & ApprovalRules.STRUCTURAL_CODES
        if structural_hit:
            return f"MEP vs structural ({', '.join(structural_hit)}): requires structural sign-off"
        if "CON" in codes:
            return "CON: duct opening requires structural coordination"
        if codes == {"PIL", "PAR"}:
            return "PIL vs PAR: column vs partition requires coordination"
        if "TUB" in codes:
            diam_str = da if pa == "TUB" else db
            diam_mm = ApprovalRules.ParseDiameterMm(diam_str)
            if diam_mm is None or diam_mm >= ApprovalRules.TUB_MAX_DIAMETER_MM:
                return f"TUB diameter {diam_str or 'unknown'} >= {ApprovalRules.TUB_MAX_DIAMETER_MM}mm"
            center = ApprovalRules.GetCenterMm(result)
            threshold_sq = ApprovalRules.CON_PROXIMITY_THRESHOLD_MM ** 2
            if any(ApprovalRules.DistSq3D(center, c) < threshold_sq for c in con_clash_centers):
                return f"TUB {diam_mm}mm but CON clash within {ApprovalRules.CON_PROXIMITY_THRESHOLD_MM}mm"
            return f"TUB {diam_mm}mm, no CON nearby"
        return f"{pa} vs {pb}: requires manual review"


class AddClashCommentsManager:

    @staticmethod
    def IterAllResults(test):
        for child in test.Children:
            if child.IsGroup:
                for r in child.Children:
                    yield r
            else:
                yield child

    @staticmethod
    def Run(document):
        clashDoc = CastUtils.CastTo[DocumentClash](document.Clash)
        testsData = clashDoc.TestsData
        run_date = datetime.now().strftime("%Y-%m-%d")

        print("Scanning clash results...")

        # Collect CON centers for proximity check
        con_centers = []
        for test in get_clash_tests(clashDoc):
            for r in AddClashCommentsManager.IterAllResults(test):
                try:
                    pa, _ = ElementInfoExtractor.GetPynetAndDiameter(r.Item1)
                    pb, _ = ElementInfoExtractor.GetPynetAndDiameter(r.Item2)
                    if "CON" in (pa, pb):
                        con_centers.append(ApprovalRules.GetCenterMm(r))
                except:
                    pass

        # Collect results that already have a status (Approved or Reviewed)
        targets = []
        for test in get_clash_tests(clashDoc):
            for r in AddClashCommentsManager.IterAllResults(test):
                if str(r.Status) not in ("Approved", "Reviewed"):
                    continue
                try:
                    reason = ApprovalRules.GetReason(r, con_centers)
                    targets.append({
                        "test": test.DisplayName,
                        "result": r,
                        "status": str(r.Status),
                        "reason": reason,
                    })
                except Exception as e:
                    print(f"  Warning: could not determine reason for {r.DisplayName} — {e}")

        if not targets:
            print("No Approved or Reviewed clash results found.")
            MessageBox.Show(
                "No Approved or Reviewed clash results found to comment.",
                "Add Clash Comments",
                MessageBoxButtons.OK,
                MessageBoxIcon.Information
            )
            return

        print(f"Found {len(targets)} result(s) to comment.")

        # Preview dialog
        lines = [f"Ready to add analysis comments to {len(targets)} clash result(s):", ""]
        for d in targets:
            lines.append(f"  [{d['status']}] {d['test']} — {d['reason']}")
        lines.append("\nProceed?")

        confirm = MessageBox.Show(
            "\n".join(lines),
            "Add Clash Comments",
            MessageBoxButtons.YesNo,
            MessageBoxIcon.Question
        )

        if confirm != DialogResult.Yes:
            print("Cancelled by user.")
            return

        # Apply comments
        applied = 0
        for d in targets:
            try:
                body = f"[Auto-review {run_date}] {d['reason']}"
                comments = CommentCollection()
                comments.Add(Comment(body, CommentStatus.New))
                testsData.TestsEditResultComments(d["result"], comments)
                print(f"  {d['test']} / {d['result'].DisplayName} ({d['status']}) → {d['reason']}")
                applied += 1
            except Exception as e:
                print(f"  ERROR {d['result'].DisplayName}: {e}")

        print(f"\nDone. Comments added to {applied}/{len(targets)} results.")
        MessageBox.Show(
            f"Comments added to {applied} clash result(s).",
            "Add Clash Comments",
            MessageBoxButtons.OK,
            MessageBoxIcon.Information
        )


# Entry point
AddClashCommentsManager.Run(doc)

#endregion
