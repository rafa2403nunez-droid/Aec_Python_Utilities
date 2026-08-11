# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

#region references
import clr
import sys
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import Comment, CommentCollection, CommentStatus

clr.AddReference("Autodesk.Navisworks.Clash")
from Autodesk.Navisworks.Api.Clash import DocumentClash, ClashResultGroup, ClashResultStatus
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
                        dn = prop.DisplayName
                        try:
                            v = prop.Value.ToDisplayString()
                        except:
                            v = ""
                        if not diameter and dn in ElementInfoExtractor.DIAM_PROPS and v and v != "0":
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
    # Structural element codes — any clash involving these requires engineering sign-off
    STRUCTURAL_CODES = {"PIL"}  # extend with beam codes as needed

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
    def Decide(result, test_name, con_clash_centers):
        pynet_a, diam_a = ElementInfoExtractor.GetPynetAndDiameter(result.Item1)
        pynet_b, diam_b = ElementInfoExtractor.GetPynetAndDiameter(result.Item2)
        codes = {pynet_a, pynet_b}

        # RULE 4: PIL vs FAC — perimeter column in facade, always Approved
        if codes == {"PIL", "FAC"}:
            return "Approved", "PIL vs FAC: perimeter column in facade"

        # RULE 1: any structural element involved — always Reviewed, no exceptions
        structural_hit = codes & ApprovalRules.STRUCTURAL_CODES
        if structural_hit:
            return "Reviewed", f"MEP vs structural ({', '.join(structural_hit)}): requires structural sign-off"

        # RULE 3: CON (duct) clash — always Reviewed regardless of size
        if "CON" in codes:
            return "Reviewed", "CON: duct opening requires structural coordination"

        # RULE 5: PIL vs PAR — column wider than partition, always Reviewed
        if codes == {"PIL", "PAR"}:
            return "Reviewed", "PIL vs PAR: column vs partition requires coordination"

        # RULE 2: TUB vs slab — Approve if diameter < threshold and no CON nearby
        if "TUB" in codes:
            diam_str = diam_a if pynet_a == "TUB" else diam_b
            diam_mm = ApprovalRules.ParseDiameterMm(diam_str)

            if diam_mm is None or diam_mm >= ApprovalRules.TUB_MAX_DIAMETER_MM:
                return "Reviewed", f"TUB diameter {diam_str or 'unknown'} >= {ApprovalRules.TUB_MAX_DIAMETER_MM}mm"

            threshold_sq = ApprovalRules.CON_PROXIMITY_THRESHOLD_MM ** 2
            center = ApprovalRules.GetCenterMm(result)
            near_con = any(
                ApprovalRules.DistSq3D(center, con_c) < threshold_sq
                for con_c in con_clash_centers
            )
            if near_con:
                return "Reviewed", f"TUB {diam_mm}mm but CON clash within {ApprovalRules.CON_PROXIMITY_THRESHOLD_MM}mm"

            return "Approved", f"TUB {diam_mm}mm, no CON nearby"

        # Tie-break: when in doubt, always Reviewed
        return "Reviewed", f"{pynet_a} vs {pynet_b}: requires manual review"


class ClashGrouper:
    """Groups clash results within each test that share a common element (2+ clashes on the same element)."""

    @staticmethod
    def GroupBySharedElement(testsData, test):
        # Only consider direct non-group children (avoid re-grouping)
        flat = [(hash(r), r) for r in test.Children if not r.IsGroup]
        if len(flat) < 2:
            return 0

        # Map each element hash to the results it appears in
        elem_map = defaultdict(list)
        for rh, r in flat:
            try:
                elem_map[hash(r.Item1)].append((rh, r, r.Item1.DisplayName))
                elem_map[hash(r.Item2)].append((rh, r, r.Item2.DisplayName))
            except:
                pass

        processed = set()
        groups_created = 0

        for elem_hash, entries in elem_map.items():
            # Skip if fewer than 2 unique results share this element
            entries = [e for e in entries if e[0] not in processed]
            if len(entries) < 2:
                continue

            elem_name = entries[0][2]
            group_name = f"{elem_name} – {len(entries)} clashes"

            group = ClashResultGroup()
            group.DisplayName = group_name
            testsData.TestsAddCopy(test, group)

            # Retrieve the live group reference from the test
            live_group = None
            for child in test.Children:
                if child.IsGroup and child.DisplayName == group_name:
                    live_group = child
                    break

            if live_group is None:
                continue

            # Move each result into the group (re-find index after each move since list shifts)
            for move_idx, (rh, r, _) in enumerate(entries):
                current_idx = None
                for j, child in enumerate(test.Children):
                    if not child.IsGroup and hash(child) == rh:
                        current_idx = j
                        break
                if current_idx is not None:
                    testsData.TestsMove(test, current_idx, live_group, move_idx)
                    processed.add(rh)

            print(f"  Grouped: '{group_name}'")
            groups_created += 1

        return groups_created


