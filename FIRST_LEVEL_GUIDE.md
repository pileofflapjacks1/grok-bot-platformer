# GROK BOT HERO — First Playable Level Guide

**Project:** GrokBotPlatformer (scaffolded with grok-chromatic-agent)  
**Target:** ModRetro Chromatic / Game Boy Color  
**Engine:** GB Studio (Platform scene type)

## 1. Open & Initialize

1. Open `GrokBotPlatformer.gbsproj` in GB Studio.
2. Let it finish initialization (it will add default player sprite, palettes, etc.).
3. Confirm Scene Type is **Platform** (or set it if needed).

## 2. Character Customization (Shape + Color + Eyes)

For the first playable version, use a single Grok Bot sprite (e.g. red circle with big eyes).  
Later you can expand to a selection screen that swaps sprites/palettes.

**Recommended first sprite:**
- 16×16 or 32×16 (two 8×16 tiles) circle/blob with large white eyes.
- Keep it simple: solid color fill + black outline + eyes.  
- Import as a sprite sheet in `assets/sprites/`.

## 3. Core Loop — First Playable Scene

**Scene name:** Level 1 – Green Hills  
**Size:** Start small (e.g. 20×18 tiles or a short horizontal stretch).

### Player
- Default Platformer player actor.
- Movement + jump are built into the Platform scene type.
- Tune in **Settings → Platformer**:
  - Jump velocity ~ 3.0–4.0
  - Gravity while jumping (floatier or tighter)

### Basic Enemy (Grok Blob)
1. Create an actor (e.g. simple red blob sprite).
2. On Update script:
   - **Actor: Move Relative** → Right 4 tiles (or a short distance).
   - Wait a few frames.
   - **Actor: Move Relative** → Left 4 tiles.
   - Loop.
3. On Hit Player:
   - If player is falling / stomping → destroy enemy + bounce player.
   - Else → damage player or knockback.

### Collectible
1. Create a small actor (star or simple icon).
2. On Hit Player:
   - Increment variable `powerups` (or `score`).
   - Play sound.
   - Destroy actor.

### Exit / Goal
- Trigger or actor at the right end of the scene.
- On Interact / On Hit:
  - If `powerups >= N` (or always for level 1) → **Scene: Change** to next level or victory.
  - Else show a message.

## 4. Hardware-Aware Checklist

- **Tiles:** Keep unique background tiles low (aim for < 100–150 in the first scene).
- **Sprites:** Stay well under 40 on screen and avoid 10+ on one scanline.
- **Palettes:** Use 2–3 sprite palettes max early on. High contrast.
- **Script length:** Keep On Update scripts short to avoid slowdown.

## 5. Suggested First Level Structure

```
[Start] ---- platforms ---- [Enemy] ---- [Collectible] ---- [Enemy] ---- [Exit]
```

- Short horizontal layout.
- 2–3 platforms of different heights (test jump feel).
- 1–2 walking enemies.
- 2–3 collectibles.
- Clear end trigger.
