# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

"""
Aligned plan viewpoint + missing-material flagging.

For the currently selected item(s):
  1. Read the "Material" property. If it is blank, override the element colour to RED.
  2. Work out the element's REAL plan rotation (elements are not always aligned to the
     model axes) so it reads square on screen instead of skewed.
  3. Delete any previous viewpoint with the same name prefix and create a fresh
     top-down orthographic viewpoint framed on the element.

Notes worth keeping in mind when maintaining this script:
  - The rotation is NOT exposed as a property. It has to be read from the geometry's
    local-to-world matrix through the COM API, and the geometry usually hangs off a
    child node rather than the selected item itself.
  - The saved viewpoint must be captured FROM THE ACTIVE VIEW
    (CaptureRuntimeOverrides + ReplaceFromCurrentView). Building a Viewpoint in code and
    saving it directly restores rotated.
  - Colour components are 0..1, not 0..255. The override is permanent, so the viewpoint
    keeps it.
"""

import clr
import math

clr.AddReference("Autodesk.Navisworks.Api")
clr.AddReference("Autodesk.Navisworks.ComApi")
clr.AddReference("Autodesk.Navisworks.Interop.ComApi")

from Autodesk.Navisworks.Api import (Application, Vector3D, BoundingBox3D,
                                     ViewpointProjection, Color)
from Autodesk.Navisworks.Api.ComApi import ComApiBridge
from Autodesk.Navisworks.Api.Interop import ComApi

doc = Application.ActiveDocument

# Viewpoint name prefix. Every saved viewpoint starting with it is deleted and
# regenerated on each run, so repeated runs never pile up duplicates.
VIEWPOINT_PREFIX = "Planta - "

# Padding around the element in the framing (1.15 = 15% of breathing room).
MARGIN = 1.15


class MaterialChecker:
    """Reads the Material property and applies the warning colour."""

    @staticmethod
    def ReadMaterial(item):
        # Walk every property tab looking for "Material".
        # Returns (text, is_blank). A missing property counts as blank.
        for cat in item.PropertyCategories:
            for p in cat.Properties:
                if str(p.DisplayName).lower() == "material":
                    v = p.Value
                    txt = None if v is None else str(v.ToDisplayString())
                    return txt, (txt is None or txt.strip() == "")
        return None, True

    @staticmethod
    def PaintIfMissing(document, item):
        txt, is_blank = MaterialChecker.ReadMaterial(item)
        print("Material: '%s' | blank: %s" % (txt, is_blank))
        if is_blank:
            # OverridePermanentColor survives orbiting, isolating, etc.
            # Colour components are 0..1, not 0..255 -> (1,0,0) is red.
            document.Models.OverridePermanentColor(
                document.CurrentSelection.SelectedItems, Color(1.0, 0.0, 0.0))
            print("Element painted red (no material assigned)")
        return txt, is_blank


class OrientationHelper:
    """Derives the element's real plan rotation."""

    @staticmethod
    def UpAxis(item):
        # The rotation lives in the geometry's local-to-world matrix: its first row is
        # the element's local X axis expressed in world coordinates.
        ax, ay = 1.0, 0.0
        for d in item.DescendantsAndSelf:
            if not d.HasGeometry:
                continue  # geometry usually hangs off a child node, not the item itself
            for f in ComApiBridge.ToInwOaPath(d).Fragments():
                matrix = ComApi.InwLTransform3f3(
                    ComApi.InwOaFragment3(f).GetLocalToWorldMatrix()).Matrix
                v = [float(x) for x in matrix]
                ax, ay = v[0], v[1]
                break
            break

        ang = math.atan2(ay, ax)                # element rotation in plan
        ux, uy = -math.sin(ang), math.cos(ang)  # local Y axis = screen "up"
        if uy < 0:                              # keep the view from ending up upside down
            ux, uy = -ux, -uy
        print("Element rotation: %.2f deg" % math.degrees(math.atan2(-ux, uy)))
        return ux, uy


class ViewpointBuilder:
    """Builds and saves the plan viewpoint."""

    @staticmethod
    def BoundingBox(items):
        # Box enclosing the whole selection.
        box = None
        for it in items:
            b = it.BoundingBox()
            if b is None:
                continue
            if box is None:
                box = BoundingBox3D(b.Min, b.Max)
            else:
                box.Extend(b.Min)
                box.Extend(b.Max)
        return box

    @staticmethod
    def Framing(box, ux, uy):
        # Project the box corners onto the rotated camera axes to get the exact
        # width/height that has to be framed.
        rx, ry = uy, -ux          # camera horizontal (right) axis
        mn, mx = box.Min, box.Max
        rs, us = [], []
        for cx in (mn.X, mx.X):
            for cy in (mn.Y, mx.Y):
                rs.append(cx * rx + cy * ry)
                us.append(cx * ux + cy * uy)
        return (max(rs) - min(rs)) * MARGIN, (max(us) - min(us)) * MARGIN

    @staticmethod
    def DeletePrevious(document):
        root = document.SavedViewpoints.RootItem
        deleted = []
        for old in list(root.Children):
            if str(old.DisplayName).startswith(VIEWPOINT_PREFIX):
                document.SavedViewpoints.Remove(root, old)
                deleted.append(str(old.DisplayName))
        print("Viewpoints deleted: %d" % len(deleted))
        return deleted

    @staticmethod
    def Create(document, items, ux, uy):
        box = ViewpointBuilder.BoundingBox(items)
        w, h = ViewpointBuilder.Framing(box, ux, uy)

        vp = document.CurrentViewpoint.CreateCopy()
        vp.Projection = ViewpointProjection.Orthographic  # plan view, no perspective
        vp.AlignUp(Vector3D(ux, uy, 0))                   # rotate camera with the element
        vp.AlignDirection(Vector3D(0, 0, -1))             # look straight down
        vp.ZoomBox(box)                                   # zoom onto the element
        vp.SetExtentsAtFocalDistance(w, h)                # fine-tune the framing
        document.CurrentViewpoint.CopyFrom(vp)            # apply to the active view

        # The viewpoint is saved FROM THE ACTIVE VIEW. CaptureRuntimeOverrides also stores
        # the red override, and ReplaceFromCurrentView guarantees it restores exactly as
        # seen on screen (a hand-built Viewpoint restores rotated).
        name = VIEWPOINT_PREFIX + str(items[0].DisplayName)
        sv = document.SavedViewpoints.CaptureRuntimeOverrides()
        sv.DisplayName = name
        document.SavedViewpoints.AddCopy(None, sv)

        saved = None
        for s in document.SavedViewpoints.RootItem.Children:
            if str(s.DisplayName) == name:
                saved = s
        document.SavedViewpoints.ReplaceFromCurrentView(saved)

        print("Viewpoint created: %s" % name)
        return name


class FeatureManager:
    """Entry point: orchestrates the whole process."""

    @staticmethod
    def Run(document):
        items = list(document.CurrentSelection.SelectedItems)
        print("Selected items: %d" % len(items))
        if not items:
            print("Nothing selected. Select an element and run again.")
            return

        MaterialChecker.PaintIfMissing(document, items[0])
        ViewpointBuilder.DeletePrevious(document)
        ux, uy = OrientationHelper.UpAxis(items[0])
        ViewpointBuilder.Create(document, items, ux, uy)
        print("Done.")


# Entry point
FeatureManager.Run(doc)
