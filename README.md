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
| `manifest.json` | og-content's **version** and a hash of every file. Apps fetch this first and download only what changed. Shown in the corner of every main menu as `content <version>`. | all apps |
| `cosmetics.json` | **Universal** cosmetics: every avatar and emote, its name, rarity and image. `rarity: "default"` = free for everyone; `common` / `rare` / `epic` / `mythic` = sold in every app's store. | all apps |
| `avatars/*.png` | Avatar images, 256×256, round, transparent corners | all apps |
| `emotes/*.png` | Emote images, 256×256, transparent | all apps |
| `floaters/*.png` | White menu-background shapes (cube, jet, map, golf ball, card, book), tinted by each app | all apps |
| `economy.json` | The gold formula and store prices (100 gold per active minute, 15-minute cap, loss 0.5×, online 2×, prices 2,000 / 4,000 / 8,000 / 16,000) | games |
| `headlines.json` | Random headlines on the victory screen (`wins`), defeat screen (`losses`) and credits screen (`credits`) | games |
| `games/<game>/store.json` | **Game-specific** store items (2D Clash gear, NATO Squad planes and add-ons, Card Combat packs): rarity (which sets the price), optional `price` override, optional `hidden` | that game only |

Game folders: `2d-clash`, `nato-squad`, `card-combat`, `borderline`, `pintally`, `storyhub` (each app's `gameId`).

## Making changes

- **Add an avatar or emote**: add the PNG under `avatars/` or `emotes/` and an entry in `cosmetics.json`
  (`id`, `name`, `rarity`, `file`). It appears in every app's profile picker (free) or store (paid).
- **Change prices or gold**: edit `economy.json`.
- **Price, rename or hide a game's item**: edit `games/<game>/store.json`.
- Push to `main`. The **Build manifest** workflow updates `manifest.json` and bumps the version
  (1.0.3 → 1.0.4). For a bigger release, set `"version"` in `manifest.json` yourself (e.g. `1.1.0`) in the same commit.
- Removing an avatar someone already uses: players who picked it fall back to the first free avatar, so prefer
  changing its rarity over deleting it.

## Versions

`manifest.json` → `"version"` is og-content's version. It shows in every app's main menu (bottom-right corner,
small text). The kit's own version (project-default) shows bottom-left after the app version.
