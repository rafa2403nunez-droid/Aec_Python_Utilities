# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr
from pathlib import Path

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document  # type: ignore

# Map: ElementId (int) -> new name
RENAME_MAP = {
    221:     "ARQ_Muros_FAC_Exterior - Brick on Mtl. Stud",
    21854:   "ARQ_Muros_FAC__Not Defined",
    56765:   "ARQ_Muros_FAC_Storefront",
    56766:   "ARQ_Muros_FAC_Exterior Glazing",
    83171:   "ARQ_Muros_FAC_Exterior - CMU on Mtl. Stud",
    441445:  "ARQ_Muros_FAC_Generic - 6\"",
    441451:  "ARQ_Muros_FAC_Generic - 8\"",
    441453:  "ARQ_Muros_FAC_Generic - 12\"",
    441454:  "ARQ_Muros_FAC_Generic - 5\"",
    441455:  "ARQ_Muros_FAC_Generic - 12\" Masonry",
    441456:  "ARQ_Muros_FAC_Generic - 8\" Masonry",
    441457:  "ARQ_Muros_FAC_Generic - 6\" Masonry",
    441459:  "ARQ_Muros_FAC_Generic - 4\" Brick",
    441461:  "ARQ_Muros_PAR_Interior - 4 7/8\" Partition (1-hr)",
    441462:  "ARQ_Muros_PAR_Interior - 6 1/8\" Partition (2-hr)",
    441465:  "ARQ_Muros_MUE_Foundation - 12\" Concrete",
    441467:  "ARQ_Muros_FAC_Generic - 8\" Filled",
    441518:  "ARQ_Muros_FAC_Generic - 4\"",
    593899:  "ARQ_Muros_FAC_Generic - 10\"",
    619631:  "ARQ_Muros_FAC_Generic - 24\"",
    624953:  "ARQ_Muros_FAC_Generic - 30\"",
    703553:  "ARQ_Muros_FAC_Solar Wall",
    930627:  "ARQ_Muros_FAC_Glazing Wall - Stair",
    972106:  "ARQ_Muros_FAC_Solar Panels",
    1005464: "ARQ_Muros_FAC_Solar Wall Window Frame",
    1026181: "ARQ_Muros_FAC_Block 37 Storefront",
    1051703: "ARQ_Muros_FAC_Generic - 21\"",
    1059192: "ARQ_Muros_FAC_Block 39 Storefront",
    1059632: "ARQ_Muros_FAC_Block 41 Storefront",
    1060723: "ARQ_Muros_FAC_Block 43 Storefront",
    1221045: "ARQ_Muros_MUE_Foundation - 24\" Concrete",
    1221510: "ARQ_Muros_MUE_Core - Concrete 12\"",
    1221636: "ARQ_Muros_MUE_Core - Concrete 10\"",
    1221692: "ARQ_Muros_MUE_Core - Concrete 18\"",
    1222123: "ARQ_Muros_PAR_Interior - CMU 8\"",
    1243847: "ARQ_Muros_PAR_Chase - GWB & Metal Stud 4 1/4\"",
    1273181: "ARQ_Muros_PAR_Party - 6 1/8\" (2-hr)",
    1276697: "ARQ_Muros_PAR_Interior - 7 1/4\" Partition (NR)",
    1279096: "ARQ_Muros_PAR_Interior - 4 7/8\" Partition (NR)",
    1286401: "ARQ_Muros_PAR_Chase - GWB & Metal Stud 2 1/4\"",
    1293517: "ARQ_Muros_FAC_Exterior - 12 5/8\" Rainscreen w Insultation on Metal Stud",
    1296106: "ARQ_Muros_PAR_Chase - GWB & Metal Stud 3 1/8\"",
    1303553: "ARQ_Muros_PAR_Chase - GWB & Metal Stud 6 5/8\"",
    1310737: "ARQ_Muros_PAR_Interior - 8 1/2\" Partition (2-hr)",
    1322992: "ARQ_Muros_FAC_Exterior - 10 1/4\" Rainscreen w Insultation on Metal Stud",
    1324807: "ARQ_Muros_PAR_Furring - GWB & Channels 1 7/8\"",
    1343470: "ARQ_Muros_FAC_Living Wall",
    1345241: "ARQ_Muros_FAC_Solar Wall (Multi-Level)",
    1439662: "ARQ_Muros_FAC_Exterior - 9 7/8\" EIFS on Mtl. Stud",
    1449008: "ARQ_Muros_FAC_Soffit - Beam Wrap (Both Sides)",
    1449129: "ARQ_Muros_FAC_Soffit - Beam Wrap 9 1/4\" (One Side)",
    1456534: "ARQ_Muros_MUE_Retaining - Split Face CMU",
    1474920: "ARQ_Muros_FAC_Exterior - 5 3/8\" Rainscreen w Insultation (for Concrete Core Walls)",
    1500908: "ARQ_Muros_FAC_Trellis Member",
    1506825: "ARQ_Muros_FAC_Exterior - GWB on Metal Stud w Insulated Panel 8 7/8\"",
    1524646: "ARQ_Muros_FAC_Soffit - Beam Wrap 11 1/4\" (One Side)",
    1533243: "ARQ_Muros_FAC_Exterior - 12 5/8\" Rainscreen w Insultation on Metal Stud (Alley)",
    1553550: "ARQ_Muros_FAC_Soffit - Beam Wrap 10 1/2\" (Two Sides)",
    1686275: "ARQ_Muros_FAC_Solar Wall (Parapet)",
    1686415: "ARQ_Muros_FAC_Solar Wall (L5)",
    1698992: "ARQ_Muros_FAC_Soffit - Beam Wrap Large (Both Sides)",
    1930010: "ARQ_Muros_FAC_Exterior - 14 5/8\" Rainscreen w Insultation on Metal Stud",
    1995823: "ARQ_Muros_FAC_Exterior - 13 5/8\" Rainscreen (Two Sides) w Insultation on Metal Stud",
    1996151: "ARQ_Muros_FAC_Parapet Cap Bandstand",
    1996712: "ARQ_Muros_FAC_Block 37 Pilaster",
    2000868: "ARQ_Muros_FAC_Block 39 Pilaster",
    2045789: "ARQ_Muros_MUE_Planter Wall - Steel Plate 1/2\"",
    2159792: "ARQ_Muros_PAR_Interior - 5 1/2\" Partition (1-hr Smoke)",
    2175692: "ARQ_Muros_PAR_Interior - 7 1/4\" Partition (1 hr)",
    2761898: "ARQ_Muros_FAC_Block 43",
    2761902: "ARQ_Muros_FAC_Block 43 w Brick Banding",
    2761942: "ARQ_Muros_FAC_Block 37",
    2761948: "ARQ_Muros_FAC_Block 37 w Brick Banding",
    2761955: "ARQ_Muros_FAC_Block 39",
    2761957: "ARQ_Muros_FAC_Block 39_L4 w Brick Banding",
    2761992: "ARQ_Muros_FAC_Block 39_L4 w Banding",
    2761999: "ARQ_Muros_FAC_Block 39_L3 w Banding",
    2762031: "ARQ_Muros_FAC_Block 39 - L2 Entablature",
    2873037: "ARQ_Muros_PAR_Retail Slat Wall",
    3002164: "ARQ_Muros_PAR_Finish - 1\" - Purple",
    3002166: "ARQ_Muros_PAR_Finish - 1\" - Green",
    3002168: "ARQ_Muros_PAR_Finish - 1\" - White",
    3002170: "ARQ_Muros_PAR_Finish - 1\" - Blue",
    3005613: "ARQ_Muros_PAR_Finish - 1\" - Yellow",
    3086269: "ARQ_Muros_PAR_Office Glass Wall",
}

def eid_val(eid):
    try: return int(eid.Value)
    except: return int(eid.IntegerValue)

# Build lookup: eid_int -> element
all_types = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Walls).WhereElementIsElementType().ToElements()
type_by_id = {eid_val(el.Id): el for el in all_types}

renamed = []
skipped = []
errors = []

t = Transaction(doc, "QC - Rename Wall Types")
t.Start()
try:
    for eid_int, new_name in RENAME_MAP.items():
        el = type_by_id.get(eid_int)
        if el is None:
            skipped.append(eid_int)
            continue
        try:
            el.Name = new_name
            renamed.append({"id": eid_int, "new": new_name})
        except Exception as ex:
            errors.append({"id": eid_int, "new": new_name, "error": str(ex)})
    t.Commit()
except Exception as ex:
    t.RollBack()
    raise

print(f"Renamed: {len(renamed)} | Skipped (not found): {len(skipped)} | Errors: {len(errors)}")

ia_Result = {
    "renamed": len(renamed),
    "skipped": skipped,
    "errors": errors,
}
