# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr
from pathlib import Path

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

app = __revit__.Application #type:ignore
doc = __revit__.ActiveUIDocument.Document #type:ignore


class EditecaSharedParamCreator:

    PARAMS = [
        # (pset, name, type_key, is_type, dim)
        ("PyNET_3D", "PyNET_3D_Clasificacion",       "TEXT",    True,  "3D"),
        ("PyNET_3D", "PyNET_3D_CodigoTipo",           "TEXT",    True,  "3D"),
        ("PyNET_3D", "PyNET_3D_Descripcion",          "TEXT",    True,  "3D"),
        ("PyNET_3D", "PyNET_3D_Disciplina",           "TEXT",    True,  "3D"),
        ("PyNET_4D", "PyNET_4D_Fase",                 "TEXT",    False, "4D"),
        ("PyNET_4D", "PyNET_4D_CodigoRecurso",        "TEXT",    True, "4D"),
        ("PyNET_4D", "PyNET_4D_FechaInicioPrevista",  "TEXT",    False, "4D"),
        ("PyNET_4D", "PyNET_4D_FechaFinPrevista",     "TEXT",    False, "4D"),
        ("PyNET_4D", "PyNET_4D_Duracion",             "INTEGER", False, "4D"),
        ("PyNET_4D", "PyNET_4D_CodigoObra",           "TEXT",    False, "4D"),
        ("PyNET_5D", "PyNET_5D_CodigoRecurso",        "TEXT",    True,  "5D"),
        ("PyNET_5D", "PyNET_5D_CapituloPresupuesto",  "TEXT",    True,  "5D"),
        ("PyNET_5D", "PyNET_5D_CosteUnitario",        "NUMBER",  True,  "5D"),
        ("PyNET_5D", "PyNET_5D_Proveedor",            "TEXT",    True,  "5D"),
    ]

    BICS_ALL = [
        BuiltInCategory.OST_Walls, BuiltInCategory.OST_Floors, BuiltInCategory.OST_Roofs,
        BuiltInCategory.OST_Ceilings, BuiltInCategory.OST_Doors, BuiltInCategory.OST_Windows,
        BuiltInCategory.OST_Stairs, BuiltInCategory.OST_Ramps, BuiltInCategory.OST_StairsRailing,
        BuiltInCategory.OST_Casework, BuiltInCategory.OST_Furniture,
        BuiltInCategory.OST_CurtainWallPanels, BuiltInCategory.OST_CurtainWallMullions,
        BuiltInCategory.OST_Rooms,
        BuiltInCategory.OST_StructuralColumns, BuiltInCategory.OST_StructuralFraming,
        BuiltInCategory.OST_StructuralFoundation, BuiltInCategory.OST_Rebar,
        BuiltInCategory.OST_DuctCurves, BuiltInCategory.OST_FlexDuctCurves,
        BuiltInCategory.OST_DuctFitting, BuiltInCategory.OST_DuctAccessory,
        BuiltInCategory.OST_DuctTerminal,
        BuiltInCategory.OST_PipeCurves, BuiltInCategory.OST_FlexPipeCurves,
        BuiltInCategory.OST_PipeFitting, BuiltInCategory.OST_PipeAccessory,
        BuiltInCategory.OST_MechanicalEquipment, BuiltInCategory.OST_ElectricalEquipment,
        BuiltInCategory.OST_LightingFixtures, BuiltInCategory.OST_PlumbingFixtures,
        BuiltInCategory.OST_ElectricalFixtures, BuiltInCategory.OST_Sprinklers,
        BuiltInCategory.OST_CableTray,
        BuiltInCategory.OST_Topography, BuiltInCategory.OST_Site,
    ]

    BICS_PROVEEDOR = [
        BuiltInCategory.OST_DuctCurves, BuiltInCategory.OST_FlexDuctCurves,
        BuiltInCategory.OST_DuctFitting, BuiltInCategory.OST_DuctAccessory,
        BuiltInCategory.OST_DuctTerminal,
        BuiltInCategory.OST_PipeCurves, BuiltInCategory.OST_FlexPipeCurves,
        BuiltInCategory.OST_PipeFitting, BuiltInCategory.OST_PipeAccessory,
        BuiltInCategory.OST_MechanicalEquipment, BuiltInCategory.OST_ElectricalEquipment,
        BuiltInCategory.OST_LightingFixtures, BuiltInCategory.OST_PlumbingFixtures,
        BuiltInCategory.OST_ElectricalFixtures, BuiltInCategory.OST_Sprinklers,
        BuiltInCategory.OST_CableTray,
        BuiltInCategory.OST_Furniture,
    ]

    @staticmethod
    def get_spec_map():
        try:
            return {
                "TEXT":    SpecTypeId.String.Text,
                "INTEGER": SpecTypeId.Int.Integer,
                "NUMBER":  SpecTypeId.Number,
            }
        except:
            return {
                "TEXT":    ParameterType.Text, #type:ignore Old API
                "INTEGER": ParameterType.Integer, #type:ignore Old API
                "NUMBER":  ParameterType.Number, #type:ignore Old API
            }

    @staticmethod
    def get_param_group(dim):
        try:
            return {"3D": GroupTypeId.IdentityData,
                    "4D": GroupTypeId.Phasing,
                    "5D": GroupTypeId.Data}[dim]
        except:
            return {"3D": BuiltInParameterGroup.PG_IDENTITY_DATA, #type:ignore Old API
                    "4D": BuiltInParameterGroup.PG_PHASING, #type:ignore Old API
                    "5D": BuiltInParameterGroup.PG_DATA}[dim] #type:ignore Old API

    @staticmethod
    def build_cat_set(bics):
        cat_set = app.Create.NewCategorySet()
        for bic in bics:
            try:
                cat = doc.Settings.Categories.get_Item(bic)
                if cat is not None and cat.AllowsBoundParameters:
                    cat_set.Insert(cat)
            except:
                pass
        return cat_set

    @staticmethod
    def create_shared_param_file():
        sp_dir = Path.home() / "AppData" / "Roaming" / "Pynet" / "Revit"
        sp_dir.mkdir(parents=True, exist_ok=True)
        sp_path = str(sp_dir / "PyNET_SharedParameters.txt")
        with open(sp_path, "w", encoding="utf-8") as f:
            f.write("# This is a Revit shared parameter file.\n# Do not edit manually.\n")
        app.SharedParametersFilename = sp_path
        return app.OpenSharedParameterFile(), sp_path

    @staticmethod
    def create_definitions(def_file, spec_map):
        groups      = {}
        definitions = {}
        for pset, name, type_key, is_type, dim in EditecaSharedParamCreator.PARAMS:
            if pset not in groups:
                grp = next((g for g in def_file.Groups if g.Name == pset), None)
                groups[pset] = grp or def_file.Groups.Create(pset)
            opts = ExternalDefinitionCreationOptions(name, spec_map[type_key])
            opts.UserModifiable = True
            opts.Visible = True
            definitions[name] = groups[pset].Definitions.Create(opts)
        return definitions

    @staticmethod
    def bind_to_categories(definitions):
        bmap        = doc.ParameterBindings
        cat_set_all = EditecaSharedParamCreator.build_cat_set(EditecaSharedParamCreator.BICS_ALL)
        cat_set_prv = EditecaSharedParamCreator.build_cat_set(EditecaSharedParamCreator.BICS_PROVEEDOR)
        ok = 0

        for pset, name, type_key, is_type, dim in EditecaSharedParamCreator.PARAMS:
            defn    = definitions[name]
            cat_set = cat_set_prv if name == "PyNET_5D_Proveedor" else cat_set_all
            binding = app.Create.NewTypeBinding(cat_set) if is_type else app.Create.NewInstanceBinding(cat_set)
            pg      = EditecaSharedParamCreator.get_param_group(dim)
            try:
                if bmap.Contains(defn):
                    bmap.ReInsert(defn, binding, pg)
                else:
                    bmap.Insert(defn, binding, pg)
                ok += 1
            except:
                pass

        return ok

    @staticmethod
    def Run():
        spec_map = EditecaSharedParamCreator.get_spec_map()

        def_file, sp_path = EditecaSharedParamCreator.create_shared_param_file()
        print(f"Fichero creado: {sp_path}")

        definitions = EditecaSharedParamCreator.create_definitions(def_file, spec_map)
        print(f"Parametros compartidos creados: {len(definitions)}")

        t = Transaction(doc, "Editeca - Crear parametros de proyecto")
        t.Start()
        try:
            ok = EditecaSharedParamCreator.bind_to_categories(definitions)
            t.Commit()
            print(f"Parametros de proyecto vinculados: {ok}/{len(definitions)}")
        except Exception as e:
            t.RollBack()
            raise


EditecaSharedParamCreator.Run()
