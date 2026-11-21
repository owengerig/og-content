#!/usr/bin/env python3
"""Checks every item set in games/<game>/sets/*.json before it reaches players (run by the Build manifest workflow).

Every set: id (matches the file name), name, order, items. Every item: a unique id (across all of a game's sets;
ids are saved in players' inventories, so never rename or reuse one), a name, a rarity (common, rare, epic,
mythic) and #RRGGBB colors. Then the game's own rules:

  2d-clash     category weapon / armor / relic, a base the game can draw (BASES below), stats, armor material,
               mythic items are elemental (fire / ice / poison, level 1-4)
  nato-squad   category plane (model drawn from the set's "models", gun pattern, stats) or addon (slot + kind,
               stats and/or weapon)

  python3 tools/check_sets.py
"""
import json, os, re, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RARITIES = {"common", "rare", "epic", "mythic"}
HEX = re.compile(r"^#[0-9A-F]{6}$")

CLASH_BASES = {
    "weapon": {"StoneAxe", "StoneClub", "FlintSpear", "FlintKnife", "CopperAxe", "CopperDagger", "CopperMace",
               "CopperHalberd", "CopperSpear"},
    "armor": {"ChestArmor", "Coif", "Pilos", "Hachigane", "PhrygianHelmet", "TurbanHelmet"},
    "relic": {"Circlet", "RoyalCrown", "SpikedCrown", "ImperialCrown", "Figurine", "CaveTablet", "BoneFlute", "Amulet",
              "Idol", "CopperIngot", "Totem"},
}
CLASH_MATERIALS = {"cloth", "hide", "fur"}
CLASH_STATS = {"health", "strength", "agility", "defense", "crit"}
ELEMENTS = {"fire", "ice", "poison"}

NATO_GUNS = {"spread", "stream", "forwardAndDown"}
NATO_PLANE_STATS = {"damage", "fireInterval", "hull", "speed", "regen"}
NATO_KINDS = {"firepower": "gun", "bombs": "payload", "missiles": "payload", "drone": "support", "warthog": "support"}
NATO_ADDON_STATS = {"damage", "fireRate", "crit"}
NATO_OPS = {"poly", "ellipse", "rect", "line"}


def check_clash(it, err):
    cat = it.get("category")
    if cat not in CLASH_BASES:
        return err(f"category must be weapon, armor or relic (got {cat!r})")
    if it.get("base") not in CLASH_BASES[cat]:
        err(f"base {it.get('base')!r} can't be drawn as a {cat}; use one of {sorted(CLASH_BASES[cat])}")
    if cat == "armor" and it.get("material") not in CLASH_MATERIALS:
        err(f"armor needs material {sorted(CLASH_MATERIALS)}")
    for c in ("color", "accent"):
        if c in it and not HEX.match(str(it[c])):
            err(f"{c} must be #RRGGBB (uppercase)")
    if "color" not in it:
        err("needs a color")
    stats = it.get("stats", {})
    if not stats or set(stats) - CLASH_STATS or any(not isinstance(v, (int, float)) or v < 0 for v in stats.values()):
        err(f"stats must be non-negative numbers from {sorted(CLASH_STATS)}")
    el = it.get("element", "none")
    if el != "none":
        if el not in ELEMENTS:
            err(f"element must be none, fire, ice or poison")
        if not 1 <= it.get("elementLevel", 0) <= 4:
            err("elementLevel must be 1-4")
    if it.get("rarity") == "mythic" and el == "none":
        err("mythic items are always elemental")


def check_nato(it, err, models):
    cat = it.get("category")
    if cat == "plane":
        if it.get("model") not in models:
            err(f"model {it.get('model')!r} isn't in this set's models")
        if it.get("gun") not in NATO_GUNS:
            err(f"gun must be one of {sorted(NATO_GUNS)}")
        st = it.get("stats", {})
        if set(st) != NATO_PLANE_STATS or any(not isinstance(v, (int, float)) or v <= 0 for v in st.values()):
            err(f"plane stats must be positive numbers for exactly {sorted(NATO_PLANE_STATS)}")
        cols = it.get("colors", {})
        if not all(HEX.match(str(cols.get(k, ""))) for k in ("body", "accent")):
            err("colors.body and colors.accent must be #RRGGBB")
    elif cat == "addon":
        kind = it.get("kind")
        if kind not in NATO_KINDS:
            return err(f"kind must be one of {sorted(NATO_KINDS)}")
        if it.get("slot") != NATO_KINDS[kind]:
            err(f"a {kind} add-on goes in the {NATO_KINDS[kind]} slot")
        st = it.get("stats", {})
        if set(st) - NATO_ADDON_STATS:
            err(f"add-on stats can only be {sorted(NATO_ADDON_STATS)}")
        w = it.get("weapon")
        if kind == "firepower" and not st:
            err("a firepower add-on needs stats")
        if kind != "firepower":
            if not w or w.get("damage", 0) <= 0 or w.get("interval", 0) <= 0:
                err("needs weapon.damage and weapon.interval (> 0)")
            if kind in ("bombs", "missiles") and not 1 <= w.get("count", 0) <= 8:
                err("bombs and missiles need weapon.count 1-8")
        if not HEX.match(str(it.get("color", ""))):
            err("color must be #RRGGBB")
    else:
        err(f"category must be plane or addon (got {cat!r})")


def main():
    problems = []
    games = os.path.join(ROOT, "games")
    for game in sorted(os.listdir(games)):
        folder = os.path.join(games, game, "sets")
        if not os.path.isdir(folder):
            continue
        seen = {}
        for f in sorted(os.listdir(folder)):
            if not f.endswith(".json"):
                continue
            path = f"games/{game}/sets/{f}"
            try:
                s = json.load(open(os.path.join(folder, f), encoding="utf-8"))
            except Exception as e:
                problems.append(f"{path}: not valid JSON ({e})")
                continue
            def err(msg, item=None):
                problems.append(f"{path}{' ' + item if item else ''}: {msg}")
            if s.get("id") != f[:-5]:
                err(f"id must match the file name ({f[:-5]})")
            for k in ("name", "order", "items"):
                if k not in s:
                    err(f"missing {k}")
            models = s.get("models", {})
            for name, m in models.items():
                if not isinstance(m.get("w"), int) or not isinstance(m.get("h"), int) or not m.get("ops"):
                    err(f"model {name} needs w, h and ops")
                for op in m.get("ops", []):
                    if not op or op[0] not in NATO_OPS:
                        err(f"model {name}: unknown op {op[:1]}")
            for it in s.get("items", []):
                iid = it.get("id", "?")
                e = lambda msg, iid=iid: err(msg, iid)
                if not re.match(r"^[a-z0-9-]+$", iid):
                    e("id must be lowercase letters, digits and hyphens")
                if iid in seen:
                    e(f"duplicate id (also in {seen[iid]})")
                seen[iid] = f
                if not it.get("name"):
                    e("needs a name")
                if it.get("rarity") not in RARITIES:
                    e(f"rarity must be one of {sorted(RARITIES)}")
                if game == "2d-clash":
                    check_clash(it, e)
                elif game == "nato-squad":
                    check_nato(it, e, models)
        print(f"{game}: {len(seen)} items checked")
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print("all item sets OK")


if __name__ == "__main__":
    main()
