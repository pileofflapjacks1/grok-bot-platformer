#!/usr/bin/env python3
"""Generate Level 1 of GrokBotPlatformer on top of the GB Studio blank template.

Run from anywhere:

    python3 scripts/build_level1.py

Rewrites the level scenes, original sprites, backgrounds, palettes, and the
project settings that point at them. Template fonts, UI, and emotes are left
in place. Identifiers are stable across runs.
"""

from __future__ import annotations

import hashlib
import json
import struct
import uuid
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NS = uuid.UUID("6f1b9c3e-8a24-4b7e-9c1d-0a5e2f7b4d11")

# Background palette. Four opaque colors, one 8x8 pattern each.
SKY = (184, 240, 232, 255)
GRASS_L = (104, 208, 112, 255)
DIRT = (40, 144, 56, 255)
OUTLINE = (24, 48, 40, 255)

# Sprite colors. GB Studio does not use these RGB values directly.
# A pixel is transparent when alpha is under 200, or when it is pure green
# or pure blue. Otherwise the green channel picks the palette slot:
# 205 or more is color 1, 130 or more is color 2, and the rest is color 3.
# Grok Bot is a round head, gray shade, and black capsule eyes.
WHITE = (244, 244, 248, 255)
GRAY = (138, 138, 152, 255)
RED = (248, 72, 72, 255)
E_WHITE = (232, 248, 255, 255)
CYAN = (80, 216, 248, 255)
BLUE = (24, 72, 200, 255)
SILVER = (216, 220, 232, 255)
CHIP_BODY = (96, 104, 120, 255)
BLACK = (24, 16, 24, 255)
CREAM = (248, 232, 208, 255)
CLOUD = (248, 252, 255, 255)
HILL = (112, 192, 216, 255)
HILL_SHADE = (40, 112, 144, 255)
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
# Electrons sit in the air so each one is its own hop, like a coin.
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
        "blobs": [(26, 10), (40, 13), (53, 11), (99, 10), (116, 13), (156, 11)],
        "electrons": [
            (8, 10),
            (14, 9),
            (22, 7),
            (29, 6),
            (36, 10),
            (50, 8),
            (56, 7),
            (84, 10),
            (88, 8),
            (94, 7),
            (104, 6),
        ],
        # On the floor, before every electron, so the demo arms Grok Bot first.
        "chip": (6, 13),
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
        "blobs": [(23, 10), (36, 13), (48, 11), (81, 10), (100, 13), (115, 9), (143, 11)],
        "electrons": [
            (6, 10),
            (10, 8),
            (20, 7),
            (27, 6),
            (33, 9),
            (52, 8),
            (58, 10),
            (78, 7),
            (85, 6),
            (112, 6),
            (146, 8),
        ],
        "chip": None,
        "next": None,
    },
]


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


def paint_player() -> list[list[tuple[int, int, int, int]]]:
    """Round Grok Bot: antenna, black capsule eyes, no mouth. Left side is mirrored."""
    image = blank(64, 16, CLEAR)
    # Idle, step down, idle, jump. Capsule eyes stay solid black.
    for frame, dy in enumerate((0, 1, 0, -1)):
        draw_grok_bot(image, frame * 16, dy)
    return image


def draw_grok_bot(
    image: list[list[tuple[int, int, int, int]]],
    origin: int,
    dy: int,
) -> None:
    cx, cy, radius = 8.0, 10.0 + dy, 5.2
    limit = radius * radius
    inner = (radius - 1.05) ** 2
    for y in range(16):
        for x in range(16):
            dx = x + 0.5 - cx
            ddy = y + 0.5 - cy
            dist = dx * dx + ddy * ddy
            if dist <= inner:
                image[y][origin + x] = GRAY if ddy > 1.4 else WHITE
            elif dist <= limit:
                image[y][origin + x] = BLACK
    for by in (dy, dy + 1):
        for bx in (origin + 7, origin + 8):
            if 0 <= by < 16:
                image[by][bx] = BLACK
    for ay in (dy + 2, dy + 3):
        if 0 <= ay < 16:
            image[ay][origin + 8] = BLACK
    # Two black capsules with white on every side, so they stay separate.
    eye_y = 8 + dy
    for ey in range(2):
        yy = eye_y + ey
        if not 0 <= yy < 16:
            continue
        for x in range(4, 12):
            image[yy][origin + x] = WHITE
        for x in (5, 6, 9, 10):
            image[yy][origin + x] = BLACK


