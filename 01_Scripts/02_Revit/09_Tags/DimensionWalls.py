# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

# Auto-dimension straight walls in the active floor plan.
# Classifies every straight wall by its centerline orientation (vertical = constant X,
# horizontal = constant Y), then creates four dimension strings: an overall + a
# partition string on each axis, each referencing the wall centerlines (Reference(wall)).
# A dimension is perpendicular to the references it measures, so vertical walls are
# measured by a horizontal dimension line and vice versa.

import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import (
    FilteredElementCollector, Level, Wall, ViewPlan, Reference, ReferenceArray,
    Line, XYZ, Transaction,
)

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

# ---------------------------------------------------------------------------
# Configuration — edit these values before running
# ---------------------------------------------------------------------------

MM = 1.0 / 304.8        # millimetres -> Revit internal units (feet)
OFFSET_OVERALL = 1000   # gap (mm) from the model to the overall dimension line
OFFSET_PARTS = 2200     # gap (mm) from the model to the partition dimension line

# ---------------------------------------------------------------------------

# Lowest level and a floor plan view to host the dimensions.
levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
if not levels:
    raise Exception("The project has no levels.")
level = min(levels, key=lambda l: l.Elevation)

view = doc.ActiveView
if not isinstance(view, ViewPlan):
    plans = [v for v in FilteredElementCollector(doc).OfClass(ViewPlan) if not v.IsTemplate]
    view = next((v for v in plans if v.GenLevel and v.GenLevel.Id == level.Id),
                plans[0] if plans else None)
if view is None:
    raise Exception("No floor plan view available to place the dimensions.")
print("View:", view.Name)

# Group straight walls by axis, keeping one representative wall per unique coordinate
# (several wall segments can share the same axis, e.g. a partition split by a doorway).
walls = list(FilteredElementCollector(doc).OfClass(Wall)
             .WhereElementIsNotElementType().ToElements())
verticals, horizontals = {}, {}     # rounded coordinate (ft) -> wall
for w in walls:
    curve = w.Location.Curve
    if curve is None:
        continue                    # skip non-straight / sketched walls
    p0, p1 = curve.GetEndPoint(0), curve.GetEndPoint(1)
    if abs(p1.X - p0.X) < abs(p1.Y - p0.Y):
        verticals.setdefault(round(p0.X, 3), w)
    else:
        horizontals.setdefault(round(p0.Y, 3), w)

xs = sorted(verticals.keys())
ys = sorted(horizontals.keys())
if len(xs) < 2 or len(ys) < 2:
    raise Exception("Need at least two walls on each axis to dimension.")
print("Axes -> vertical:", len(xs), "| horizontal:", len(ys))

# Model extents (feet), used to span the dimension lines beyond the references.
x_min, x_max = xs[0], xs[-1]
y_min, y_max = ys[0], ys[-1]


def add_dimension(dim_line, ref_walls):
    """Create one dimension string along dim_line referencing the given wall centerlines."""
    refs = ReferenceArray()
    for w in ref_walls:
        refs.Append(Reference(w))
    doc.Create.NewDimension(view, dim_line, refs)


t = Transaction(doc, "PyNET - Auto-dimension walls")
t.Start()
try:
    n = 0

    # Horizontal dimension lines (measure X) placed below the plan.
    y_parts = y_min - OFFSET_PARTS * MM
    y_over = y_min - OFFSET_OVERALL * MM
    add_dimension(Line.CreateBound(XYZ(x_min, y_parts, 0), XYZ(x_max, y_parts, 0)),
                  [verticals[x] for x in xs]); n += 1
    add_dimension(Line.CreateBound(XYZ(x_min, y_over, 0), XYZ(x_max, y_over, 0)),
                  [verticals[x_min], verticals[x_max]]); n += 1

    # Vertical dimension lines (measure Y) placed to the left of the plan.
    x_parts = x_min - OFFSET_PARTS * MM
    x_over = x_min - OFFSET_OVERALL * MM
    add_dimension(Line.CreateBound(XYZ(x_parts, y_min, 0), XYZ(x_parts, y_max, 0)),
                  [horizontals[y] for y in ys]); n += 1
    add_dimension(Line.CreateBound(XYZ(x_over, y_min, 0), XYZ(x_over, y_max, 0)),
                  [horizontals[y_min], horizontals[y_max]]); n += 1

    t.Commit()
    print("Dimensions created:", n, "(2 horizontal + 2 vertical)")
except:
    t.RollBack()
    raise
