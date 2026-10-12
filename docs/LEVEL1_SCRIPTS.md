# Level 1 — Detailed Event Scripts

**Scene:** Level1_GreenHills  
**Type:** Platform  
**Goal:** Short horizontal stage that teaches jump, stomp, and collect.

## Player
Default Platformer player.  
Tune in Settings → Platformer:
- Jump velocity: 3.5
- Gravity while jumping: slightly lower for floatier feel
- Optional Platformer+: enable coyote time + variable jump height

## Enemy: Waddle Blob
**On Update:**
1. Actor: Move Relative → Right 3 tiles
2. Wait 20 frames
3. Actor: Move Relative → Left 3 tiles
4. Wait 20 frames
5. Loop (or use a timer)

**On Hit Player:**
- If player Y velocity > 0 (falling/stomping):
  - Actor: Destroy
  - Player: Bounce (medium)
  - Sound: stomp
- Else:
  - Player: Knockback or damage
  - Sound: hit

## Collectible: Power-up Star
**On Hit Player:**
1. Variable: Increment `powerups`
2. Sound: collect
3. Actor: Destroy
4. Optional: temporary jump boost (set a timer variable + higher jump field)

## Exit Trigger
**On Hit / On Interact:**
- If `powerups` >= 3:
  - Scene: Change to Level2 (or Victory for now)
- Else:
  - Display Dialogue: “Need more power-ups!”

## Recommended layout (tiles)
```
[Start platform] -- gap -- [mid platform + enemy] -- gap -- [collectible] -- [final platform + exit]
```
- Height variation: 2–3 tiles so jumps feel meaningful.
- Keep unique tiles low (< 80 for the first build).
