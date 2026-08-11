# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import *

uidoc = __revit__.ActiveUIDocument  #type:ignore
doc = uidoc.Document

CATEGORY = BuiltInCategory.OST_Doors


class GetDoorsOrWindowsOfARoomScript:
    @staticmethod
    def Run(doc):
        phases = FilteredElementCollector(doc).OfClass(Phase).ToElements()
        phase = list(phases)[-1] if phases else None
        if phase is None:
            print("No phases found in document.")
            return []

        category = doc.Settings.Categories.get_Item(CATEGORY)
        categoryFilter = ElementCategoryFilter(category.Id)

        rooms = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements()
        familyInstances = FilteredElementCollector(doc).WherePasses(categoryFilter).WhereElementIsNotElementType().ToElements()

        def GetRoomDoors(familyInstances, rooms, phase):
            result = []
            for room in rooms:
                listInstance = [room]
                listRoom = []
                for instance in familyInstances:
                    if instance.__class__ == FamilyInstance and hasattr(instance, "ToRoom") and hasattr(instance, "FromRoom"):
                        if instance.ToRoom[phase] is not None and room.Id == instance.ToRoom[phase].Id:
                            listRoom.append(instance)
                        if instance.FromRoom[phase] is not None and room.Id == instance.FromRoom[phase].Id:
                            listRoom.append(instance)
                listInstance.append(listRoom)
                result.append(listInstance)
            return result

        result = GetRoomDoors(familyInstances, rooms, phase)
        total_doors = sum(len(r[1]) for r in result)
        print(f"Scanned {len(list(rooms))} rooms, found {total_doors} door/window associations.")
        return result


GetDoorsOrWindowsOfARoomScript.Run(doc)
