#!/usr/bin/env python3
"""Generate Level 1 of GROK BOT HERO (project file GrokBotPlatformer.gbsproj) on top of the GB Studio blank template.

Run from anywhere:

    python3 scripts/build_level1.py

Rewrites the level scenes, original sprites, backgrounds, palettes, and the
project settings that point at them. Template fonts, UI, and emotes are left
in place. Identifiers are stable across runs.
"""

from __future__ import annotations

import hashlib
import re
import json
import struct
import uuid
import zlib
from pathlib import Path

SYMBOL_RE = re.compile(r"[a-z0-9_]+")
ROOT = Path(__file__).resolve().parents[1]
NS = uuid.UUID("6f1b9c3e-8a24-4b7e-9c1d-0a5e2f7b4d11")

# Background palette. Four opaque colors, one 8x8 pattern each.
SKY = (184, 240, 232, 255)
# GB Studio indexes background pixels by green channel (tileDataIndexFn in
# src/shared/lib/tiles/tileData.ts): 205+ is color 0, 130+ is 1, 65+ is 2,
# and the rest is 3. These PNG shades only pick the slot; the palette sets the color.
GRASS_L = (104, 176, 112, 255)
DIRT = (40, 104, 56, 255)
OUTLINE = (24, 48, 40, 255)

# Sprite colors. GB Studio does not use these RGB values directly.
# A pixel is transparent when alpha is under 200, or when it is pure green
# or pure blue. Otherwise the green channel picks the palette slot:
# 205 or more is color 1, 130 or more is color 2, and the rest is color 3.
#
# A GB Studio palette has four colors, but a SPRITE palette only uses three
# of them: compileData.ts getSpritePalette (and scriptBuilder paletteSetSprite)
# build [c0, c0, c1, c3], so sprite color 1 (light) shows palette color 0,
# color 2 (mid) shows palette color 1, color 3 (dark) shows palette color 3,
# and palette color 2 is never used. sprite_palette() below writes palettes
# in that order. Getting this wrong left every sprite's light pixels white
# (the character-select fill bug) and drew mid/dark art in the wrong slots.
# Grok Bot is a round head, gray shade, and black capsule eyes.
WHITE = (244, 244, 248, 255)
GRAY = (138, 138, 152, 255)
RED = (248, 150, 150, 255)  # mid band: the red slot of Blob Red
E_WHITE = (232, 248, 255, 255)
CYAN = (80, 176, 248, 255)  # mid band: the cyan slot of Electron Blue
BLUE = (24, 72, 200, 255)
SILVER = (216, 220, 232, 255)
CHIP_BODY = (96, 150, 120, 255)  # mid band: the body slot of Chip Gray
BLACK = (24, 16, 24, 255)
CREAM = (248, 232, 208, 255)
CLOUD = (232, 200, 240, 255)
HILL = (112, 120, 216, 255)
HILL_SHADE = (40, 56, 144, 255)
CLEAR = (0, 0, 0, 0)
# Far background palette. Color 0 matches the ground palette's sky.
FAR = [SKY, CLOUD, HILL, HILL_SHADE]

# Two scenes of 170 tiles. 340 tiles is five times the previous 68-tile run.
# One scene cannot be wider than 255 tiles.
LEVEL_H = 18
SEG_W = 170
CLEAR_W = 20
CLEAR_H = 18
FLOOR_TOP = 15
PLAYER_START = (2, FLOOR_TOP - 2)
CLEAR_TOP = 16
MUSIC_ID = "f50428ab-a084-4591-9bba-2ba10fe7b1c6"
BASE_JUMP = 14336
MAX_ACTORS = 20
SCENE_GAP = 80
LIVES_AT = (1, 0)
AMMO_AT = (16, 0)
POWER_VAR = "9"
SCORE_VAR = "8"
# Score HUD: three pinned actors at tiles 7, 8 and 9-10 on the HUD row show
# thousands, hundreds, and "tens + a fixed 0" (every award is a multiple of
# 10). The single-digit frames leave the right 8 px blank, which GB Studio
# drops from the frame, so those two actors cost 1 hardware sprite each.
SCORE_AT = 7
SCORE_DIGITS = (("k", 1000, "sprite_score_digit"), ("h", 100, "sprite_score_digit"), ("t", 10, "sprite_score_tens"))
POINTS = {"blob": 100, "flyer": 200, "turret": 500, "electron": 10, "chip": 1000, "clear": 1000}
VIOLET = (152, 160, 224, 255)  # mid band: the body slot of Flyer Violet
# Screen bands. Speeds are GB Studio parallax values: 0 is normal, 2 is 1/4, 4 is 1/16.
# Solids stay at row 10 and below so the floor scrolls with the player.
PARALLAX = [
    {"height": 5, "speed": 4},
    {"height": 5, "speed": 2},
    {"height": 0, "speed": 0},
]
PLAY_ROW = 10


def world_x(index: int) -> int:
    return 80 + index * (SEG_W * 8 + SCENE_GAP)


# A 16px actor standing on a surface uses y = top - 2.
# Electrons sit in the air so each one is its own hop.
# Per scene GB Studio keeps at most 20 actors (MAX_ACTORS in src/consts.ts;
# extras are dropped at build time) and 30 triggers. The 3 pinned HUD
# actors count, so each half is laid out to exactly fit. Order along each
# half: blobs first, then the silicon chip, then electrons.
SEGMENTS = [
    {
        "key": "hills",
        "name": "Level 1 Green Hills",
        "symbol": "scene_level1_green_hills",
        "folder": "level_1_green_hills",
        "bg_symbol": "bg_level1_green_hills",
        "bg_file": "level1_green_hills.png",
        "index": 0,
        "reset": True,
        "floor": [(0, SEG_W - 1, FLOOR_TOP)],
        "raised": [(20, 32, 12), (48, 58, 13), (90, 108, 12), (124, 140, 11), (150, 162, 13)],
        "pits": [(70, 72)],
        "blobs": [(12, 13), (26, 10), (40, 13), (99, 10)],
        "chips": [(54, 11), (118, 13)],
        "electrons": [(60, 10), (88, 8), (94, 7), (104, 6), (146, 8)],
        "flyers": [(80, 9), (132, 7)],
        "next": "scene_level1_high_ridge",
    },
    {
        "key": "ridge",
        "name": "Level 1 High Ridge",
        "symbol": "scene_level1_high_ridge",
        "folder": "level_1_high_ridge",
        "bg_symbol": "bg_level1_high_ridge",
        "bg_file": "level1_high_ridge.png",
        "index": 1,
        "reset": False,
        "floor": [(0, SEG_W - 1, FLOOR_TOP)],
        "raised": [(16, 30, 12), (42, 54, 13), (74, 88, 12), (108, 122, 11), (136, 150, 13)],
        "pits": [(62, 64)],
        "blobs": [(10, 13), (23, 10), (36, 13), (81, 10)],
        "chips": [(48, 11), (140, 11)],
        "electrons": [(52, 8), (78, 7), (146, 8)],
        "flyers": [(70, 9), (128, 8)],
        # One shooter on the high ledge; it fires a bolt at Grok Bot every 2 s.
        # Bolt Towers, spaced so no 20-tile screen ever holds two (one bolt
        # in flight per screen keeps every row at 10 sprites or fewer).
        "turret": [(60, 13), (110, 9), (143, 11)],
        # Level-complete car, 4 tiles wide, parked on the floor before the end.
        "roadster": [(SEG_W - 12, FLOOR_TOP - 2)],
        "next": None,
    },
]
HUD_ACTORS = 2 + 3  # lives, ammo, three score digits


def segment_bodies(segment: dict) -> list[tuple[str, int, int]]:
    """Every non-HUD actor in a half as (kind, x, y)."""
    bodies = []
    for kind in ("blobs", "chips", "electrons", "flyers", "turret", "roadster"):
        bodies.extend((kind, x, y) for x, y in segment.get(kind, []))
    return bodies


def actor_count(segment: dict) -> int:
    return HUD_ACTORS + len(segment_bodies(segment))


def uid(name: str) -> str:
    return str(uuid.uuid5(NS, name))


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_png(path: Path, width: int, height: int, rows: list[list[tuple[int, int, int, int]]]) -> None:
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            raw.extend(rows[y][x])

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


# Player sheets are written as palette-mode (indexed) PNGs. Index order
# matches the GB Studio sprite color numbers: 0 transparent, 1 light (fill),
# 2 mid (shade), 3 dark (outline). GB Studio decodes any PNG to RGBA with
# pngjs and then maps each pixel by alpha and green channel (spriteDataIndexFn
# in src/shared/lib/sprites/spriteData.ts), so the RGB values below are what
# it sees; tRNS makes index 0 fully transparent.
PLAYER_INDEXED = [CLEAR, WHITE, GRAY, BLACK]


def write_png_indexed(
    path: Path,
    width: int,
    height: int,
    rows: list[list[tuple[int, int, int, int]]],
    palette: list[tuple[int, int, int, int]],
) -> None:
    lookup = {color: index for index, color in enumerate(palette)}
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            raw.append(lookup[rows[y][x]])

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 3, 0, 0, 0)
    plte = b"".join(bytes(color[:3]) for color in palette)
    trns = bytes(color[3] for color in palette)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"PLTE", plte)
        + chunk(b"tRNS", trns)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def compress8(values: list[int]) -> str:
    if not values:
        return ""
    output: list[str] = []
    last = values[0]
    count = 0
    for value in values:
        if value != last:
            output.append(_run(last, count))
            last = value
            count = 0
        count += 1
    output.append(_run(last, count))
    return "".join(output)


def _run(value: int, count: int) -> str:
    token = f"{value & 0xFF:02x}"
    if count == 1:
        return token + "!"
    return token + f"{count:x}+"


def blank(width: int, height: int, color: tuple[int, int, int, int]) -> list[list[tuple[int, int, int, int]]]:
    return [[color for _ in range(width)] for _ in range(height)]


def stamp_disk(
    image: list[list[tuple[int, int, int, int]]],
    origin_x: int,
    cx: float,
    cy: float,
    radius: float,
    fill: tuple[int, int, int, int],
    shade: tuple[int, int, int, int],
    outline: tuple[int, int, int, int],
) -> None:
    r2 = radius * radius
    inner = (radius - 1.15) ** 2
    for y in range(16):
        for x in range(16):
            dx = x + 0.5 - cx
            dy = y + 0.5 - cy
            dist = dx * dx + dy * dy
            pixel_x = origin_x + x
            if dist <= inner:
                image[y][pixel_x] = shade if y >= int(cy + radius * 0.35) else fill
            elif dist <= r2:
                image[y][pixel_x] = outline


def stamp_eye(
    image: list[list[tuple[int, int, int, int]]],
    origin_x: int,
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    color: tuple[int, int, int, int],
) -> None:
    for y in range(16):
        for x in range(16):
            dx = (x + 0.5 - cx) / rx
            dy = (y + 0.5 - cy) / ry
            if dx * dx + dy * dy <= 1:
                pixel = image[y][origin_x + x]
                if pixel[3] != 0:
                    image[y][origin_x + x] = color


def shift_frame(
    image: list[list[tuple[int, int, int, int]]],
    origin_x: int,
    dy: int,
) -> None:
    original = [row[origin_x : origin_x + 16][:] for row in image]
    for y in range(16):
        for x in range(16):
            src = y - dy
            image[y][origin_x + x] = original[src][x] if 0 <= src < 16 else CLEAR


# Locked Grok Imagine player style: one solid fill, a thin black outline, and
# two short thick horizontal black oval eyes. No mouth, eye whites, pupils,
# antenna, or shade band. Every fill pixel is WHITE (sprite color 1, palette
# color 0), the one slot the picker's color recolors, so the whole body takes
# the chosen color. The outline is GRAY (color 2, palette color 1): black in
# the normal palettes, and the slot the power-up glow swaps. The eyes are
# BLACK (color 3, palette color 3), black in every palette.
# The list order is the picker order and the player_shape (var 6) value.
PLAYER_SHAPES = ["circle", "square", "heart", "star", "triangle", "teardrop", "oval", "blob"]
PLAYER_FILES = {
    "circle": "player_grok.png",
    "square": "player_grok_square.png",
    "heart": "player_heart.png",
    "star": "player_star.png",
    "triangle": "player_triangle.png",
    "teardrop": "player_teardrop.png",
    "oval": "player_oval.png",
    "blob": "player_blob.png",
}
# Row of the top of each shape's eyes on the idle frame, and the left x of
# each 3x2 eye (mirrored about the 16px cell's centre line, x = 7.5).
PLAYER_EYES = {
    "circle": (8, (4, 9)),
    "square": (8, (4, 9)),
    "heart": (7, (4, 9)),
    "star": (7, (4, 9)),
    "triangle": (11, (4, 9)),
    "teardrop": (9, (4, 9)),
    "oval": (9, (4, 9)),
    "blob": (8, (4, 9)),
}


def _star_edge(dx: float, dy: float) -> float:
    """Distance from the star centre to its outline along (dx, dy).

    The outline is the true straight-sided five-point star (outer radius R,
    inner radius r), so the edges are straight lines, not a sawtooth in angle.
    """
    import math
    R, r = 8.0, 4.2
    a = math.atan2(dx, -dy) % (2 * math.pi / 5)
    seg = 2 * math.pi / 5
    # Edge from the outer point at angle 0 to the inner point at seg/2.
    if a > seg / 2:
        a = seg - a
    p1 = (0.0, R)
    p2 = (r * math.sin(seg / 2), r * math.cos(seg / 2))
    # Intersect the ray at angle a with segment p1-p2.
    ux, uy = math.sin(a), math.cos(a)
    ex, ey = p2[0] - p1[0], p2[1] - p1[1]
    det = ux * (-ey) - uy * (-ex)
    t = (p1[0] * (-ey) - p1[1] * (-ex)) / det
    return t


def _inside(shape: str, x: float, y: float) -> bool:
    """Shape test in a 16x16 cell; (x, y) is a sample point, body sits low."""
    import math
    if shape == "circle":
        return (x - 8) ** 2 + (y - 9.5) ** 2 <= 6.0 ** 2
    if shape == "square":
        return 2 <= x <= 14 and 3.5 <= y <= 15
    if shape == "heart":
        # Two round lobes with a centre notch over a pointed base.
        lobe = 3.55
        if (x - 4.75) ** 2 + (y - 6.4) ** 2 <= lobe ** 2:
            return True
        if (x - 11.25) ** 2 + (y - 6.4) ** 2 <= lobe ** 2:
            return True
        return 6.4 <= y <= 15.2 and abs(x - 8) <= (15.2 - y) * 0.84
    if shape == "star":
        dx, dy = x - 8, y - 9.4
        return math.hypot(dx, dy) <= _star_edge(dx, dy)
    if shape == "triangle":
        return 2.5 <= y <= 15 and abs(x - 8) <= (y - 2.0) * 0.6
    if shape == "teardrop":
        # Round base with a point at the top; the sides are tangent to the base.
        cx, cy, radius, tip = 8.0, 9.9, 6.1, 1.3
        if (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2:
            return True
        d = cy - tip
        if not tip <= y <= cy:
            return False
        half = math.asin(radius / d)
        return abs(x - cx) <= (y - tip) * math.tan(half)
    if shape == "oval":
        # Wider than tall, so it reads differently from the circle.
        return ((x - 8) / 7.1) ** 2 + ((y - 10.0) / 5.3) ** 2 <= 1
    if shape == "blob":
        # Irregular rounded blob: a lumpy polar outline, wide through the
        # eye line, with a flat base.
        dx, dy = x - 8, y - 9.4
        a = math.atan2(dy, dx)
        edge = 6.5 + 0.55 * math.sin(3 * a - 0.5) + 0.35 * math.cos(2 * a + 1.1)
        return math.hypot(dx, dy) <= edge and y <= 15.0
    raise ValueError(shape)


# Straight-sided shapes keep the single centre sample; curved and pointed ones
# use 4x4 coverage so their diagonal outlines step evenly.
SUPERSAMPLED = {"heart", "star", "teardrop", "oval", "blob"}


def _shape_mask(shape: str, dy: int) -> list[list[bool]]:
    if shape not in SUPERSAMPLED:
        return [[_inside(shape, x + 0.5, y + 0.5 - dy) for x in range(16)] for y in range(16)]
    n = 4
    mask = []
    for y in range(16):
        row = []
        for x in range(16):
            hits = sum(
                _inside(shape, x + (sx + 0.5) / n, y + (sy + 0.5) / n - dy)
                for sy in range(n)
                for sx in range(n)
            )
            row.append(hits * 2 >= n * n)
        mask.append(row)
    # Drop one-pixel spurs (a pixel with at most one filled 4-neighbour) so
    # points and corners do not leave a stray outline pixel.
    for _ in range(2):
        mask = [
            [
                mask[y][x]
                and sum(
                    0 <= y + oy < 16 and 0 <= x + ox < 16 and mask[y + oy][x + ox]
                    for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                )
                >= 2
                for x in range(16)
            ]
            for y in range(16)
        ]
    # Trim outline-only stubs: an outline pixel with no interior (fill) pixel
    # among its eight neighbours would be a black stub past a point.
    def edge_at(y: int, x: int) -> bool:
        return any(
            not (0 <= y + oy < 16 and 0 <= x + ox < 16 and mask[y + oy][x + ox])
            for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1))
        )

    interior = [[mask[y][x] and not edge_at(y, x) for x in range(16)] for y in range(16)]
    mask = [
        [
            mask[y][x]
            and any(
                0 <= y + oy < 16 and 0 <= x + ox < 16 and interior[y + oy][x + ox]
                for ox in (-1, 0, 1)
                for oy in (-1, 0, 1)
            )
            for x in range(16)
        ]
        for y in range(16)
    ]
    return mask


EYE_SHIFTS = (2, 1)