def paint_enemy() -> list[list[tuple[int, int, int, int]]]:
    """Two waddle frames: cream eyes with black pupils, belly, brows, and feet."""
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

    Blob Red shows slot 1 as red, slot 2 as cream, and slot 3 as black.
    CREAM has a high green channel, so the heart is red in game.
    GRAY is the middle band, so the digit is cream in game.
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
                    image[5 + y][ox + x] = CREAM
        draw_digit(image, ox + 9, 3, frame, GRAY, 2)
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


def paint_clear() -> tuple[list[list[tuple[int, int, int, int]]], list[int], list[int]]:
    def solid_at(tile_x: int) -> int:
        del tile_x
        return CLEAR_TOP

    return paint_level(CLEAR_W, CLEAR_H, solid_at)


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


def tile_ref(name: str, x: int, slice_x: int) -> dict:
    return {
        "id": uid(name),
        "x": x,
        "y": 0,
        "sliceX": slice_x,
        "sliceY": 0,
        "flipX": False,
        "flipY": False,
        "palette": 0,
        "paletteIndex": 0,
        "objPalette": "OBP0",
        "priority": False,
    }


def frame_of(name: str, slice_x: int) -> dict:
    return {
        "id": uid(name),
        "tiles": [
            tile_ref(name + "-l", 0, slice_x),
            tile_ref(name + "-r", 8, slice_x + 8),
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
) -> dict:
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
        "canvasWidth": 16,
        "canvasHeight": 16,
        "boundsX": 0,
        "boundsY": 0,
        "boundsWidth": 16,
        "boundsHeight": 16,
        "animSpeed": 8 if animation_type == "platform_player" else 15,
        "filename": filename,
        "width": width,
        "height": height,
        "checksum": sha1(image_path),
    }


