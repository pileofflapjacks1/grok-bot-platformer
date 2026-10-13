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

# Sprite colors. Index 0 is transparent (alpha 0).
PINK = (248, 144, 196, 255)
PINK_D = (192, 96, 152, 255)
RED = (248, 72, 72, 255)
RED_D = (160, 24, 24, 255)
YELLOW = (248, 224, 48, 255)
ORANGE = (224, 144, 16, 255)
BLACK = (24, 16, 24, 255)
CLEAR = (0, 0, 0, 0)

LEVEL_W = 68
LEVEL_H = 18
CLEAR_W = 20
CLEAR_H = 18

# About 3.4 screens. One hole in the middle is the only pit.
# Other height changes are solid all the way down, so the run has to jump.
FLOOR_TOP = 15
FLOOR = [(0, 31, FLOOR_TOP), (35, 67, FLOOR_TOP)]
# The first ledge stops early so a running jump off it still lands before the pit.
RAISED = [(16, 24, 12), (48, 67, 13)]
PIT = (32, 34)
PLAYER_START = (2, FLOOR_TOP - 2)
CLEAR_TOP = 16
MUSIC_ID = "f50428ab-a084-4591-9bba-2ba10fe7b1c6"

# Sprite positions are the top-left tile. A 16px actor on a ledge uses y = top - 2.
BLOB_1 = (20, 10)
BLOB_2 = (52, 11)
STARS = [(6, 10), (40, 9), (61, 8)]
EXIT_BOX = (64, 11, 3, 2)
PIT_BOX = (32, 15, 3, 3)
LIVES_AT = (1, 0)
# Level scene is 544px wide from x=80, so the clear scene starts past that.
CLEAR_SCENE_X = 680


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
    image = blank(64, 16, CLEAR)
    for frame, cy in enumerate((8.2, 9.2, 7.2, 6.2)):
        origin = frame * 16
        stamp_disk(image, origin, 8, cy, 6.3, PINK, PINK_D, BLACK)
        stamp_eye(image, origin, 5.6, cy - 1.2, 1.7, 2.3, BLACK)
        stamp_eye(image, origin, 10.4, cy - 1.2, 1.7, 2.3, BLACK)
    return image


def paint_enemy() -> list[list[tuple[int, int, int, int]]]:
    image = blank(16, 16, CLEAR)
    # Wider than the player so the blob reads as an enemy.
    r2 = 7.2 * 7.2
    inner = 6.0 * 6.0
    for y in range(16):
        for x in range(16):
            dx = (x + 0.5 - 8) / 1.15
            dy = y + 0.5 - 9
            dist = dx * dx + dy * dy
            if dist <= inner:
                image[y][x] = RED_D if y >= 11 else RED
            elif dist <= r2:
                image[y][x] = BLACK
    stamp_eye(image, 0, 5.4, 8.2, 1.55, 2.1, BLACK)
    stamp_eye(image, 0, 10.6, 8.2, 1.55, 2.1, BLACK)
    return image


def paint_star() -> list[list[tuple[int, int, int, int]]]:
    # 16x16 star. y = yellow, o = orange, k = outline.
    rows = [
        "................",
        ".......kk.......",
        "......kyyk......",
        "......kyyk......",
        ".....kyyyyk.....",
        ".kkkkyyyyyykkkk.",
        "kkyyyyyyyyyyykk.",
        ".kyyyyyoyyyyyk..",
        "..kyyyyoyyyyk...",
        "..kyyyyooyyk....",
        "...kyyookk......",
        "...kyykyyk......",
        "..kyyk..kyyk....",
        "..kyk....kyk....",
        "...k......k.....",
        "................",
    ]
    lookup = {".": CLEAR, "y": YELLOW, "o": ORANGE, "k": BLACK}
    return [[lookup[ch] for ch in row] for row in rows]


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


def solid_top(x: int) -> int | None:
    if PIT[0] <= x <= PIT[1]:
        return None
    tops = [top for x0, x1, top in FLOOR + RAISED if x0 <= x <= x1]
    if not tops:
        return None
    return min(tops)


