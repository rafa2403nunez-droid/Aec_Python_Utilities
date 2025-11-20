#region references

import clr
import sys

sys.path.append("C:\\Program Files (x86)\\IronPython 2.7\\Lib")
import os
import json

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import *

clr.AddReference("Autodesk.Navisworks.ComApi")
from Autodesk.Navisworks.Api.ComApi import *

clr.AddReference("Autodesk.Navisworks.Interop.ComApi")
from Autodesk.Navisworks.Api.Interop.ComApi import *

clr.AddReference("Autodesk.Navisworks.Clash")
from Autodesk.Navisworks.Api.Clash import *

from System.Collections.Generic import List

clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")

from System.Windows.Forms import*
from System.Drawing import*

sys.path.append(os.path.join(os.path.expanduser('~'),
    "AppData\\Roaming\\Autodesk\\ApplicationPlugins\\RNM.Navisworks.Balio.bundle\\Contents\\{version}".format(version = 2023)))

from datetime import date, datetime

doc = __navisworks__ #type:ignore

#endregion


class ClashDataResult():
    """
    Wrapper class used to extract, normalize and store information from
    a Navisworks Clash Test. Computes each clash status count (New, Active,
    Reviewed, Approved, Resolved) and exposes clean read-only properties
    for export or UI consumption.
    """
    def __init__(self, test):
        self.testName = test.DisplayName
        self.tolerance = test.Tolerance
        self.status = test.Status
        self.lastRun = test.LastRun
        self.new = self.active = self.reviewed = self.approved = self.resolved = 0

        for children in test.Children:
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



class DataLog():
    """
    Manages creation and writing of CSV log files for exported clash data.
    Generates a file per export session and appends formatted rows for
    each Clash Test, including all status counts and metadata.
    """

    def OpenClashLog(self):
        """Opens the clash log file in append mode."""
        return open(self.clashLogPath ,"a")

    def OpenModelLog(self):
        """Opens the model log file in append mode."""
        return open(self.modelLogPath ,"a")

    def WriteClashLog(self, test):
        """
        Appends a formatted line to the clash log representing a single
        test result, including status counts and test metadata.
        """
        log = self.OpenClashLog()
        log.write("{line}{name}{tab}{status}{tab}{tolerance}{tab}{lastRun}{tab}{new}{tab}{active}{tab}{reviewed}{tab}{approved}{tab}{resolved}".format(
            line="\n", tab="\t",
            name=test.Name, status=str(test.Status),
            tolerance=str(test.Tolerance), lastRun=str(test.LastRun),
            new=str(test.NewCount), active=str(test.ActiveCount),
            reviewed=str(test.ReviewedCount), approved=str(test.ApprovedCount),
            resolved=str(test.ResolvedCount)))
        log.close()

    def WriteModelLog(self, model):
        """Writes a single model entry to the model export log."""
        log = self.OpenModelLog()
        log.write("{line}{name}".format(line="\n", name=model.FileName))
        log.close()

    def __init__(self, path):
        """
        Creates a new log file for clash data export. The file is stored
        using today's date and initialized with the header row.
        """
        if path:
            self.clashLogPath = "{browser}/ClashtestData_{date}.csv".format(
                browser=path, date=str(date.today()))

            log = open(self.clashLogPath,"w")
            log.write("ClashTest\tStatus\tTolerance\tLastRun\tNew\tActive\tReviewed\tApproved\tResolved")
            log.close()



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
        folder = os.path.join(os.path.expanduser("~"), "Desktop")
        tests = document.Clash.TestsData.Tests
        log = DataLog(folder)

        for test in tests:
            log.WriteClashLog(ClashDataResult(test))

        DialogManager.DataExportedDialog()



class DialogManager():
    """
    Handles all user dialogs and notifications displayed during script
    execution. Currently used to confirm successful exports.
    """

    @staticmethod
    def DataExportedDialog():
        """Displays a confirmation message when data is exported correctly."""
        MessageBox.Show("Clash Test Exported Correctly",
                        "Navisworks API",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Information)



ModelManager.ExportResults(doc)

#endregion
