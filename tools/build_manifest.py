#!/usr/bin/env python3
"""Rebuilds the manifests: lists of content files with their hashes, plus a version.

There is one manifest for the shared content and one per game, so each app reads only what it uses:

  versions.json                 every manifest's version: the first (and usually only) file apps fetch
  manifest.json                 shared files (cosmetics, economy, headlines, themes, avatars/, emotes/)
  games/<game>/manifest.json    that game's files (store.json, floaters/, item sets, ...)

Apps download the shared manifest and their own game's manifest, then only the files whose hash changed.
Each manifest's version goes up by one patch number when one of its files changed (1.0.3 -> 1.0.4), so a change
to one game's files doesn't change any other game's version. To start a new minor or major version, edit
"version" in that manifest by hand (e.g. 1.1.0); it is kept, and later changes count up from it.

  python3 tools/build_manifest.py          # also run automatically by .github/workflows/manifest.yml on every push
"""
import hashlib, json, os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SKIP_DIRS = {".git", ".github", "tools", "docs"}
EXTS = (".json", ".png")


def walk(top, skip_games):
    for d, dirs, names in os.walk(top):
        if skip_games and os.path.normpath(d) == ROOT:
            dirs[:] = [x for x in dirs if x != "games"]
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS and not x.startswith("."))
        for n in sorted(names):
            if n in ("manifest.json", "versions.json") and os.path.normpath(d) == os.path.normpath(top):
                continue
            if n.endswith(EXTS):
                p = os.path.join(d, n)
                yield os.path.relpath(p, ROOT).replace(os.sep, "/"), p


def build(manifest_path, files):
    """Writes manifest_path if its files changed and returns its version. Paths in it are relative to the repo root."""
    old = json.load(open(manifest_path)) if os.path.exists(manifest_path) else None
    entries = []
    for rel, p in files:
        if rel.endswith(".json"):
            json.load(open(p))  # fail loudly on broken JSON
        entries.append({"path": rel, "sha": hashlib.sha1(open(p, "rb").read()).hexdigest()})
    name = os.path.relpath(manifest_path, ROOT).replace(os.sep, "/")
    if old is not None and entries == old.get("files"):
        print(f"{name}: no changes; version stays {old['version']}")
        return old["version"]
    if old is None or not old.get("files"):
        version = (old or {}).get("version") or "1.0.0"
        if version == "0.0.0":
            version = "1.0.0"
    else:
        major, minor, patch = (int(x) for x in old["version"].split("."))
        version = f"{major}.{minor}.{patch + 1}"
    with open(manifest_path, "w", newline="\n") as f:
        json.dump({"version": version, "files": entries}, f, indent=2)
        f.write("\n")
    print(f"{name}: version {version}, {len(entries)} files")
    return version


def main():
    versions = {"shared": build(os.path.join(ROOT, "manifest.json"), walk(ROOT, skip_games=True)), "games": {}}
    games = os.path.join(ROOT, "games")
    for g in sorted(os.listdir(games)):
        d = os.path.join(games, g)
        if os.path.isdir(d):
            versions["games"][g] = build(os.path.join(d, "manifest.json"), walk(d, skip_games=False))
    # versions.json: the one tiny file apps check first. When the versions they have cached match it, they stop
    # there and download nothing else.
    with open(os.path.join(ROOT, "versions.json"), "w", newline="\n") as f:
        json.dump(versions, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
