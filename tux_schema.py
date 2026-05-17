#!/usr/bin/env python3
# tux_schema.py — simple platformer piloted by mishmaath schema evaluators

import pygame, sys, random
sys.path.insert(0, '/home/ajax80/projects/mishmaath')
from schema_eval import brings_joy, eleanor as el_eval

WIN_W, WIN_H = 960, 540
GAME_W = 680
PANEL_W = WIN_W - GAME_W
TILE  = 32
FPS   = 60

BG       = ( 20,  30,  50)
TILE_C   = ( 60, 120,  80)
TILE2_C  = ( 40,  90,  60)
PLAYER_C = ( 80, 160, 255)
ENEMY_C  = (220,  60,  60)
PANEL_BG = (  8,   8,  28)
TEXT_C   = (160, 160, 200)
ACCENT   = (  0, 200, 255)
WARN_C   = (255,  80,  80)
GOOD_C   = ( 80, 255, 120)
DIM_C    = ( 60,  60,  90)

GRAVITY    = 0.6
JUMP_VEL   = -13
MOVE_SPEED = 3

WEIGHT_NAMES = {
    1:"source", 3:"divine", 4:"door", 5:"friction",
    7:"settled", 8:"new octave", 9:"reset",
}
WEIGHT_MEANINGS = {
    1: "something is forming. starting out.",
    3: "alignment. clear path. moving well.",
    4: "threshold. edge ahead. decision.",
    5: "friction. danger nearby. Eleanor alert.",
    7: "settled. holding course. good ground.",
    8: "new octave. jumping to higher ground.",
    9: "reset. fell. start again.",
}


# ── level generation ───────────────────────────────────────────────────────────
def make_level():
    tiles   = []
    enemies = []
    x = 0

    # floor from 0 → 200
    for i in range(7):
        tiles.append(pygame.Rect(i * TILE, WIN_H - TILE, TILE, TILE))

    x = 7 * TILE

    chunks = [
        {"gap": 2, "plat": (3, WIN_H - TILE * 3), "enemy": True},
        {"gap": 3, "plat": (4, WIN_H - TILE * 2), "enemy": False},
        {"gap": 2, "plat": (3, WIN_H - TILE * 4), "enemy": True},
        {"gap": 3, "plat": (5, WIN_H - TILE * 2), "enemy": False},
        {"gap": 2, "plat": (4, WIN_H - TILE * 3), "enemy": True},
        {"gap": 2, "plat": (3, WIN_H - TILE * 2), "enemy": False},
        {"gap": 3, "plat": (5, WIN_H - TILE * 3), "enemy": True},
    ]

    for chunk in chunks:
        gap_w = chunk["gap"] * TILE
        x += gap_w

        pw, py = chunk["plat"]
        for i in range(pw):
            tiles.append(pygame.Rect(x + i * TILE, py, TILE, TILE))
        # floor under platform
        for i in range(pw):
            tiles.append(pygame.Rect(x + i * TILE, WIN_H - TILE, TILE, TILE))

        if chunk["enemy"]:
            ex = x + TILE
            enemies.append({"rect": pygame.Rect(ex, py - TILE, TILE - 4, TILE - 4),
                            "vx": 1, "left": x, "right": x + (pw - 1) * TILE})

        x += pw * TILE

    # end floor
    for i in range(5):
        tiles.append(pygame.Rect(x + i * TILE, WIN_H - TILE, TILE, TILE))

    total_w = x + 5 * TILE
    return tiles, enemies, total_w