class AutoReviewManager:

    @staticmethod
    def IterAllResults(test):
        """Yield all ClashResult items under a test, including those inside groups."""
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

        # First pass: collect CON clash centers for proximity check (filter by PYNET code)
        con_clash_centers = []
        for test in get_clash_tests(clashDoc):
            for r in AutoReviewManager.IterAllResults(test):
                try:
                    pa, _ = ElementInfoExtractor.GetPynetAndDiameter(r.Item1)
                    pb, _ = ElementInfoExtractor.GetPynetAndDiameter(r.Item2)
                    if "CON" in (pa, pb):
                        con_clash_centers.append(ApprovalRules.GetCenterMm(r))
                except:
                    pass
        print(f"CON clash centers collected: {len(con_clash_centers)}")

        # Second pass: decide all New clashes
        decisions = []
        clash_index = 1
        for test in get_clash_tests(clashDoc):
            for r in AutoReviewManager.IterAllResults(test):
                if str(r.Status) != "New":
                    clash_index += 1
                    continue
                status, reason = ApprovalRules.Decide(r, test.DisplayName, con_clash_centers)
                decisions.append({
                    "idx": clash_index,
                    "test": test.DisplayName,
                    "result": r,
                    "new_status": status,
                    "reason": reason,
                })
                clash_index += 1

        if not decisions:
            print("No New clashes to process.")
            MessageBox.Show(
                "No New clash results found to process.",
                "Auto Review",
                MessageBoxButtons.OK,
                MessageBoxIcon.Information
            )
            return

        # Show summary and ask confirmation
        approved = [d for d in decisions if d["new_status"] == "Approved"]
        reviewed = [d for d in decisions if d["new_status"] == "Reviewed"]

        lines = [f"Ready to process {len(decisions)} New clash(es):", ""]
        lines.append(f"  Approve ({len(approved)}):")
        for d in approved:
            lines.append(f"    [{d['idx']:02d}] {d['test']} — {d['reason']}")
        lines.append(f"\n  Reviewed ({len(reviewed)}):")
        for d in reviewed:
            lines.append(f"    [{d['idx']:02d}] {d['test']} — {d['reason']}")
        lines.append("\nProceed?")

        confirm = MessageBox.Show(
            "\n".join(lines),
            "Auto Review Clash Results",
            MessageBoxButtons.YesNo,
            MessageBoxIcon.Question
        )

        if confirm != DialogResult.Yes:
            print("Cancelled by user.")
            return

        # Apply statuses and comments
        assignee = Assignee()
        assignee.DisplayName = "PyNET"

        status_enum = {
            "Approved": ClashResultStatus.Approved,
            "Reviewed": ClashResultStatus.Reviewed,
        }

        applied = 0
        for d in decisions:
            try:
                testsData.TestsEditResultStatus(d["result"], status_enum[d["new_status"]], assignee)
                body = f"[Auto-review {run_date}] {d['reason']}"
                comments = CommentCollection()
                comments.Add(Comment(body, CommentStatus.New))
                testsData.TestsEditResultComments(d["result"], comments)
                print(f"  [{d['idx']:02d}] {d['test']} → {d['new_status']} | {d['reason']}")
                applied += 1
            except Exception as e:
                print(f"  [{d['idx']:02d}] ERROR: {e}")

        print(f"\nApplied: {applied}/{len(decisions)}")

        # Group related clashes by shared element (within each test)
        print("\nGrouping related clashes...")
        total_groups = 0
        for test in get_clash_tests(clashDoc):
            total_groups += ClashGrouper.GroupBySharedElement(testsData, test)
        print(f"Groups created: {total_groups}")

        MessageBox.Show(
            f"Done.\n{len(approved)} Approved, {len(reviewed)} Reviewed.\n{total_groups} group(s) created.",
            "Auto Review Complete",
            MessageBoxButtons.OK,
            MessageBoxIcon.Information
        )


# Entry point
AutoReviewManager.Run(doc)

#endregion
