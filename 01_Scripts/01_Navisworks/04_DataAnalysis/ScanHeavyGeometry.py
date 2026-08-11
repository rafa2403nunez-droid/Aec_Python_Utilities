# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

"""
ScanHeavyGeometry - Scans the active Navisworks model and reports heavy groups.

Outputs:
    <NWF folder>/ScanReports/scan_heavy_geometry_<timestamp>.json
    <NWF folder>/ScanReports/scan_heavy_geometry_<timestamp>.csv

Goal:
    Help choose a sane default MaxFacesPerElement plus exceptions.

How it works:
    - Walks geometry leaves with the same grouping logic used by the GLB exporter
    - Tessellates each group once with TriangleMeshCollector
    - Counts triangles, fragments, leaves, and bbox size
    - Writes a full report plus a summary recommendation per group
"""

import clr
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

clr.AddReference("Autodesk.Navisworks.Api")
clr.AddReference("Autodesk.Navisworks.ComApi")
clr.AddReference("Autodesk.Navisworks.Interop.ComApi")
clr.AddReference("System.Windows.Forms")

from Autodesk.Navisworks.Api import Application
from Autodesk.Navisworks.Api.ComApi import ComApiBridge
from Autodesk.Navisworks.Api.Interop.ComApi import InwOaFragment3
from System.Windows.Forms import MessageBox, MessageBoxButtons, MessageBoxIcon

_bundle_root = (Path.home() / "AppData" / "Roaming" / "Autodesk" / "ApplicationPlugins"
                / "RAEN.Navisworks.PyNET.bundle" / "Contents")
for _year in ("2027", "2026", "2025", "2024"):
    _candidate = _bundle_root / _year
    if _candidate.exists():
        sys.path.append(str(_candidate))

for _asm in ("Raen.Core.Pynet.Resources",
             "Raen.Navisworks.Pynet.2027",
             "Raen.Navisworks.Pynet.2026",
             "Raen.Navisworks.Pynet.2025",
             "Raen.Navisworks.Pynet.2024"):
    try:
        clr.AddReference(_asm)
    except Exception:
        pass

from Raen.Core.Pynet.Resources import CastUtils  # type: ignore
from Raen.Navisworks.Pynet.Utils import TriangleMeshCollector  # type: ignore


MAX_SCAN_FACES = 30000
NORMAL_LIMIT = 10000
HIGH_LIMIT = 20000
LOG_EVERY_GROUPS = 50


def safe_name(item) -> str:
    try:
        return item.DisplayName or ""
    except Exception:
        return ""


def get_group_name(item) -> str:
    node = item.Parent
    while node is not None:
        name = safe_name(node)
        if name:
            return name
        node = node.Parent
    return "element"


def get_parent_hash(item) -> int:
    try:
        if item.Parent is not None:
            return item.Parent.GetHashCode()
    except Exception:
        pass
    return item.GetHashCode()


def get_parent_chain(item, depth_max: int = 8) -> list:
    names = []
    node = item.Parent
    depth = 0
    while node is not None and depth < depth_max:
        name = safe_name(node)
        if name:
            names.append(name)
        node = node.Parent
        depth += 1
    return names


def get_top_root_name(item) -> str:
    node = item
    last = item
    while node is not None:
        last = node
        node = node.Parent
    return safe_name(last)


def bbox_for_items(items):
    bminx = float("inf")
    bminy = float("inf")
    bminz = float("inf")
    bmaxx = float("-inf")
    bmaxy = float("-inf")
    bmaxz = float("-inf")
    any_box = False

    for it in items:
        try:
            bb = it.BoundingBox()
            bminx = min(bminx, bb.Min.X)
            bminy = min(bminy, bb.Min.Y)
            bminz = min(bminz, bb.Min.Z)
            bmaxx = max(bmaxx, bb.Max.X)
            bmaxy = max(bmaxy, bb.Max.Y)
            bmaxz = max(bmaxz, bb.Max.Z)
            any_box = True
        except Exception:
            pass

    if not any_box:
        return None

    return {
        "min": [bminx, bminy, bminz],
        "max": [bmaxx, bmaxy, bmaxz],
        "size": [bmaxx - bminx, bmaxy - bminy, bmaxz - bminz],
        "center": [(bminx + bmaxx) * 0.5, (bminy + bmaxy) * 0.5, (bminz + bmaxz) * 0.5],
    }


def collect_fragments(item, frags):
    try:
        path = ComApiBridge.ToInwOaPath(item)
        if path is None:
            return
        for raw_frag in path.Fragments():
            frag = CastUtils.CastTo[InwOaFragment3](raw_frag)
            if frag is not None:
                frags.append(frag)
    except Exception:
        pass


def recommendation_for(triangle_count: int, overflowed: bool) -> str:
    if overflowed:
        return "bbox_or_special_limit"
    if triangle_count > HIGH_LIMIT:
        return "special_limit_over_20000"
    if triangle_count > NORMAL_LIMIT:
        return "high_limit_20000"
    return "normal_limit_10000"


def scan_group(first_item, group_key: str, items: list, frags: list) -> dict:
    collector = TriangleMeshCollector()
    collector.MaxFaces = MAX_SCAN_FACES
    collector.KeepLocal = False

    for frag in frags:
        try:
            collector.CollectFromFragment(frag)
        except Exception:
            pass
        if collector.Overflowed:
            break

    tri_count = collector.Faces.Count
    bbox = bbox_for_items(items)

    return {
        "root_name": get_top_root_name(first_item),
        "group_name": get_group_name(first_item),
        "group_key": group_key,
        "leaf_count": len(items),
        "fragment_count": len(frags),
        "triangle_count": tri_count,
        "overflowed": bool(collector.Overflowed),
        "bbox": bbox,
        "parent_chain": get_parent_chain(first_item),
        "recommendation": recommendation_for(tri_count, bool(collector.Overflowed)),
    }