def paint_lives() -> list[list[tuple[int, int, int, int]]]:
    """Four frames: 0, 1, 2, and 3 red hearts. Frame index matches `lives`."""
    image = blank(64, 16, CLEAR)
    outline = [(0, 0), (2, 0), (4, 0), (0, 2), (4, 2), (1, 3), (3, 3), (2, 4)]
    fill = [(1, 0), (3, 0), (1, 1), (2, 1), (3, 1), (1, 2), (2, 2), (3, 2), (2, 3)]
    for frame in range(4):
        for slot in range(frame):
            ox = frame * 16 + slot * 5
            oy = 4
            for x, y in outline:
                image[oy + y][ox + x] = BLACK
            for x, y in fill:
                image[oy + y][ox + x] = RED
    return image


def paint_level() -> tuple[list[list[tuple[int, int, int, int]]], list[int]]:
    tiles = {0: sky_tile(), 1: grass_tile(), 2: dirt_tile()}
    image = blank(LEVEL_W * 8, LEVEL_H * 8, SKY)
    collisions = [0] * (LEVEL_W * LEVEL_H)
    for tile_y in range(LEVEL_H):
        for tile_x in range(LEVEL_W):
            top = solid_top(tile_x)
            if top is None or tile_y < top:
                kind = 0
            elif tile_y == top:
                kind = 1
                collisions[tile_y * LEVEL_W + tile_x] = 15
            else:
                kind = 2
                collisions[tile_y * LEVEL_W + tile_x] = 15
            pattern = tiles[kind]
            for py in range(8):
                for px in range(8):
                    image[tile_y * 8 + py][tile_x * 8 + px] = pattern[py][px]
    return image, collisions


def paint_clear() -> tuple[list[list[tuple[int, int, int, int]]], list[int]]:
    tiles = {0: sky_tile(), 1: grass_tile(), 2: dirt_tile()}
    image = blank(CLEAR_W * 8, CLEAR_H * 8, SKY)
    collisions = [0] * (CLEAR_W * CLEAR_H)
    for tile_y in range(CLEAR_H):
        for tile_x in range(CLEAR_W):
            if tile_y < CLEAR_TOP:
                kind = 0
            elif tile_y == CLEAR_TOP:
                kind = 1
                collisions[tile_y * CLEAR_W + tile_x] = 15
            else:
                kind = 2
                collisions[tile_y * CLEAR_W + tile_x] = 15
            pattern = tiles[kind]
            for py in range(8):
                for px in range(8):
                    image[tile_y * 8 + py][tile_x * 8 + px] = pattern[py][px]
    return image, collisions


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
    # Frame index matches the lives variable: 0, 1, 2, then 3 hearts.
    frames = [frame_of(f"lives-f{index}", index * 16) for index in range(4)]
    animations = [{"id": uid("lives-anim0"), "frames": frames}]
    animations.extend(empty_frame(f"lives-anim{index}") for index in range(1, 8))
    return animations


def background_resource(
    *,
    name: str,
    symbol: str,
    filename: str,
    tiles_x: int,
    tiles_y: int,
) -> dict:
    return {
        "_resourceType": "background",
        "id": uid(symbol),
        "name": name,
        "symbol": symbol,
        "tileColors": compress8([0] * (tiles_x * tiles_y)),
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
        "hit1Script": [],
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
) -> dict:
    return {
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


def enemy_update(suffix: str) -> list:
    return [
        move_by(f"{suffix}-move-right", 3),
        wait_frames(f"{suffix}-wait-right", 20),
        move_by(f"{suffix}-move-left", -3),
        wait_frames(f"{suffix}-wait-left", 20),
    ]


def vanish_blob(suffix: str) -> list:
    # Hide first so the sprite is gone even if deactivate ends the script.
    return [
        event(f"blob-hide-{suffix}", "EVENT_ACTOR_HIDE", {"actorId": "$self$"}),
        event(
            f"blob-nocol-{suffix}",
            "EVENT_ACTOR_COLLISIONS_DISABLE",
            {"actorId": "$self$"},
        ),
        event(f"blob-stop-{suffix}", "EVENT_ACTOR_STOP_UPDATE", {"actorId": "$self$"}),
        beep(f"blob-stomp-sound-{suffix}", 6),
        event(f"blob-bounce-{suffix}", "EVENT_PLAYER_BOUNCE", {"height": "medium"}),
        deactivate(f"blob-stomp-hide-{suffix}"),
    ]


def enemy_script(suffix: str) -> list:
    hurt = [
        beep(f"{suffix}-hurt-sound", 2),
        event(f"{suffix}-knockback", "EVENT_PLATFORMER_STATE_SET", {"state": "knockback"}),
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
        {"true": vanish_blob(suffix + "-fall"), "false": hurt},
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
            {"true": vanish_blob(suffix + "-above"), "false": [falling]},
        )
    ]


