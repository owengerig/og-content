#!/usr/bin/env python3
"""Monthly color themes: picks each color's role and checks contrast. Run on every push (CI) and by hand.

  python3 tools/themes.py check       validate themes.json (exit 1 on any failure)
  python3 tools/themes.py assign      (re)choose roles for each month from its four colors, then check
  python3 tools/themes.py preview OUT write a preview PNG of every month (needs rsvg-convert)

Colors are stored as "#RRGGBB" hex, the one format Unity, Android, iOS, web, PC and Xbox builds all read.
Text color is never stored: apps pick white or ink (#14121C) per surface, whichever contrasts more.

Roles:
  primary    main menu buttons (loadout), tabs (selected), popup headers, selected carousel ring
  secondary  STORE button, round buttons, carousel arrows, unselected tabs
  frame      outlines of panels, cards, boxes and popups
  ambient    subtle tint over every menu background, horizon glow, floating shapes, sparkles

Rules (a theme that breaks one is rejected, and apps fall back to the default theme):
  1. primary and secondary: white or ink text on them reaches 4.5:1
  2. primary and secondary stand out from the dark panel behind them (>= 1.6:1) and from each other (dE >= 25)
  3. primary and secondary don't look like the fixed PLAY green, back red or currency gold (dE >= 20),
     also for the common color-blind types (protan, deutan, tritan simulation, dE >= 12)
  4. frame reaches 3:1 against the dark panel it outlines
"""
import itertools, json, math, os, subprocess, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PATH = os.path.join(ROOT, "themes.json")
WHITE, INK, PANEL = "#FFFFFF", "#14121C", "#1E1A38"
FIXED = {"PLAY green": "#43C53A", "back red": "#D62F3A", "currency gold": "#FFB820"}
ROLES = ["primary", "secondary", "frame", "ambient"]


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lum(h):
    r, g, b = (lin(c) for c in rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def best_text(h):
    return WHITE if contrast(h, WHITE) >= contrast(h, INK) else INK


def lab_from_lin(r, g, b):
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


# Machado et al. 2009 simulation matrices (severity 1.0), applied in linear RGB
CVD = {
    "protan": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    "deutan": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    "tritan": [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
}


def lab(h, cvd=None):
    c = [lin(v) for v in rgb(h)]
    if cvd:
        m = CVD[cvd]
        c = [max(0.0, min(1.0, sum(m[i][j] * c[j] for j in range(3)))) for i in range(3)]
    return lab_from_lin(*c)


def de(a, b, cvd=None):
    return math.dist(lab(a, cvd), lab(b, cvd))


def problems(t):
    """Every rule the theme breaks, as readable lines."""
    c = {r: t[r]["hex"] for r in ROLES}
    out = []
    for r in ("primary", "secondary"):
        if contrast(c[r], best_text(c[r])) < 4.5:
            out.append(f"{r} {t[r]['name']}: text contrast {contrast(c[r], best_text(c[r])):.2f} < 4.5")
        if contrast(c[r], PANEL) < 1.6:
            out.append(f"{r} {t[r]['name']}: too close to the dark panel ({contrast(c[r], PANEL):.2f} < 1.6)")
        for fname, fhex in FIXED.items():
            if de(c[r], fhex) < 20:
                out.append(f"{r} {t[r]['name']} looks like the {fname} (dE {de(c[r], fhex):.0f} < 20)")
            for v in CVD:
                if de(c[r], fhex, v) < 12:
                    out.append(f"{r} {t[r]['name']} looks like the {fname} with {v} color blindness (dE {de(c[r], fhex, v):.0f})")
    if de(c["primary"], c["secondary"]) < 25:
        out.append(f"primary and secondary look alike (dE {de(c['primary'], c['secondary']):.0f} < 25)")
    for v in CVD:
        if de(c["primary"], c["secondary"], v) < 12:
            out.append(f"primary and secondary look alike with {v} color blindness")
    if contrast(c["frame"], PANEL) < 3:
        out.append(f"frame {t['frame']['name']}: outline contrast {contrast(c['frame'], PANEL):.2f} < 3 against the panel")
    return out


def score(t):
    c = {r: t[r]["hex"] for r in ROLES}
    return (min(contrast(c[r], best_text(c[r])) for r in ("primary", "secondary"))
            + de(c["primary"], c["secondary"]) / 20
            + min(de(c[r], f) for r in ("primary", "secondary") for f in FIXED.values()) / 20
            + contrast(c["frame"], PANEL) / 3)


def assign(colors):
    """Best role assignment for four colors; (theme, problems)."""
    best = None
    for perm in itertools.permutations(colors):
        t = dict(zip(ROLES, perm))
        p = problems(t)
        key = (len(p), -score(t))
        if best is None or key < best[0]:
            best = (key, t, p)
    return best[1], best[2]


def load():
    return json.load(open(PATH))


def save(d):
    with open(PATH, "w", newline="\n") as f:
        json.dump(d, f, indent=2, ensure_ascii=True)
        f.write("\n")


def check(d):
    bad = 0
    themes = [("default", d["default"])] + [(m["month"], m) for m in d["months"]] + [("app " + a["app"], a) for a in d.get("apps", [])]
    for key, t in themes:
        for r in ROLES:
            h = t[r]["hex"]
            assert len(h) == 7 and h[0] == "#" and all(ch in "0123456789ABCDEF" for ch in h[1:]), f"{key} {r}: hex must be #RRGGBB uppercase, got {h}"
        for p in problems(t):
            print(f"[{key}] {p}")
            bad += 1
    print("themes OK" if not bad else f"{bad} problem(s)")
    return bad == 0


def preview(d, out):
    rows = [("default", d["default"])] + [(m["label"], m) for m in d["months"]]
    W, H = 1200, 110 * len(rows) + 20
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="{PANEL}"/>']
    for i, (label, t) in enumerate(rows):
        y = 20 + i * 110
        s.append(f'<rect x="20" y="{y}" width="{W-40}" height="96" rx="14" fill="{t["ambient"]["hex"]}" fill-opacity="0.25" stroke="{t["frame"]["hex"]}" stroke-width="4"/>')
        s.append(f'<text x="40" y="{y+56}" font-family="DejaVu Sans" font-weight="bold" font-size="24" fill="#FFFFFF">{label}</text>')
        x = 230
        for r, w in (("primary", 260), ("secondary", 260)):
            h = t[r]["hex"]
            s.append(f'<rect x="{x}" y="{y+18}" width="{w}" height="60" rx="18" fill="{h}" stroke="#000" stroke-opacity="0.5" stroke-width="3"/>')
            s.append(f'<text x="{x+w/2}" y="{y+56}" text-anchor="middle" font-family="DejaVu Sans" font-weight="bold" font-size="20" fill="{best_text(h)}">{t[r]["name"].upper()}</text>')
            x += w + 16
        s.append(f'<rect x="{x}" y="{y+18}" width="150" height="60" rx="18" fill="#43C53A" stroke="#000" stroke-opacity="0.5" stroke-width="3"/><text x="{x+75}" y="{y+56}" text-anchor="middle" font-family="DejaVu Sans" font-weight="bold" font-size="20" fill="#FFFFFF">PLAY</text>')
        x += 166
        s.append(f'<text x="{x}" y="{y+42}" font-family="DejaVu Sans" font-size="16" fill="#FFFFFF">frame: {t["frame"]["name"]}</text>')
        s.append(f'<text x="{x}" y="{y+68}" font-family="DejaVu Sans" font-size="16" fill="#FFFFFF">ambient: {t["ambient"]["name"]}</text>')
    s.append("</svg>")
    svg = out[:-4] + ".svg"
    open(svg, "w").write("".join(s))
    subprocess.run(["rsvg-convert", "-o", out, svg], check=True)
    os.remove(svg)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    d = load()
    if cmd == "assign":
        for m in d["months"]:
            colors = [m[r] for r in ROLES]
            t, p = assign(colors)
            for r in ROLES:
                m[r] = t[r]
            for line in p:
                print(f"[{m['month']}] {line}")
        save(d)
        sys.exit(0 if check(d) else 1)
    if cmd == "preview":
        preview(d, sys.argv[2])
        sys.exit(0)
    sys.exit(0 if check(d) else 1)