def write_csv(path: Path, rows: list) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "root_name",
            "group_name",
            "triangle_count",
            "overflowed",
            "recommendation",
            "leaf_count",
            "fragment_count",
            "bbox_size_x",
            "bbox_size_y",
            "bbox_size_z",
            "parent_chain",
            "group_key",
        ])
        for row in rows:
            bbox_size = row["bbox"]["size"] if row["bbox"] else [None, None, None]
            writer.writerow([
                row["root_name"],
                row["group_name"],
                row["triangle_count"],
                row["overflowed"],
                row["recommendation"],
                row["leaf_count"],
                row["fragment_count"],
                bbox_size[0],
                bbox_size[1],
                bbox_size[2],
                " > ".join(row["parent_chain"]),
                row["group_key"],
            ])


def main():
    doc = Application.ActiveDocument
    if doc is None:
        raise RuntimeError("No active Navisworks document.")

    root = doc.Models[0].RootItem
    model_path = Path(doc.FileName)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = model_path.parent / "ScanReports"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"scan_heavy_geometry_{timestamp}.json"
    csv_path = out_dir / f"scan_heavy_geometry_{timestamp}.csv"

    print("=== ScanHeavyGeometry ===")
    print(f"Model: {model_path}")
    print(f"Max scan faces per group: {MAX_SCAN_FACES}")
    print(f"Normal limit target: {NORMAL_LIMIT}")
    print(f"High limit target: {HIGH_LIMIT}")
    print("")

    started = time.time()
    results = []
    counts = {
        "groups_total": 0,
        "overflowed": 0,
        "gt_5000": 0,
        "gt_10000": 0,
        "gt_20000": 0,
    }

    grp_key = None
    grp_item = None
    grp_items = []
    grp_frags = []

    for item in root.DescendantsAndSelf:
        try:
            if not item.HasGeometry:
                continue
        except Exception:
            continue

        key = get_group_name(item) + "|" + str(get_parent_hash(item))
        if key != grp_key:
            if grp_item is not None:
                row = scan_group(grp_item, grp_key, grp_items, grp_frags)
                results.append(row)
                counts["groups_total"] += 1
                if row["overflowed"]:
                    counts["overflowed"] += 1
                if row["triangle_count"] > 5000:
                    counts["gt_5000"] += 1
                if row["triangle_count"] > 10000:
                    counts["gt_10000"] += 1
                if row["triangle_count"] > 20000:
                    counts["gt_20000"] += 1
                if counts["groups_total"] % LOG_EVERY_GROUPS == 0:
                    elapsed = time.time() - started
                    print(f"Scanned groups: {counts['groups_total']} | elapsed: {elapsed:.1f}s")

            grp_key = key
            grp_item = item
            grp_items = []
            grp_frags = []

        grp_items.append(item)
        collect_fragments(item, grp_frags)

    if grp_item is not None:
        row = scan_group(grp_item, grp_key, grp_items, grp_frags)
        results.append(row)
        counts["groups_total"] += 1
        if row["overflowed"]:
            counts["overflowed"] += 1
        if row["triangle_count"] > 5000:
            counts["gt_5000"] += 1
        if row["triangle_count"] > 10000:
            counts["gt_10000"] += 1
        if row["triangle_count"] > 20000:
            counts["gt_20000"] += 1

    results.sort(
        key=lambda r: (
            1 if r["overflowed"] else 0,
            r["triangle_count"],
            r["leaf_count"],
            r["fragment_count"],
        ),
        reverse=True,
    )

    summary = {
        "model_path": str(model_path),
        "generated_at": datetime.now().isoformat(),
        "max_scan_faces": MAX_SCAN_FACES,
        "normal_limit": NORMAL_LIMIT,
        "high_limit": HIGH_LIMIT,
        "elapsed_seconds": round(time.time() - started, 2),
        "counts": counts,
        "top_20": results[:20],
    }

    payload = {
        "summary": summary,
        "results": results,
    }

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(csv_path, results)

    print("")
    print("Scan complete.")
    print(f"Groups scanned: {counts['groups_total']}")
    print(f">5000 triangles:  {counts['gt_5000']}")
    print(f">10000 triangles: {counts['gt_10000']}")
    print(f">20000 triangles: {counts['gt_20000']}")
    print(f"Overflowed:       {counts['overflowed']}")
    print(f"JSON report: {json_path}")
    print(f"CSV report:  {csv_path}")
    MessageBox.Show(
        f"Scan complete.\n\nGroups scanned: {counts['groups_total']}\n"
        f">10000 triangles: {counts['gt_10000']}\n"
        f">20000 triangles: {counts['gt_20000']}\n\n"
        f"CSV:\n{csv_path}\n\nJSON:\n{json_path}",
        "ScanHeavyGeometry",
        MessageBoxButtons.OK,
        MessageBoxIcon.Information,
    )


try:
    main()
except Exception as ex:
    try:
        print("ScanHeavyGeometry failed:", str(ex))
    except Exception:
        pass
    MessageBox.Show(
        "ScanHeavyGeometry failed:\n\n" + str(ex),
        "ScanHeavyGeometry",
        MessageBoxButtons.OK,
        MessageBoxIcon.Error,
    )
