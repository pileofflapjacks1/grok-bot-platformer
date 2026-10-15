# Platformer+ Feel Notes

For a responsive platformer with an optional float:

## Recommended settings
- Variable jump height (hold longer = higher)
- Coyote time (small grace period after leaving a platform)
- Jump buffering
- Mid-air direction change (if using Platformer+ events)

## Tuning targets
- Jump feels responsive but not floaty unless you want a floaty style.
- Stomp bounce should feel satisfying (medium bounce on enemy hit).
- Keep gravity high enough that the stage stays readable on the small Chromatic screen.

## Implementation
1. Install Platformer+ plugin if available for your GB Studio version.
2. On player Init or scene Init: enable the desired engine fields.
3. Test jump arcs early — adjust velocity and gravity before building many levels.

These changes stay inside normal GBC performance limits when used sparingly.
