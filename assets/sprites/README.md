# Sprites

GB Studio reads every `.png` in this folder. The Level 1 sheets below are 16x16, 8x16 sprite mode, with a transparent background and three opaque colors.

| File | Use |
|------|-----|
| player_grok.png | Grok Bot. Round head, antenna, black capsule eyes, no mouth. Four frames: idle, walk A, walk B, jump. Left facing is mirrored. |
| enemy_red_blob.png | Waddle Blob. Two frames, cream eyes, black pupils, belly, brows, and feet. |
| electron.png | Electron pickup and the projectile Grok Bot fires. |
| silicon_chip.png | One power-up. Collecting it unlocks firing for the rest of the run. |
| lives.png | Four frames in one animation. Frame 0 is empty, then 1, 2, and 3 hearts. The pinned actor shows the frame that matches `lives`. |
| ammo.png | One frame per electron count, from 0 up. The pinned actor shows the frame that matches `electrons`. |

`actor.png`, `actor_animated.png`, and `static.png` are the GB Studio blank-template placeholders. The player setting points at `player_grok.png`.

Other shapes from the character-select design (heart, star, teardrop, and the rest) are not drawn yet. Palette swaps for those shapes come after this level is playable.

Regenerate with `python3 scripts/build_level1.py`.
