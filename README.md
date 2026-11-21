# og-content

Live content for every OG Software app: avatars, emotes, the gold rules, store prices and the victory / defeat /
credits headlines. Apps download it at startup, so changes here reach players **without a new app build**.
This repository is public on purpose: the apps read it from
`https://raw.githubusercontent.com/owengerig/og-content/main/`. Never put anything private here.

Apps never wait for it: they show their built-in copy first and apply downloaded content in the background.
If a phone is offline, nothing breaks.

## What's here

| File | What it controls | Used by |
|---|---|---|
| `versions.json` | The version of every manifest below. The one file apps fetch on every launch; when it matches what they already have, they stop and download nothing else. Written by the workflow: don't edit. | all apps |
| `manifest.json` | The **shared** content's version and a hash of every shared file (everything outside `games/`). | all apps |
| `cosmetics.json` | **Universal** cosmetics: every avatar and emote, its name, rarity and image. `rarity: "default"` = free for everyone; `common` / `rare` / `epic` / `mythic` = sold in every app's store. | all apps |
| `avatars/*.png` | Avatar images, 256×256, round, transparent corners | all apps |
| `emotes/*.png` | Emote images, 256×256, transparent | all apps |
| `economy.json` | The gold formula and store prices (100 gold per active minute, 15-minute cap, loss 0.5×, online 2×, prices 2,000 / 4,000 / 8,000 / 16,000) | games |
| `themes.json` | **Monthly color themes**: four colors per month (`primary`, `secondary`, `frame`, `ambient`) plus a `default`. Every app picks the month from the device date. Preview: `docs/themes-preview.png` | all apps |
| `headlines.json` | Random headlines on the victory screen (`wins`), defeat screen (`losses`) and credits screen (`credits`) | games |
| `games/<game>/manifest.json` | That game's **own version** and a hash of each of its files | that game only |
| `games/<game>/store.json` | **Game-specific** store items (2D Clash gear, NATO Squad planes and add-ons, Card Combat packs): rarity (which sets the price), optional `price` override, optional `hidden` | that game only |
| `games/<game>/floaters/*.png` | That game's white menu-background shape (cube, jet, card, map, golf ball, book), tinted by the app | that game only |

Game folders: `2d-clash`, `nato-squad`, `card-combat`, `borderline`, `pintally`, `storyhub` (each app's `gameId`).
An app only ever downloads the shared files and its own game folder; anything that only one game uses belongs in
that game's folder. A new game needs just a new folder (with at least a `store.json`).

## How apps download it

1. Fetch `versions.json` (a few hundred bytes). If the shared version and this game's version match the copies
   cached on the device, stop: nothing else is downloaded.
2. Otherwise fetch only the manifest whose version changed (`manifest.json` and/or `games/<game>/manifest.json`).
3. Download only the files in it whose hash changed, and cache them.

A failed download keeps the old cached manifest, so it's retried next launch. Offline, the cached (or built-in) copy
is used.

## Making changes

- **Add an avatar or emote**: add the PNG under `avatars/` or `emotes/` and an entry in `cosmetics.json`
  (`id`, `name`, `rarity`, `file`). It appears in every app's profile picker (free) or store (paid).
- **Change prices or gold**: edit `economy.json`.
- **Price, rename or hide a game's item**: edit `games/<game>/store.json`.
- Push to `main`. The **Build manifest** workflow updates the manifests and `versions.json`, bumping the patch version
  of each manifest whose files changed (1.0.3 → 1.0.4). A change in `games/card-combat/` bumps only Card Combat's
  version. For a bigger release, set `"version"` in that manifest yourself (e.g. `1.1.0`) and commit; later changes
  count up from it.
- Removing an avatar someone already uses: players who picked it fall back to the first free avatar, so prefer
  changing its rarity over deleting it.

## Color themes

Each month has four colors, stored as `#RRGGBB` hex, the one format Unity, Android, iOS, web, PC and Xbox all read.
Every color also has an `id` (lowercase, hyphens) and a display `name`.

| Role | Used for |
|---|---|
| `primary` | main menu buttons other than PLAY, the selected tab, popup header bars |
| `secondary` | the STORE button, round buttons, carousel arrows, unselected tabs |
| `frame` | outlines of panels, cards, boxes and popups |
| `ambient` | a subtle tint over every menu background, the horizon glow, floating shapes, sparkles |

Never themed (they carry meaning): PLAY / confirm green, back / cancel red, currency gold, rarity colors.
Text color is never stored: apps pick white or dark ink for each surface, whichever contrasts more.

**Changing a month**: edit its names / hex values in `themes.json`, then run `python3 tools/themes.py assign`. It
picks which color takes which role and checks:
- text on buttons reaches 4.5:1; buttons stand out from the dark panels (1.6:1) and from each other;
- buttons don't look like the PLAY green, back red or currency gold, also for protan, deutan and tritan color
  blindness;
- outlines reach 3:1 against the panel.

If a month can't pass, it says why; nudge the shade (keep the name; an `adjustedFrom` field remembers the original).
`python3 tools/themes.py preview docs/themes-preview.png` redraws the preview. The **Build manifest** workflow runs the
check on every push, and the apps run it again before using a theme, falling back to `default` if it fails.

## Versions

Every main menu's bottom-right corner shows `content <shared version> · game <game version>`, e.g.
`content 1.1.0 · game 1.0.3`: the versions in `manifest.json` and `games/<game>/manifest.json`. The kit's own version (project-default) shows bottom-left after the app version.
