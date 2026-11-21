#!/usr/bin/env python3
"""Rebuilds manifest.json: the list of every content file with its hash, plus og-content's version.

Apps download manifest.json first and then only the files whose hash changed.
The version goes up by one patch number whenever any file changed (1.0.3 -> 1.0.4); to start a new minor or
major version, edit "version" in manifest.json by hand and commit (it is kept as long as it is higher).

  python3 tools/build_manifest.py          # also run automatically by .github/workflows/manifest.yml on every push
"""
import hashlib, json, os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SKIP_DIRS = {".git", ".github", "tools", "docs"}


def files():
    for d, dirs, names in os.walk(ROOT):
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS and not x.startswith("."))
        for n in sorted(names):
            if n == "manifest.json" and d == ROOT:
                continue
            if n.endswith((".json", ".png")):
                p = os.path.join(d, n)
                yield os.path.relpath(p, ROOT).replace(os.sep, "/"), p


def main():
    path = os.path.join(ROOT, "manifest.json")
    old = json.load(open(path)) if os.path.exists(path) else {"version": "0.0.0", "files": []}
    entries = [{"path": rel, "sha": hashlib.sha1(open(p, "rb").read()).hexdigest()} for rel, p in files()]
    for e in entries:
        if e["path"].endswith(".json"):
            json.load(open(os.path.join(ROOT, e["path"])))  # fail loudly on broken JSON
    if entries == old.get("files"):
        print("no changes; version stays", old["version"])
        return
    major, minor, patch = (int(x) for x in old.get("version", "0.0.0").split("."))
    version = f"{major}.{minor}.{patch + 1}" if old.get("files") else old.get("version", "1.0.0")
    with open(path, "w", newline="\n") as f:
        json.dump({"version": version, "files": entries}, f, indent=2)
        f.write("\n")
    print("manifest", version, "with", len(entries), "files")


if __name__ == "__main__":
    main()
