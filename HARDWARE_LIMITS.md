# Game Boy / GBC Hardware Limits

Keep these in mind when scaffolding or auditing.

## Screen
- Resolution: 160 × 144 pixels
- Visible area is small; design for short, readable scenes

## Graphics
- Background: limited unique tiles per scene (commonly ~256 or fewer depending on mode and banking)
- Sprites: classic limit of 40 on screen, 10 per scanline (GBC is more flexible but still constrained)
- Sprite size: usually 8×8 or 8×16
- Palettes: GBC has 8 background + 8 sprite palettes, 4 colors each. Use carefully for readability.

## Memory & Size
- Start with 32 KB or 128 KB ROMs. Larger sizes require banking.
- Keep actor and script counts reasonable in early prototypes.

## Common Failure Modes
- Too many unique tiles in one scene → build warning or failure
- Sprite overflow on a scanline → flickering
- Poor palette contrast → unreadable on real hardware / Chromatic screen
- Large scripts or too many actors → slowdowns

When auditing, check tile counts, sprite dimensions, and palette usage first. Recommend simplifying art or splitting scenes if limits are approached.
