# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

"""
Build the stub lookup index.

The stub files are huge (a single namespace can be 160k lines), which makes them
unreadable in one go. Splitting them per class would mean 11k files and would break
`from Autodesk.Revit.DB import Wall` for Pylance -- the files are what Pylance reads.

So instead of cutting the corpus up, this makes it addressable: an index that maps
each class to its exact line range, so a lookup is one grep over ~1 MB followed by a
read of the 16-140 lines that class actually occupies.

Runs standalone with local CPython -- no Autodesk host, no MCP bridge. Run it after
GenerateStubs.py, which is what produces the stubs themselves.

    python 01_Scripts/00_utils/IndexStubs.py

Writes into 02_PyNet Stubs/_index/:
    CLASSES.tsv   class -> namespace, file, start, end, base, member count
    STATS.md      corpus summary, per-namespace counts

There is deliberately no member-level index. Searching for a method or property is
already a grep over the stubs themselves, which reports the file and line; a second
copy of all 118k members would cost 14 MB to answer a question the corpus answers
for free. The index only carries what grepping cannot cheaply produce: a class's
exact line range, and the namespace that disambiguates a repeated class name.
"""

import re
import sys
from pathlib import Path

# Repo root, resolved from this file so the script travels with the repo.
ROOT = Path(__file__).resolve().parents[2]
STUBS = ROOT / "02_PyNet Stubs"
OUT = STUBS / "_index"

CLASS_RE = re.compile(r"^class\s+(\w+)\s*(?:\(([^)]*)\))?\s*:")
DEF_RE = re.compile(r"^    def\s+(\w+)\s*\((.*?)\)\s*->\s*(.+?):")
PROP_RE = re.compile(r"^    (\w+):\s*(.+)$")
STATIC_RE = re.compile(r"^    @staticmethod")


def namespace_of(rel: Path) -> str:
    """Reverse of the generator's namespace -> path mapping."""
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts.pop()
    else:
        parts[-1] = rel.stem
    return ".".join(parts)


def scan(path: Path, rel: Path):
    """Yield (class_name, base, start, end, members) for one stub file."""
    lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
    starts = []
    for i, ln in enumerate(lines):
        m = CLASS_RE.match(ln)
        if m:
            starts.append((i, m.group(1), (m.group(2) or "").strip()))

    for idx, (i, name, base) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        members = []
        was_static = False
        for j in range(i + 1, end):
            ln = lines[j]
            if STATIC_RE.match(ln):
                was_static = True
                continue
            dm = DEF_RE.match(ln)
            if dm:
                mname, args, ret = dm.groups()
                if mname != "__init__":
                    kind = "static" if was_static else "method"
                    members.append((mname, kind, f"({args}) -> {ret}", j + 1))
                was_static = False
                continue
            pm = PROP_RE.match(ln)
            if pm and not ln.lstrip().startswith(("@", '"')):
                members.append((pm.group(1), "prop", pm.group(2).strip(), j + 1))
            was_static = False
        # Lines are 1-based for the Read tool's offset parameter.
        yield name, base, i + 1, end, members


def main():
    if not STUBS.is_dir():
        print(f"Stub folder not found: {STUBS}")
        return 1

    classes, members, per_ns = [], [], {}
    for path in sorted(STUBS.rglob("*.py")):
        rel = path.relative_to(STUBS)
        if rel.parts[0] == "_index":
            continue
        ns = namespace_of(rel)
        posix = rel.as_posix()
        n = 0
        for name, base, start, end, mem in scan(path, rel):
            classes.append((name, ns, posix, start, end, base, len(mem)))
            for mname, kind, sig, line in mem:
                members.append((mname, f"{ns}.{name}", kind, sig, posix, line))
            n += 1
        if n:
            per_ns[ns] = n

    OUT.mkdir(parents=True, exist_ok=True)

    with (OUT / "CLASSES.tsv").open("w", encoding="utf-8", newline="\n") as f:
        f.write("class\tnamespace\tfile\tstart\tend\tbase\tmembers\n")
        for row in sorted(classes):
            f.write("\t".join(str(x) for x in row) + "\n")

    dupes = {}
    for name, ns, *_ in classes:
        dupes.setdefault(name, []).append(ns)
    collide = {k: v for k, v in dupes.items() if len(v) > 1}

    corpus = sum(p.stat().st_size for p in STUBS.rglob("*.py")
                 if p.relative_to(STUBS).parts[0] != "_index")
    idx_size = sum(p.stat().st_size for p in OUT.glob("*.tsv"))

    with (OUT / "STATS.md").open("w", encoding="utf-8", newline="\n") as f:
        f.write("<!-- SPDX-License-Identifier: MIT -->\n")
        f.write("<!-- Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform -->\n\n")
        f.write("# Stub corpus\n\n")
        f.write("Generated by `01_Scripts/00_utils/IndexStubs.py`. Do not edit by hand.\n\n")
        f.write(f"- Classes: **{len(classes):,}** across **{len(per_ns)}** namespaces\n")
        f.write(f"- Members behind them: **{len(members):,}** (not indexed on purpose — grep the stubs)\n")
        f.write(f"- Corpus: **{corpus/1048576:.1f} MB** | index: **{idx_size/1048576:.1f} MB**\n")
        f.write(f"- Class names used in more than one namespace: **{len(collide)}** "
                f"(always match on the `namespace` column, never on the name alone)\n\n")
        f.write("## Classes per namespace\n\n")
        f.write("| Namespace | Classes |\n| :--- | ---: |\n")
        for ns, n in sorted(per_ns.items(), key=lambda kv: -kv[1]):
            f.write(f"| `{ns}` | {n:,} |\n")

    print(f"classes : {len(classes):,}")
    print(f"members : {len(members):,}")
    print(f"corpus  : {corpus/1048576:.1f} MB")
    print(f"index   : {idx_size/1048576:.1f} MB")
    print(f"collisions: {len(collide)}")
    print(f"written -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
