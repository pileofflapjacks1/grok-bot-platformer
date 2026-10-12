# Character Selection System

## Overview
Title screen → Shape select → Color select → Start Level 1.

Uses the exact shapes and colors from the reference image. Every variant keeps the big fun eyes.

## Variables
- `player_shape` (0–11): Circle, Cloud, Diamond, Plus, Flower, Heart, Teardrop, Oval, Triangle, Star, Pentagon, etc.
- `player_color` (0–10): White, Brown, Red, Orange, Yellow, Green, Teal, Blue, Purple, Pink, Gray

## Flow (GB Studio)

### Scene: Title
- Background: simple logo or “GROK BOT”
- Trigger or actor: “Press Start”
- On Interact → Scene: Change to ShapeSelect

### Scene: ShapeSelect (Platform or Top-down)
Place 6–12 choice actors (or a menu).
- On Interact with a shape actor:
  - Set Variable `player_shape` = X
  - Scene: Change to ColorSelect

### Scene: ColorSelect
Same pattern.
- On Interact:
  - Set Variable `player_color` = Y
  - Scene: Change to Level1 (and optionally apply palette / swap player sprite)

### Applying the choice
For the first playable version:
- Use a single player sprite sheet.
- On Level1 Init: set sprite palette based on `player_color`.
- Later: swap entire sprite sheet based on `player_shape`.

## Palette mapping (example)
| Color Index | Palette |
|-------------|---------| 
| 0 White     | Light gray / white |
| 2 Red       | Strong red |
| 4 Yellow    | Bright yellow |
| 6 Teal      | Cyan/teal |
| 7 Blue      | Strong blue |
| 9 Pink      | Magenta/pink |

Keep high contrast for the Chromatic screen.
