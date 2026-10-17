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
| coin.png | Round gold coin pickup (Coin Gold palette). |
| coin_hud.png | One frame per coin count: a small coin and a digit. The pinned actor shows the frame that matches `coins` (variable 8). |
| flyer.png | Zap Bat, a small winged bot. Two frames, wings up and down. |
| turret.png | Bolt Tower, the High Ridge shooter. |
| bolt.png | The Bolt Tower's projectile. |
| roadster.png | 32x16 generic red two-seat convertible for the level-complete cutscene. No badge, logo, or wordmark. |
| press_start_0..3.png | Single-frame strips that together read PRESS START on the title. |

`actor.png`, `actor_animated.png`, and `static.png` are the GB Studio blank-template placeholders. The player setting points at `player_grok.png`.

All player sheets are palette-mode (indexed) PNGs with four entries: transparent, fill, outline, eyes. GB Studio sprite palettes show palette colors 0, 1 and 3 for sprite colors 1, 2 and 3; see `sprite_palette()` in the generator. The picker's color choice recolors any shape through sprite palette slot 0 instead of duplicating PNGs. Each sheet is 64x16: 4 frames x 2 8x16 tiles = 8 tiles. In a scene GB Studio reserves VRAM for one player sheet (the largest the player can be set to), and `Player: Set Sprite` loads the chosen sheet into that slot, so eight shapes do not cost 64 tiles of VRAM. `docs/shapes-sheet.png` is a contact sheet of every shape.

Regenerate with `python3 scripts/build_level1.py`.
