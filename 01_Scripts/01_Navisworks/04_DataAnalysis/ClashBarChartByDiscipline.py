# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import plotly.graph_objects as go
import plotly.io as pio
import clr
import sys
import re
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
TORESOLVE_COLOR = "#f39c12"   # ámbar — color propio del estado ToResolve

DISCIPLINE_MAP = {
    "EM": "Estructura Metalica",
    "EH": "Hormigon in Situ",
    "EP": "H. Prefabricado",
    "IC": "Climatizacion",
    "II": "P. Incendios",
    "IF": "Fontaneria",
    "IS": "Saneamiento",
    "IO": "Frio Industrial"
}


sys.path.append(str(Path.home() / "AppData" / "Roaming" / "Pynet" / "Library" / "01_Scripts" / "00_utils"))
from pynet_clash import get_clash_tests


class DataManager:
    """
    Collects new clash counts grouped by discipline from the active document.
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
    def CollectByDiscipline(document):
        clashDoc = CastUtils.CastTo[DocumentClash](document.Clash)
        discipline_counts = {}

        for test in get_clash_tests(clashDoc):
            name = test.DisplayName
            match = re.search(r'([A-Z]{2}) vs ', name)
            code = match.group(1) if match else "??"
            label = DISCIPLINE_MAP.get(code, code)

            toresolve_count = 0
            for child in DataManager.IterResults(test):
                result = CastUtils.CastTo[ClashResult](child)
                if result is not None and str(result.Status) in TORESOLVE_STATUSES:
                    toresolve_count += 1

            discipline_counts[label] = discipline_counts.get(label, 0) + toresolve_count

        return discipline_counts


class ChartManager:
    """
    Renders a bar chart of new clash interferences per discipline using Plotly.
    """

    @staticmethod
    def ShowBarChart(discipline_counts):
        sorted_items = sorted(discipline_counts.items(), key=lambda x: x[1], reverse=True)
        labels = [i[0] for i in sorted_items]
        values = [i[1] for i in sorted_items]
        total = sum(values)

        colors = [TORESOLVE_COLOR if v > 0 else "#90a4ae" for v in values]

        fig = go.Figure(data=[go.Bar(
            x=labels,
            y=values,
            marker_color=colors,
            text=values,
            textposition="outside"
        )])

        fig.update_layout(
            title=dict(
                text=f"Interferencias ToResolve por Disciplina — Total: {total}",
                font=dict(size=16),
                x=0.5
            ),
            xaxis_title="Disciplina",
            yaxis_title="N Interferencias ToResolve",
            yaxis=dict(rangemode="tozero"),
            plot_bgcolor="white",
            bargap=0.3
        )

        pio.show(fig)
        return total


class FeatureManager:
    """
    Entry point for generating a bar chart of new clashes by discipline.
    """

    @staticmethod
    def Run(document):
        discipline_counts = DataManager.CollectByDiscipline(document)
        total = ChartManager.ShowBarChart(discipline_counts)
        return {"status": "Grafico mostrado", "total_toresolve": total, "por_disciplina": discipline_counts}


# Entry point
doc = Application.ActiveDocument
ia_Result = FeatureManager.Run(doc)
