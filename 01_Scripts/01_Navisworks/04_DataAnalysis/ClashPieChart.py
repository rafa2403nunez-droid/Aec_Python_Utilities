# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import plotly.graph_objects as go
import plotly.io as pio
import clr
import sys
from pathlib import Path

bundlePath = (Path.home()/ "AppData"/ "Roaming"/ "Autodesk"/ "ApplicationPlugins"/ "RAEN.Navisworks.PyNET.bundle"/ "Contents"/ "2024")
sys.path.append(str(bundlePath))
clr.AddReference("Raen.Core.Pynet.Resources")
from Raen.Core.Pynet.Resources import CastUtils  # type: ignore

clr.AddReference("Autodesk.Navisworks.Api")
clr.AddReference("Autodesk.Navisworks.Clash")
from Autodesk.Navisworks.Api import Application
from Autodesk.Navisworks.Api.Clash import DocumentClash, ClashResult
# Estados "ToResolve": aún por resolver (se excluyen Approved y Resolved)
TORESOLVE_STATUSES = {"New", "Active", "Reviewed"}
# Paleta ámbar (color del estado ToResolve); las porciones se distinguen por tono
TORESOLVE_PALETTE = ["#f39c12", "#e67e22", "#f5b041", "#d68910", "#f8c471", "#ca6f1e", "#fad7a0", "#b9770e"]


sys.path.append(str(Path.home() / "AppData" / "Roaming" / "Pynet" / "Library" / "01_Scripts" / "00_utils"))
from pynet_clash import get_clash_tests


class DataManager:
    """
    Collects ToResolve clash result counts (New, Active, Reviewed) from each test.
    """

    @staticmethod
    def IterResults(test):
        """Yields all clash results under a test, entering groups if present."""
        for child in test.Children:
            if child.IsGroup:
                for r in child.Children:
                    yield r
            else:
                yield child

    @staticmethod
    def CollectToResolveClashes(document):
        clashDoc = CastUtils.CastTo[DocumentClash](document.Clash)
        data = []
        for test in get_clash_tests(clashDoc):
            toresolve_count = 0
            for child in DataManager.IterResults(test):
                result = CastUtils.CastTo[ClashResult](child)
                if result is not None and str(result.Status) in TORESOLVE_STATUSES:
                    toresolve_count += 1
            if toresolve_count > 0:
                data.append({"name": test.DisplayName, "toresolve": toresolve_count})
        return data


class ChartManager:
    """
    Renders a pie chart of pending clash interferences per test using Plotly.
    """

    @staticmethod
    def ShowPieChart(data):
        labels = [d["name"] for d in data]
        values = [d["toresolve"] for d in data]
        total = sum(values)
        colors = [TORESOLVE_PALETTE[i % len(TORESOLVE_PALETTE)] for i in range(len(values))]

        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0,
            textinfo='label+percent+value',
            marker=dict(colors=colors),
            pull=[0.05] * len(values)
        )])

        fig.update_layout(
            title=dict(
                text=f"Interferencias ToResolve por Test de Clash — Total: {total}",
                font=dict(size=16),
                x=0.5
            ),
            legend=dict(orientation="h", yanchor="bottom", y=-0.3)
        )

        pio.show(fig)
        return total


class FeatureManager:
    """
    Entry point for generating a pie chart of pending clash interferences.
    """

    @staticmethod
    def Run(document):
        data = DataManager.CollectToResolveClashes(document)
        if data:
            total = ChartManager.ShowPieChart(data)
            print({"status": "Grafico mostrado", "total_toresolve": total})
        else:
            print({"status": "No hay interferencias ToResolve"})


# Entry point
doc = Application.ActiveDocument
FeatureManager.Run(doc)
