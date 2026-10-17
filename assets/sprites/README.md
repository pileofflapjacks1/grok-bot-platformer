# Sprites

GB Studio reads every `.png` in this folder. The Level 1 sheets below are 16x16, 8x16 sprite mode, with a transparent background and three opaque colors.

| File | Use |
|------|-----|
| player_grok.png | Grok Bot, circle shape (picker shape 0). Locked Grok Imagine style: solid fill, thin black outline, lower shade, two short thick black oval eyes; no mouth, eye whites, pupils, or antenna. Four frames: idle, walk A, walk B, jump. Left facing is mirrored. |
| player_grok_square.png | Same style, square (shape 1). |
| player_heart.png | Same style, heart (shape 2). |
| player_star.png | Same style, star (shape 3). |
| player_triangle.png | Same style, triangle (shape 4). |
| enemy_red_blob.png | Grok Blob. Two frames, cream eyes, black pupils, belly, brows, and feet. |
| electron.png | Electron pickup and the projectile Grok Bot fires. |
| silicon_chip.png | One power-up. Collecting it unlocks firing for the rest of the run. |
| lives.png | Four frames. Each frame is a black badge with a heart and a digit, 0 through 3. The pinned actor shows the frame that matches `lives`. |
| ammo.png | One frame per electron count, from 0 up. Each frame is a blue badge with two digits. The pinned actor shows the frame that matches `electrons`. |

`actor.png`, `actor_animated.png`, and `static.png` are the GB Studio blank-template placeholders. The player setting points at `player_grok.png`.

All player sheets use only transparent + three indexed colors (fill, shade, outline), so the picker's color choice recolors any shape through sprite palette slot 0 instead of duplicating PNGs. Teardrop, oval, and the rest are not drawn yet. Each sheet is 8 tiles (4 frames x 2 8x16 tiles); only the active sheet is loaded per scene.

Regenerate with `python3 scripts/build_level1.py`.
