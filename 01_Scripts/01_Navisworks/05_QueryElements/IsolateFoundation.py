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
    Isolates target items by hiding everything else.
    """

    @staticmethod
    def IsolateItems(document, targetItems):
        allItems = document.Models.RootItemDescendantsAndSelf
        document.Models.SetHidden(allItems, False)

        targetSet = set()
        for item in targetItems:
            targetSet.add(str(item.InstanceGuid))

        nonTarget = ModelItemCollection()
        for item in allItems:
            if item.HasGeometry and str(item.InstanceGuid) not in targetSet:
                nonTarget.Add(item)

        document.Models.SetHidden(nonTarget, True)

        document.CurrentSelection.Clear()
        document.CurrentSelection.CopyFrom(targetItems)

        return nonTarget.Count


class FeatureManager:
    """
    Entry point for isolating foundation pile elements in the model.
    """

    @staticmethod
    def Run(document):
        pilotes = QueryManager.FindByType(document, "IDP_COM_Pilote_Circular:HormigonArmado")
        hiddenCount = ViewManager.IsolateItems(document, pilotes)
        print(f"Aislados {pilotes.Count} pilotes. Ocultos {hiddenCount} elementos.")


# Entry point
doc = Application.ActiveDocument
FeatureManager.Run(doc)
