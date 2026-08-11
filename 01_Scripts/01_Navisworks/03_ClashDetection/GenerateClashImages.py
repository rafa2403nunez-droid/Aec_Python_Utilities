# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

#region references
import clr
import sys
from pathlib import Path
from datetime import datetime

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import Application, ImageGenerationStyle

clr.AddReference("Autodesk.Navisworks.Clash")
from Autodesk.Navisworks.Api.Clash import DocumentClash
clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import MessageBox, MessageBoxButtons, MessageBoxIcon

bundlePath = (Path.home() / "AppData" / "Roaming" / "Autodesk" / "ApplicationPlugins" / "RAEN.Navisworks.PyNET.bundle" / "Contents" / "2024")
sys.path.append(str(bundlePath))

clr.AddReference("Raen.Core.Pynet.Resources")
from Raen.Core.Pynet.Resources import CastUtils  # type: ignore

from Autodesk.Navisworks.Api import Application
doc = Application.ActiveDocument

#endregion


sys.path.append(str(Path.home() / "AppData" / "Roaming" / "Pynet" / "Library" / "01_Scripts" / "00_utils"))
from pynet_clash import get_clash_tests


class ClashImageExporter:
    IMAGE_WIDTH = 800
    IMAGE_HEIGHT = 600
    # ImageGenerationStyle values: Scene | ScenePlusOverlay | SceneUsingRayTrace
    IMAGE_STYLE = ImageGenerationStyle.ScenePlusOverlay

    # Only generate images for clashes with these statuses (empty = all statuses)
    TARGET_STATUSES = {"Reviewed"}

    @staticmethod
    def GetOutputFolder(document):
        date_str = datetime.now().strftime("%Y%m%d")
        doc_name = Path(document.FileName).stem if document.FileName else "Unknown"
        folder = (
            Path.home()
            / "AppData" / "Roaming" / "Pynet" / "Navisworks"
            / f"{date_str}_{doc_name}"
        )
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    @staticmethod
    def Export(document):
        clashDoc = CastUtils.CastTo[DocumentClash](document.Clash)
        testsData = clashDoc.TestsData
        save_dir = ClashImageExporter.GetOutputFolder(document)

        print(f"Output folder: {save_dir}")

        clash_index = 1
        saved = 0
        skipped = 0
        for test in get_clash_tests(clashDoc):
            for r in test.Children:
                status = str(r.Status)
                if ClashImageExporter.TARGET_STATUSES and status not in ClashImageExporter.TARGET_STATUSES:
                    skipped += 1
                    clash_index += 1
                    continue
                try:
                    bmp = testsData.TestsImageForResult(
                        r,
                        ClashImageExporter.IMAGE_STYLE,
                        ClashImageExporter.IMAGE_WIDTH,
                        ClashImageExporter.IMAGE_HEIGHT
                    )
                    test_name = test.DisplayName.replace(" ", "_")
                    img_path = save_dir / f"clash_{clash_index:02d}_{test_name}.png"
                    bmp.Save(str(img_path))
                    print(f"  [{clash_index:02d}] {test.DisplayName} ({status}) → saved")
                    saved += 1
                except Exception as e:
                    print(f"  [{clash_index:02d}] {test.DisplayName} → ERROR: {e}")
                clash_index += 1

        print(f"\nDone: {saved} images saved, {skipped} skipped.")
        return save_dir, saved


class DialogManager:
    @staticmethod
    def ShowCompletion(save_dir, count):
        MessageBox.Show(
            f"{count} clash image(s) saved to:\n{save_dir}",
            "Clash Images",
            MessageBoxButtons.OK,
            MessageBoxIcon.Information
        )


# Entry point
save_dir, count = ClashImageExporter.Export(doc)
DialogManager.ShowCompletion(save_dir, count)

#endregion
