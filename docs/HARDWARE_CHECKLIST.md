# Hardware Audit Checklist (GROK BOT HERO)

Run before adding heavy art or new scenes.

## Graphics
- [ ] Unique background tiles in current scene < 150
- [ ] Sprite count on screen < 20 (well under 40)
- [ ] No more than 8–10 sprites on any single scanline
- [ ] Sprite size 8×8 or 8×16 (or small metasprites)
- [ ] 2–4 sprite palettes used; high contrast

## Memory & Performance
- [ ] On Update scripts are short
- [ ] Actor count per scene is reasonable (< 15 early)
- [ ] Targeting 32 KB or small 128 KB ROM for the first build

## Chromatic-specific
- [ ] Palettes readable on the Chromatic screen (test in emulator + device)
- [ ] No low-contrast color pairs
- [ ] Short levels (1–3 min)

## Quick command
```bash
# From the skill repo
python /tmp/grok-chromatic-agent/scripts/audit_checklist.py
```

Fix issues by simplifying art, splitting scenes, or reducing simultaneous actors before expanding to later levels.
