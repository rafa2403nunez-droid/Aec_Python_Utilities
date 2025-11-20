#region references

import clr
import sys

sys.path.append("C:\\Program Files (x86)\\IronPython 2.7\\Lib")
import os

clr.AddReference("System.Xml")
from System.Xml import *  #type:ignore

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

from System.Windows.Forms import *
from System.Drawing import *

from datetime import datetime

doc = __navisworks__  #type:ignore
selectionSets = doc.SelectionSets

#endregion


class ClashResultData():
    """
    Data container for clash results imported from the XML file.
    Stores the clash test name, the result GUID, the new status 
    (Approved/Reviewed) and optional comments associated with the result.
    """
    def __init__(self, testName, guid, status, comment):
        self.testName = testName
        self.guid = guid
        self.status = status
        self.comment = comment

    @property
    def TestName(self):
        """Returns the name of the clash test where the result belongs."""
        return self.testName

    @property
    def Guid(self):
        """Returns the GUID of the clash result."""
        return self.guid

    @property
    def Status(self):
        """Returns the updated status for the clash result."""
        return self.status

    @property
    def Comment(self):
        """Returns the collection of comments attached to the clash result."""
        return self.comment



class DialogManager():
    """
    Helper class to manage user interface dialogs such as file selection
    and confirmation messages after data import and update.
    """
    @staticmethod
    def ShowOpenFileDialog():
        """
        Displays a file dialog to allow the user to select the XML file
        containing the clash results to import.
        
        Returns:
            str: Full path of the selected XML file, or None if cancelled.
        """
        with OpenFileDialog() as openDialog:
            openDialog.InitialDirectory = os.path.join(os.path.expanduser('~'), 'Desktop')
            openDialog.Filter = "xml files (*.xml)|*.xml|All files (*.*)|*.*"
            if openDialog.ShowDialog() == DialogResult.OK:
                return openDialog.FileName

    @staticmethod
    def DataImportedDialog():
        """
        Displays a confirmation dialog indicating that clash results 
        were successfully updated to Approved or Reviewed.
        """
        MessageBox.Show(
            "Clash results updated, status changed to approved or reviewed",
            "Update Clash Results",
            MessageBoxButtons.OK,
            MessageBoxIcon.Information
        )



# Store results extracted from XML
dataResults = []

xmlDocument = XmlDocument()  #type:ignore
xmlDocument.Load(DialogManager.ShowOpenFileDialog())

clashTestNodes = xmlDocument.SelectNodes("//clashtests/clashtest")
if clashTestNodes != None:

    for clashTestNode in clashTestNodes:
        clashTestName = clashTestNode.Attributes["name"].Value

        clashResultNodes = clashTestNode.SelectNodes(
            "clashresults/clashresult[@status='approved' or @status='reviewed']"
        )

        if clashResultNodes != None:
            for clashResultNode in clashResultNodes:

                if clashResultNode.SelectNodes("comments/comment/body") != None:
                    comments = CommentCollection()  #type:ignore

                    for node in clashResultNode.SelectNodes("comments/comment/body"):
                        comments.Add(Comment(node.InnerText, CommentStatus.New))  #type:ignore

                    clashResult = ClashResultData(
                        clashTestName,
                        clashResultNode.Attributes["guid"].Value,
                        clashResultNode.Attributes["status"].Value,
                        comments
                    )
                else:
                    clashResult = ClashResultData(
                        clashTestName,
                        clashResultNode.Attributes["guid"].Value,
                        clashResultNode.Attributes["status"].Value,
                        None
                    )

                dataResults.append(clashResult)



documentClash = doc.Clash.TestsData
tests = doc.Clash.TestsData.Tests

# Apply imported updates to the Navisworks clash tests
for test in tests:
    for data in dataResults:
        if data.TestName == test.DisplayName:
            for children in test.Children:

                if str(children.Guid) == data.Guid and str(children.Status).upper() != data.Status.upper():

                    # Add comments if present
                    if data.Comment != None:
                        documentClash.TestsEditResultComments(children, data.Comment)

                    # Apply new status
                    if data.Status.upper() == str(ClashResultStatus.Approved).upper():
                        documentClash.TestsEditResultStatus(children, ClashResultStatus.Approved)

                    elif data.Status.upper() == str(ClashResultStatus.Reviewed).upper():
                        documentClash.TestsEditResultStatus(children, ClashResultStatus.Reviewed)



# Confirmation dialog
DialogManager.DataImportedDialog()