def draw_shape_bot(image, origin: int, dy: int, shape: str) -> None:
    mask = _shape_mask(shape, dy)
    for y in range(16):
        for x in range(16):
            if not mask[y][x]:
                continue
            edge = any(
                not (0 <= y + oy < 16 and 0 <= x + ox < 16 and mask[y + oy][x + ox])
                for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            )
            image[y][origin + x] = GRAY if edge else WHITE
    # Facing: the sheet faces right (flipLeft mirrors it for left). The
    # trailing (left) edge gets a 2 px outline, a darker back side, so even
    # the symmetric shapes read as pointing one way.
    back = [
        (y, x)
        for y in range(16)
        for x in range(1, 8)
        if image[y][origin + x] == WHITE and image[y][origin + x - 1] == GRAY
    ]
    for y, x in back:
        image[y][origin + x] = GRAY
    # Eyes: two short, thick horizontal black ovals, 3x2 px each, shifted
    # toward the facing side by EYE_SHIFT px (2, or 1 where the shape is too
    # narrow), staying on fill pixels so the outline stays closed.
    eye_top, eye_xs = PLAYER_EYES[shape]
    eye_y = eye_top + dy

    def fits(shift: int) -> bool:
        return all(
            0 <= yy < 16 and image[yy][origin + xx] == WHITE
            for cx in eye_xs
            for yy in (eye_y, eye_y + 1)
            for xx in range(cx + shift, cx + shift + 3)
        )

    shift = next((s for s in EYE_SHIFTS if fits(s)), 0)
    for cx in eye_xs:
        for yy in (eye_y, eye_y + 1):
            for xx in range(cx + shift, cx + shift + 3):
                if 0 <= yy < 16 and image[yy][origin + xx][3]:
                    image[yy][origin + xx] = BLACK


def paint_shape_player(shape: str):
    """Four frames: idle, walk A (bob down), walk B, jump (up). Left is mirrored."""
    image = blank(64, 16, CLEAR)
    for frame, dy in enumerate((0, 1, 0, -1)):
        draw_shape_bot(image, frame * 16, dy, shape)
    return image


def paint_enemy() -> list[list[tuple[int, int, int, int]]]:
    """Two walk frames: cream eyes with black pupils, belly, brows, and feet."""
    image = blank(32, 16, CLEAR)
    draw_blob(image, 0, 0, left_foot=13, right_foot=14)
    draw_blob(image, 16, 1, left_foot=14, right_foot=13)
    return image


def draw_blob(
    image: list[list[tuple[int, int, int, int]]],
    origin: int,
    bob: int,
    left_foot: int,
    right_foot: int,
) -> None:
    cx, cy, rx, ry = 8.0, 8.0 + bob, 6.5, 5.6
    for y in range(16):
        for x in range(16):
            dx = (x + 0.5 - cx) / rx
            dy = (y + 0.5 - cy) / ry
            dist = dx * dx + dy * dy
            if dist <= 0.8:
                image[y][origin + x] = RED
            elif dist <= 1:
                image[y][origin + x] = BLACK
    # 4x4 cream eyes, 2x2 pupils, two red pixels between the eyes.
    for eye_x in (3, 9):
        for y in range(6 + bob, 10 + bob):
            for x in range(eye_x, eye_x + 4):
                put(image, origin, x, y, CREAM)
        for y in range(7 + bob, 9 + bob):
            for x in range(eye_x + 1, eye_x + 3):
                put(image, origin, x, y, BLACK)
    for y in range(6 + bob, 10 + bob):
        put(image, origin, 7, y, RED)
        put(image, origin, 8, y, RED)
        filled = [x for x in range(16) if image[y][origin + x][3] != 0]
        if filled:
            image[y][origin + filled[0]] = BLACK
            image[y][origin + filled[-1]] = BLACK
    mouth_y = 11 + bob
    put(image, origin, 7, mouth_y, BLACK)
    put(image, origin, 8, mouth_y, BLACK)
    for y in range(12 + bob, 14 + bob):
        for x in range(6, 10):
            if 0 <= y < 16 and image[y][origin + x] == RED:
                image[y][origin + x] = CREAM
    paint_foot(image, origin, 3, left_foot)
    paint_foot(image, origin, 10, right_foot)


def put(
    image: list[list[tuple[int, int, int, int]]],
    origin: int,
    x: int,
    y: int,
    color: tuple[int, int, int, int],
) -> None:
    if 0 <= y < 16 and 0 <= x < 16:
        image[y][origin + x] = color


def paint_foot(
    image: list[list[tuple[int, int, int, int]]],
    origin: int,
    x0: int,
    y0: int,
) -> None:
    for y in range(y0, y0 + 2):
        for x in range(x0, x0 + 3):
            if 0 <= y < 16 and 0 <= x < 16:
                image[y][origin + x] = BLACK


def paint_electron() -> list[list[tuple[int, int, int, int]]]:
    """Small charged orb. The bar in the middle is the electron's minus."""
    image = blank(16, 16, CLEAR)
    radius = 4.3
    for y in range(16):
        for x in range(16):
            dx = x + 0.5 - 8
            dy = y + 0.5 - 8
            dist = dx * dx + dy * dy
            if dist <= 1.7 * 1.7:
                image[y][x] = E_WHITE
            elif dist <= (radius - 1.15) ** 2:
                image[y][x] = CYAN
            elif dist <= radius * radius:
                image[y][x] = BLUE
    for x in range(6, 10):
        image[8][x] = BLUE
    return image


def paint_flyer() -> list[list[tuple[int, int, int, int]]]:
    """Zap Bat: a small round bot with a visor and two flapping wings.

    Frame 0 wings up, frame 1 wings down. Body VIOLET (mid), wings and visor
    WHITE (light), outline BLACK (dark).
    """
    image = blank(32, 16, CLEAR)
    for frame, up in ((0, True), (1, False)):
        ox = frame * 16
        # Wings first so the body outline sits on top.
        wing_rows = ((3, 4), (4, 6), (5, 7)) if up else ((8, 4), (9, 6), (10, 7))
        for y, length in wing_rows:
            for x in range(length):
                for wx in (x, 15 - x):
                    image[y][ox + wx] = BLACK if x == 0 or y == wing_rows[0][0] else WHITE
        for y in range(16):
            for x in range(16):
                dx = (x + 0.5 - 8) / 4.6
                dy = (y + 0.5 - 8) / 4.2
                dist = dx * dx + dy * dy
                if dist <= 0.62:
                    image[y][ox + x] = VIOLET
                elif dist <= 1:
                    image[y][ox + x] = BLACK
        for x in range(6, 10):
            image[7][ox + x] = WHITE
        image[7][ox + 7] = BLACK
        image[7][ox + 8] = BLACK
        # Little feet so it reads as a bot, not a ball.
        image[12][ox + 6] = BLACK
        image[12][ox + 9] = BLACK
    return image


def paint_turret() -> list[list[tuple[int, int, int, int]]]:
    """Bolt Tower: a squat dome on a base with a stubby cannon and one eye."""
    image = blank(16, 16, CLEAR)
    for y in range(16):
        for x in range(16):
            dx = (x + 0.5 - 8) / 5.5
            dy = (y + 0.5 - 9) / 5.0
            if y <= 9 and dx * dx + dy * dy <= 1:
                inner = dx * dx + dy * dy <= 0.6
                image[y][x] = CHIP_BODY if inner else BLACK
    for y in range(10, 16):
        for x in range(2, 14):
            edge = y in (10, 15) or x in (2, 13)
            image[y][x] = BLACK if edge else CHIP_BODY
    for x in range(4, 12, 3):
        image[12][x] = SILVER
        image[13][x] = SILVER
    # Cannon on both sides so it reads as aiming either way.
    for y in (6, 7):
        for x in list(range(0, 3)) + list(range(13, 16)):
            image[y][x] = BLACK if y == 6 else SILVER
    for y in (5, 6, 7):
        for x in (7, 8):
            image[y][x] = SILVER
    image[6][7] = BLACK
    return image


def paint_bolt() -> list[list[tuple[int, int, int, int]]]:
    """Turret shot: a small hot energy ball, cream core in a red glow."""
    image = blank(16, 16, CLEAR)
    for y in range(16):
        for x in range(16):
            dist = (x + 0.5 - 8) ** 2 + (y + 0.5 - 8) ** 2
            if dist <= 1.6**2:
                image[y][x] = CREAM
            elif dist <= 2.6**2:
                image[y][x] = RED
            elif dist <= 3.4**2:
                image[y][x] = BLACK
    return image


R_WHITE = (248, 248, 248, 255)  # light band: Roadster White body
R_GRAY = (120, 150, 170, 255)  # mid band: canopy glass and wheel hubs