def player_animations() -> list[dict]:
    # Engine slots: idle R, idle L, jump R, jump L, move R, move L, climb, spare.
    # Left-facing slots stay empty because flipLeft mirrors the right-facing art.
    idle = frame_of("player-idle", 0)
    walk_a = frame_of("player-walk-a", 16)
    walk_b = frame_of("player-walk-b", 32)
    jump = frame_of("player-jump", 48)
    return [
        {"id": uid("player-anim-idle"), "frames": [idle]},
        empty_frame("player-anim-idle-left"),
        {"id": uid("player-anim-jump"), "frames": [jump]},
        empty_frame("player-anim-jump-left"),
        {"id": uid("player-anim-move"), "frames": [walk_a, walk_b]},
        empty_frame("player-anim-move-left"),
        {"id": uid("player-anim-climb"), "frames": [idle]},
        empty_frame("player-anim-spare"),
    ]


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
) -> dict:
    return {
        "_resourceType": "actor",
        "id": uid(symbol),
        "_index": index,
        "symbol": symbol,
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
        "moveSpeed": 1,
        "animSpeed": 15,
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
) -> dict:
    data = {
        "_resourceType": "scene",
        "id": uid(symbol),
        "_index": index,
        "type": "PLATFORM",
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
        "playerHit3Script": [],
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


def rate_limit(name: str, variable: str, seconds: float, body: list) -> dict:
    return event(
        name,
        "EVENT_RATE_LIMIT",
        {
            "variable": variable,
            "units": "time",
            "time": {"type": "number", "value": seconds},
            "frames": {"type": "number", "value": 1},
        },
        {"true": body},
    )


def lose_life(name: str, lives_symbol: str, alive: list, dead: list) -> list:
    # Variable 1 is lives. Variable 4 is the hit count toward the next life.
    return [
        event(f"{name}-dec-life", "EVENT_DEC_VALUE", {"variable": "1"}),
        set_number(f"{name}-clear-hits", "4", 0),
        show_lives(f"{name}-hearts", lives_symbol),
        if_value(f"{name}-dead", "1", "==", 0, dead, alive),
    ]


def game_over(name: str, fade_out_first: bool) -> list:
    start_x, start_y = PLAYER_START
    steps = []
    if fade_out_first:
        steps.append(fade(f"{name}-over-out", "out"))
    steps.extend(
        [
            fade(f"{name}-over-in", "in"),
            event(f"{name}-over", "EVENT_TEXT", {"text": "Game Over"}),
            switch_scene(f"{name}-restart", "scene_level1_green_hills", start_x, start_y),
        ]
    )
    return steps


def enemy_update(suffix: str) -> list:
    return [
        move_by(f"{suffix}-move-right", 3),
        wait_frames(f"{suffix}-wait-right", 20),
        move_by(f"{suffix}-move-left", -3),
        wait_frames(f"{suffix}-wait-left", 20),
    ]


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
    steps.append(deactivate(f"blob-stomp-hide-{suffix}"))
    return steps


def enemy_script(suffix: str, segment: dict) -> list:
    # One overlap used to run this several times a second. The rate limit
    # makes one touch count as one hit. Three hits cost a life.
    lives_symbol = f"actor_lives_{segment['key']}"
    hurt = [
        rate_limit(
            f"{suffix}-hurt-limit",
            "5",
            1,
            [
                event(f"{suffix}-hit-inc", "EVENT_INC_VALUE", {"variable": "4"}),
                beep(f"{suffix}-hurt-sound", 2),
                event(
                    f"{suffix}-knockback",
                    "EVENT_PLATFORMER_STATE_SET",
                    {"state": "knockback"},
                ),
                shake(f"{suffix}-hurt-shake", 0.2, 3),
                if_value(
                    f"{suffix}-hit-check",
                    "4",
                    ">=",
                    3,
                    lose_life(
                        suffix,
                        lives_symbol,
                        [
                            beep(f"{suffix}-life-sound", 1),
                            shake(f"{suffix}-life-shake", 0.4, 5),
                        ],
                        game_over(suffix, True),
                    ),
                ),
            ],
        )
    ]
    # Falling uses a positive Y velocity. A landing often overlaps the blob,
    # so "player is above" alone misses the stomp.
    falling = event(
        f"{suffix}-if-falling",
        "EVENT_IF",
        {
            "condition": {
                "type": "gt",
                "valueA": {"type": "engineField", "value": "plat_vel_y"},
                "valueB": {"type": "number", "value": 0},
            },
            "__collapseElse": False,
        },
        {"true": vanish_blob(suffix + "-fall", True), "false": hurt},
    )
    return [
        event(
            f"{suffix}-hit-if",
            "EVENT_IF_ACTOR_RELATIVE_TO_ACTOR",
            {
                "actorId": "player",
                "operation": "up",
                "otherActorId": "$self$",
                "__collapseElse": False,
            },
            {"true": vanish_blob(suffix + "-above", True), "false": [falling]},
        )
    ]


def set_engine(name: str, key: str, number: int) -> dict:
    return event(
        name,
        "EVENT_ENGINE_FIELD_SET",
        {"engineFieldKey": key, "value": {"type": "number", "value": number}},
    )


def electron_script(name: str, ammo_symbol: str) -> list:
    return [
        event(f"{name}-inc", "EVENT_INC_VALUE", {"variable": "0"}),
        show_counter(f"{name}-ammo", ammo_symbol, "0"),
        beep(f"{name}-sound", 7),
        deactivate(f"{name}-hide"),
    ]


def chip_script(name: str) -> list:
    # The chip unlocks firing. It does not change the jump.
    return [
        set_number(f"{name}-flag", "2", 1),
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
            "lifeTime": 1.2,
            "initialOffset": 12,
            "loopAnim": True,
            "destroyOnHit": True,
            "collisionGroup": "1",
            "collisionMask": ["1"],
        },
    )


