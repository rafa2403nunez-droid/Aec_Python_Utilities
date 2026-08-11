# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

app = __revit__.Application  #type:ignore


class AutodeskUserLoginScript:
    @staticmethod
    def Run(app):
        try:
            is_logged_in = app.IsLoggedIn
        except Exception:
            # Older Revit API — check via LoginUserId
            is_logged_in = bool(app.LoginUserId)

        if is_logged_in:
            user_id = app.LoginUserId
            print(f"Logged in as: {user_id}")
        else:
            print("User not logged in. Sign in to Autodesk to obtain the user ID.")

        return app.LoginUserId if is_logged_in else None


AutodeskUserLoginScript.Run(app)