def star_script(index: int) -> list:
    return [
        event("star-inc-" + str(index), "EVENT_INC_VALUE", {"variable": "0"}),
        beep(f"star-sound-{index}", 7),
        deactivate(f"star-hide-{index}"),
    ]


def exit_script() -> list:
    return [
        event(
            "exit-if",
            "EVENT_IF_VALUE",
            {
                "variable": "0",
                "operator": ">=",
                "comparator": 3,
                "__collapseElse": False,
            },
            {
                "true": [switch_scene("exit-clear", "scene_level1_clear", 2, CLEAR_TOP - 2)],
                "false": [
                    event(
                        "exit-need-more",
                        "EVENT_TEXT",
                        {"text": "Need more power-ups!"},
                    )
                ],
            },
        )
    ]


def respawn(name: str) -> list:
    return [
        event(
            f"{name}-pos",
            "EVENT_ACTOR_SET_POSITION",
            {
                "actorId": "player",
                "x": {"type": "number", "value": PLAYER_START[0]},
                "y": {"type": "number", "value": PLAYER_START[1]},
                "units": "tiles",
            },
        ),
        event(
            f"{name}-vx",
            "EVENT_ENGINE_FIELD_SET",
            {"engineFieldKey": "plat_vel_x", "value": {"type": "number", "value": 0}},
        ),
        event(
            f"{name}-vy",
            "EVENT_ENGINE_FIELD_SET",
            {"engineFieldKey": "plat_vel_y", "value": {"type": "number", "value": 0}},
        ),
        event(f"{name}-ground", "EVENT_PLATFORMER_STATE_SET", {"state": "ground"}),
    ]


def show_lives(name: str) -> dict:
    return event(
        name,
        "EVENT_ACTOR_SET_FRAME",
        {
            "actorId": uid("actor_lives"),
            "frame": {"type": "variable", "value": "1"},
        },
    )


def pit_script(name: str) -> list:
    # The trigger sits at the bottom of the gap, so this runs after the fall.
    # The heart marker updates in place. A scene reload, used only at 0 lives,
    # sets lives back to 3 and clears the stars.
    return [
        event(f"{name}-dec", "EVENT_DEC_VALUE", {"variable": "1"}),
        show_lives(f"{name}-hearts"),
        if_value(
            f"{name}-dead",
            "1",
            "==",
            0,
            [
                event(f"{name}-over", "EVENT_TEXT", {"text": "Game Over"}),
                switch_scene(
                    f"{name}-restart",
                    "scene_level1_green_hills",
                    PLAYER_START[0],
                    PLAYER_START[1],
                ),
            ],
            respawn(name),
        ),
    ]


def build_images() -> dict[str, int]:
    sprites = ROOT / "assets" / "sprites"
    backgrounds = ROOT / "assets" / "backgrounds"
    player = paint_player()
    enemy = paint_enemy()
    star = paint_star()
    lives = paint_lives()
    level, level_collisions = paint_level()
    clear, clear_collisions = paint_clear()
    write_png(sprites / "player_pink.png", 64, 16, player)
    write_png(sprites / "enemy_red_blob.png", 16, 16, enemy)
    write_png(sprites / "collectible_star.png", 16, 16, star)
    write_png(sprites / "lives.png", 64, 16, lives)
    write_png(backgrounds / "level1_green_hills.png", LEVEL_W * 8, LEVEL_H * 8, level)
    write_png(backgrounds / "level1_clear.png", CLEAR_W * 8, CLEAR_H * 8, clear)
    return {
        "level_tiles": unique_tiles(level),
        "clear_tiles": unique_tiles(clear),
        "level_collisions": level_collisions,
        "clear_collisions": clear_collisions,
    }


