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
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")

from System.Windows.Forms import SaveFileDialog, DialogResult, MessageBox, MessageBoxButtons, MessageBoxIcon

bundlePath = (Path.home()/ "AppData"/ "Roaming"/ "Autodesk"/ "ApplicationPlugins"/ "RAEN.Navisworks.PyNET.bundle"/ "Contents"/ "2024")
NavisworksinconPath = (Path.home() / "AppData" / "Roaming" / "Autodesk" / "ApplicationPlugins" / "Raen.Navisworks.Pynet.bundle" / "manage.ico")

sys.path.append(str(bundlePath))

clr.AddReference("Raen.Core.Pynet.Resources")

from Raen.Core.Pynet.Resources import CastUtils  # type: ignore

from Autodesk.Navisworks.Api import Application 
doc = Application.ActiveDocument

#endregion


sys.path.append(str(Path.home() / "AppData" / "Roaming" / "Pynet" / "Library" / "01_Scripts" / "00_utils"))
from pynet_clash import get_clash_tests


class ClashDataResult():
    """
    Wrapper class used to extract, normalize and store information from
    a Navisworks Clash Test. Computes each clash status count (New, Active,
    Reviewed, Approved, Resolved) and exposes clean read-only properties
    for export or UI consumption.
    """
    def __init__(self, test):
        self.testName: str = test.DisplayName
        self.tolerance: float = test.Tolerance
        self.status: str = test.Status
        self.lastRun: str = test.LastRun
        self.new: int = 0
        self.active: int = 0
        self.reviewed: int = 0
        self.approved: int = 0
        self.resolved: int = 0

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

    @property
    def Name(self):
        """Returns the Clash Test display name."""
        return self.testName

    @property
    def Tolerance(self):
        """Returns the test clash tolerance."""
        return self.tolerance

    @property
    def Status(self):
        """Returns the overall status of the clash test."""
        return self.status

    @property
    def LastRun(self):
        """Returns the last execution date/time of the clash test."""
        return self.lastRun

    @property
    def NewCount(self):
        """Returns the number of NEW clash results."""
        return self.new

    @property
    def ActiveCount(self):
        """Returns the number of ACTIVE clash results."""
        return self.active

    @property
    def ReviewedCount(self):
        """Returns the number of REVIEWED clash results."""
        return self.reviewed

    @property
    def ApprovedCount(self):
        """Returns the number of APPROVED clash results."""
        return self.approved

    @property
    def ResolvedCount(self):
        """Returns the number of RESOLVED clash results."""
        return self.resolved



class DataManager():
    """
    High-level controller to manage the export of the data
    to CSV format using Pandas.
    """
        
    @staticmethod
    def ExportData(data, path):
        """
        Take the properties from the object to convert them to a dictionary.
        Export the dictionary to CSV.
        """
        df = pd.DataFrame([clash.__dict__ for clash in data])
        df.to_csv(path, index=False)
    @staticmethod
    def AnalyzeDataBar(data):
        df = pd.DataFrame([clash.__dict__ for clash in data])
        df["clashes"] = df["active"] + df["new"] + df["reviewed"]

        df["left"] = df["testName"].str.split("_vs_").str[0]
        df["left"] = df["left"].str.replace(r"^[ABC]_", "", regex=True)
        df["right"] = df["testName"].str.split("_vs_").str[1]

        def extract_subdiscipline(name: str) -> str:
            name = re.sub(r"^[^_]+_", "", name)
            name = re.sub(r"_[A-Z]+$", "", name)
            return name.strip()

        df["left"] = df["left"].apply(extract_subdiscipline)
        df["right"] = df["right"].apply(extract_subdiscipline)

        left_df = df[["left", "clashes"]].rename(columns={"left": "subdiscipline"})
        right_df = df[["right", "clashes"]].rename(columns={"right": "subdiscipline"})

        long_df = pd.concat([left_df, right_df])

        result = (
            long_df
            .groupby("subdiscipline")["clashes"]
            .sum()
            .sort_values(ascending=False)
        )

        result = result[result > 0]

        plt.figure(figsize=(10, 5), num="Clashes to Resolve")
        colors = plt.cm.tab20(range(len(result)))

        bars = plt.bar(result.index, result.values, color=colors)
        plt.ylabel("Clashes to resolve")
        plt.xlabel("Subdiscipline")
        plt.xticks(rotation=45, ha="right")

        plt.ylim(0, result.max() * 1.1)

        for bar in bars:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                height,
                f"{int(height)}",
                ha="center",
                va="bottom"
            )

        plt.tight_layout()
        plt.show()
    @staticmethod
    def AnalizeStackBars(data):
        df = pd.DataFrame([clash.__dict__ for clash in data])

        df["left"] = df["testName"].str.split(" vs ").str[0]
        df["left"] = df["left"].str.replace(r"^[ABC]_", "", regex=True)
        df["right"] = df["testName"].str.split(" vs ").str[1]

        def extract_subdiscipline(name: str) -> str:
            if pd.isna(name):
                return ""
            name = re.sub(r"^[^_]+_", "", name)
            name = re.sub(r"_[A-Z]+$", "", name)
            return name.strip()

        df["left"] = df["left"].apply(extract_subdiscipline)
        df["right"] = df["right"].apply(extract_subdiscipline)

        types = ["new", "active", "reviewed", "approved"]
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

        colors = {"new": "#FF1200", "active": "#FFC500", "reviewed": "#00C4FF", "approved": "#00FF00"}

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
        plt.ylim(0, totals.max() * 1.5) 
        plt.legend()
        plt.tight_layout()
        plt.show()


class ModelManager():
    """
    High-level controller for exporting clash test results.
    Reads all tests from the active document, processes them using
    ClashDataResult, writes them to the CSV log and displays a
    confirmation dialog.
    """

    @staticmethod
    def ExportResults(document):
        """
        Extracts all clash tests from the supplied Navisworks document
        and exports them to a timestamped CSV file on the desktop.
        """
        clashDocument = CastUtils.CastTo[DocumentClash](document.Clash)

        tests = get_clash_tests(clashDocument)

        path = DialogManager.ShowSaveFileDialog()

        if path != None:
            
            data = [ClashDataResult(test) for test in tests]

            DataManager.ExportData(data, path)

            DialogManager.DataExportedDialog()

            DataManager.AnalizeStackBars(data)



class DialogManager:
    @staticmethod
    def ShowSaveFileDialog():
        saveDialog = SaveFileDialog()
        saveDialog.Title = "Save Clashes File"
        saveDialog.InitialDirectory = str(Path.home() / "Desktop")
        saveDialog.Filter = "Csv files (*.csv)|*.csv|All files (*.*)|*.*"
        saveDialog.DefaultExt = "csv"
        saveDialog.AddExtension = True
        saveDialog.OverwritePrompt = True

        if saveDialog.ShowDialog() == DialogResult.OK:
            return saveDialog.FileName

        return None
    @staticmethod
    def DataExportedDialog():
        MessageBox.Show("Data exported correctly", "Data Extraction", MessageBoxButtons.OK, MessageBoxIcon.Information)

ModelManager.ExportResults(doc)

#endregion
