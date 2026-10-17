# Sprites

GB Studio reads every `.png` in this folder. The Level 1 sheets below are 16x16, 8x16 sprite mode, with a transparent background and three opaque colors.

| File | Use |
|------|-----|
| player_grok.png | Grok Bot, circle shape (picker shape 0, the default). Locked Grok Imagine style: solid fill, thin black outline, lower shade, two short thick black oval eyes; no mouth, eye whites, pupils, or antenna. Four frames: idle, walk A, walk B, jump. Left facing is mirrored. |
| player_grok_square.png | Same style, square (shape 1). |
| player_heart.png | Same style, heart (shape 2). |
| player_star.png | Same style, star (shape 3). |
| player_triangle.png | Same style, triangle (shape 4). |
| player_teardrop.png | Same style, teardrop (shape 5). |
| player_oval.png | Same style, oval (shape 6). |
| player_blob.png | Same style, irregular blob (shape 7). |
| enemy_red_blob.png | Grok Blob. Two frames, cream eyes, black pupils, belly, brows, and feet. |
| electron.png | Electron pickup and the projectile Grok Bot fires. |
| silicon_chip.png | One power-up. Collecting it unlocks firing for the rest of the run. |
| lives.png | Four frames. Each frame is a black badge with a heart and a digit, 0 through 3. The pinned actor shows the frame that matches `lives`. |
| ammo.png | One frame per electron count, from 0 up. Each frame is a blue badge with two digits. The pinned actor shows the frame that matches `electrons`. |

`actor.png`, `actor_animated.png`, and `static.png` are the GB Studio blank-template placeholders. The player setting points at `player_grok.png`.

All player sheets are palette-mode (indexed) PNGs with four entries: transparent, fill, shade, outline. The picker's color choice recolors any shape through sprite palette slot 0 instead of duplicating PNGs. Each sheet is 64x16: 4 frames x 2 8x16 tiles = 8 tiles. In a scene GB Studio reserves VRAM for one player sheet (the largest the player can be set to), and `Player: Set Sprite` loads the chosen sheet into that slot, so eight shapes do not cost 64 tiles of VRAM. `docs/shapes-sheet.png` is a contact sheet of every shape.

Regenerate with `python3 scripts/build_level1.py`.