# ── schema pilot ───────────────────────────────────────────────────────────────
def scan_ahead(player, tiles, enemies, cam_x, direction=1, steps=4):
    px = player.right if direction > 0 else player.left
    py = player.bottom
    for step in range(1, steps + 1):
        sx = px + direction * (step * TILE // 2)
        ground = any(
            t.left <= sx <= t.right and abs(t.top - py) < TILE
            for t in tiles
        )
        if not ground:
            return step - 1, "gap"
    return steps, "clear"

def enemy_ahead(player, enemies, direction=1, dist=TILE * 3):
    for e in enemies:
        if direction > 0 and e["rect"].left > player.right and e["rect"].left < player.right + dist:
            return True
        if direction < 0 and e["rect"].right < player.left and e["rect"].right > player.left - dist:
            return True
    return False

def platform_above(player, tiles, dist=TILE * 4):
    for t in tiles:
        if t.bottom < player.top and abs(t.centerx - player.centerx) < TILE * 3:
            if player.top - t.bottom < dist:
                return True
    return False

def schema_pilot(player, tiles, enemies, on_ground, cam_x, state):
    direction = state.get("direction", 1)
    steps, ahead = scan_ahead(player, tiles, enemies, cam_x, direction)
    danger       = enemy_ahead(player, enemies, direction)
    above        = platform_above(player, tiles)
    at_wall      = steps == 0

    jump   = False
    weight = 7

    if not on_ground:
        weight = 8 if state.get("just_jumped") else 7
        return direction, jump, weight, ahead, danger

    if danger:
        weight = 5
        el_fired = el_eval(5)
        if not el_fired:
            jump = True
            weight = 8
        else:
            direction = -direction

    elif at_wall or steps <= 1:
        weight = 4
        if above:
            jump = True
            weight = 8
        else:
            direction = -direction

    elif steps <= 2:
        weight = 4

    else:
        ctx = {"history": [], "reserves": 1.0, "failure_paths": {8: [9]}}
        weight = 7 if brings_joy(7, ctx) else 3

    return direction, jump, weight, ahead, danger


# ── draw helpers ───────────────────────────────────────────────────────────────
def draw_text(surf, text, x, y, color=TEXT_C, size=13, bold=False):
    font = pygame.font.SysFont("monospace", size, bold=bold)
    surf.blit(font.render(text, True, color), (x, y))

def draw_panel(surf, weight, ahead, danger, direction, score, on_ground):
    px = GAME_W
    surf.fill(PANEL_BG, (px, 0, PANEL_W, WIN_H))
    y = 20
    draw_text(surf, "mishmaath", px + 16, y, ACCENT, 16, bold=True)
    y += 28
    draw_text(surf, "─" * 20, px + 8, y, DIM_C)
    y += 20

    name    = WEIGHT_NAMES.get(weight, "?")
    meaning = WEIGHT_MEANINGS.get(weight, "")
    wcolor  = WARN_C if weight in {5, 9} else GOOD_C if weight in {7, 8} else ACCENT
    draw_text(surf, f"weight  {weight}", px + 16, y, TEXT_C)
    y += 18
    draw_text(surf, f"  {name}", px + 16, y, wcolor, bold=True)
    y += 18

    for line in _wrap(meaning, 24):
        draw_text(surf, f"  {line}", px + 16, y, DIM_C, 11)
        y += 15
    y += 10

    draw_text(surf, "─" * 20, px + 8, y, DIM_C)
    y += 20
    draw_text(surf, "sensors", px + 16, y, TEXT_C, bold=True)
    y += 18
    ac = WARN_C if ahead == "gap" else GOOD_C
    draw_text(surf, f"  ahead:   {ahead}", px + 16, y, ac)
    y += 18
    dc = WARN_C if danger else GOOD_C
    draw_text(surf, f"  danger:  {'YES' if danger else 'no'}", px + 16, y, dc)
    y += 18
    draw_text(surf, f"  ground:  {'yes' if on_ground else 'NO'}", px + 16, y, TEXT_C)
    y += 18
    draw_text(surf, f"  heading: {'RIGHT' if direction > 0 else 'LEFT'}", px + 16, y, TEXT_C)
    y += 30

    draw_text(surf, "─" * 20, px + 8, y, DIM_C)
    y += 20
    draw_text(surf, f"score  {score}", px + 16, y, TEXT_C)
    y += 30
    draw_text(surf, "─" * 20, px + 8, y, DIM_C)
    y += 20
    draw_text(surf, "↑↓  speed", px + 16, y, DIM_C, 11)
    y += 16
    draw_text(surf, "r   restart", px + 16, y, DIM_C, 11)
    y += 16
    draw_text(surf, "q   quit", px + 16, y, DIM_C, 11)

def _wrap(text, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= width:
            cur = (cur + " " + w).strip()
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines


# ── main ───────────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    surf  = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("tux — mishmaath pilot")
    clock = pygame.time.Clock()
    font  = pygame.font.SysFont("monospace", 13)

    def reset():
        tiles, enemies, total_w = make_level()
        player = pygame.Rect(TILE, WIN_H - TILE * 2, TILE - 4, TILE - 4)
        return tiles, enemies, total_w, player, 0.0, 0.0, False, 0

    tiles, enemies, total_w, player, vx, vy, on_ground, score = reset()
    state     = {"direction": 1, "just_jumped": False}
    weight    = 1
    ahead_st  = "clear"
    danger_st = False
    fps       = FPS
    cam_x     = 0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q: pygame.quit(); sys.exit()
                if event.key == pygame.K_r:
                    tiles, enemies, total_w, player, vx, vy, on_ground, score = reset()
                    state = {"direction": 1, "just_jumped": False}
                    weight = 1; cam_x = 0
                if event.key == pygame.K_UP:   fps = min(fps + 10, 120)
                if event.key == pygame.K_DOWN: fps = max(fps - 10, 10)

        # pilot decision
        direction, jump, weight, ahead_st, danger_st = schema_pilot(
            player, tiles, enemies, on_ground, cam_x, state)
        state["direction"] = direction

        if jump and on_ground:
            vy = JUMP_VEL
            on_ground = False
            state["just_jumped"] = True
        else:
            state["just_jumped"] = False

        vx = direction * MOVE_SPEED
        vy += GRAVITY

        # move x
        player.x += int(vx)
        for t in tiles:
            tr = t.move(-cam_x, 0)
            if player.colliderect(tr):
                if vx > 0: player.right = tr.left
                else:       player.left  = tr.right
                vx = 0

        # move y
        player.y += int(vy)
        on_ground = False
        for t in tiles:
            tr = t.move(-cam_x, 0)
            if player.colliderect(tr):
                if vy > 0:
                    player.bottom = tr.top
                    on_ground = True
                else:
                    player.top = tr.bottom
                vy = 0

        # enemy movement
        for e in enemies:
            e["rect"].x += e["vx"]
            if e["rect"].left <= e["left"] or e["rect"].right >= e["right"] + TILE:
                e["vx"] = -e["vx"]
            er = e["rect"].move(-cam_x, 0)
            if player.colliderect(er):
                weight = 9
                tiles, enemies, total_w, player, vx, vy, on_ground, score = reset()
                state = {"direction": 1, "just_jumped": False}
                cam_x = 0
                break

        # fell off
        if player.top > WIN_H:
            weight = 9
            tiles, enemies, total_w, player, vx, vy, on_ground, score = reset()
            state = {"direction": 1, "just_jumped": False}
            cam_x = 0

        # scroll camera
        target_cam = player.centerx - GAME_W // 3
        cam_x = max(0, min(target_cam, total_w - GAME_W))
        score += 1

        # ── draw ──
        surf.fill(BG, (0, 0, GAME_W, WIN_H))

        for t in tiles:
            tr = t.move(-cam_x, 0)
            if -TILE < tr.x < GAME_W + TILE:
                pygame.draw.rect(surf, TILE_C, tr)
                pygame.draw.rect(surf, TILE2_C, tr, 2)

        for e in enemies:
            er = e["rect"].move(-cam_x, 0)
            if -TILE < er.x < GAME_W + TILE:
                pygame.draw.rect(surf, ENEMY_C, er)
                pygame.draw.rect(surf, (255, 120, 120), er, 2)

        pc = WARN_C if weight in {5, 9} else GOOD_C if weight == 8 else PLAYER_C
        pygame.draw.rect(surf, pc, player)
        pygame.draw.rect(surf, (200, 230, 255), player, 2)

        draw_panel(surf, weight, ahead_st, danger_st, state["direction"], score, on_ground)
        pygame.display.flip()
        clock.tick(fps)


if __name__ == "__main__":
    main()