def attach_fire(segment: dict) -> dict:
    # B still runs. A press fires only after the chip, and only while ammo remains.
    key = segment["key"]
    ammo_symbol = f"actor_ammo_{key}"
    shot = [
        event(f"{key}-shot-dec", "EVENT_DEC_VALUE", {"variable": "0"}),
        show_counter(f"{key}-shot-hud", ammo_symbol, "0"),
        beep(f"{key}-shot-sound", 8),
        launch_electron(f"{key}-shot-launch"),
    ]
    limited = event(
        f"{key}-shot-limit",
        "EVENT_RATE_LIMIT",
        {
            "variable": "3",
            "units": "time",
            "time": {"type": "number", "value": 0.3},
            "frames": {"type": "number", "value": 1},
        },
        {"true": shot},
    )
    armed = if_value(f"{key}-shot-chip", "2", ">", 0, [limited])
    has_ammo = if_value(f"{key}-shot-ammo", "0", ">", 0, [armed])
    return event(
        f"{key}-fire-input",
        "EVENT_SET_INPUT_SCRIPT",
        {"input": ["b"], "override": False},
        {"true": [has_ammo]},
    )


def exit_script() -> list:
    return [switch_scene("exit-clear", "scene_level1_clear", 2, CLEAR_TOP - 2)]


