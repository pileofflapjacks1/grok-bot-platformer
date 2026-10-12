# Sprites

GB Studio reads every `.png` in this folder. The Level 1 sheets below are 16x16, 8x16 sprite mode, with a transparent background and three opaque colors.

| File | Use |
|------|-----|
| player_pink.png | Grok Bot, right-facing. Four frames: idle, walk A, walk B, jump. Left facing is mirrored. |
| enemy_red_blob.png | Waddle Blob |
| collectible_star.png | Power-up star |

`actor.png`, `actor_animated.png`, and `static.png` are the GB Studio blank-template placeholders. The player setting points at `player_pink.png`.

Other shapes from the character-select design (heart, star, teardrop, and the rest) are not drawn yet. Palette swaps for those shapes come after this level is playable.

Regenerate with `python3 scripts/build_level1.py`.
