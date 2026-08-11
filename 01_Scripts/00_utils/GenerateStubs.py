# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr
from pathlib import Path
from collections import defaultdict
from System import AppDomain
from System.Reflection import BindingFlags  # type:ignore

PYTHON_KEYWORDS = {
    'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
    'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
    'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
    'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try',
    'while', 'with', 'yield',
}

def safe_name(name):
    if not name:
        return "value_"
    return name + "_" if name in PYTHON_KEYWORDS else name

# ── Host detection ─────────────────────────────────────────────────────────────
try:
    _revit = __revit__  # type:ignore
    HOST = "Revit"
    VERSION = _revit.Application.VersionNumber
except NameError:
    # Try Civil 3D before Navisworks
    try:
        clr.AddReference("AeccDbMgd")
        from Autodesk.Civil.ApplicationServices import CivilApplication as _CivilApp
        _civil_doc = _CivilApp.ActiveDocument
        HOST = "Civil"
        try:
            clr.AddReference("AcMgd")
            from Autodesk.AutoCAD.ApplicationServices import Application as _AcadApp
            VERSION = _AcadApp.Version.Major
        except Exception:
            VERSION = "unknown"
    except Exception:
        HOST = "Navisworks"
        try:
            clr.AddReference("Autodesk.Navisworks.Api")
            from Autodesk.Navisworks.Api import Application as _NavApp
            VERSION = str(_NavApp.Version.RuntimeMajor)
        except Exception:
            VERSION = "unknown"

print(f"Host: {HOST} {VERSION}")

# ── Assembly lists per host ────────────────────────────────────────────────────
ASSEMBLY_SETS = {
    "Navisworks": [
        "Autodesk.Navisworks.Api",
        "Autodesk.Navisworks.ComApi",
        "Autodesk.Navisworks.Interop.ComApi",
        "Autodesk.Navisworks.Clash",
    ],
    "Revit": [
        "RevitAPI",
        "RevitAPIUI",
    ],
    "Civil": [
        "AcMgd",
        "AcCoreMgd",
        "AcDbMgd",
        "AecBaseMgd",
        "AeccDbMgd",
    ],
}

ASSEMBLIES = ASSEMBLY_SETS.get(HOST, ASSEMBLY_SETS["Navisworks"])

# ── Output: repo stubs folder (committed to GitHub) ───────────────────────────
# Cleans only the Autodesk\<Host> subtree so Navisworks and Revit stubs coexist.
STUBS_ROOT = Path.home() / "source" / "repos" / "GithubRNM" / "PyNetLibrary" / "02_PyNet Stubs"
STUBS_ROOT.mkdir(parents=True, exist_ok=True)

# Host root inside Autodesk\ (e.g. Autodesk\Revit or Autodesk\Navisworks)
HOST_NS_ROOT = {
    "Revit":     "Revit",
    "Navisworks": "Navisworks",
    "Civil":     "Civil3D",
}
HOST_AUTODESK_DIR = STUBS_ROOT / "Autodesk" / HOST_NS_ROOT.get(HOST, HOST)

print(f"Stubs root:  {STUBS_ROOT}")
print(f"Cleaning:    {HOST_AUTODESK_DIR}\n")

# ── Clean only the host subtree ────────────────────────────────────────────────
def remove_tree(p: Path):
    if p.is_dir():
        for child in p.iterdir():
            remove_tree(child)
        p.rmdir()
    elif p.exists():
        p.unlink()

if HOST_AUTODESK_DIR.exists():
    remove_tree(HOST_AUTODESK_DIR)

# ── Type map ───────────────────────────────────────────────────────────────────
TYPE_MAP = {
    "String": "str",   "Boolean": "bool",
    "Int32": "int",    "Int64": "int",   "UInt32": "int",  "UInt64": "int",
    "Int16": "int",    "UInt16": "int",  "Byte": "int",    "SByte": "int",
    "Double": "float", "Single": "float",
    "Char": "str",     "Void": "None",   "Object": "object",
}

def map_type(t):
    try:
        if t.IsArray:
            return "list"
        if t.IsByRef or t.IsPointer:
            return map_type(t.GetElementType())
        name = t.Name.split("`")[0]
        return TYPE_MAP.get(name, name)
    except Exception:
        return "object"

