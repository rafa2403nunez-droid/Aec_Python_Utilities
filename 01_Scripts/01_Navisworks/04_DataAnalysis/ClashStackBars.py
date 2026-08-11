# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

#region references
import pandas as pd

import clr
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import re

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import Application

clr.AddReference("Autodesk.Navisworks.Clash")
from Autodesk.Navisworks.Api.Clash import DocumentClash, ClashResultStatus
bundlePath = (Path.home()/ "AppData"/ "Roaming"/ "Autodesk"/ "ApplicationPlugins"/ "RAEN.Navisworks.PyNET.bundle"/ "Contents"/ "2024")
NavisworksinconPath = (Path.home() / "AppData" / "Roaming" / "Autodesk" / "ApplicationPlugins" / "Raen.Navisworks.Pynet.bundle" / "manage.ico")

sys.path.append(str(bundlePath))

clr.AddReference("Raen.Core.Pynet.Resources")

from Raen.Core.Pynet.Resources import CastUtils  # type: ignore

from Autodesk.Navisworks.Api import Application
from Autodesk.Navisworks.Api.Clash import DocumentClash

#endregion


sys.path.append(str(Path.home() / "AppData" / "Roaming" / "Pynet" / "Library" / "01_Scripts" / "00_utils"))
from pynet_clash import get_clash_tests


class ClashDataResult:
    """
    Extracts and stores clash status counts (New, Active, Reviewed, Approved, Resolved)
    from a single Navisworks Clash Test.
    """

    def __init__(self, test):
        self.testName = test.DisplayName
        self.tolerance = test.Tolerance
        self.status = test.Status
        self.lastRun = test.LastRun
        self.new = 0
        self.active = 0
        self.reviewed = 0
        self.approved = 0
        self.resolved = 0

        results = []
        for child in test.Children:
            if child.IsGroup:
                results.extend(child.Children)
            else:
                results.append(child)

        for children in results:
            if str(children.Status).upper() == str(ClashResultStatus.New).upper():
                self.new += 1
            if str(children.Status).upper() == str(ClashResultStatus.Active).upper():
                self.active += 1
            if str(children.Status).upper() == str(ClashResultStatus.Reviewed).upper():
                self.reviewed += 1
            if str(children.Status).upper() == str(ClashResultStatus.Approved).upper():
                self.approved += 1
            if str(children.Status).upper() == str(ClashResultStatus.Resolved).upper():
                self.resolved += 1


class DataManager:
    """
    Extracts clash test data from the active Navisworks document using CastUtils.
    """

    @staticmethod
    def ExtractClashData(document):
        clashDocument = CastUtils.CastTo[DocumentClash](document.Clash)
        tests = get_clash_tests(clashDocument)
        return [ClashDataResult(test) for test in tests]


class ChartManager:
    """
    Renders a stacked bar chart of clash statuses per subdiscipline using matplotlib.
    """

    @staticmethod
    def ExtractSubdiscipline(name):
        if pd.isna(name):
            return ""
        name = re.sub(r"^[^_]+_", "", name)
        name = re.sub(r"_[A-Z]+$", "", name)
        return name.strip()

    @staticmethod
    def ShowStackBars(data):
        df = pd.DataFrame([clash.__dict__ for clash in data])

        df["left"] = df["testName"].str.split("_vs_").str[0]
        df["left"] = df["left"].str.replace(r"^[ABC]_", "", regex=True)
        df["right"] = df["testName"].str.split("_vs_").str[1]

        df["left"] = df["left"].apply(ChartManager.ExtractSubdiscipline)
        df["right"] = df["right"].apply(ChartManager.ExtractSubdiscipline)

        types = ["new", "active", "reviewed"]
        stacked_df = pd.DataFrame()

        for t in types:
            temp_df = pd.concat([
                df[["left", t]].rename(columns={"left": "subdiscipline"}),
                df[["right", t]].rename(columns={"right": "subdiscipline"})
            ]).groupby("subdiscipline").sum()
            stacked_df[t] = temp_df[t]

        stacked_df["total"] = stacked_df.sum(axis=1)
        stacked_df = stacked_df.sort_values("total", ascending=False)
        stacked_df = stacked_df.drop(columns="total")

        stacked_df = stacked_df[stacked_df.sum(axis=1) > 0]

        colors = {"new": "#FF1200", "active": "#FFC500", "reviewed": "#00C4FF"}

        plt.figure(figsize=(10, 5), num="Clashes to Resolve")
        bottom = pd.Series([0]*len(stacked_df), index=stacked_df.index)

        for t in types:
            plt.bar(
                stacked_df.index,
                stacked_df[t],
                bottom=bottom,
                color=colors[t],
                label=t.capitalize()
            )
            bottom += stacked_df[t]

        totals = stacked_df.sum(axis=1)
        for i, total in enumerate(totals):
            plt.text(
                i,
                total + 0.5,
                str(total),
                ha="center",
                va="bottom",
                fontsize=10,
                fontweight="bold"
            )

        plt.ylabel("Clashes to resolve")
        plt.xlabel("Subdiscipline")
        plt.xticks(rotation=45, ha="right")
        plt.ylim(0, totals.max() * 1.1)
        plt.legend()
        plt.tight_layout()
        plt.show()


class FeatureManager:
    """
    Entry point for generating a stacked bar chart of clashes by subdiscipline.
    """

    @staticmethod
    def Run(document):
        data = DataManager.ExtractClashData(document)
        ChartManager.ShowStackBars(data)


# Entry point
doc = Application.ActiveDocument
FeatureManager.Run(doc)