def roadster_top(x: int) -> int:
    """Top row of the body at column x: a low wedge / teardrop, facing right.

    Short kicked-up tail on the left, canopy peak just behind the middle,
    then a long falling nose down to the right edge.
    """
    if x <= 2:
        return 9
    if x <= 7:
        return 8
    if x <= 18:
        # Teardrop canopy: rises to row 5 around x=11-13, falls back by x=18.
        return max(5, 8 - min(x - 7, 3) + max(0, (x - 13) * 3 // 5))
    return 8 + (x - 18) // 4


def paint_roadster() -> list[list[tuple[int, int, int, int]]]:
    """A sleek, low two-seat electric hypercar silhouette, facing right.

    32x16, original procedural art (inspired by a modern electric roadster's
    proportions only). No badge, logo, emblem, or wordmark. Roadster White
    palette: white body (light), dark glass canopy and gray hubs (mid),
    black outline and wheels (dark).
    """
    image = blank(32, 16, CLEAR)
    bottom = 12
    for x in range(1, 31):
        top = roadster_top(x)
        for y in range(top, bottom + 1):
            edge = y in (top, bottom) or x in (1, 30)
            # Outline also wherever the neighbour column's top is lower (keeps
            # the wedge edge closed on steps).
            if x > 1 and y < roadster_top(x - 1) or x < 30 and y < roadster_top(x + 1):
                edge = True
            image[y][x] = BLACK if edge else R_WHITE
    # Dark glass canopy: the bubble above the beltline (row 8), x 8..18.
    for x in range(8, 19):
        for y in range(roadster_top(x) + 1, 9):
            if image[y][x] == R_WHITE:
                image[y][x] = R_GRAY
    # Beltline under the glass, and a thin lower side intake.
    for x in range(12, 18):
        image[11][x] = BLACK
    # Slim headlight slit at the nose, tail light at the back.
    image[12][27] = BLACK
    image[12][28] = BLACK
    image[10][2] = BLACK
    # Black wheels with gray hubs.
    for cx in (7, 24):
        for y in range(11, 16):
            for x in range(cx - 3, cx + 3):
                if (x + 0.5 - cx) ** 2 + (y + 0.5 - 13.5) ** 2 <= 2.6**2:
                    image[y][x] = BLACK
        image[13][cx - 1] = R_GRAY
        image[13][cx] = R_GRAY
    return image


# Kickflip: in-plane rotation steps in degrees (counter-clockwise reads as
# the nose lifting first). Frame 0 is the car at rest.
KICKFLIP_ANGLES = (0, 60, 120, 180, 240, 300)
ROADSTER_CANVAS = (32, 32)


def paint_roadster_flip() -> list[list[tuple[int, int, int, int]]]:
    """One 32x32 cell per KICKFLIP_ANGLES entry, side by side.

    Cell 0 is the parked car on the bottom 16 rows (exactly where the old
    32x16 sheet put it). The other cells rotate that car about the canvas
    centre with nearest-neighbour sampling, so they stay 3 colors plus clear
    and keep the black outline; rotation crops a few corner pixels at most.
    """
    import math

    car = paint_roadster()
    width, height = ROADSTER_CANVAS
    base = blank(width, height, CLEAR)
    for y in range(16):
        for x in range(32):
            base[16 + y][x] = car[y][x]
    # Centre of the car's opaque area (rows 21-31 of the cell, cols 1-30).
    ccx, ccy = 15.5, 26.0
    # The car is about 33 px along its diagonal, more than the 32 px cell, so
    # the tilted frames are drawn slightly smaller: the largest scale (in
    # 0.05 steps) at which no rotated frame touches the cell edge.
    for scale in [1 - step * 0.05 for step in range(0, 7)]:
        image = _flip_frames(base, ccx, ccy, scale, math)
        # Search with a 2 px safety ring, so even a tip that nearest-pixel
        # sampling would round outward stays clear of the edge.
        if not flip_edge_problems(image, ring=2):
            return image
    raise SystemExit(f"kickflip frames touch the canvas edge: {flip_edge_problems(image)}")


def flip_edge_problems(image, ring: int = 1) -> list[str]:
    """Frames with an opaque pixel on a 32x32 cell edge.

    Frame 0 (parked) may touch the bottom edge only: its wheels stand on the
    ground there, as on the old 32x16 sheet.
    """
    width, height = ROADSTER_CANVAS
    problems = []
    for index in range(len(KICKFLIP_ANGLES)):
        ox = index * width
        # Frame 0 is the unrotated art (1 px from the sides by design).
        band = range(1 if index == 0 else ring)
        edges = [(y, x) for y in range(height) for r in band for x in (r, width - 1 - r)]
        edges += [(r, x) for r in band for x in range(width)]
        if index != 0:
            edges += [(height - 1 - r, x) for r in band for x in range(width)]
        if any(image[y][ox + x][3] for y, x in edges):
            problems.append(f"frame {index} ({KICKFLIP_ANGLES[index]} deg)")
    return problems


def _flip_frames(base, ccx: float, ccy: float, scale: float, math) -> list:
    width, height = ROADSTER_CANVAS
    image = blank(width * len(KICKFLIP_ANGLES), height, CLEAR)
    for index, angle in enumerate(KICKFLIP_ANGLES):
        ox = index * width
        if angle == 0:
            for y in range(height):
                for x in range(width):
                    image[y][ox + x] = base[y][x]
            continue
        rad = math.radians(angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        for y in range(height):
            for x in range(width):
                # Destination is centred on the canvas centre (lifted), source
                # on the car's own centre.
                dx, dy = (x + 0.5 - 16) / scale, (y + 0.5 - 16) / scale
                sx = cos_a * dx - sin_a * dy + ccx
                sy = sin_a * dx + cos_a * dy + ccy
                ix, iy = int(math.floor(sx)), int(math.floor(sy))
                if 0 <= ix < width and 0 <= iy < height:
                    image[y][ox + x] = base[iy][ix]
    return image


def flip_animation(name: str) -> list[dict]:
    """One animation, one frame per kickflip cell, 4x2 tiles of 8x16 each.

    Tile x is relative to the centred 16 px base (x = -8..16, as in
    wide_animation) and tile y counts up from the base: y=0 is the bottom 16
    rows of the 32 px canvas, y=16 the top (readSpriteData: originY -
    tile.y). Blank tiles are dropped by GB Studio.
    """
    palette_index = SLOT.get(name, 0)
    width, height = ROADSTER_CANVAS
    frames = []
    for index in range(len(KICKFLIP_ANGLES)):
        tiles = []
        for row, tile_y in enumerate((16, 0)):
            for col in range(width // 8):
                ref = tile_ref(f"{name}-f{index}-r{row}-c{col}", col * 8 - 8, index * width + col * 8, palette_index)
                ref["y"] = tile_y
                ref["sliceY"] = row * 16
                tiles.append(ref)
        frames.append({"id": uid(f"{name}-f{index}"), "tiles": tiles})
    animations = [{"id": uid(name + "-anim0"), "frames": frames}]
    animations.extend(empty_frame(f"{name}-anim{index}") for index in range(1, 8))
    return animations


def flip_tile_count(image) -> int:
    """Non-blank 8x16 tiles across all kickflip cells (before dedup)."""
    count = 0
    for cell in range(len(KICKFLIP_ANGLES)):
        for row in (0, 16):
            for col in range(4):
                x0 = cell * 32 + col * 8
                if any(image[row + y][x0 + x][3] for y in range(16) for x in range(8)):
                    count += 1
    return count


def paint_score_digits(with_zero: bool) -> list[list[tuple[int, int, int, int]]]:
    """Ten 16x16 frames: a light 2x digit with a dark outline in the left 8 px.

    with_zero adds a fixed "0" in the right 8 px (the score's last digit).
    Electron Blue palette: E_WHITE is light, BLUE is dark.
    """
    image = blank(160, 16, CLEAR)
    for value in range(10):
        origin = value * 16
        cells = [(origin + 1, value)] + ([(origin + 9, 0)] if with_zero else [])
        for ox, digit in cells:
            draw_digit(image, ox, 3, digit, E_WHITE, 2)
        # 1 px dark outline around the light pixels, kept inside each 8 px cell.
        light = {(x, y) for y in range(16) for x in range(origin, origin + 16) if image[y][x] == E_WHITE}
        for x, y in light:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                same_cell = (nx - origin) // 8 == (x - origin) // 8
                if 0 <= ny < 16 and same_cell and (nx, ny) not in light:
                    image[ny][nx] = BLUE
    return image


def paint_chip() -> list[list[tuple[int, int, int, int]]]:
    """A silicon package: silver pins, dark body, black die."""
    image = blank(16, 16, CLEAR)
    for y in (5, 7, 9, 11):
        for x in (1, 2, 13, 14):
            image[y][x] = SILVER
    for y in range(4, 13):
        for x in range(3, 13):
            image[y][x] = CHIP_BODY
    for x in range(3, 13):
        image[4][x] = BLACK
        image[12][x] = BLACK
    for y in range(4, 13):
        image[y][3] = BLACK
        image[y][12] = BLACK
    for y in range(6, 11):
        for x in range(6, 10):
            image[y][x] = BLACK
    image[7][7] = SILVER
    image[7][8] = SILVER
    image[8][7] = SILVER
    return image


def grass_tile() -> list[list[tuple[int, int, int, int]]]:
    tile = [[DIRT for _ in range(8)] for _ in range(8)]
    for x in range(8):
        tile[0][x] = OUTLINE
        tile[1][x] = GRASS_L
        tile[2][x] = GRASS_L
    tile[1][1] = OUTLINE
    tile[1][4] = OUTLINE
    tile[1][6] = OUTLINE
    return tile


def dirt_tile() -> list[list[tuple[int, int, int, int]]]:
    tile = [[DIRT for _ in range(8)] for _ in range(8)]
    tile[2][3] = OUTLINE
    tile[5][6] = OUTLINE
    return tile


def sky_tile() -> list[list[tuple[int, int, int, int]]]:
    return [[SKY for _ in range(8)] for _ in range(8)]


DIGITS = (
    ("111", "101", "101", "101", "111"),
    ("010", "110", "010", "010", "111"),
    ("111", "001", "111", "100", "111"),
    ("111", "001", "111", "001", "111"),
    ("101", "101", "111", "001", "001"),
    ("111", "100", "111", "001", "111"),
    ("111", "100", "111", "101", "111"),
    ("111", "001", "001", "001", "001"),
    ("111", "101", "111", "101", "111"),
    ("111", "101", "111", "001", "111"),
)


def electron_total() -> int:
    return sum(len(segment["electrons"]) for segment in SEGMENTS)


def paint_ammo() -> list[list[tuple[int, int, int, int]]]:
    """One frame per ammo value. Blue plate, two white digits.

    On the Electron Blue palette, BLUE is slot 3 and E_WHITE is slot 1.
    """
    count = electron_total() + 1
    image = blank(count * 16, 16, BLUE)
    for value in range(count):
        origin = value * 16
        draw_digit(image, origin + 1, 3, value // 10, E_WHITE, 2)
        draw_digit(image, origin + 8, 3, value % 10, E_WHITE, 2)
    return image


def draw_digit(
    image: list[list[tuple[int, int, int, int]]],
    origin_x: int,
    origin_y: int,
    digit: int,
    color: tuple[int, int, int, int],
    scale: int = 1,
) -> None:
    for y, row in enumerate(DIGITS[digit]):
        for x, bit in enumerate(row):
            if bit == "1":
                for sy in range(scale):
                    for sx in range(scale):
                        image[origin_y + y * scale + sy][origin_x + x * scale + sx] = color


def indexed_tile(spec: tuple[str, ...], colors: list[tuple[int, int, int, int]]) -> list[list[tuple[int, int, int, int]]]:
    return [[colors[int(pixel)] for pixel in row] for row in spec]


CLOUD_L = indexed_tile(
    (
        "00000000",
        "00000111",
        "00001111",
        "00011111",
        "00001111",
        "00000111",
        "00000000",
        "00000000",
    ),
    FAR,
)
CLOUD_M = indexed_tile(
    (
        "00000000",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "00000000",
        "00000000",
    ),
    FAR,
)
CLOUD_R = indexed_tile(
    (
        "00000000",
        "11100000",
        "11110000",
        "11111000",
        "11110000",
        "11100000",
        "00000000",
        "00000000",
    ),
    FAR,
)
PUFF = indexed_tile(
    (
        "00000000",
        "00011000",
        "00111100",
        "00111100",
        "00011000",
        "00000000",
        "00000000",
        "00000000",
    ),
    FAR,
)
SLOPE_L = indexed_tile(
    (
        "00000000",
        "00000000",
        "00000002",
        "00000222",
        "00022222",
        "00222222",
        "02222222",
        "22222222",
    ),
    FAR,
)
PEAK = indexed_tile(
    (
        "00000000",
        "00000000",
        "00022000",
        "00222200",
        "02222220",
        "22222222",
        "22222222",
        "22222222",
    ),
    FAR,
)
SLOPE_R = indexed_tile(
    (
        "00000000",
        "00000000",
        "20000000",
        "22200000",
        "22222000",
        "22222200",
        "22222220",
        "22222222",
    ),
    FAR,
)
HILL_BODY = indexed_tile(
    (
        "22222222",
        "22222222",
        "22232222",
        "22222222",
        "22222322",
        "22222222",
        "22222222",
        "22222222",
    ),
    FAR,
)
DECOR = {
    "cloud_l": CLOUD_L,
    "cloud_m": CLOUD_M,
    "cloud_r": CLOUD_R,
    "puff": PUFF,
    "slope_l": SLOPE_L,
    "peak": PEAK,
    "slope_r": SLOPE_R,
    "hill": HILL_BODY,
}


def decoration_name(tile_x: int, tile_y: int) -> str | None:
    # Rows 0-4 scroll very slowly, rows 5-9 a bit faster. Both stay above the floor.
    if tile_y == 1 and tile_x % 16 in (3, 4, 5):
        return ("cloud_l", "cloud_m", "cloud_r")[tile_x % 16 - 3]
    if tile_y == 2 and tile_x % 22 in (12, 13, 14):
        return ("cloud_l", "cloud_m", "cloud_r")[tile_x % 22 - 12]
    if tile_y == 3 and tile_x % 14 == 8:
        return "puff"
    phase = tile_x % 10
    if phase >= 4:
        return None
    if tile_y == 6:
        return ("slope_l", "peak", "peak", "slope_r")[phase]
    if tile_y in (7, 8):
        return "hill"
    return None


def solid_top(segment: dict, x: int) -> int | None:
    for x0, x1 in segment["pits"]:
        if x0 <= x <= x1:
            return None
    tops = [top for x0, x1, top in segment["floor"] + segment["raised"] if x0 <= x <= x1]
    if not tops:
        return None
    return min(tops)


def paint_lives() -> list[list[tuple[int, int, int, int]]]:
    """Four frames. Frame index matches `lives`: a heart and the digit 0 through 3.

    On Blob Red the heart (RED, mid band) is red, the digit (CREAM, light
    band) is cream, and the badge (BLACK) is black.
    """
    heart = (
        "0110110",
        "1111111",
        "1111111",
        "0111110",
        "0011100",
        "0001000",
    )
    image = blank(64, 16, BLACK)
    for frame in range(4):
        ox = frame * 16
        for y, row in enumerate(heart):
            for x, bit in enumerate(row):
                if bit == "1":
                    image[5 + y][ox + x] = RED
        draw_digit(image, ox + 9, 3, frame, CREAM, 2)
    return image


def paint_level(
    width: int,
    height: int,
    solid_at,
) -> tuple[list[list[tuple[int, int, int, int]]], list[int], list[int]]:
    ground = {0: sky_tile(), 1: grass_tile(), 2: dirt_tile()}
    image = blank(width * 8, height * 8, SKY)
    collisions = [0] * (width * height)
    tile_colors = [0] * (width * height)
    for tile_y in range(height):
        for tile_x in range(width):
            top = solid_at(tile_x)
            cell = tile_y * width + tile_x
            if top is None or tile_y < top:
                name = decoration_name(tile_x, tile_y)
                pattern = DECOR[name] if name else ground[0]
                if name:
                    tile_colors[cell] = 1
            elif tile_y == top:
                pattern = ground[1]
                collisions[cell] = 15
            else:
                pattern = ground[2]
                collisions[cell] = 15
            for py in range(8):
                for px in range(8):
                    image[tile_y * 8 + py][tile_x * 8 + px] = pattern[py][px]
    return image, collisions, tile_colors


def paint_segment(segment: dict) -> tuple[list[list[tuple[int, int, int, int]]], list[int], list[int]]:
    return paint_level(SEG_W, LEVEL_H, lambda tile_x: solid_top(segment, tile_x))


def unique_tiles(image: list[list[tuple[int, int, int, int]]], tile: int = 8) -> int:
    height = len(image)
    width = len(image[0])
    seen: set[bytes] = set()
    for ty in range(0, height, tile):
        for tx in range(0, width, tile):
            blob = bytearray()
            for y in range(tile):
                for x in range(tile):
                    blob.extend(image[ty + y][tx + x])
            seen.add(bytes(blob))
    return len(seen)


def tile_ref(name: str, x: int, slice_x: int, palette_index: int = 0) -> dict:
    return {
        "id": uid(name),
        "x": x,
        "y": 0,
        "sliceX": slice_x,
        "sliceY": 0,
        "flipX": False,
        "flipY": False,
        "palette": 0,
        "paletteIndex": palette_index,
        "objPalette": "OBP0",
        "priority": False,
    }


# Scene sprite palette slots. In color mode GB Studio 4 reads the palette
# from each sprite tile's paletteIndex (compileSprites.ts makeProps), not from
# the actor's paletteId. Slot 0 is Grok Bot; the picker color swaps slot 0.
SLOT = {"scoredigit": 2, "scoretens": 2, "enemy": 1, "lives": 1, "electron": 2, "ammo": 2, "chip": 3, "flyer": 5, "turret": 3, "bolt": 1, "roadster": 4}


def frame_of(name: str, slice_x: int) -> dict:
    palette_index = SLOT.get(name.split("-")[0], 0)
    return {
        "id": uid(name),
        "tiles": [
            tile_ref(name + "-l", 0, slice_x, palette_index),
            tile_ref(name + "-r", 8, slice_x + 8, palette_index),
        ],
    }


def empty_frame(name: str) -> dict:
    return {"id": uid(name), "frames": [{"id": uid(name + "-frame"), "tiles": []}]}


def sprite_resource(
    *,
    name: str,
    symbol: str,
    filename: str,
    image_path: Path,
    width: int,
    height: int,
    animation_type: str,
    animations: list[dict],
    num_tiles: int,
    canvas_width: int = 16,
    bounds: tuple[int, int, int, int] | None = None,
    canvas_height: int = 16,
) -> dict:
    # Bounds are (x, y, w, h) from the top-left of the 16 px base, y down
    # (compileBounds in generateGBVMData.ts).
    bx, by, bw, bh = bounds or (min(0, 8 - canvas_width // 2), 0, canvas_width, 16)
    return {
        "_resourceType": "sprite",
        "id": uid(symbol),
        "name": name,
        "symbol": symbol,
        "states": [
            {
                "id": uid(symbol + "-state"),
                "name": "",
                "animationType": animation_type,
                "flipLeft": True,
                "animations": animations,
            }
        ],
        "numTiles": num_tiles,
        "canvasOriginX": 0,
        "canvasOriginY": 0,
        "canvasWidth": canvas_width,
        "canvasHeight": canvas_height,
        # Bounds are relative to the same 16 px base as metasprite tiles, so a
        # wider canvas starts (canvas_width / 2 - 8) px left of it.
        "boundsX": bx,
        "boundsY": by,
        "boundsWidth": bw,
        "boundsHeight": bh,
        "animSpeed": 8 if animation_type == "platform_player" else 15,
        "filename": filename,
        "width": width,
        "height": height,
        "checksum": sha1(image_path),
    }


def player_animations(prefix: str = "") -> list[dict]:
    # Engine slots: idle R, idle L, jump R, jump L, move R, move L, climb, spare.
    # Left-facing slots stay empty because flipLeft mirrors the right-facing art.
    # The round sheet keeps its original ids; the square sheet adds a prefix.
    p = prefix + "player"
    idle = frame_of(f"{p}-idle", 0)
    walk_a = frame_of(f"{p}-walk-a", 16)
    walk_b = frame_of(f"{p}-walk-b", 32)
    jump = frame_of(f"{p}-jump", 48)
    return [
        {"id": uid(f"{p}-anim-idle"), "frames": [idle]},
        empty_frame(f"{p}-anim-idle-left"),
        {"id": uid(f"{p}-anim-jump"), "frames": [jump]},
        empty_frame(f"{p}-anim-jump-left"),
        {"id": uid(f"{p}-anim-move"), "frames": [walk_a, walk_b]},
        empty_frame(f"{p}-anim-move-left"),
        {"id": uid(f"{p}-anim-climb"), "frames": [idle]},
        empty_frame(f"{p}-anim-spare"),
    ]


def wide_animation(name: str, width: int) -> list[dict]:
    """One frame built from width/8 8x16 tiles side by side.

    GB Studio places metasprite tile x relative to the 16 px base at the
    centre of the canvas, not the canvas's left edge (originX = canvasWidth/2 - 8
    in optimiseTiles, src/lib/sprites/readSpriteData.ts; MetaspriteEditor.tsx).
    A tile that starts past the canvas is masked as Unknown, counts as blank,
    and is dropped from the compiled frame. So a 32 px sheet's tiles go at
    x = -8, 0, 8, 16.
    """
    palette_index = SLOT.get(name, 0)
    left = 8 - width // 2
    frame = {
        "id": uid(name + "-f0"),
        "tiles": [
            tile_ref(f"{name}-t{index}", left + index * 8, index * 8, palette_index) for index in range(width // 8)
        ],
    }
    animations = [{"id": uid(name + "-anim0"), "frames": [frame]}]
    animations.extend(empty_frame(f"{name}-anim{index}") for index in range(1, 8))
    return animations


def check_wide_coverage(name: str, image: list, width: int) -> None:
    """Every opaque pixel must fall in a tile wide_animation places on screen.

    Tile x is relative to the centred 16 px base (originX = width/2 - 8), so
    tile i covers canvas columns originX + (8 - width/2) + 8i .. +7. A column
    left uncovered would be cut off in game (the old "missing nose" bug).
    """
    origin = width // 2 - 8
    covered = set()
    for index in range(width // 8):
        start = origin + (8 - width // 2) + index * 8
        if not 0 <= start <= width - 8:
            raise SystemExit(f"{name}: tile {index} starts outside the canvas at {start}")
        covered.update(range(start, start + 8))
    for row in image:
        for x, pixel in enumerate(row):
            if pixel[3] and x not in covered:
                raise SystemExit(f"{name}: opaque pixel at column {x} is not in any tile")


def fixed_animation(name: str) -> list[dict]:
    frame = frame_of(name, 0)
    animations = [{"id": uid(name + "-anim0"), "frames": [frame]}]
    animations.extend(empty_frame(f"{name}-anim{index}") for index in range(1, 8))
    return animations


def lives_animations() -> list[dict]:
    # Frame index matches the lives variable: heart plus 0, 1, 2, or 3.
    return frames_animation("lives", 4)


def frames_animation(name: str, count: int) -> list[dict]:
    frames = [frame_of(f"{name}-f{index}", index * 16) for index in range(count)]
    animations = [{"id": uid(name + "-anim0"), "frames": frames}]
    animations.extend(empty_frame(f"{name}-anim{index}") for index in range(1, 8))
    return animations


def background_resource(
    *,
    name: str,
    symbol: str,
    filename: str,
    tiles_x: int,
    tiles_y: int,
    tile_colors: list[int],
) -> dict:
    return {
        "_resourceType": "background",
        "id": uid(symbol),
        "name": name,
        "symbol": symbol,
        "tileColors": compress8(tile_colors),
        "filename": filename,
        "width": tiles_x,
        "height": tiles_y,
        "imageWidth": tiles_x * 8,
        "imageHeight": tiles_y * 8,
        "autoColor": False,
    }


def sprite_palette(light: str, mid: str, dark: str) -> list[str]:
    """Palette colors in GB Studio's sprite order: [light, mid, unused, dark].

    Palette color 2 is never shown on sprites; it repeats light so the
    palette editor swatches still look sensible.
    """
    return [light, mid, light, dark]


def palette(name: str, colors: list[str]) -> dict:
    return {
        "_resourceType": "palette",
        "id": uid("palette-" + name),
        "name": name,
        "colors": colors,
    }


def event(name: str, command: str, args: dict | None = None, children: dict | None = None) -> dict:
    data: dict = {"id": uid(name), "command": command}
    if args is not None:
        data["args"] = args
    if children is not None:
        data["children"] = children
    return data


def actor(
    *,
    name: str,
    symbol: str,
    index: int,
    x: int,
    y: int,
    sprite_symbol: str,
    palette_name: str,
    script: list,
    update_script: list | None = None,
    hit1_script: list | None = None,
    frame: int = 0,
    animate: bool = True,
    pinned: bool = False,
    collision_group: str = "1",
    move_speed: int = 1,
) -> dict:
    # Callers key actors as actor_<segment>-<kind>N; the id stays hashed from that
    # key (stable ids, and enemy_symbols() splits on "-"), but the emitted C/asm
    # symbol must be a valid identifier: the assembler rejects hyphens.
    c_symbol = symbol.replace("-", "_")
    assert SYMBOL_RE.fullmatch(c_symbol), f"bad actor symbol {c_symbol!r}"
    return {
        "_resourceType": "actor",
        "id": uid(symbol),
        "_index": index,
        "symbol": c_symbol,
        "prefabId": "",
        "name": name,
        "coordinateType": "tiles",
        "x": x,
        "y": y,
        "frame": frame,
        "animate": animate,
        "spriteSheetId": uid(sprite_symbol),
        "paletteId": uid("palette-" + palette_name),
        "direction": "right",
        "moveSpeed": move_speed,
        # 255 is GB Studio's "None" animation speed (ANIM_PAUSED). Without it the
        # engine cycles every multi-frame sheet regardless of "animate", so HUD
        # counters and the Press Start strips scrolled through their frames.
        "animSpeed": 15 if animate else 255,
        "isPinned": pinned,
        "persistent": False,
        "collisionGroup": collision_group,
        "collisionExtraFlags": [],
        "prefabScriptOverrides": {},
        "script": script,
        "startScript": [],
        "updateScript": update_script or [],
        "hit1Script": hit1_script or [],
        "hit2Script": [],
        "hit3Script": [],
    }


def trigger(name: str, symbol: str, index: int, x: int, y: int, width: int, height: int, script: list) -> dict:
    return {
        "_resourceType": "trigger",
        "id": uid(symbol),
        "_index": index,
        "symbol": symbol,
        "prefabId": "",
        "name": name,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "prefabScriptOverrides": {},
        "script": script,
        "leaveScript": [],
    }


def scene(
    *,
    name: str,
    symbol: str,
    index: int,
    x: int,
    y: int,
    width: int,
    height: int,
    background_symbol: str,
    palette_ids: list[str],
    sprite_palette_ids: list[str],
    script: list,
    collisions: list[int],
    parallax: list | None = None,
    scene_type: str = "PLATFORM",
    player_hit3: list | None = None,
) -> dict:
    data = {
        "_resourceType": "scene",
        "id": uid(symbol),
        "_index": index,
        "type": scene_type,
        "name": name,
        "symbol": symbol,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "backgroundId": uid(background_symbol),
        "tilesetId": "",
        "colorModeOverride": "none",
        "paletteIds": palette_ids,
        "spritePaletteIds": sprite_palette_ids,
        "autoFadeSpeed": 1,
        "script": script,
        "playerHit1Script": [],
        "playerHit2Script": [],
        "playerHit3Script": player_hit3 or [],
        "collisions": compress8(collisions),
    }
    if parallax:
        data["parallax"] = parallax
    return data


def beep(name: str, pitch: int) -> dict:
    return event(
        name,
        "EVENT_SOUND_PLAY_EFFECT",
        {
            "type": "beep",
            "priority": "low",
            "pitch": pitch,
            "duration": 0.12,
            "units": "time",
            "wait": False,
        },
    )


def deactivate(name: str) -> dict:
    return event(name, "EVENT_ACTOR_DEACTIVATE", {"actorId": "$self$"})


def set_number(name: str, variable: str, number: int) -> dict:
    return event(
        name,
        "EVENT_SET_VALUE",
        {"variable": variable, "value": {"type": "number", "value": number}},
    )


def if_value(name: str, variable: str, operator: str, comparator: int, true: list, false: list | None = None) -> dict:
    args = {
        "variable": variable,
        "operator": operator,
        "comparator": comparator,
        "__collapseElse": false is None,
    }
    children = {"true": true}
    if false is not None:
        args["__collapseElse"] = False
        children["false"] = false
    return event(name, "EVENT_IF_VALUE", args, children)


def switch_scene(name: str, scene_symbol: str, x: int, y: int) -> dict:
    return event(
        name,
        "EVENT_SWITCH_SCENE",
        {
            "sceneId": uid(scene_symbol),
            "x": {"type": "number", "value": x},
            "y": {"type": "number", "value": y},
            "direction": "right",
            "fadeSpeed": "2",
        },
    )


def move_by(name: str, tiles: int) -> dict:
    return event(
        name,
        "EVENT_ACTOR_MOVE_RELATIVE",
        {
            "actorId": "$self$",
            "x": {"type": "number", "value": tiles},
            "y": {"type": "number", "value": 0},
            "units": "tiles",
            "moveType": "horizontal",
            "useCollisions": True,
            "collideWith": ["walls"],
        },
    )


def wait_frames(name: str, frames: int) -> dict:
    return event(
        name,
        "EVENT_WAIT",
        {
            "units": "frames",
            "frames": {"type": "number", "value": frames},
            "time": {"type": "number", "value": round(frames / 60, 2)},
        },
    )


def shake(name: str, seconds: float, magnitude: int) -> dict:
    return event(
        name,
        "EVENT_CAMERA_SHAKE",
        {
            "time": seconds,
            "units": "time",
            "shakeDirection": "horizontal",
            "magnitude": {"type": "number", "value": magnitude},
        },
    )


def fade(name: str, direction: str) -> dict:
    command = "EVENT_FADE_OUT" if direction == "out" else "EVENT_FADE_IN"
    return event(name, command, {"speed": "2"})


def lose_life(name: str, lives_symbol: str, alive: list, dead: list) -> list:
    # Variable 1 is lives. Variable 4 is the hit count toward the next life.
    return [
        event(f"{name}-dec-life", "EVENT_DEC_VALUE", {"variable": "1"}),
        set_number(f"{name}-clear-hits", "4", 0),
        show_lives(f"{name}-hearts", lives_symbol),
        if_value(f"{name}-dead", "1", "==", 0, dead, alive),
    ]


def reset_run(name: str) -> list:
    """Lives 3, and ammo, chip, hits, score, powered, hurt lock, level-done 0."""
    return [
        set_number(f"{name}-lives", "1", 3),
        set_number(f"{name}-ammo", "0", 0),
        set_number(f"{name}-chip", "2", 0),
        set_number(f"{name}-hits", "4", 0),
        set_number(f"{name}-score", SCORE_VAR, 0),
        set_number(f"{name}-power", POWER_VAR, 0),
        set_number(f"{name}-hurt", HURT_LOCK, 0),
        set_number(f"{name}-done", LEVEL_DONE, 0),
        set_number(f"{name}-respawning", RESPAWN_VAR, 0),
    ]


def game_over(name: str, fade_out_first: bool, from_hit: bool = False) -> list:
    """Game Over text, full reset of the run, then back to the title screen.

    from_hit: called from a hurt script, which owns hurt_lock == HURT_LIFE (3)
    while it takes the life. If the
    lock is anything else by the time the fade-out ends, the roadster (or a
    pit) has taken over, so Game Over is skipped: a last-life hit can never
    race LEVEL 1 CLEAR. The screen fades back in and the cutscene carries on.
    """
    steps = []
    if fade_out_first:
        steps.append(fade(f"{name}-over-out", "out"))
    over = [
        fade(f"{name}-over-in", "in"),
        event(f"{name}-over", "EVENT_TEXT", {"text": "Game Over"}),
        # Full reset so the next game starts clean (Green Hills' init resets
        # these again when the new game starts).
        *reset_run(f"{name}-over-reset"),
        switch_scene(f"{name}-to-title", "scene_title", *MENU_PLAYER),
    ]
    if from_hit:
        return steps + [if_value(f"{name}-over-check", HURT_LOCK, "==", HURT_LIFE, over, [fade(f"{name}-over-skip-in", "in")])]
    return steps + over


def enemy_update(suffix: str) -> list:
    return [
        move_by(f"{suffix}-move-right", 3),
        wait_frames(f"{suffix}-wait-right", 20),
        move_by(f"{suffix}-move-left", -3),
        wait_frames(f"{suffix}-wait-left", 20),
    ]


def move_path(name: str, dx: int, dy: int) -> dict:
    return event(
        name,
        "EVENT_ACTOR_MOVE_RELATIVE",
        {
            "actorId": "$self$",
            "x": {"type": "number", "value": dx},
            "y": {"type": "number", "value": dy},
            "units": "tiles",
            "moveType": "diagonal",
            "useCollisions": False,
            "collideWith": [],
        },
    )


def flyer_update(suffix: str) -> list:
    """A bobbing left/right loop: two diagonal hops each way, 4 tiles wide."""
    steps = []
    for index, (dx, dy) in enumerate(((2, -1), (2, 1), (-2, -1), (-2, 1))):
        steps.append(move_path(f"{suffix}-path{index}", dx, dy))
    steps.append(wait_frames(f"{suffix}-path-wait", 10))
    return steps


def launch_bolt(name: str) -> dict:
    # Group 3 with mask "player": a hit runs the scene's player hit 3 script.
    return event(
        name,
        "EVENT_LAUNCH_PROJECTILE",
        {
            "spriteSheetId": uid("sprite_bolt"),
            "spriteStateId": uid("sprite_bolt-state"),
            "actorId": "$self$",
            "x": 0,
            "y": 0,
            "directionType": "target",
            "targetActorId": "player",
            "otherActorId": "$self$",
            "direction": "left",
            "speed": 2,
            "animSpeed": 15,
            "lifeTime": BOLT_LIFE,
            "initialOffset": 8,
            "loopAnim": True,
            "destroyOnHit": True,
            "collisionGroup": "3",
            "collisionMask": ["player"],
        },
    )


TOWER_RANGE = 9  # tiles: about half a screen, so the tower is inside the camera frame


def turret_update(suffix: str) -> list:
    # GB Studio only runs update scripts for active actors (on screen plus a
    # small margin). On top of that the tower only fires when Grok Bot is
    # within TOWER_RANGE tiles, i.e. the tower is inside the camera frame
    # (the camera follows the player), so it never shoots from off screen.
    return [
        wait_frames(f"{suffix}-reload", 120),
        unless_done(f"{suffix}-fire-done-check", [event(
            f"{suffix}-in-frame",
            "EVENT_IF_ACTOR_DISTANCE_FROM_ACTOR",
            {
                "actorId": "player",
                "operator": "<=",
                "distance": {"type": "number", "value": TOWER_RANGE},
                "otherActorId": "$self$",
                "__collapseElse": True,
            },
            {
                "true": [
                    beep(f"{suffix}-fire-sound", 4),
                    launch_bolt(f"{suffix}-fire"),
                ],
                "false": [],
            },
        )]),
    ]


def tower_script(suffix: str, segment: dict) -> list:
    """Touching a tower always hurts; a stomp counts as a touch and hurts too. Only electron shots kill it."""
    return hurt_steps(suffix, segment)


def score_digit_value(place: int) -> dict:
    """(score / place) % 10 as a GB Studio script value."""
    return {
        "type": "mod",
        "valueA": {
            "type": "div",
            "valueA": {"type": "variable", "value": SCORE_VAR},
            "valueB": {"type": "number", "value": place},
        },
        "valueB": {"type": "number", "value": 10},
    }


def show_score(name: str, key: str) -> list:
    return [
        event(
            f"{name}-score-{tag}",
            "EVENT_ACTOR_SET_FRAME",
            {"actorId": uid(f"actor_score_{tag}_{key}"), "frame": score_digit_value(place)},
        )
        for tag, place, _sprite in SCORE_DIGITS
    ]


def add_score(name: str, key: str, points: int) -> list:
    return [
        event(
            f"{name}-score-add",
            "EVENT_SET_VALUE",
            {
                "variable": SCORE_VAR,
                "value": {
                    "type": "add",
                    "valueA": {"type": "variable", "value": SCORE_VAR},
                    "valueB": {"type": "number", "value": points},
                },
            },
        ),
        *show_score(f"{name}-hud", key),
    ]


def points_for(suffix: str) -> int:
    for kind, points in POINTS.items():
        if f"-{kind}" in suffix:
            return points
    return 0


def vanish_blob(suffix: str, bounce: bool) -> list:
    # Hide first so the sprite is gone even if deactivate ends the script.
    steps = [
        event(f"blob-hide-{suffix}", "EVENT_ACTOR_HIDE", {"actorId": "$self$"}),
        event(
            f"blob-nocol-{suffix}",
            "EVENT_ACTOR_COLLISIONS_DISABLE",
            {"actorId": "$self$"},
        ),
        event(f"blob-stop-{suffix}", "EVENT_ACTOR_STOP_UPDATE", {"actorId": "$self$"}),
        beep(f"blob-stomp-sound-{suffix}", 6 if bounce else 5),
    ]
    if bounce:
        steps.append(event(f"blob-bounce-{suffix}", "EVENT_PLAYER_BOUNCE", {"height": "medium"}))
    # Suffixes look like "hills-blob3-above": the half's key, then the kind.
    steps.extend(add_score(f"blob-{suffix}", suffix.split("-")[0], points_for(suffix)))
    steps.append(deactivate(f"blob-stomp-hide-{suffix}"))
    return steps


def blink_player(name: str, times: int = 5) -> list:
    """About a second of hide/show flicker; doubles as the invulnerable window."""
    steps = []
    for index in range(times):
        steps += [
            event(f"{name}-blink-hide{index}", "EVENT_ACTOR_HIDE", {"actorId": "player"}),
            wait_frames(f"{name}-blink-off{index}", 6),
            event(f"{name}-blink-show{index}", "EVENT_ACTOR_SHOW", {"actorId": "player"}),
            wait_frames(f"{name}-blink-on{index}", 6),
        ]
    return steps


def lose_power(name: str, segment: dict) -> list:
    """A hit while powered costs the power-up and all electron ammo, not a life."""
    return [
        set_number(f"{name}-unpower", POWER_VAR, 0),
        set_number(f"{name}-unpower-ammo", "0", 0),
        show_ammo(f"{name}-unpower-ammo-hud", f"actor_ammo_{segment['key']}"),
        *player_palette_events(f"{name}-unpower-pal"),
        beep(f"{name}-unpower-sound", 3),
        unless_done(f"{name}-unpower-knock-check", [
            event(f"{name}-unpower-knock", "EVENT_PLATFORMER_STATE_SET", {"state": "knockback"})
        ]),
        *blink_player(f"{name}-unpower"),
    ]


# hurt_lock values: 0 free, 1 a hit script is running, 2 held by a pit fall
# or the roadster cutscene (released only by that script or scene init).
HURT_HOLD = 2
# 3: a hit script is taking a life (claimed from 1 just before the
# decrement). 4: a pit started while a hit was taking a life, so the pit
# falls and respawns without taking a second one. The roadster counts down
# from ROADSTER_HOLD + 60 to ROADSTER_HOLD, well clear of 0-4.
HURT_LIFE = 3
HURT_PIT_FREE = 4
ROADSTER_HOLD = 10
# Variable 3: 1 once the roadster has been touched. Every hurt path checks it
# first, and again right before knockback (a hit script already running when
# the roadster starts must not knock the player out of the cutscene).
LEVEL_DONE = "3"
# Variable 10: 1 while a lost life reloads the current half. Respawning by
# Change Scene (instead of moving the player inside the live scene) gives a
# clean actor, projectile and OAM state; the half's init then keeps lives,
# score, ammo, chip and power instead of resetting them, and starts a short
# invulnerability window (lock HURT_RESPAWN, released by timer 1).
RESPAWN_VAR = "10"
HURT_RESPAWN = 5


def respawn_reload(name: str, segment: dict) -> list:
    return [
        set_number(f"{name}-respawn-flag", RESPAWN_VAR, 1),
        switch_scene(f"{name}-respawn-reload", segment["symbol"], *PLAYER_START),
    ]


def unless_done(name: str, steps: list) -> dict:
    return if_value(name, LEVEL_DONE, "==", 0, steps)
HURT_LOCK = "5"
HURT_GRACE_FRAMES = 60


def hurt_steps(suffix: str, segment: dict, held: bool = False) -> list:
    # Variable 5 is a hurt lock shared by every hazard: 0 = can be hurt,
    # 1 = a hit is being handled (about a second of grace). It replaces the
    # old EVENT_RATE_LIMIT on variable 5. GBVM's vm_rate_limit_const stores a
    # deadline (sys_time + frames) and skips the body while
    # (sys_time - deadline) >= 0x8000; the scene init set variable 5 to 0, so
    # whenever the 16-bit sys_time was 32768-65535 (from about 9 minutes after
    # power-on, for about 9 minutes of every 18) every hurt was skipped:
    # Grok Bot walked through blobs, bats, towers and bolts. Each scene init
    # resets the lock, so a script cut short by a scene switch cannot leave it
    # stuck. Values: 0 free, 1 this kind of hit script, HURT_HOLD (2) a pit
    # fall or the roadster; a hit only releases 1, the pit releases its own 2
    # after the respawn grace.
    lives_symbol = f"actor_lives_{segment['key']}"
    return [unless_done(f"{suffix}-hurt-done-check", [
        if_value(
            f"{suffix}-hurt-ready",
            HURT_LOCK,
            "==",
            # held: the caller (enemy_script) already took the lock 0 -> 1.
            1 if held else 0,
            [set_number(f"{suffix}-hurt-lock", HURT_LOCK, 1)]
            + [if_value(f"{suffix}-if-powered", POWER_VAR, "==", 1, lose_power(suffix, segment), [
                event(f"{suffix}-hit-inc", "EVENT_INC_VALUE", {"variable": "4"}),
                beep(f"{suffix}-hurt-sound", 2),
                unless_done(f"{suffix}-knockback-check", [
                    event(
                        f"{suffix}-knockback",
                        "EVENT_PLATFORMER_STATE_SET",
                        {"state": "knockback"},
                    )
                ]),
                shake(f"{suffix}-hurt-shake", 0.2, 3),
                if_value(
                    f"{suffix}-hit-check",
                    "4",
                    ">=",
                    3,
                    # Claim the life loss (1 -> 3). If a pit already holds the
                    # lock (2), the pit takes the life and this hit does not.
                    [if_value(f"{suffix}-life-claim", HURT_LOCK, "==", 1, [
                    set_number(f"{suffix}-life-claimed", HURT_LOCK, HURT_LIFE),
                    *lose_life(
                        suffix,
                        lives_symbol,
                        [
                            beep(f"{suffix}-life-sound", 1),
                            shake(f"{suffix}-life-shake", 0.4, 5),
                            # Like a pit: back to the start of this half.
                            unless_done(f"{suffix}-life-respawn-check", [
                                event(f"{suffix}-life-freeze", "EVENT_PLATFORMER_STATE_SET", {"state": "blank"}),
                                # B is unbound through the fade (like the pit),
                                # so no electron is spent while the screen is dark.
                                no_fire(f"{suffix}-life-nofire"),
                                # Reload this half at its start (see RESPAWN_VAR).
                                *respawn_reload(f"{suffix}-life", segment),
                            ]),
                        ],
                        game_over(suffix, True, from_hit=True),
                    ),
                    if_value(f"{suffix}-life-done", HURT_LOCK, "==", HURT_LIFE, [
                        set_number(f"{suffix}-life-unclaim", HURT_LOCK, 1)
                    ]),
                    ])],
                ),
                wait_frames(f"{suffix}-hurt-grace", HURT_GRACE_FRAMES),
            ])]
            # Only release our own lock (1). A pit or the roadster holds 2,
            # and a hit's grace that outlives a respawn must not cut it short.
            + [if_value(f"{suffix}-hurt-unlock-check", HURT_LOCK, "==", 1, [set_number(f"{suffix}-hurt-unlock", HURT_LOCK, 0)])],
        )
    ])]


def enemy_script(suffix: str, segment: dict) -> list:
    """Blob / Zap Bat contact: stomp (from above or falling) or get hurt.

    The hurt lock is checked and taken (0 -> 1) as the very first steps,
    before the relative-position and velocity tests. GBVM preempts a thread
    after a 17-instruction quantum (vm.h INSTRUCTIONS_PER_QUANT 0x10, post-
    decrement); a fresh hit thread starts with a full quantum, so a check and
    set within the first few instructions cannot interleave with another hit
    thread. Keep any new events after the lock, not ahead of it. With the
    lock busy, a stomp still works but a side touch does nothing.
    """

    def body(tag: str, held: bool) -> list:
        stomp_above = vanish_blob(tag + "-above", True)
        stomp_fall = vanish_blob(tag + "-fall", True)
        if held:
            release = [if_value(f"{tag}-stomp-unlock", HURT_LOCK, "==", 1, [set_number(f"{tag}-stomp-release", HURT_LOCK, 0)])]
            stomp_above = stomp_above + release
            stomp_fall = stomp_fall + [
                if_value(f"{tag}-stomp-unlock2", HURT_LOCK, "==", 1, [set_number(f"{tag}-stomp-release2", HURT_LOCK, 0)])
            ]
        hurt = hurt_steps(tag, segment, held=True) if held else []
        # Falling uses a positive Y velocity. A landing often overlaps the
        # blob, so "player is above" alone misses the stomp.
        falling = event(
            f"{tag}-if-falling",
            "EVENT_IF",
            {
                "condition": {
                    "type": "gt",
                    "valueA": {"type": "engineField", "value": "plat_vel_y"},
                    "valueB": {"type": "number", "value": 0},
                },
                "__collapseElse": False,
            },
            {"true": stomp_fall, "false": hurt},
        )
        return [
            event(
                f"{tag}-hit-if",
                "EVENT_IF_ACTOR_RELATIVE_TO_ACTOR",
                {
                    "actorId": "player",
                    "operation": "up",
                    "otherActorId": "$self$",
                    "__collapseElse": False,
                },
                {"true": stomp_above, "false": [falling]},
            )
        ]

    return [
        unless_done(
            f"{suffix}-contact-done-check",
            [
                if_value(
                    f"{suffix}-contact-lock",
                    HURT_LOCK,
                    "==",
                    0,
                    [set_number(f"{suffix}-contact-take", HURT_LOCK, 1), *body(suffix, True)],
                    body(f"{suffix}-busy", False),
                )
            ],
        )
    ]


def set_engine(name: str, key: str, number: int) -> dict:
    return event(
        name,
        "EVENT_ENGINE_FIELD_SET",
        {"engineFieldKey": key, "value": {"type": "number", "value": number}},
    )


def electron_script(name: str, ammo_symbol: str) -> list:
    # Ammo is kept through a respawn reload (RESPAWN_VAR) while the electrons
    # come back, so it could pass electron_total(). The badge has one frame
    # per value 0..electron_total() and gbvm wraps a larger frame offset
    # (actor_set_frame_offset: offset % frame count), so 9 would show 00.
    # Cap the count; the pickup still scores and vanishes.
    return [
        if_value(f"{name}-cap", "0", "<", electron_total(), [
            event(f"{name}-inc", "EVENT_INC_VALUE", {"variable": "0"}),
        ]),
        show_counter(f"{name}-ammo", ammo_symbol, "0"),
        *add_score(name, name.split("-")[0], POINTS["electron"]),
        beep(f"{name}-sound", 7),
        deactivate(f"{name}-hide"),
    ]


def chip_script(name: str) -> list:
    # The chip unlocks firing for the run (var 2) and powers Grok Bot up
    # (var 9): the outline glows until the next hit. It does not change the jump.
    return [
        set_number(f"{name}-flag", "2", 1),
        set_number(f"{name}-power", POWER_VAR, 1),
        *player_palette_events(f"{name}-pal"),
        *add_score(name, name.split("-")[0], POINTS["chip"]),
        beep(f"{name}-sound", 10),
        deactivate(f"{name}-hide"),
    ]


def launch_electron(name: str) -> dict:
    return event(
        name,
        "EVENT_LAUNCH_PROJECTILE",
        {
            "spriteSheetId": uid("sprite_electron"),
            "spriteStateId": uid("sprite_electron-state"),
            "actorId": "player",
            "x": 0,
            "y": 2,
            "directionType": "actor",
            "otherActorId": "player",
            "direction": "right",
            "speed": 3,
            "animSpeed": 15,
            "lifeTime": SHOT_LIFE,
            "initialOffset": 12,
            "loopAnim": True,
            "destroyOnHit": True,
            "collisionGroup": "1",
            "collisionMask": ["1"],
        },
    )


def no_fire(name: str) -> dict:
    """Unbind B so a cutscene or the pit fall cannot fire from the hidden player."""
    return event(name, "EVENT_REMOVE_INPUT_SCRIPT", {"input": ["b"]})


# Shot cap: one electron per SHOT_GAP seconds, each living SHOT_LIFE seconds,
# so at most MAX_SHOTS are in flight (2 sprites each on the player's row).
SHOT_GAP = 0.6
SHOT_LIFE = 0.55
MAX_SHOTS = 1
# Under the 2 s reload, so one bolt per tower. Short enough that even at run
# speed the 15 out-of-range tiles between towers 110 and 143 (0.78 s)
# outlast a bolt, so two bolts are never on screen together. 0.7 s = 42
# frames at 2 px/frame is about 11.3 tiles of worst-case diagonal reach,
# still past the ~10.3-tile truncated fire distance.
BOLT_LIFE = 0.7


def attach_fire(segment: dict, prefix: str | None = None) -> dict:
    # B still runs. A press fires only after the chip, and only while ammo remains.
    # A prefix gives re-attached copies (after a pit respawn) their own event ids.
    key = prefix or segment["key"]
    ammo_symbol = f"actor_ammo_{segment['key']}"
    # Take the electron first, then launch only if the count did not go
    # below 0. With today's code this branch cannot trigger: the ammo check
    # and the decrement are the first instructions of a fresh input thread,
    # inside one VM quantum, and new hit threads only start between frames.
    # It stays as a cheap guard (2 events) so ammo can never go negative if
    # events are ever added ahead of the decrement.
    shot = [
        event(f"{key}-shot-dec", "EVENT_DEC_VALUE", {"variable": "0"}),
        if_value(
            f"{key}-shot-still-ammo",
            "0",
            ">=",
            0,
            [
                show_counter(f"{key}-shot-hud", ammo_symbol, "0"),
                beep(f"{key}-shot-sound", 8),
                launch_electron(f"{key}-shot-launch"),
            ],
            [
                set_number(f"{key}-shot-clamp", "0", 0),
                show_counter(f"{key}-shot-clamp-hud", ammo_symbol, "0"),
            ],
        ),
    ]
    # No EVENT_RATE_LIMIT here (it had the same sys_time/0 init bug as the
    # hurt cooldown and could block firing for minutes). GBVM does not start
    # an input script again while it is still running (events_update checks
    # the handle), so waiting at the end of the shot is the rate limit.
    shot.append(wait_frames(f"{key}-shot-gap", round(SHOT_GAP * 60)))
    armed = if_value(f"{key}-shot-chip", "2", ">", 0, shot)
    has_ammo = if_value(f"{key}-shot-ammo", "0", ">", 0, [armed])
    return event(
        f"{key}-fire-input",
        "EVENT_SET_INPUT_SCRIPT",
        {"input": ["b"], "override": False},
        {"true": [has_ammo]},
    )


def enemy_symbols(segment: dict) -> list[str]:
    key = segment["key"]
    return [
        f"actor_{key}-{kind}{index + 1}"
        for field, kind in (("blobs", "blob"), ("flyers", "flyer"), ("turret", "turret"))
        for index in range(len(segment.get(field, [])))
    ]


def clear_hazards(name: str, segment: dict) -> list:
    """Level done: no enemy, tower or bolt may touch the player any more.

    LEVEL_DONE=1 makes every hurt path a no-op (checked first, and again
    before knockback). Bolts already in flight are NOT removed and still
    "hit": gbvm tests a player-mask projectile against PLAYER's bounds and
    collision group only (projectiles.c:120-126), not ACTOR_FLAG_COLLISION,
    so the bolt runs player hit 3, whose hurt path no-ops on LEVEL_DONE, and
    is destroyed. Player collisions are still disabled so actor contact
    cannot start anything. Deactivating each enemy terminates its update script
    (towers stop firing) and detaches its hit script (actor.c:276-281); they
    are hidden and their collisions disabled too, in case the engine's
    on-screen activation brings one back.
    """
    steps = [
        set_number(f"{name}-done", LEVEL_DONE, 1),
        event(f"{name}-player-nocollide", "EVENT_ACTOR_COLLISIONS_DISABLE", {"actorId": "player"}),
    ]
    for symbol in enemy_symbols(segment):
        tag = symbol.split("-")[-1]
        steps += [
            event(f"{name}-{tag}-nocollide", "EVENT_ACTOR_COLLISIONS_DISABLE", {"actorId": uid(symbol)}),
            event(f"{name}-{tag}-hide", "EVENT_ACTOR_HIDE", {"actorId": uid(symbol)}),
            event(f"{name}-{tag}-off", "EVENT_ACTOR_DEACTIVATE", {"actorId": uid(symbol)}),
        ]
    return steps


def roadster_script(name: str, segment: dict) -> list:
    """Level complete: hop in, drive off, lift off up and away, LEVEL CLEAR."""

    def drive(tag: str, dx: int, dy: int, kind: str) -> dict:
        return event(
            f"{name}-{tag}",
            "EVENT_ACTOR_MOVE_RELATIVE",
            {
                "actorId": "$self$",
                "x": {"type": "number", "value": dx},
                "y": {"type": "number", "value": dy},
                "units": "tiles",
                "moveType": kind,
                "useCollisions": False,
                "collideWith": [],
            },
        )

    return [
        set_number(f"{name}-done-first", LEVEL_DONE, 1),
        event(f"{name}-once", "EVENT_ACTOR_COLLISIONS_DISABLE", {"actorId": "$self$"}),
        event(f"{name}-freeze", "EVENT_PLATFORMER_STATE_SET", {"state": "blank"}),
        # Hold the hurt lock for the whole cutscene (like the pit): a bolt
        # still reaches the player in blank state and its knockback would
        # break the sequence. Never released here; the title scene does not
        # use it and Level 1's init clears it.
        # Counting the lock down from HURT_HOLD + 60 to HURT_HOLD keeps it at
        # 2 or more throughout (no hit can start or release it, and a hit
        # already on its last life skips Game Over, see game_over) while the
        # player is re-hidden every frame for 60 frames: longer than a
        # powered hit's blink_player, which could otherwise show Grok Bot
        # beside the car.
        set_number(f"{name}-hurt-hold", HURT_LOCK, ROADSTER_HOLD + 60),
        set_engine(f"{name}-stop-vx", "plat_vel_x", 0),
        set_engine(f"{name}-stop-vy", "plat_vel_y", 0),
        no_fire(f"{name}-nofire"),
        *clear_hazards(name, segment),
        event(f"{name}-board", "EVENT_ACTOR_HIDE", {"actorId": "player"}),
        beep(f"{name}-door", 6),
        event(
            f"{name}-hide-hold",
            "EVENT_LOOP_WHILE",
            {
                "condition": {
                    "type": "gt",
                    "valueA": {"type": "variable", "value": HURT_LOCK},
                    "valueB": {"type": "number", "value": ROADSTER_HOLD},
                }
            },
            {
                "true": [
                    event(f"{name}-hide-again", "EVENT_ACTOR_HIDE", {"actorId": "player"}),
                    # Re-assert blank every frame: a hit script that was
                    # already past its checks could still set knockback.
                    event(f"{name}-blank-again", "EVENT_PLATFORMER_STATE_SET", {"state": "blank"}),
                    wait_frames(f"{name}-hide-tick", 1),
                    event(f"{name}-hide-count", "EVENT_DEC_VALUE", {"variable": HURT_LOCK}),
                ]
            },
        ),
        beep(f"{name}-engine", 3),
        # Keep the drive short so the car stays on the screen the camera shows
        # (it follows the hidden player at the car's rest spot).
        drive("roll", 1, 0, "horizontal"),
        # Kickflip: a short hop, one full turn through the rotation frames
        # (about 4 frames each), back to frame 0, then the climb as before.
        beep(f"{name}-hop-sound", 7),
        drive("hop", 0, -1, "vertical"),
        *[
            step
            for index in list(range(1, len(KICKFLIP_ANGLES))) + [0]
            for step in (
                event(
                    f"{name}-flip{index}",
                    "EVENT_ACTOR_SET_FRAME",
                    {"actorId": "$self$", "frame": {"type": "number", "value": index}},
                ),
                wait_frames(f"{name}-flip-wait{index}", 4),
            )
        ],
        beep(f"{name}-lift", 9),
        drive("climb", 1, -3, "diagonal"),
        # Relative moves saturate at y=0, so the car cannot leave through the
        # top. It rises to row 2 (just under the HUD), blinks out and is hidden
        # there, which reads as flying off instead of parking on the edge.
        drive("away", 1, -8, "diagonal"),
        event(f"{name}-flash-off", "EVENT_ACTOR_HIDE", {"actorId": "$self$"}),
        wait_frames(f"{name}-flash-wait", 4),
        event(f"{name}-flash-on", "EVENT_ACTOR_SHOW", {"actorId": "$self$"}),
        wait_frames(f"{name}-flash-wait2", 4),
        event(f"{name}-gone", "EVENT_ACTOR_HIDE", {"actorId": "$self$"}),
        beep(f"{name}-whoosh", 10),
        wait_frames(f"{name}-beat", 20),
        # LEVEL 1 CLEAR is shown once, here or by the fallback exit, never both.
        *exit_script(name, name.split("-")[0]),
    ]


def exit_script(prefix: str, key: str) -> list:
    """Clear bonus, one LEVEL 1 CLEAR box with the final score, then the title.

    Each caller passes its own prefix so no event id is shared between the
    roadster and the fallback exit trigger. There is no separate clear scene.
    """
    return [
        *add_score(f"{prefix}-bonus", key, POINTS["clear"]),
        event(f"{prefix}-clear-text", "EVENT_TEXT", {"text": f"LEVEL 1 CLEAR\nSCORE ${SCORE_VAR}$"}),
        switch_scene(f"{prefix}-to-title", "scene_title", *MENU_PLAYER),
    ]


def show_counter(name: str, actor_symbol: str, variable: str) -> dict:
    return event(
        name,
        "EVENT_ACTOR_SET_FRAME",
        {
            "actorId": uid(actor_symbol),
            "frame": {"type": "variable", "value": variable},
        },
    )


def show_lives(name: str, actor_symbol: str) -> dict:
    return show_counter(name, actor_symbol, "1")


def show_ammo(name: str, actor_symbol: str) -> dict:
    return show_counter(name, actor_symbol, "0")


# Pixels per step of the scripted pit fall, 3 frames apart: it speeds up
# like gravity and carries Grok Bot from the pit mouth (row 15) off the
# bottom of the screen in about half a second.
FALL_STEPS = (2, 3, 4, 5, 6, 7, 8, 8, 8, 8)


def pit_script(name: str, segment: dict) -> list:
    # The trigger covers the pit mouth. Blank platformer state stops input and
    # the engine's own physics, then the script drops Grok Bot off screen so
    # the fall is visible. Then fade out and take the life (and any power-up).
    # A life still left fades back in at the start of this half. The last
    # life fades in on "Game Over".
    lives_symbol = f"actor_lives_{segment['key']}"
    fall = []
    for index, pixels in enumerate(FALL_STEPS):
        fall += [
            event(
                f"{name}-fall{index}",
                "EVENT_ACTOR_SET_POSITION_RELATIVE",
                {
                    "actorId": "player",
                    "x": {"type": "number", "value": 0},
                    "y": {"type": "number", "value": pixels},
                    "units": "pixels",
                },
            ),
            wait_frames(f"{name}-fall-wait{index}", 3),
        ]
    def alive(tag: str) -> list:
        # Reload this half at its start (see RESPAWN_VAR); the init gives
        # the respawn invulnerability window.
        return respawn_reload(tag, segment)

    return [
        event(f"{name}-freeze", "EVENT_PLATFORMER_STATE_SET", {"state": "blank"}),
        # Hold the hurt lock for the whole fall: a Bolt Tower bolt (the x=60
        # tower sits next to the High Ridge pit) still reaches the player in
        # blank state (projectiles.c tests PLAYER directly), and its hurt
        # script would set knockback mid-fall and could take a second life.
        # The alive path releases it after the respawn grace; Game Over
        # reloads the scene, whose init clears it.
        # A hit already taking a life (3) means this pit must not take
        # another: hold with HURT_PIT_FREE instead of HURT_HOLD.
        if_value(
            f"{name}-hurt-life-check",
            HURT_LOCK,
            "==",
            HURT_LIFE,
            [set_number(f"{name}-hurt-hold-free", HURT_LOCK, HURT_PIT_FREE)],
            [set_number(f"{name}-hurt-hold", HURT_LOCK, HURT_HOLD)],
        ),
        no_fire(f"{name}-nofire"),
        set_engine(f"{name}-stop-vx", "plat_vel_x", 0),
        set_engine(f"{name}-stop-vy", "plat_vel_y", 0),
        beep(f"{name}-fall-sound", 1),
        *fall,
        event(f"{name}-gone", "EVENT_ACTOR_HIDE", {"actorId": "player"}),
        wait_frames(f"{name}-pause", 12),
        fade(f"{name}-out", "out"),
        set_number(f"{name}-unpower", POWER_VAR, 0),
        *player_palette_events(f"{name}-unpower-pal"),
        if_value(
            f"{name}-life-free",
            HURT_LOCK,
            "==",
            HURT_PIT_FREE,
            # The hit already took the life (and skips its own Game Over
            # because the lock is no longer 3), so only check for 0 lives.
            [if_value(f"{name}-free-dead", "1", "==", 0, game_over(f"{name}-free", False), alive(f"{name}-free"))],
            lose_life(name, lives_symbol, alive(name), game_over(name, False)),
        ),
    ]



def segment_init(segment: dict) -> list:
    key = segment["key"]
    lives_symbol = f"actor_lives_{key}"
    ammo_symbol = f"actor_ammo_{key}"
    script = [
        event(
            f"{key}-music",
            "EVENT_MUSIC_PLAY",
            {"musicId": MUSIC_ID, "loop": True},
        )
    ]
    if segment["reset"]:
        script.append(if_value(f"{key}-new-run", RESPAWN_VAR, "==", 0, [
                set_number(f"{key}-electrons", "0", 0),
                set_number(f"{key}-power", POWER_VAR, 0),
                set_number(f"{key}-score", SCORE_VAR, 0),
                set_number(f"{key}-lives", "1", 3),
                set_number(f"{key}-chip", "2", 0),
                set_number(f"{key}-hits", "4", 0),
                set_engine(f"{key}-jump", "plat_jump_vel", BASE_JUMP),
        ]))
    # Both halves clear the hurt lock (see hurt_steps) and the level-done
    # flag, and make sure the player can be hit again. After a respawn
    # reload the lock is held at HURT_RESPAWN for HURT_GRACE_FRAMES instead.
    script.append(if_value(f"{key}-respawned", RESPAWN_VAR, "==", 1, [
        set_number(f"{key}-hurt-respawn", HURT_LOCK, HURT_RESPAWN),
        set_number(f"{key}-respawn-clear", RESPAWN_VAR, 0),
        event(
            f"{key}-respawn-grace",
            "EVENT_SET_TIMER_SCRIPT",
            {"timer": 1, "duration": HURT_GRACE_FRAMES / 60, "units": "time", "frames": HURT_GRACE_FRAMES},
            {"script": [
                if_value(f"{key}-grace-end", HURT_LOCK, "==", HURT_RESPAWN, [set_number(f"{key}-grace-release", HURT_LOCK, 0)]),
                event(f"{key}-grace-timer-off", "EVENT_TIMER_DISABLE", {"timer": 1}),
            ]},
        ),
    ], [set_number(f"{key}-hurt", HURT_LOCK, 0)]))
    script.append(set_number(f"{key}-not-done", LEVEL_DONE, 0))
    script.append(event(f"{key}-player-collide", "EVENT_ACTOR_COLLISIONS_ENABLE", {"actorId": "player"}))
    script.extend(apply_player_choice(key))
    script.append(show_lives(f"{key}-hearts", lives_symbol))
    script.append(show_ammo(f"{key}-ammo", ammo_symbol))
    script.extend(show_score(f"{key}-init", key))
    script.append(attach_fire(segment))
    return script


def shot_blob(suffix: str) -> list:
    return vanish_blob(suffix + "-shot", False)


def write_shapes_sheet(path: Path) -> None:
    """docs/shapes-sheet.png: one row per picker shape (player_shape order).

    Columns: idle, walk A, walk B, jump in the Grok Bot (white) palette, then
    the idle frame in Grok Red, Grok Yellow, and Grok Teal, as GB Studio's
    sprite palette slot 0 would color it. Scaled 4x on a sky backdrop.
    """
    scale, cell, gap = 4, 16, 2
    columns = 4 + len(GROK_COLORS) - 1
    width = (columns * (cell + gap) + gap) * scale
    height = (len(PLAYER_SHAPES) * (cell + gap) + gap) * scale
    sheet = blank(width, height, SKY)

    def recolor(pixel, colors):
        if pixel == CLEAR:
            return None
        # Sprite color 1/2/3 shows palette color 0/1/3 (see sprite_palette).
        hex_color = colors[(None, 0, 1, 3)[PLAYER_INDEXED.index(pixel)]]
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4)) + (255,)

    for row, shape in enumerate(PLAYER_SHAPES):
        frames = paint_shape_player(shape)
        cells = [(frame, GROK_COLORS[0][1]) for frame in range(4)]
        cells += [(0, colors) for _name, colors in GROK_COLORS[1:]]
        for column, (frame, colors) in enumerate(cells):
            ox = (gap + column * (cell + gap)) * scale
            oy = (gap + row * (cell + gap)) * scale
            for y in range(cell):
                for x in range(cell):
                    color = recolor(frames[y][frame * cell + x], colors)
                    if color is None:
                        continue
                    for sy in range(scale):
                        for sx in range(scale):
                            sheet[oy + y * scale + sy][ox + x * scale + sx] = color
    write_png(path, width, height, sheet)


def build_images() -> dict:
    sprites = ROOT / "assets" / "sprites"
    backgrounds = ROOT / "assets" / "backgrounds"
    ammo_frames = electron_total() + 1
    for shape in PLAYER_SHAPES:
        write_png_indexed(sprites / PLAYER_FILES[shape], 64, 16, paint_shape_player(shape), PLAYER_INDEXED)
    write_shapes_sheet(ROOT / "docs" / "shapes-sheet.png")
    for index, part in enumerate(paint_press_start()):
        write_png(sprites / f"press_start_{index}.png", 16, 16, part)
    write_png(sprites / "enemy_red_blob.png", 32, 16, paint_enemy())
    write_png(sprites / "electron.png", 16, 16, paint_electron())
    write_png(sprites / "silicon_chip.png", 16, 16, paint_chip())
    write_png(sprites / "flyer.png", 32, 16, paint_flyer())
    write_png(sprites / "score_digit.png", 160, 16, paint_score_digits(False))
    write_png(sprites / "score_tens.png", 160, 16, paint_score_digits(True))
    write_png(sprites / "turret.png", 16, 16, paint_turret())
    roadster = paint_roadster()
    check_wide_coverage("roadster", roadster, 32)
    flip = paint_roadster_flip()
    if flip_edge_problems(flip):
        raise SystemExit(f"roadster kickflip touches the canvas edge: {flip_edge_problems(flip)}")
    write_png(sprites / "roadster.png", 32 * len(KICKFLIP_ANGLES), 32, flip)
    write_png(sprites / "bolt.png", 16, 16, paint_bolt())
    write_png(sprites / "lives.png", 64, 16, paint_lives())
    write_png(sprites / "ammo.png", ammo_frames * 16, 16, paint_ammo())
    for stale in (
        "player_pink.png",
        "player_pink.png.gbsres",
        "collectible_star.png",
        "collectible_star.png.gbsres",
        "press_start.png",
        "press_start.png.gbsres",
        "coin.png",
        "coin.png.gbsres",
        "coin_hud.png",
        "coin_hud.png.gbsres",
    ):
        path = sprites / stale
        if path.exists():
            path.unlink()
    painted = {}
    for segment in SEGMENTS:
        image, collisions, colors = paint_segment(segment)
        write_png(backgrounds / segment["bg_file"], SEG_W * 8, LEVEL_H * 8, image)
        painted[segment["symbol"]] = {
            "tiles": unique_tiles(image),
            "collisions": collisions,
            "colors": colors,
        }
    for key, painter in (("title", paint_title), ("picker", paint_picker)):
        image, menu_collisions, menu_colors = painter()
        write_png(backgrounds / f"{key}.png", CLEAR_W * 8, CLEAR_H * 8, image)
        painted[key] = {
            "tiles": unique_tiles(image),
            "collisions": menu_collisions,
            "colors": menu_colors,
        }
    return painted


def delete_gbsres(path: Path) -> None:
    if path.exists():
        for child in path.glob("*.gbsres"):
            child.unlink()


def write_segment(
    segment: dict,
    collisions: list[int],
    bg_ids: list[str],
    sprite_ids: list[str],
) -> None:
    level_dir = ROOT / "project" / "scenes" / segment["folder"]
    actor_dir = level_dir / "actors"
    trigger_dir = level_dir / "triggers"
    delete_gbsres(actor_dir)
    delete_gbsres(trigger_dir)
    key = segment["key"]
    write_json(
        level_dir / "scene.gbsres",
        scene(
            name=segment["name"],
            symbol=segment["symbol"],
            index=segment["index"],
            x=world_x(segment["index"]),
            y=40,
            width=SEG_W,
            height=LEVEL_H,
            background_symbol=segment["bg_symbol"],
            palette_ids=bg_ids,
            sprite_palette_ids=sprite_ids,
            script=segment_init(segment),
            collisions=collisions,
            parallax=PARALLAX,
            # Turret bolts (projectile group 3) hurt like a blob's side touch.
            player_hit3=hurt_steps(f"{key}-bolt", segment) if segment.get("turret") else None,
        ),
    )
    next_index = 1
    write_json(
        actor_dir / "lives.gbsres",
        actor(
            name="Lives",
            symbol=f"actor_lives_{key}",
            index=0,
            x=LIVES_AT[0],
            y=LIVES_AT[1],
            sprite_symbol="sprite_lives",
            palette_name="Blob Red",
            script=[],
            frame=3,
            animate=False,
            pinned=True,
            collision_group="",
        ),
    )
    write_json(
        actor_dir / "ammo.gbsres",
        actor(
            name="Ammo",
            symbol=f"actor_ammo_{key}",
            index=next_index,
            x=AMMO_AT[0],
            y=AMMO_AT[1],
            sprite_symbol="sprite_ammo",
            palette_name="Electron Blue",
            script=[],
            frame=0,
            animate=False,
            pinned=True,
            collision_group="",
        ),
    )
    next_index += 1
    for offset, (tag, _place, sprite) in enumerate(SCORE_DIGITS):
        write_json(
            actor_dir / f"score_{tag}.gbsres",
            actor(
                name=f"Score {tag}",
                symbol=f"actor_score_{tag}_{key}",
                index=next_index,
                x=SCORE_AT + offset,
                y=0,
                sprite_symbol=sprite,
                palette_name="Electron Blue",
                script=[],
                animate=False,
                pinned=True,
                collision_group="",
            ),
        )
        next_index += 1
    for index, (x, y) in enumerate(segment["blobs"], start=1):
        suffix = f"{key}-blob{index}"
        write_json(
            actor_dir / f"blob_{index}.gbsres",
            actor(
                name=f"Grok Blob {index}",
                symbol=f"actor_{suffix}",
                index=next_index,
                x=x,
                y=y,
                sprite_symbol="sprite_enemy_red_blob",
                palette_name="Blob Red",
                script=enemy_script(suffix, segment),
                update_script=enemy_update(suffix),
                hit1_script=shot_blob(suffix),
            ),
        )
        next_index += 1
    for index, (x, y) in enumerate(segment["electrons"], start=1):
        suffix = f"{key}-electron{index}"
        write_json(
            actor_dir / f"electron_{index}.gbsres",
            actor(
                name=f"Electron {index}",
                symbol=f"actor_{suffix}",
                index=next_index,
                x=x,
                y=y,
                sprite_symbol="sprite_electron",
                palette_name="Electron Blue",
                script=electron_script(suffix, f"actor_ammo_{key}"),
                # Group 2 is touched by the player. Shots only hit group 1.
                collision_group="2",
            ),
        )
        next_index += 1
    for index, (x, y) in enumerate(segment.get("flyers", []), start=1):
        suffix = f"{key}-flyer{index}"
        write_json(
            actor_dir / f"flyer_{index}.gbsres",
            actor(
                name=f"Zap Bat {index}",
                symbol=f"actor_{suffix}",
                index=next_index,
                x=x,
                y=y,
                sprite_symbol="sprite_flyer",
                palette_name="Flyer Violet",
                # Same contact rules as a blob: stomp it, shoot it, or get hurt.
                script=enemy_script(suffix, segment),
                update_script=flyer_update(suffix),
                hit1_script=shot_blob(suffix),
            ),
        )
        next_index += 1
    for index, (x, y) in enumerate(segment.get("turret", []), start=1):
        suffix = f"{key}-turret{index}"
        write_json(
            actor_dir / f"turret_{index}.gbsres",
            actor(
                name=f"Bolt Tower {index}",
                symbol=f"actor_{suffix}",
                index=next_index,
                x=x,
                y=y,
                sprite_symbol="sprite_turret",
                palette_name="Chip Gray",
                script=tower_script(suffix, segment),
                update_script=turret_update(suffix),
                hit1_script=shot_blob(suffix),
            ),
        )
        next_index += 1
    for x, y in segment.get("roadster", []):
        write_json(
            actor_dir / "roadster.gbsres",
            actor(
                name="Roadster",
                symbol=f"actor_{key}-roadster",
                index=next_index,
                x=x,
                y=y,
                sprite_symbol="sprite_roadster",
                palette_name="Roadster White",
                script=roadster_script(f"{key}-roadster", segment),
                animate=False,
                # Group 2: touched by the player, ignored by electron shots.
                collision_group="2",
                move_speed=2,
            ),
        )
        next_index += 1
    for chip_index, (chip_x, chip_y) in enumerate(segment["chips"], start=1):
        # The first chip keeps its original id and file name.
        suffix = f"{key}-chip" if chip_index == 1 else f"{key}-chip{chip_index}"
        write_json(
            actor_dir / ("silicon_chip.gbsres" if chip_index == 1 else f"silicon_chip_{chip_index}.gbsres"),
            actor(
                name="Silicon Chip" if chip_index == 1 else f"Silicon Chip {chip_index}",
                symbol=f"actor_{suffix}",
                index=next_index,
                x=chip_x,
                y=chip_y,
                sprite_symbol="sprite_silicon_chip",
                palette_name="Chip Gray",
                script=chip_script(suffix),
                collision_group="2",
            ),
        )
        next_index += 1
    trigger_index = 0
    for pit_index, (x0, x1) in enumerate(segment["pits"], start=1):
        write_json(
            trigger_dir / f"pit_{pit_index}.gbsres",
            trigger(
                f"Pit {pit_index}",
                f"trigger_pit_{key}_{pit_index}",
                trigger_index,
                x0,
                FLOOR_TOP,
                x1 - x0 + 1,
                3,
                pit_script(f"{key}-pit{pit_index}", segment),
            ),
        )
        trigger_index += 1
    gate_script = (
        [switch_scene(f"{key}-continue", segment["next"], PLAYER_START[0], PLAYER_START[1])]
        if segment["next"]
        else exit_script("exit", key)
    )
    gate_name = "Continue" if segment["next"] else "Exit"
    gate_symbol = f"trigger_continue_{key}" if segment["next"] else "trigger_exit"
    gate_file = "continue.gbsres" if segment["next"] else "exit.gbsres"
    # With a roadster the old exit stays only as a 2-tile fallback at the
    # very end, in case Grok Bot jumps clean over the car.
    gate_x, gate_w = (SEG_W - 2, 2) if segment.get("roadster") else (SEG_W - 4, 4)
    write_json(
        trigger_dir / gate_file,
        trigger(gate_name, gate_symbol, trigger_index, gate_x, 9, gate_w, 6, gate_script),
    )


def build_resources(collisions: dict) -> None:
    sprites = ROOT / "assets" / "sprites"
    backgrounds = ROOT / "assets" / "backgrounds"
    write_json(
        sprites / "player_grok.png.gbsres",
        sprite_resource(
            name="player_grok",
            symbol="sprite_player_grok",
            filename="player_grok.png",
            image_path=sprites / "player_grok.png",
            width=64,
            height=16,
            animation_type="platform_player",
            animations=player_animations(),
            num_tiles=8,
        ),
    )
    write_json(
        sprites / "enemy_red_blob.png.gbsres",
        sprite_resource(
            name="enemy_red_blob",
            symbol="sprite_enemy_red_blob",
            filename="enemy_red_blob.png",
            image_path=sprites / "enemy_red_blob.png",
            width=32,
            height=16,
            animation_type="fixed",
            animations=frames_animation("enemy", 2),
            num_tiles=4,
        ),
    )
    write_json(
        sprites / "electron.png.gbsres",
        sprite_resource(
            name="electron",
            symbol="sprite_electron",
            filename="electron.png",
            image_path=sprites / "electron.png",
            width=16,
            height=16,
            animation_type="fixed",
            animations=fixed_animation("electron"),
            num_tiles=2,
        ),
    )
    write_json(
        sprites / "silicon_chip.png.gbsres",
        sprite_resource(
            name="silicon_chip",
            symbol="sprite_silicon_chip",
            filename="silicon_chip.png",
            image_path=sprites / "silicon_chip.png",
            width=16,
            height=16,
            animation_type="fixed",
            animations=fixed_animation("chip"),
            num_tiles=2,
        ),
    )
    write_json(
        sprites / "roadster.png.gbsres",
        sprite_resource(
            name="roadster",
            symbol="sprite_roadster",
            filename="roadster.png",
            image_path=sprites / "roadster.png",
            width=32 * len(KICKFLIP_ANGLES),
            height=32,
            animation_type="fixed",
            animations=flip_animation("roadster"),
            num_tiles=flip_tile_count(paint_roadster_flip()),
            canvas_width=32,
            canvas_height=32,
        ),
    )
    for name in ("turret", "bolt"):
        write_json(
            sprites / f"{name}.png.gbsres",
            sprite_resource(
                name=name,
                symbol=f"sprite_{name}",
                filename=f"{name}.png",
                image_path=sprites / f"{name}.png",
                width=16,
                height=16,
                animation_type="fixed",
                animations=fixed_animation(name),
                num_tiles=2,
                # The bolt is a ~7 px ball: an 8x8 centred box, so near misses miss.
                bounds=(4, 4, 8, 8) if name == "bolt" else None,
            ),
        )
    for name, tag in (("score_digit", "scoredigit"), ("score_tens", "scoretens")):
        write_json(
            sprites / f"{name}.png.gbsres",
            sprite_resource(
                name=name,
                symbol=f"sprite_{name}",
                filename=f"{name}.png",
                image_path=sprites / f"{name}.png",
                width=160,
                height=16,
                animation_type="fixed",
                animations=frames_animation(tag, 10),
                num_tiles=10 if name == "score_digit" else 20,
            ),
        )
    write_json(
        sprites / "flyer.png.gbsres",
        sprite_resource(
            name="flyer",
            symbol="sprite_flyer",
            filename="flyer.png",
            image_path=sprites / "flyer.png",
            width=32,
            height=16,
            animation_type="fixed",
            animations=frames_animation("flyer", 2),
            num_tiles=4,
        ),
    )
    write_json(
        sprites / "lives.png.gbsres",
        sprite_resource(
            name="lives",
            symbol="sprite_lives",
            filename="lives.png",
            image_path=sprites / "lives.png",
            width=64,
            height=16,
            animation_type="fixed",
            animations=lives_animations(),
            num_tiles=8,
        ),
    )
    write_json(
        sprites / "player_grok_square.png.gbsres",
        sprite_resource(
            name="player_grok_square",
            symbol="sprite_player_grok_square",
            filename="player_grok_square.png",
            image_path=sprites / "player_grok_square.png",
            width=64,
            height=16,
            animation_type="platform_player",
            animations=player_animations("square-"),
            num_tiles=8,
        ),
    )
    for shape in PLAYER_SHAPES[2:]:
        name = PLAYER_FILES[shape][:-4]
        write_json(
            sprites / (PLAYER_FILES[shape] + ".gbsres"),
            sprite_resource(
                name=name,
                symbol="sprite_" + name,
                filename=PLAYER_FILES[shape],
                image_path=sprites / PLAYER_FILES[shape],
                width=64,
                height=16,
                animation_type="platform_player",
                animations=player_animations(shape + "-"),
                num_tiles=8,
            ),
        )
    for index in range(PRESS_PARTS):
        write_json(
            sprites / f"press_start_{index}.png.gbsres",
            sprite_resource(
                name=f"press_start_{index}",
                symbol=f"sprite_press_start_{index}",
                filename=f"press_start_{index}.png",
                image_path=sprites / f"press_start_{index}.png",
                width=16,
                height=16,
                animation_type="fixed",
                animations=fixed_animation(f"press{index}"),
                num_tiles=2,
            ),
        )
    for key in ("title", "picker"):
        write_json(
            backgrounds / f"{key}.png.gbsres",
            background_resource(
                name=key,
                symbol=f"bg_{key}",
                filename=f"{key}.png",
                tiles_x=CLEAR_W,
                tiles_y=CLEAR_H,
                tile_colors=collisions[key]["colors"],
            ),
        )
    ammo_frames = electron_total() + 1
    write_json(
        sprites / "ammo.png.gbsres",
        sprite_resource(
            name="ammo",
            symbol="sprite_ammo",
            filename="ammo.png",
            image_path=sprites / "ammo.png",
            width=ammo_frames * 16,
            height=16,
            animation_type="fixed",
            animations=frames_animation("ammo", ammo_frames),
            num_tiles=ammo_frames * 2,
        ),
    )
    for segment in SEGMENTS:
        write_json(
            backgrounds / f"{segment['bg_file']}.gbsres",
            background_resource(
                name=segment["bg_file"].replace(".png", ""),
                symbol=segment["bg_symbol"],
                filename=segment["bg_file"],
                tiles_x=SEG_W,
                tiles_y=LEVEL_H,
                tile_colors=collisions[segment["symbol"]]["colors"],
            ),
        )

    palettes = ROOT / "project" / "palettes"
    write_json(
        palettes / "green_hills.gbsres",
        palette("Green Hills", ["B8F0E8", "68D070", "289038", "183028"]),
    )
    write_json(
        palettes / "far_hills.gbsres",
        palette("Far Hills", ["B8F0E8", "F8FCFF", "70C0D8", "287090"]),
    )
    write_json(
        palettes / "grok_bot.gbsres",
        palette("Grok Bot", GROK_COLORS[0][1]),
    )
    write_json(
        palettes / "blob_red.gbsres",
        palette("Blob Red", sprite_palette("F8E8D0", "F84848", "181018")),
    )
    write_json(
        palettes / "roadster_white.gbsres",
        palette("Roadster White", sprite_palette("F8F8F8", "586078", "101018")),
    )
    write_json(
        palettes / "electron_blue.gbsres",
        palette("Electron Blue", sprite_palette("E8F8FF", "50D8F8", "1848C8")),
    )
    write_json(
        palettes / "chip_gray.gbsres",
        palette("Chip Gray", sprite_palette("D8DCE8", "606878", "181018")),
    )
    write_json(
        palettes / "flyer_violet.gbsres",
        palette("Flyer Violet", sprite_palette("F0E8FF", "9868E0", "281848")),
    )
    for name, colors in POWER_COLORS:
        write_json(palettes / f"{name.lower().replace(' ', '_')}.gbsres", palette(name, colors))
    for name, colors in GROK_COLORS[1:]:
        write_json(palettes / f"{name.lower().replace(' ', '_')}.gbsres", palette(name, colors))
    for name, color in DOTS:
        write_json(
            palettes / f"{name.lower().replace(' ', '_')}.gbsres",
            palette(name, ["B8F0E8", color, "70C0D8", "183028"]),
        )
    for stale in ("grok_pink.gbsres", "star_yellow.gbsres", "coin_gold.gbsres"):
        path = palettes / stale
        if path.exists():
            path.unlink()

    bg_ids = [
        uid("palette-Green Hills"),
        uid("palette-Far Hills"),
        "default-bg-3",
        "default-bg-4",
        "default-bg-5",
        "default-bg-6",
        "dmg",
        "default-ui",
    ]
    sprite_ids = [
        uid("palette-Grok Bot"),
        uid("palette-Blob Red"),
        uid("palette-Electron Blue"),
        uid("palette-Chip Gray"),
        uid("palette-Roadster White"),
        uid("palette-Flyer Violet"),
        "default-sprite",
        "default-sprite",
    ]

    for segment in SEGMENTS:
        write_segment(segment, collisions[segment["symbol"]]["collisions"], bg_ids, sprite_ids)
    write_menus(collisions, bg_ids, sprite_ids)


# Title and picker. Variables 6 and 7 hold the picker choice and are never
# reset by Level 1, so the choice survives pits, Game Over, and a clear.
SHAPE_VAR = "6"
COLOR_VAR = "7"
# The menus hide the player and lock its movement, so where it starts does not matter.
MENU_PLAYER = (1, 1)
# Picker colors, in player_color (var 7) order. Sprite order: the fill is
# palette color 0 (the whole body), the outline palette color 1 (black), the
# eyes palette color 3 (black). See sprite_palette().
GROK_FILLS = [
    ("Grok Bot", "F4F4F8"),
    ("Grok Red", "F85050"),
    ("Grok Yellow", "F8E040"),
    ("Grok Teal", "40D8C8"),
]
GROK_COLORS = [(name, sprite_palette(fill, "181018", "181018")) for name, fill in GROK_FILLS]
# Powered-up look: the same fill with a glowing outline (palette color 1).
# A palette swap costs no VRAM, unlike 8 extra sprite sheets. Teal glow,
# except on the teal body, which glows yellow so the change still reads.
POWER_GLOW = {"Grok Teal": "F8F040"}
POWER_COLORS = [
    (name + " Power", sprite_palette(fill, POWER_GLOW.get(name, "30F8E0"), "181018")) for name, fill in GROK_FILLS
]
DOTS = [
    ("Dot White", "F8F8F8"),
    ("Dot Red", "F84848"),
    ("Dot Yellow", "F8D830"),
    ("Dot Teal", "30C8B8"),
]
SHAPES = ["sprite_" + PLAYER_FILES[shape][:-4] for shape in PLAYER_SHAPES]
PRESS_TEXT = "PRESS START"
# GB Studio 4 does not compile an actor's starting "frame" into the scene
# (generateGBVMData.ts only emits anim_tick, not a frame), so six actors that
# shared one 6-frame sheet all drew frame 0 ("PR"). Each strip is now its own
# single-frame 16x16 sheet: no frame index anywhere. A 6 px glyph pitch fits
# the 11 characters in 64 px, so 4 actors = 8 hardware sprites on the row
# (the old 6 actors were 12, over the 10-per-scanline limit).
PRESS_PARTS = 4
PRESS_AT = (6, 11)
TITLE_BOT_AT = (9, CLEAR_TOP - 2)
PICKER_BOT_AT = (9, 8)

GLYPHS = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    ":": ("00000", "00100", "00100", "00000", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "<": ("00010", "00110", "01110", "11110", "01110", "00110", "00010"),
    ">": ("01000", "01100", "01110", "01111", "01110", "01100", "01000"),
    " ": ("00000",) * 7,
}
DOT_TILE = (
    "00000000",
    "00111100",
    "01111110",
    "01111110",
    "01111110",
    "01111110",
    "00111100",
    "00000000",
)


def draw_text(image, px: int, py: int, text: str, color, scale: int = 1) -> None:
    """Each character fills one 8px cell per scale step: a 5x7 glyph, offset (1, 0)."""
    for index, char in enumerate(text):
        for y, row in enumerate(GLYPHS[char]):
            for x, bit in enumerate(row):
                if bit != "1":
                    continue
                for sy in range(scale):
                    for sx in range(scale):
                        image[py + y * scale + sy][px + index * 8 * scale + (1 + x) * scale + sx] = color


def paint_menu_base():
    # The Green Hills sky and floor: clouds, far hills, grass.
    image, collisions, colors = paint_level(CLEAR_W, CLEAR_H, lambda tile_x: CLEAR_TOP)
    # Menus have no platforming. Clear collisions so nothing can catch the hidden player.
    return image, [0] * len(collisions), colors


GAME_TITLE = "GROK BOT HERO"


def paint_title():
    """Logo: GROK BOT on rows 3-4, HERO on rows 6-7, each 2x scale.

    Tiles under the logo are reset to plain sky on background palette 0 so
    the letters do not pick up the far-hills palette.
    """
    image, collisions, colors = paint_menu_base()
    lines = [("GROK BOT", 2, 3), ("HERO", 6, 6)]
    for text, tile_x, tile_y in lines:
        # HERO sits on the hill band (rows 6-8); clear the whole band there.
        rows = range(tile_y, 9) if tile_y == 6 else range(tile_y, tile_y + 2)
        for ty in rows:
            for tx in range(tile_x, tile_x + len(text) * 2):
                colors[ty * CLEAR_W + tx] = 0
                for y in range(8):
                    for x in range(8):
                        image[ty * 8 + y][tx * 8 + x] = SKY
        draw_text(image, tile_x * 8, tile_y * 8 + 1, text, OUTLINE, 2)
    return image, collisions, colors


PICKER_HINTS = (("LEFT/RIGHT: SHAPE", 3), ("UP/DOWN: COLOR", 5))


def paint_picker():
    image, collisions, colors = paint_menu_base()
    # Control hints, drawn into the background (no sprites, no VRAM beyond
    # the letter tiles). Tiles under each line go back to plain sky on
    # background palette 0 so clouds do not tint the text.
    for text, tile_y in PICKER_HINTS:
        tile_x = (CLEAR_W - len(text)) // 2
        for tx in range(tile_x, tile_x + len(text)):
            colors[tile_y * CLEAR_W + tx] = 0
            for y in range(8):
                for x in range(8):
                    image[tile_y * 8 + y][tx * 8 + x] = SKY
        draw_text(image, tile_x * 8, tile_y * 8, text, OUTLINE)
    arrow_y = (PICKER_BOT_AT[1] + 1) * 8
    draw_text(image, (PICKER_BOT_AT[0] - 3) * 8, arrow_y, "<", OUTLINE)
    draw_text(image, (PICKER_BOT_AT[0] + 4) * 8, arrow_y, ">", OUTLINE)
    draw_text(image, 7 * 8, 14 * 8, "A = GO", OUTLINE)
    dot = indexed_tile(DOT_TILE, FAR)
    for index, tile_x in enumerate((5, 8, 11, 14)):
        tile_y = 12
        for y in range(8):
            for x in range(8):
                image[tile_y * 8 + y][tile_x * 8 + x] = dot[y][x]
        # Background palette slots 2-5 are the four dot palettes.
        colors[tile_y * CLEAR_W + tile_x] = 2 + index
    return image, collisions, colors


def draw_text_narrow(image, px: int, py: int, text: str, color) -> int:
    """5x7 glyphs at a 6 px pitch; a space is 4 px. Returns the end x."""
    x = px
    for char in text:
        if char == " ":
            x += 4
            continue
        for y, row in enumerate(GLYPHS[char]):
            for gx, bit in enumerate(row):
                if bit == "1":
                    image[py + y][x + gx] = color
        x += 6
    return x


def paint_press_start() -> list[list[list[tuple[int, int, int, int]]]]:
    """Four single-frame 16x16 strips that together read PRESS START."""
    strip = blank(PRESS_PARTS * 16, 16, CLEAR)
    draw_text_narrow(strip, 1, 4, PRESS_TEXT, BLACK)
    return [[row[index * 16 : index * 16 + 16] for row in strip] for index in range(PRESS_PARTS)]


def palette_set(name: str, palette_name: str) -> dict:
    args = {f"palette{index}": "keep" for index in range(8)}
    args["palette0"] = uid("palette-" + palette_name)
    return event(name, "EVENT_PALETTE_SET_SPRITE", args)


def color_events(name: str) -> list:
    # Sprite palette slot 0 is Grok Bot's. Each color replaces that slot.
    return [
        if_value(f"{name}-color{index}", COLOR_VAR, "==", index, [palette_set(f"{name}-palette{index}", pal)])
        for index, (pal, _colors) in enumerate(GROK_COLORS)
    ]


def player_palette_events(name: str) -> list:
    """Level palette for slot 0: the chosen color, glowing when powered (var 9)."""
    return [
        if_value(
            f"{name}-color{index}",
            COLOR_VAR,
            "==",
            index,
            [
                if_value(
                    f"{name}-powered{index}",
                    POWER_VAR,
                    "==",
                    1,
                    [palette_set(f"{name}-power{index}", POWER_COLORS[index][0])],
                    [palette_set(f"{name}-palette{index}", pal)],
                )
            ],
        )
        for index, (pal, _colors) in enumerate(GROK_COLORS)
    ]


def apply_player_choice(key: str) -> list:
    """Level init: swap to the chosen shape's sheet (0 keeps the default), then the palette."""
    return [
        *[
            if_value(
                f"{key}-shape-{index}" if index > 1 else f"{key}-shape-square",
                SHAPE_VAR,
                "==",
                index,
                [
                    event(
                        f"{key}-set-{PLAYER_SHAPES[index]}" if index > 1 else f"{key}-set-square",
                        "EVENT_PLAYER_SET_SPRITE",
                        {"spriteSheetId": uid(SHAPES[index])},
                    )
                ],
            )
            for index in range(1, len(SHAPES))
        ],
        *player_palette_events(f"{key}-choice"),
    ]


def preview(tag: str) -> list:
    bot = uid("actor_picker_bot")
    sprite = [
        event(f"pick-{tag}-sprite{index}", "EVENT_ACTOR_SET_SPRITE", {"actorId": bot, "spriteSheetId": uid(symbol)})
        for index, symbol in enumerate(SHAPES)
    ]
    return [
        *[
            if_value(f"pick-{tag}-shape{index}" if index else f"pick-{tag}-shape", SHAPE_VAR, "==", index, [sprite[index]])
            for index in range(len(SHAPES))
        ],
        *color_events(f"pick-{tag}"),
    ]


def input_script(name: str, buttons: list[str], body: list) -> dict:
    return event(name, "EVENT_SET_INPUT_SCRIPT", {"input": buttons, "override": True}, {"true": body})


def hide_player(name: str) -> dict:
    return event(name, "EVENT_ACTOR_HIDE", {"actorId": "player"})


def lock_dpad(name: str) -> list:
    return [input_script(f"{name}-lock-{button}", [button], []) for button in ("left", "right", "up", "down")]


def title_script() -> list:
    return [
        hide_player("title-hide-player"),
        *lock_dpad("title"),
        # Bound first, so Start or A works before the blink or the song.
        input_script(
            "title-start",
            ["start", "a"],
            [switch_scene("title-to-picker", "scene_picker", *MENU_PLAYER)],
        ),
        event("title-music", "EVENT_MUSIC_PLAY", {"musicId": MUSIC_ID, "loop": True}),
    ]


def picker_script() -> list:
    start_x, start_y = PLAYER_START
    last_shape = len(SHAPES) - 1
    right = [
        event("pick-shape-inc", "EVENT_INC_VALUE", {"variable": SHAPE_VAR}),
        if_value("pick-shape-wrap", SHAPE_VAR, ">", last_shape, [set_number("pick-shape-to-0", SHAPE_VAR, 0)]),
        beep("pick-shape-sound", 6),
        *preview("shape"),
    ]
    left = [
        if_value(
            "pick-shape-under",
            SHAPE_VAR,
            "==",
            0,
            [set_number("pick-shape-to-last", SHAPE_VAR, last_shape)],
            [event("pick-shape-dec", "EVENT_DEC_VALUE", {"variable": SHAPE_VAR})],
        ),
        beep("pick-left-sound", 6),
        *preview("left"),
    ]
    up = [
        event("pick-color-inc", "EVENT_INC_VALUE", {"variable": COLOR_VAR}),
        if_value("pick-color-wrap", COLOR_VAR, ">", 3, [set_number("pick-color-to-0", COLOR_VAR, 0)]),
        beep("pick-up-sound", 7),
        *preview("up"),
    ]
    down = [
        if_value(
            "pick-color-under",
            COLOR_VAR,
            "==",
            0,
            [set_number("pick-color-to-3", COLOR_VAR, 3)],
            [event("pick-color-dec", "EVENT_DEC_VALUE", {"variable": COLOR_VAR})],
        ),
        beep("pick-down-sound", 7),
        *preview("down"),
    ]
    go = [switch_scene("pick-go", "scene_level1_green_hills", start_x, start_y)]
    return [
        hide_player("pick-hide-player"),
        input_script("pick-go-input", ["a", "start"], go),
        input_script("pick-left-right", ["right"], right),
        input_script("pick-left", ["left"], left),
        input_script("pick-up", ["up"], up),
        input_script("pick-down", ["down"], down),
        # Show the current choice: round + white on a fresh boot.
        *preview("init"),
    ]


def write_menus(painted: dict, bg_ids: list[str], sprite_ids: list[str]) -> None:
    scenes_dir = ROOT / "project" / "scenes"
    picker_bg_ids = bg_ids[:2] + [uid("palette-" + name) for name, _color in DOTS] + bg_ids[6:]
    base_x = world_x(len(SEGMENTS) + 1)
    for key, script, palettes, x in (
        ("title", title_script(), bg_ids, base_x),
        ("picker", picker_script(), picker_bg_ids, base_x + CLEAR_W * 8 + SCENE_GAP),
    ):
        delete_gbsres(scenes_dir / key / "actors")
        write_json(
            scenes_dir / key / "scene.gbsres",
            scene(
                name=key.title(),
                symbol=f"scene_{key}",
                index=len(SEGMENTS) + (0 if key == "title" else 1),
                x=x,
                y=40,
                width=CLEAR_W,
                height=CLEAR_H,
                background_symbol=f"bg_{key}",
                palette_ids=palettes,
                sprite_palette_ids=sprite_ids,
                script=script,
                collisions=painted[key]["collisions"],
                scene_type="TOPDOWN",
            ),
        )
    title_actors = scenes_dir / "title" / "actors"
    write_json(
        title_actors / "grok_bot.gbsres",
        actor(
            name="Grok Bot",
            symbol="actor_title_bot",
            index=0,
            x=TITLE_BOT_AT[0],
            y=TITLE_BOT_AT[1],
            sprite_symbol=SHAPES[0],
            palette_name="Grok Bot",
            script=[],
            animate=False,
            collision_group="",
        ),
    )
    press = [uid(f"actor_title_press_{index}") for index in range(PRESS_PARTS)]
    blink = [
        wait_frames("blink-on", 36),
        *[event(f"blink-hide-{index}", "EVENT_ACTOR_HIDE", {"actorId": actor_id}) for index, actor_id in enumerate(press)],
        wait_frames("blink-off", 18),
        *[event(f"blink-show-{index}", "EVENT_ACTOR_SHOW", {"actorId": actor_id}) for index, actor_id in enumerate(press)],
    ]
    for index in range(PRESS_PARTS):
        write_json(
            title_actors / f"press_start_{index}.gbsres",
            actor(
                name=f"Press Start {index}",
                symbol=f"actor_title_press_{index}",
                index=1 + index,
                x=PRESS_AT[0] + index * 2,
                y=PRESS_AT[1],
                sprite_symbol=f"sprite_press_start_{index}",
                palette_name="Grok Bot",
                script=[],
                update_script=blink if index == 0 else None,
                animate=False,
                collision_group="",
            ),
        )
    write_json(
        scenes_dir / "picker" / "actors" / "grok_bot.gbsres",
        actor(
            name="Picker Bot",
            symbol="actor_picker_bot",
            index=0,
            x=PICKER_BOT_AT[0],
            y=PICKER_BOT_AT[1],
            sprite_symbol=SHAPES[0],
            palette_name="Grok Bot",
            script=[],
            animate=False,
            collision_group="",
        ),
    )


def patch_project() -> None:
    metadata_path = ROOT / "GrokBotPlatformer.gbsproj"
    metadata = {
        "_resourceType": "project",
        "name": "GROK BOT HERO",
        "author": "Joe",
        "notes": "Level 1 is two scenes, about five times the first demo. Open in GB Studio 4.2 or newer.",
        "_version": "4.2.0",
        "_release": "10",
    }
    template_metadata = ROOT / "project.gbsproj"
    if template_metadata.exists():
        metadata.update(
            {
                "_version": json.loads(template_metadata.read_text())["_version"],
                "_release": json.loads(template_metadata.read_text())["_release"],
            }
        )
        template_metadata.unlink()
    write_json(metadata_path, metadata)

    settings_path = ROOT / "project" / "settings.gbsres"
    settings = json.loads(settings_path.read_text())
    player_id = uid("sprite_player_grok")
    settings["colorMode"] = "color"
    settings["startSceneId"] = uid("scene_title")
    settings["startX"] = MENU_PLAYER[0]
    settings["startY"] = MENU_PLAYER[1]
    settings["startDirection"] = "right"
    settings["defaultSceneTypeId"] = "PLATFORM"
    settings["playerPaletteId"] = uid("palette-Grok Bot")
    settings["defaultSpritePaletteId"] = uid("palette-Grok Bot")
    settings["defaultBackgroundPaletteIds"][0] = uid("palette-Green Hills")
    if len(settings["defaultBackgroundPaletteIds"]) > 1:
        settings["defaultBackgroundPaletteIds"][1] = uid("palette-Far Hills")
    settings["defaultSpritePaletteIds"] = [
        uid("palette-Grok Bot"),
        uid("palette-Blob Red"),
        uid("palette-Electron Blue"),
        uid("palette-Chip Gray"),
        uid("palette-Roadster White"),
        uid("palette-Flyer Violet"),
        "default-sprite",
        "default-sprite",
    ]
    settings["defaultPlayerSprites"] = {key: player_id for key in settings["defaultPlayerSprites"]}
    settings["customColorsWhite"] = "B8F0E8"
    settings["customColorsLight"] = "68D070"
    settings["customColorsDark"] = "289038"
    settings["customColorsBlack"] = "183028"
    write_json(settings_path, settings)

    write_json(
        ROOT / "project" / "variables.gbsres",
        {
            "_resourceType": "variables",
            "variables": [
                {
                    "id": "0",
                    "name": "electrons",
                    "symbol": "var_electrons",
                    "type": "number",
                },
                {
                    "id": "1",
                    "name": "lives",
                    "symbol": "var_lives",
                    "type": "number",
                },
                {
                    "id": "2",
                    "name": "chip",
                    "symbol": "var_chip",
                    "type": "number",
                },
                {
                    "id": LEVEL_DONE,
                    "name": "level_done",
                    "symbol": "var_level_done",
                    "type": "number",
                },
                {
                    "id": "4",
                    "name": "hits",
                    "symbol": "var_hits",
                    "type": "number",
                },
                {
                    "id": "5",
                    "name": "hurt_lock",
                    "symbol": "var_hurt_lock",
                    "type": "number",
                },
                {
                    "id": RESPAWN_VAR,
                    "name": "respawning",
                    "symbol": "var_respawning",
                    "type": "number",
                },
                {
                    "id": SCORE_VAR,
                    "name": "score",
                    "symbol": "var_score",
                    "type": "number",
                },
                {
                    "id": POWER_VAR,
                    "name": "powered",
                    "symbol": "var_powered",
                    "type": "number",
                },
                {
                    "id": SHAPE_VAR,
                    "name": "player_shape",
                    "symbol": "var_player_shape",
                    "type": "number",
                },
                {
                    "id": COLOR_VAR,
                    "name": "player_color",
                    "symbol": "var_player_color",
                    "type": "number",
                },

            ],
            "constants": [],
        },
    )

    engine_path = ROOT / "project" / "engine_field_values.gbsres"
    engine = json.loads(engine_path.read_text())
    overrides = {
        "FEAT_PLATFORM_JUMP": 1,
        "plat_jump_vel": 14336,
        "plat_hold_grav": 400,
        "plat_jump_hold_frames": 15,
        "FEAT_PLATFORM_COYOTE_TIME": 1,
        "plat_coyote_frames": 6,
        "plat_jump_buffer_frames": 4,
        "FEAT_PLATFORM_KNOCKBACK": 1,
    }
    fields = engine["engineFieldValues"]
    seen = {item["id"] for item in fields}
    for item in fields:
        if item["id"] in overrides:
            item["value"] = overrides[item["id"]]
    for key, value in overrides.items():
        if key not in seen:
            fields.append({"id": key, "value": value})
    write_json(engine_path, engine)


def write_sprite_readme() -> None:
    text = """# Sprites

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
| flyer.png | Zap Bat, a small winged bot. Two frames, wings up and down. |
| turret.png | Bolt Tower, the High Ridge shooter. |
| bolt.png | The Bolt Tower's projectile. |
| roadster.png | Six 32x32 kickflip frames (0, 60, ... 300 degrees; 32 non-blank 8x16 tiles) of a 32x16 white low two-seat electric hypercar silhouette (wedge profile, dark canopy, black wheels with gray hubs) for the level-complete cutscene. Original art; no badge, logo, or wordmark. |
| press_start_0..3.png | Single-frame strips that together read PRESS START on the title. |

`actor.png`, `actor_animated.png`, and `static.png` are the GB Studio blank-template placeholders. The player setting points at `player_grok.png`.

All player sheets are palette-mode (indexed) PNGs with four entries: transparent, fill, outline, eyes. GB Studio sprite palettes show palette colors 0, 1 and 3 for sprite colors 1, 2 and 3; see `sprite_palette()` in the generator. The picker's color choice recolors any shape through sprite palette slot 0 instead of duplicating PNGs. Each sheet is 64x16: 4 frames x 2 8x16 tiles = 8 tiles. In a scene GB Studio reserves VRAM for one player sheet (the largest the player can be set to), and `Player: Set Sprite` loads the chosen sheet into that slot, so eight shapes do not cost 64 tiles of VRAM. `docs/shapes-sheet.png` is a contact sheet of every shape.

Regenerate with `python3 scripts/build_level1.py`.
"""
    (ROOT / "assets" / "sprites" / "README.md").write_text(text, encoding="utf-8")


def required_rise(stand_y: int, actor_y: int) -> int:
    """Pixels the player must rise before two 16px sprites overlap."""
    return stand_y * 8 - (actor_y * 8 + 15)


# Hardware sprites (8x16 mode) per 16 px actor, and how far each kind can
# drift from its placed tile while patrolling (for the scanline check).
HW_SPRITES = {"roadster": 4}
PATROL = {"blobs": 3, "flyers": 4}


# Fastest the player moves: holding B to run, plat_run_vel 10496 = 82
# subpx/frame, about 19.2 tiles/s (gbvm platform.c:989; walking is 11.7).
MAX_RUN_TILES_PER_S = 19.2


def towers_can_chain(a: int, b: int) -> bool:
    """True if a bolt from tower a can still be alive when tower b fires.

    The player must walk from leaving a's range (a + TOWER_RANGE) to entering
    b's (b - TOWER_RANGE); if that takes less than BOLT_LIFE, both bolts can
    be in flight at once.
    """
    gap = abs(b - a) - 2 * TOWER_RANGE
    return gap / MAX_RUN_TILES_PER_S < BOLT_LIFE


def tower_chains(segment: dict, x: int) -> bool:
    return any(other != x and towers_can_chain(x, other) for other, _y in segment.get("turret", []))


def scanline_peak(segment: dict) -> int:
    """Worst count of hardware sprites sharing one 8 px row on any screen.

    Counts the player (2) and the HUD row, slides a 20-tile window along the
    half, and widens each patrolling actor by its patrol distance. The GBC
    draws at most 10 sprites per scanline.
    """
    worst = 0
    hud = [(LIVES_AT[0], LIVES_AT[1]), (AMMO_AT[0], AMMO_AT[1])]
    for left in range(0, SEG_W - 19):
        rows = [0] * (LEVEL_H + 2)
        for _x, y in hud:
            rows[y] += 2
            rows[y + 1] += 2
        # Score digits: 1 + 1 + 2 hardware sprites on the HUD row.
        rows[0] += 4
        rows[1] += 4
        bolts = 0
        for kind, x, y in segment_bodies(segment):
            reach = PATROL.get(kind, 0)
            # The roadster's art spans x-1..x+3 (tiles centred on its 16 px base).
            x0, x1 = (x - 1, x + 3) if kind == "roadster" else (x, x + 2)
            if x1 + reach <= left or x0 - reach >= left + 20:
                continue
            if kind == "turret":
                # A bolt from a tower that can chain with another tower in
                # view (see towers_can_chain) may still be alive when the next
                # tower fires, so two bolts can share the screen.
                bolts = max(bolts, 4 if tower_chains(segment, x) else 2)
            # Flyers bob one row up from their placed row.
            top = y - 1 if kind == "flyers" else y
            for row in range(top, y + 2):
                if 0 <= row < len(rows):
                    rows[row] += HW_SPRITES.get(kind, 2)
        # The player (2), its electron shots (2 each, on its row) and a turret
        # bolt (aimed at it) can share any row the player reaches; it never
        # reaches the HUD rows 0-1.
        moving = 2 + MAX_SHOTS * 2 + bolts
        worst = max(worst, max(rows[0], rows[1]), max(rows[2:]) + moving)
    return worst


def validate_layout() -> None:
    # Projectile life_time is a uint8_t frame count (gbs_types.h); the
    # generator bypasses the editor's 4 s cap, so guard against wrapping.
    for label, seconds in (("BOLT_LIFE", BOLT_LIFE), ("SHOT_LIFE", SHOT_LIFE)):
        if round(seconds * 60) > 255:
            raise SystemExit(f"{label} {seconds}s is {round(seconds * 60)} frames; life_time is uint8 (max 255)")
    for segment in SEGMENTS:
        label = segment["name"]
        bodies = segment_bodies(segment)
        count = actor_count(segment)
        if count > MAX_ACTORS:
            raise SystemExit(f"{label} has {count} actors; the limit is {MAX_ACTORS}")
        peak = scanline_peak(segment)
        if peak > 10:
            raise SystemExit(f"{label} can put {peak} sprites on one scanline")
        for x in range(SEG_W):
            top = solid_top(segment, x)
            if top is not None and top < PLAY_ROW:
                raise SystemExit(f"{label} solid at column {x} is inside the scenery band")
        for x0, x1 in segment["pits"]:
            for x in range(x0, x1 + 1):
                if solid_top(segment, x) is not None:
                    raise SystemExit(f"{label} pit column {x} is solid")
            landing = 0
            for x in range(x0 - 1, -1, -1):
                if solid_top(segment, x) != FLOOR_TOP:
                    break
                landing += 1
            if landing < 6:
                raise SystemExit(f"{label} has only {landing} tiles of floor before the pit")
        for x, y in segment.get("flyers", []):
            for path_x in range(x - 4, x + 6):
                top = solid_top(segment, path_x)
                if top is not None and top <= y + 2:
                    raise SystemExit(f"{label} flyer at {(x, y)} clips the ground on its path")
            if y + 1 > FLOOR_TOP - 3:
                raise SystemExit(f"{label} flyer at {(x, y)} is too low to walk under")
        for x, y in segment["blobs"]:
            if solid_top(segment, x) != y + 2:
                raise SystemExit(f"{label} blob at {(x, y)} is not standing on a ledge")
            if x - 3 < 0 or solid_top(segment, x - 3) != y + 2 or solid_top(segment, x + 3) != y + 2:
                raise SystemExit(f"{label} blob at {(x, y)} patrols off its ledge")
        for kind in ("electrons",):
            for x, y in segment[kind]:
                ground = solid_top(segment, x)
                if ground is None:
                    raise SystemExit(f"{label} {kind} at {(x, y)} is over a pit")
                rise = required_rise(ground - 2, y)
                if rise <= 0 or rise > 40:
                    raise SystemExit(f"{label} {kind} at {(x, y)} needs a {rise}px rise")
        if not segment["chips"]:
            raise SystemExit(f"{label} has no silicon chip")
        for chip_x, chip_y in segment["chips"]:
            ground = solid_top(segment, chip_x)
            if ground is None or chip_y + 1 >= ground:
                raise SystemExit(f"{label} chip is buried")
            if ground - FLOOR_TOP > 4:
                raise SystemExit(f"{label} chip ledge is too high for the base jump")
        first_chip = min(x for x, _y in segment["chips"])
        for electron_x, _electron_y in segment["electrons"]:
            if electron_x <= first_chip:
                raise SystemExit(f"{label} electron at x={electron_x} is not after the chip")
        # Joe's order: meet blobs before the chip.
        if len([x for x, _y in segment["blobs"] if x < first_chip]) < 2:
            raise SystemExit(f"{label} needs at least two blobs before the chip")
        if solid_top(segment, PLAYER_START[0]) != PLAYER_START[1] + 2:
            raise SystemExit(f"{label} start is not on the floor")
        gate_x = SEG_W - 4
        if solid_top(segment, gate_x) != FLOOR_TOP:
            raise SystemExit(f"{label} gate is not on the floor")
        for index, (_kind, x, y) in enumerate(bodies):
            for _other_kind, other_x, other_y in bodies[index + 1 :]:
                if abs(x - other_x) < 2 and abs(y - other_y) < 2:
                    raise SystemExit(f"{label} actors overlap at {(x, y)} and {(other_x, other_y)}")
    if electron_total() < 7:
        raise SystemExit(f"expected a longer cast, got {electron_total()} electrons")


LAYOUT_MARKS = {"blobs": "B", "chips": "C", "electrons": "e", "flyers": "F", "turret": "T", "roadster": "R"}


def layout_rows(segment: dict) -> list[str]:
    marks = {PLAYER_START: "P", LIVES_AT: "H", AMMO_AT: "A"}
    for kind, x, y in segment_bodies(segment):
        marks[(x, y)] = LAYOUT_MARKS[kind]
    for dx in range(4):
        for dy in range(6):
            marks.setdefault((SEG_W - 4 + dx, 9 + dy), "E")
    for x0, x1 in segment["pits"]:
        for x in range(x0, x1 + 1):
            for y in range(FLOOR_TOP, FLOOR_TOP + 3):
                marks.setdefault((x, y), "V")
    rows = []
    for y in range(LEVEL_H):
        chars = []
        for x in range(SEG_W):
            top = solid_top(segment, x)
            marker = marks.get((x, y))
            if marker is not None and (top is None or y < top):
                chars.append(marker)
            elif top is None or y < top:
                chars.append(" ")
            elif y == top:
                chars.append("=")
            else:
                chars.append("#")
        rows.append("".join(chars))
    return rows


def main() -> None:
    validate_layout()
    painted = build_images()
    build_resources(painted)
    patch_project()
    write_sprite_readme()
    for segment in SEGMENTS:
        info = painted[segment["symbol"]]
        if len(info["collisions"]) != SEG_W * LEVEL_H:
            raise SystemExit(f"{segment['name']} collision size mismatch")
        if info["tiles"] > 16:
            raise SystemExit(f"{segment['name']} has {info['tiles']} background tiles")
        print(
            f"{segment['name']}: {SEG_W} tiles, {actor_count(segment)} actors, "
            f"{info['tiles']} background tiles, scanline peak {scanline_peak(segment)}/10"
        )
        print("\n".join(layout_rows(segment)))
    for key in ("title", "picker"):
        tiles = painted[key]["tiles"]
        if tiles > 64:
            raise SystemExit(f"{key} has {tiles} background tiles")
        print(f"{key.title()}: {tiles} background tiles")
    print("Electrons:", sum(len(segment["electrons"]) for segment in SEGMENTS))
    print("Blobs:", sum(len(segment["blobs"]) for segment in SEGMENTS))
    print("Wrote", ROOT / "GrokBotPlatformer.gbsproj")


if __name__ == "__main__":
    main()