# ── Code generators ────────────────────────────────────────────────────────────
def gen_methods(methods, declaring_type):
    grouped = defaultdict(list)
    for m in methods:
        if m.IsSpecialName or m.DeclaringType != declaring_type:
            continue
        grouped[m.Name].append(m)

    lines = []
    for name, overloads in sorted(grouped.items()):
        try:
            safe_method = safe_name(name)
            best = max(overloads, key=lambda m: len(m.GetParameters()))
            params = [f"{safe_name(p.Name)}: {map_type(p.ParameterType)}" for p in best.GetParameters()]
            ret = map_type(best.ReturnType)
            if best.IsStatic:
                lines.append(f"    @staticmethod")
                lines.append(f"    def {safe_method}({', '.join(params)}) -> {ret}: ...")
            else:
                lines.append(f"    def {safe_method}(self, {', '.join(params)}) -> {ret}: ...")
        except Exception:
            continue
    return lines

def gen_class(t):
    try:
        if not t.IsPublic:
            return None
        name = t.Name.split("`")[0]
        bases = []
        if t.BaseType and t.BaseType.FullName not in (
                "System.Object", "System.ValueType",
                "System.Enum", "System.MulticastDelegate"):
            bases.append(map_type(t.BaseType))
        base_str = f"({', '.join(bases)})" if bases else ""

        flags = (BindingFlags.Public | BindingFlags.Instance |
                 BindingFlags.Static | BindingFlags.DeclaredOnly)

        body = [
            f'class {name}{base_str}:',
            f'    """.NET: {t.FullName}"""',
            f'    def __init__(self, *args) -> None: ...',
        ]
        for p in t.GetProperties():
            try:
                body.append(f"    {p.Name}: {map_type(p.PropertyType)}")
            except Exception:
                continue
        body.extend(gen_methods(t.GetMethods(flags), t))
        if len(body) == 3:
            body.append("    ...")
        return "\n".join(body)
    except Exception:
        return None

# ── Namespace → relative file path ────────────────────────────────────────────
def ns_to_relpath(ns: str, all_ns: set) -> Path:
    parts = ns.split(".")
    has_children = any(n.startswith(ns + ".") for n in all_ns if n != ns)
    if has_children:
        return Path(*parts) / "__init__.py"
    return Path(*parts[:-1]) / f"{parts[-1]}.py"

def ensure_inits(file_path: Path, root: Path):
    current = file_path.parent
    while current != root and current != current.parent:
        init = current / "__init__.py"
        if not init.exists():
            init.write_text("# auto-generated\n", encoding="utf-8")
        current = current.parent

# ── Load assemblies ────────────────────────────────────────────────────────────
for asm_name in ASSEMBLIES:
    try:
        clr.AddReference(asm_name)
        print(f"  Loaded: {asm_name}")
    except Exception as e:
        print(f"  SKIP:   {asm_name} — {e}")

loaded = {a.GetName().Name.lower(): a for a in AppDomain.CurrentDomain.GetAssemblies()}

# ── Collect types by namespace ─────────────────────────────────────────────────
ns_types: dict = defaultdict(list)
for asm_name in ASSEMBLIES:
    asm = loaded.get(asm_name.lower())
    if asm is None:
        continue
    try:
        for t in asm.GetTypes():
            try:
                if t.IsPublic and t.Namespace:
                    ns_types[t.Namespace].append(t)
            except Exception:
                continue
    except Exception as e:
        print(f"  ERROR reading {asm_name}: {e}")

all_ns = set(ns_types.keys())
print(f"\nNamespaces: {len(all_ns)}")

# ── Write stub files ───────────────────────────────────────────────────────────
written = errors = 0
for ns, types in sorted(ns_types.items()):
    try:
        rel = ns_to_relpath(ns, all_ns)
        out = STUBS_ROOT / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        ensure_inits(out, STUBS_ROOT)

        lines = [f"# Auto-generated — {HOST} {VERSION} — {ns}", ""]
        for t in sorted(types, key=lambda x: x.Name):
            code = gen_class(t)
            if code:
                lines.append(code)
                lines.append("")

        out.write_text("\n".join(lines), encoding="utf-8")
        written += 1
    except Exception as e:
        print(f"  ERROR {ns}: {e}")
        errors += 1

print(f"\nDone: {written} files written, {errors} errors.")
print(f"Location: {STUBS_ROOT}")
