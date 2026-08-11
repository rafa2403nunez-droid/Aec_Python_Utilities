# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import Application, Search, SearchLocations, SearchCondition, ModelItemCollection


class QueryManager:
    """
    Searches for model items in Navisworks by property conditions.
    """

    @staticmethod
    def FindByType(document, typeValue):
        searchSet = Search()
        searchSet.Locations = SearchLocations.DescendantsAndSelf
        searchSet.Selection.SelectAll()

        condition = SearchCondition.HasPropertyByDisplayName("Item", "Type")
        conditionValue = condition.DisplayStringContains(typeValue)
        searchSet.SearchConditions.Add(conditionValue)

        return searchSet.FindAll(document, False)


class ViewManager:
    """
    Controls element visibility in the Navisworks scene.
    Isolates target items and their geometry descendants by hiding everything else.
    """

    @staticmethod
    def GetPath(item):
        parts = []
        current = item
        while current is not None:
            parts.append(current.DisplayName)
            current = current.Parent
        return "|".join(reversed(parts))

    @staticmethod
    def IsolateByDescendants(document, targetItems):
        allItems = document.Models.RootItemDescendantsAndSelf
        document.Models.SetHidden(allItems, False)

        protectedGeometry = ModelItemCollection()
        for item in targetItems:
            for desc in item.Descendants:
                if desc.HasGeometry:
                    protectedGeometry.Add(desc)

        protectedPaths = set()
        for item in protectedGeometry:
            protectedPaths.add(ViewManager.GetPath(item))

        toHide = ModelItemCollection()
        for item in allItems:
            if item.HasGeometry and ViewManager.GetPath(item) not in protectedPaths:
                toHide.Add(item)

        document.Models.SetHidden(toHide, True)

        document.CurrentSelection.Clear()
        document.CurrentSelection.CopyFrom(targetItems)

        return toHide.Count


class FeatureManager:
    """
    Entry point for isolating padel glass panel elements in the model.
    """

    @staticmethod
    def Run(document):
        targetItems = QueryManager.FindByType(document, "IDP_ARQ_VidrioPadel_1.6cm")
        hiddenCount = ViewManager.IsolateByDescendants(document, targetItems)
        print(f"Aislados {targetItems.Count} vidrios de padel. Ocultos {hiddenCount} elementos.")


# Entry point
doc = Application.ActiveDocument
FeatureManager.Run(doc)