def respawn(name: str, x: int, y: int) -> list:
    return [
        event(
            f"{name}-pos",
            "EVENT_ACTOR_SET_POSITION",
            {
                "actorId": "player",
                "x": {"type": "number", "value": x},
                "y": {"type": "number", "value": y},
                "units": "tiles",
            },
        ),
        set_engine(f"{name}-vx", "plat_vel_x", 0),
        set_engine(f"{name}-vy", "plat_vel_y", 0),
        event(f"{name}-ground", "EVENT_PLATFORMER_STATE_SET", {"state": "ground"}),
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


def pit_script(name: str, segment: dict) -> list:
    # The trigger sits at the bottom of the gap, so this runs after the fall.
    # Shake, then fade out, then take the life. A life still left fades back
    # in at the start of this half. The last life fades in on "Game Over".
    lives_symbol = f"actor_lives_{segment['key']}"
    start_x, start_y = PLAYER_START
    return [
        shake(f"{name}-shake", 0.4, 5),
        wait_frames(f"{name}-pause", 18),
        fade(f"{name}-out", "out"),
        *lose_life(
            name,
            lives_symbol,
            respawn(name, start_x, start_y) + [fade(f"{name}-in", "in")],
            game_over(name, False),
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
        script.extend(
            [
                set_number(f"{key}-electrons", "0", 0),
                set_number(f"{key}-lives", "1", 3),
                set_number(f"{key}-chip", "2", 0),
                set_number(f"{key}-cooldown", "3", 0),
                set_number(f"{key}-hits", "4", 0),
                set_number(f"{key}-hurt", "5", 0),
                set_engine(f"{key}-jump", "plat_jump_vel", BASE_JUMP),
            ]
        )
    script.append(show_lives(f"{key}-hearts", lives_symbol))
    script.append(show_ammo(f"{key}-ammo", ammo_symbol))
    script.append(attach_fire(segment))
    return script


def shot_blob(suffix: str) -> list:
    return vanish_blob(suffix + "-shot", False)


def build_images() -> dict:
    sprites = ROOT / "assets" / "sprites"
    backgrounds = ROOT / "assets" / "backgrounds"
    ammo_frames = electron_total() + 1
    write_png(sprites / "player_grok.png", 64, 16, paint_player())
    write_png(sprites / "enemy_red_blob.png", 32, 16, paint_enemy())
    write_png(sprites / "electron.png", 16, 16, paint_electron())
    write_png(sprites / "silicon_chip.png", 16, 16, paint_chip())
    write_png(sprites / "lives.png", 64, 16, paint_lives())
    write_png(sprites / "ammo.png", ammo_frames * 16, 16, paint_ammo())
    for stale in (
        "player_pink.png",
        "player_pink.png.gbsres",
        "collectible_star.png",
        "collectible_star.png.gbsres",
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
    clear, clear_collisions, clear_colors = paint_clear()
    write_png(backgrounds / "level1_clear.png", CLEAR_W * 8, CLEAR_H * 8, clear)
    painted["clear"] = {
        "tiles": unique_tiles(clear),
        "collisions": clear_collisions,
        "colors": clear_colors,
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
    for index, (x, y) in enumerate(segment["blobs"], start=1):
        suffix = f"{key}-blob{index}"
        write_json(
            actor_dir / f"blob_{index}.gbsres",
            actor(
                name=f"Waddle Blob {index}",
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
    if segment["chip"] is not None:
        chip_x, chip_y = segment["chip"]
        suffix = f"{key}-chip"
        write_json(
            actor_dir / "silicon_chip.gbsres",
            actor(
                name="Silicon Chip",
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
        else exit_script()
    )
    gate_name = "Continue" if segment["next"] else "Exit"
    gate_symbol = f"trigger_continue_{key}" if segment["next"] else "trigger_exit"
    gate_file = "continue.gbsres" if segment["next"] else "exit.gbsres"
    write_json(
        trigger_dir / gate_file,
        trigger(gate_name, gate_symbol, trigger_index, SEG_W - 4, 9, 4, 6, gate_script),
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
    write_json(
        backgrounds / "level1_clear.png.gbsres",
        background_resource(
            name="level1_clear",
            symbol="bg_level1_clear",
            filename="level1_clear.png",
            tiles_x=CLEAR_W,
            tiles_y=CLEAR_H,
            tile_colors=collisions["clear"]["colors"],
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
        palette("Grok Bot", ["F8F8F8", "F4F4F8", "8A8A98", "181018"]),
    )
    write_json(
        palettes / "blob_red.gbsres",
        palette("Blob Red", ["F8F8F8", "F84848", "F8E8D0", "181018"]),
    )
    write_json(
        palettes / "electron_blue.gbsres",
        palette("Electron Blue", ["F8F8F8", "E8F8FF", "50D8F8", "1848C8"]),
    )
    write_json(
        palettes / "chip_gray.gbsres",
        palette("Chip Gray", ["F8F8F8", "D8DCE8", "606878", "181018"]),
    )
    for stale in ("grok_pink.gbsres", "star_yellow.gbsres"):
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
        "default-sprite",
        "default-sprite",
        "default-sprite",
        "default-sprite",
    ]

    for segment in SEGMENTS:
        write_segment(segment, collisions[segment["symbol"]]["collisions"], bg_ids, sprite_ids)
    write_json(
        ROOT / "project" / "scenes" / "level_1_clear" / "scene.gbsres",
        scene(
            name="Level 1 Clear",
            symbol="scene_level1_clear",
            index=len(SEGMENTS),
            x=world_x(len(SEGMENTS)),
            y=40,
            width=CLEAR_W,
            height=CLEAR_H,
            background_symbol="bg_level1_clear",
            palette_ids=bg_ids,
            sprite_palette_ids=sprite_ids,
            script=[event("clear-text", "EVENT_TEXT", {"text": "Level 1 clear!"})],
            collisions=collisions["clear"]["collisions"],
        ),
    )


def patch_project() -> None:
    metadata_path = ROOT / "GrokBotPlatformer.gbsproj"
    metadata = {
        "_resourceType": "project",
        "name": "GrokBotPlatformer",
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
    settings["startSceneId"] = uid("scene_level1_green_hills")
    settings["startX"] = PLAYER_START[0]
    settings["startY"] = PLAYER_START[1]
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
        "default-sprite",
        "default-sprite",
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
                    "id": "3",
                    "name": "shot_cooldown",
                    "symbol": "var_shot_cooldown",
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
                    "name": "hurt_cooldown",
                    "symbol": "var_hurt_cooldown",
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
| player_grok.png | Grok Bot. Round head, antenna, black capsule eyes, no mouth. Four frames: idle, walk A, walk B, jump. Left facing is mirrored. |
| enemy_red_blob.png | Waddle Blob. Two frames, cream eyes, black pupils, belly, brows, and feet. |
| electron.png | Electron pickup and the projectile Grok Bot fires. |
| silicon_chip.png | One power-up. Collecting it unlocks firing for the rest of the run. |
| lives.png | Four frames. Each frame is a black badge with a heart and a digit, 0 through 3. The pinned actor shows the frame that matches `lives`. |
| ammo.png | One frame per electron count, from 0 up. Each frame is a blue badge with two digits. The pinned actor shows the frame that matches `electrons`. |

`actor.png`, `actor_animated.png`, and `static.png` are the GB Studio blank-template placeholders. The player setting points at `player_grok.png`.

Other shapes from the character-select design (heart, star, teardrop, and the rest) are not drawn yet. Palette swaps for those shapes come after this level is playable.

Regenerate with `python3 scripts/build_level1.py`.
"""
    (ROOT / "assets" / "sprites" / "README.md").write_text(text, encoding="utf-8")


def required_rise(stand_y: int, actor_y: int) -> int:
    """Pixels the player must rise before two 16px sprites overlap."""
    return stand_y * 8 - (actor_y * 8 + 15)


def validate_layout() -> None:
    total_electrons = 0
    total_blobs = 0
    for segment in SEGMENTS:
        label = segment["name"]
        bodies = list(segment["blobs"]) + list(segment["electrons"])
        if segment["chip"] is not None:
            bodies.append(segment["chip"])
        actor_count = 2 + len(bodies)
        if actor_count > MAX_ACTORS:
            raise SystemExit(f"{label} has {actor_count} actors; the limit is {MAX_ACTORS}")
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
        for x, y in segment["blobs"]:
            if solid_top(segment, x) != y + 2:
                raise SystemExit(f"{label} blob at {(x, y)} is not standing on a ledge")
            if x - 3 < 0 or solid_top(segment, x - 3) != y + 2 or solid_top(segment, x + 3) != y + 2:
                raise SystemExit(f"{label} blob at {(x, y)} patrols off its ledge")
        for x, y in segment["electrons"]:
            ground = solid_top(segment, x)
            if ground is None:
                raise SystemExit(f"{label} electron at {(x, y)} is over a pit")
            rise = required_rise(ground - 2, y)
            if rise <= 0 or rise > 40:
                raise SystemExit(f"{label} electron at {(x, y)} needs a {rise}px rise")
        if segment["chip"] is not None:
            chip_x, chip_y = segment["chip"]
            ground = solid_top(segment, chip_x)
            if ground is None or chip_y + 1 >= ground:
                raise SystemExit(f"{label} chip is buried")
            if ground - FLOOR_TOP > 4:
                raise SystemExit(f"{label} chip ledge is too high for the base jump")
            for electron_x, _electron_y in segment["electrons"]:
                if electron_x <= chip_x:
                    raise SystemExit(f"{label} electron at x={electron_x} is not after the chip")
        if solid_top(segment, PLAYER_START[0]) != PLAYER_START[1] + 2:
            raise SystemExit(f"{label} start is not on the floor")
        gate_x = SEG_W - 4
        if solid_top(segment, gate_x) != FLOOR_TOP:
            raise SystemExit(f"{label} gate is not on the floor")
        for index, (x, y) in enumerate(bodies):
            for other_x, other_y in bodies[index + 1 :]:
                if abs(x - other_x) < 2 and abs(y - other_y) < 2:
                    raise SystemExit(f"{label} actors overlap at {(x, y)} and {(other_x, other_y)}")
        total_electrons += len(segment["electrons"])
        total_blobs += len(segment["blobs"])
    if total_electrons < 20 or total_blobs < 10:
        raise SystemExit(f"expected a longer cast, got {total_electrons} electrons and {total_blobs} blobs")


def layout_rows(segment: dict) -> list[str]:
    marks = {PLAYER_START: "P", LIVES_AT: "H", AMMO_AT: "A"}
    for x, y in segment["blobs"]:
        marks[(x, y)] = "B"
    for x, y in segment["electrons"]:
        marks[(x, y)] = "e"
    if segment["chip"] is not None:
        marks[segment["chip"]] = "C"
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
        actors = 2 + len(segment["blobs"]) + len(segment["electrons"]) + (segment["chip"] is not None)
        print(f"{segment['name']}: {SEG_W} tiles, {actors} actors, {info['tiles']} background tiles")
        print("\n".join(layout_rows(segment)))
    if len(painted["clear"]["collisions"]) != CLEAR_W * CLEAR_H:
        raise SystemExit("clear collision size mismatch")
    print("Electrons:", sum(len(segment["electrons"]) for segment in SEGMENTS))
    print("Blobs:", sum(len(segment["blobs"]) for segment in SEGMENTS))
    print("Wrote", ROOT / "GrokBotPlatformer.gbsproj")


if __name__ == "__main__":
    main()