def build_resources(collisions: dict) -> None:
    sprites = ROOT / "assets" / "sprites"
    backgrounds = ROOT / "assets" / "backgrounds"
    write_json(
        sprites / "player_pink.png.gbsres",
        sprite_resource(
            name="player_pink",
            symbol="sprite_player_pink",
            filename="player_pink.png",
            image_path=sprites / "player_pink.png",
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
            width=16,
            height=16,
            animation_type="fixed",
            animations=fixed_animation("enemy"),
            num_tiles=2,
        ),
    )
    write_json(
        sprites / "collectible_star.png.gbsres",
        sprite_resource(
            name="collectible_star",
            symbol="sprite_collectible_star",
            filename="collectible_star.png",
            image_path=sprites / "collectible_star.png",
            width=16,
            height=16,
            animation_type="fixed",
            animations=fixed_animation("star"),
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
    write_json(
        backgrounds / "level1_green_hills.png.gbsres",
        background_resource(
            name="level1_green_hills",
            symbol="bg_level1_green_hills",
            filename="level1_green_hills.png",
            tiles_x=LEVEL_W,
            tiles_y=LEVEL_H,
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
        ),
    )

    palettes = ROOT / "project" / "palettes"
    write_json(
        palettes / "green_hills.gbsres",
        palette("Green Hills", ["B8F0E8", "68D070", "289038", "183028"]),
    )
    write_json(
        palettes / "grok_pink.gbsres",
        palette("Grok Pink", ["F8F8F8", "F890C4", "C06098", "181018"]),
    )
    write_json(
        palettes / "blob_red.gbsres",
        palette("Blob Red", ["F8F8F8", "F84848", "A01818", "181018"]),
    )
    write_json(
        palettes / "star_yellow.gbsres",
        palette("Star Yellow", ["F8F8F8", "F8E030", "E09010", "181018"]),
    )

    bg_ids = [
        uid("palette-Green Hills"),
        "default-bg-2",
        "default-bg-3",
        "default-bg-4",
        "default-bg-5",
        "default-bg-6",
        "dmg",
        "default-ui",
    ]
    sprite_ids = [
        uid("palette-Grok Pink"),
        uid("palette-Blob Red"),
        uid("palette-Star Yellow"),
        "default-sprite",
        "default-sprite",
        "default-sprite",
        "default-sprite",
        "default-sprite",
    ]

    level_dir = ROOT / "project" / "scenes" / "level_1_green_hills"
    clear_dir = ROOT / "project" / "scenes" / "level_1_clear"
    write_json(
        level_dir / "scene.gbsres",
        scene(
            name="Level 1 Green Hills",
            symbol="scene_level1_green_hills",
            index=0,
            x=80,
            y=40,
            width=LEVEL_W,
            height=LEVEL_H,
            background_symbol="bg_level1_green_hills",
            palette_ids=bg_ids,
            sprite_palette_ids=sprite_ids,
            script=[
                event(
                    "level-music",
                    "EVENT_MUSIC_PLAY",
                    {"musicId": MUSIC_ID, "loop": True},
                ),
                set_number("level-reset-powerups", "0", 0),
                set_number("level-reset-lives", "1", 3),
                show_lives("level-hearts"),
            ],
            collisions=collisions["level_collisions"],
        ),
    )
    write_json(
        level_dir / "actors" / "lives.gbsres",
        actor(
            name="Lives",
            symbol="actor_lives",
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
    blobs = [
        ("Waddle Blob", "actor_waddle_blob", "waddle_blob.gbsres", 1, BLOB_1, "blob1"),
        ("Waddle Blob 2", "actor_waddle_blob_2", "waddle_blob_2.gbsres", 2, BLOB_2, "blob2"),
    ]
    for name, symbol, filename, index, (x, y), suffix in blobs:
        write_json(
            level_dir / "actors" / filename,
            actor(
                name=name,
                symbol=symbol,
                index=index,
                x=x,
                y=y,
                sprite_symbol="sprite_enemy_red_blob",
                palette_name="Blob Red",
                script=enemy_script(suffix),
                update_script=enemy_update(suffix),
            ),
        )
    for index, (x, y) in enumerate(STARS, start=1):
        write_json(
            level_dir / "actors" / f"star_{index}.gbsres",
            actor(
                name=f"Star {index}",
                symbol=f"actor_star_{index}",
                index=index + 2,
                x=x,
                y=y,
                sprite_symbol="sprite_collectible_star",
                palette_name="Star Yellow",
                script=star_script(index),
            ),
        )
    exit_x, exit_y, exit_w, exit_h = EXIT_BOX
    pit_x, pit_y, pit_w, pit_h = PIT_BOX
    write_json(
        level_dir / "triggers" / "exit.gbsres",
        trigger("Exit", "trigger_exit", 0, exit_x, exit_y, exit_w, exit_h, exit_script()),
    )
    write_json(
        level_dir / "triggers" / "pit.gbsres",
        trigger("Pit", "trigger_pit", 1, pit_x, pit_y, pit_w, pit_h, pit_script("pit")),
    )
    for stale in ("pit_left.gbsres", "pit_right.gbsres"):
        stale_path = level_dir / "triggers" / stale
        if stale_path.exists():
            stale_path.unlink()
    write_json(
        clear_dir / "scene.gbsres",
        scene(
            name="Level 1 Clear",
            symbol="scene_level1_clear",
            index=1,
            x=CLEAR_SCENE_X,
            y=40,
            width=CLEAR_W,
            height=CLEAR_H,
            background_symbol="bg_level1_clear",
            palette_ids=bg_ids,
            sprite_palette_ids=sprite_ids,
            script=[event("clear-text", "EVENT_TEXT", {"text": "Level 1 clear!"})],
            collisions=collisions["clear_collisions"],
        ),
    )


def patch_project() -> None:
    metadata_path = ROOT / "GrokBotPlatformer.gbsproj"
    metadata = {
        "_resourceType": "project",
        "name": "GrokBotPlatformer",
        "author": "Joe",
        "notes": "Level 1 demo for ModRetro Chromatic. Open in GB Studio 4.2 or newer.",
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
    player_id = uid("sprite_player_pink")
    settings["colorMode"] = "color"
    settings["startSceneId"] = uid("scene_level1_green_hills")
    settings["startX"] = PLAYER_START[0]
    settings["startY"] = PLAYER_START[1]
    settings["startDirection"] = "right"
    settings["defaultSceneTypeId"] = "PLATFORM"
    settings["playerPaletteId"] = uid("palette-Grok Pink")
    settings["defaultSpritePaletteId"] = uid("palette-Grok Pink")
    settings["defaultBackgroundPaletteIds"][0] = uid("palette-Green Hills")
    settings["defaultSpritePaletteIds"] = [
        uid("palette-Grok Pink"),
        uid("palette-Blob Red"),
        uid("palette-Star Yellow"),
        "default-sprite",
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
                    "name": "powerups",
                    "symbol": "var_powerups",
                    "type": "number",
                },
                {
                    "id": "1",
                    "name": "lives",
                    "symbol": "var_lives",
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
| player_pink.png | Grok Bot, right-facing. Four frames: idle, walk A, walk B, jump. Left facing is mirrored. |
| enemy_red_blob.png | Waddle Blob |
| collectible_star.png | Power-up star |
| lives.png | Four frames in one animation. Frame 0 is empty, then 1, 2, and 3 hearts. The pinned actor shows the frame that matches `lives`. |

`actor.png`, `actor_animated.png`, and `static.png` are the GB Studio blank-template placeholders. The player setting points at `player_pink.png`.

Other shapes from the character-select design (heart, star, teardrop, and the rest) are not drawn yet. Palette swaps for those shapes come after this level is playable.

Regenerate with `python3 scripts/build_level1.py`.
"""
    (ROOT / "assets" / "sprites" / "README.md").write_text(text, encoding="utf-8")


def required_rise(stand_y: int, actor_y: int) -> int:
    """Pixels the player must rise before two 16px sprites overlap."""
    return stand_y * 8 - (actor_y * 8 + 15)


def validate_layout() -> None:
    for x in range(PIT[0], PIT[1] + 1):
        if solid_top(x) is not None:
            raise SystemExit(f"pit column {x} is solid")
    for x, y in (BLOB_1, BLOB_2):
        if solid_top(x) != y + 2:
            raise SystemExit(f"blob at {(x, y)} is not standing on a ledge")
        if x - 3 < 0 or solid_top(x - 3) != y + 2 or solid_top(x + 3) != y + 2:
            raise SystemExit(f"blob at {(x, y)} patrols off its ledge")
    for x, y in STARS:
        ground = solid_top(x)
        if ground is None:
            raise SystemExit(f"star at {(x, y)} is over the pit")
        rise = required_rise(ground - 2, y)
        if rise <= 0 or rise > 40:
            raise SystemExit(f"star at {(x, y)} needs a {rise}px rise")
    exit_x, exit_y, _exit_w, exit_h = EXIT_BOX
    if exit_y + exit_h > solid_top(exit_x):
        raise SystemExit("exit trigger overlaps the floor")
    pit_x, pit_y, pit_w, _pit_h = PIT_BOX
    if (pit_x, pit_x + pit_w - 1) != PIT or pit_y < FLOOR_TOP:
        raise SystemExit("pit trigger is not at the bottom of the hole")
    if solid_top(PLAYER_START[0]) != PLAYER_START[1] + 2:
        raise SystemExit("player start is not standing on the floor")
    landing = 0
    for x in range(PIT[0] - 1, -1, -1):
        if solid_top(x) != FLOOR_TOP:
            break
        landing += 1
    if landing < 6:
        raise SystemExit(f"only {landing} tiles of floor before the pit")
    boxes = [BLOB_1, BLOB_2, *STARS]
    for index, (x, y) in enumerate(boxes):
        for other_x, other_y in boxes[index + 1 :]:
            if abs(x - other_x) < 2 and abs(y - other_y) < 2:
                raise SystemExit(f"actors overlap at {(x, y)} and {(other_x, other_y)}")


def layout_rows() -> list[str]:
    marks = {
        PLAYER_START: "P",
        BLOB_1: "A",
        BLOB_2: "B",
        LIVES_AT: "H",
    }
    for index, pos in enumerate(STARS, start=1):
        marks[pos] = str(index)
    exit_x, exit_y, exit_w, exit_h = EXIT_BOX
    for dx in range(exit_w):
        for dy in range(exit_h):
            marks.setdefault((exit_x + dx, exit_y + dy), "E")
    pit_x, pit_y, pit_w, pit_h = PIT_BOX
    for dx in range(pit_w):
        for dy in range(pit_h):
            marks.setdefault((pit_x + dx, pit_y + dy), "V")
    rows = []
    for y in range(LEVEL_H):
        chars = []
        for x in range(LEVEL_W):
            top = solid_top(x)
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
    counts = build_images()
    build_resources(counts)
    patch_project()
    write_sprite_readme()
    level_collisions = counts["level_collisions"]
    if len(level_collisions) != LEVEL_W * LEVEL_H:
        raise SystemExit("level collision size mismatch")
    if len(counts["clear_collisions"]) != CLEAR_W * CLEAR_H:
        raise SystemExit("clear collision size mismatch")
    if counts["level_tiles"] != 3:
        raise SystemExit(f"expected 3 background tiles, got {counts['level_tiles']}")
    print("Level 1 unique background tiles:", counts["level_tiles"])
    print("Clear screen unique background tiles:", counts["clear_tiles"])
    print("Player start tile:", PLAYER_START)
    print("\n".join(layout_rows()))
    print("Wrote", ROOT / "GrokBotPlatformer.gbsproj")


if __name__ == "__main__":
    main()
