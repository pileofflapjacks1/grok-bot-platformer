# GrokBotPlatformer

Scaffolded GB Studio platformer for the ModRetro Chromatic.

## Docs
- `docs/CHARACTER_SELECTION.md` — Shape + color selection flow
- `docs/LEVEL1_SCRIPTS.md` — Exact event sequences for the first playable level
- `docs/ROADMAP.md` — 9 levels + Shadow Grok boss
- `docs/PLATFORMER_PLUS.md` — Jump feel recommendations
- `docs/HARDWARE_CHECKLIST.md` — GBC / Chromatic limits
- `FIRST_LEVEL_GUIDE.md` — Original overview
- `SKILL.md` — grok-chromatic-agent skill

## Play Level 1
Open `GrokBotPlatformer.gbsproj` in GB Studio 4.2 or newer and press Play.

Level 1 – Green Hills is a short platform scene:

- Pink Grok Bot with idle, walk, and jump frames. Left facing is mirrored.
- One Waddle Blob. Stomp it to bounce. Touching it from the side knocks you back.
- Three stars. The exit on the right opens after `powerups` reaches 3.
- Two pits respawn you at the start.
- Clearing the exit loads a small “Level 1 clear!” scene.

Jump feel is set in `project/engine_field_values.gbsres`: jump velocity 3.5, a slightly lower hold-gravity, coyote time, and jump buffering. See `docs/PLATFORMER_PLUS.md`.

The background uses 3 unique tiles. On screen you have the player, one enemy, and up to three stars.

`python3 scripts/build_level1.py` regenerates the level art, scenes, and those settings. It does not remove the GB Studio template fonts or UI.

Fonts, the dialogue frame, emotes, and the placeholder `actor*.png` sprites come from the GB Studio blank project template (Chris Maltby, MIT).

## Assets
Level 1 sheets are in `assets/sprites/`:

- `player_pink.png`
- `enemy_red_blob.png`
- `collectible_star.png`

Shape and color variants from `docs/CHARACTER_SELECTION.md` are not in the project yet.

## Next Steps
1. Play Level 1 in GB Studio and tune the jump if the arcs feel wrong.
2. Add the shape and color select flow from `docs/CHARACTER_SELECTION.md`.
3. Build Level 2 from `docs/ROADMAP.md`.
4. Audit with `docs/HARDWARE_CHECKLIST.md` before the scenes get bigger.

Generated with the grok-chromatic-agent skill.
