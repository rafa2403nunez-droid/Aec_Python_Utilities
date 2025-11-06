#region references

import clr
import sys

sys.path.append("C:\\Program Files (x86)\\IronPython 2.7\\Lib")
import os

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import *

clr.AddReference("Autodesk.Navisworks.ComApi")
from Autodesk.Navisworks.Api.ComApi import *

clr.AddReference("Autodesk.Navisworks.Interop.ComApi")
from Autodesk.Navisworks.Api.Interop.ComApi import *

from System.Collections.Generic import List

#Import Windows form
clr.AddReference("System.Windows.Forms")
# Import System Drawing
clr.AddReference("System.Drawing")

from System.Windows.Forms import*
from System.Drawing import*

from datetime import datetime

doc = __navisworks__ #type:ignore

class ModelManagement():
    @staticmethod
    def GetModelsList(document):
        models = document.Models.GetEnumerator()
        names = [model.FileName for model in models]
        MessageBox.Show("\n".join(names))
    @staticmethod
    def OpenFile(path, document, useTry):
        if useTry:
            document.TryOpenFile(path)
        else:
            document.OpenFile(path)
    @staticmethod
    def AppendFiles(document, filePaths, useTry):
        if useTry:
            document.TryAppendFiles(List[str](filePaths))
        else:
            document.AppendFiles(List[str](filePaths))
    @staticmethod
    def PublishModel(document, path):
        properties = PublishProperties() #type:ignore

        properties.AllowResave = True
        properties.Author = ""
        properties.Comments = ""
        properties.Copyright = ""
        properties.DisplayAtPassword = True
        properties.DisplayOnOpen = True
        properties.EmbedDatabaseProperties = True
        properties.EmbedTextures = True
        properties.ExpiryDate = ""
        properties.Keywords = ""
        properties.PreventObjectPropertyExport = False
        properties.PublishDate = datetime.now()
        properties.PublishedFor = ""
        properties.Publisher = ""
        properties.Subject = ""
        properties.Title = ""
        properties.SetPassword("Password")

        document.PublishFile(path, properties)

#endregion