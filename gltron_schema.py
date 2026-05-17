#!/usr/bin/env python3
# gltron_schema.py — light cycle piloted by mishmaath schema evaluators

import pygame, sys, random
sys.path.insert(0, '/home/ajax80/projects/mishmaath')
from schema_eval import brings_joy

# ── layout ─────────────────────────────────────────────────────────────────────
GAME_W, GAME_H = 640, 480
PANEL_W        = 280
WIN_W          = GAME_W + PANEL_W
WIN_H          = GAME_H
CELL           = 16
COLS           = GAME_W  // CELL
ROWS           = GAME_H  // CELL
FPS            = 12

# ── palette ────────────────────────────────────────────────────────────────────
BG       = (  4,   4,  18)
TRAIL_C  = (  0, 200, 255)
HEAD_C   = (255, 255, 255)
PANEL_BG = (  8,   8,  28)
TEXT_C   = (160, 160, 200)
ACCENT   = (  0, 200, 255)
WARN_C   = (255,  80,  80)
GOOD_C   = ( 80, 255, 120)
DIM_C    = ( 60,  60,  90)
GRID_C   = ( 14,  14,  35)

# ── directions ─────────────────────────────────────────────────────────────────
UP    = ( 0, -1)
DOWN  = ( 0,  1)
LEFT  = (-1,  0)
RIGHT = ( 1,  0)
L_OF  = {UP: LEFT,  LEFT: DOWN,  DOWN: RIGHT, RIGHT: UP}
R_OF  = {UP: RIGHT, RIGHT: DOWN, DOWN: LEFT,  LEFT: UP}
DIR_NAMES = {UP: "UP", DOWN: "DOWN", LEFT: "LEFT", RIGHT: "RIGHT"}

WEIGHT_NAMES = {
    0:"void",       1:"source",     2:"speak",    3:"divine",
    4:"door",       5:"friction",   6:"comfort",  7:"settled",
    8:"new octave", 9:"reset",     10:"repentance",
    88:"88",        76:"76",
}


# ── grid scan ──────────────────────────────────────────────────────────────────
def scan_depth(pos, direction, grid, limit=20):
    x, y = pos
    dx, dy = direction
    for i in range(1, limit + 1):
        nx, ny = x + dx * i, y + dy * i
        if nx < 0 or nx >= COLS or ny < 0 or ny >= ROWS or grid[ny][nx]:
            return i - 1
    return limit


# ── schema pilot ───────────────────────────────────────────────────────────────
def pilot(pos, direction, grid):
    options = {
        "straight": direction,
        "left":     L_OF[direction],
        "right":    R_OF[direction],
    }
    depths = {name: scan_depth(pos, d, grid) for name, d in options.items()}

    chosen_dir  = None
    chosen_name = None
    chosen_depth = -1

    scan_results = {}

    for name, d in options.items():
        depth = depths[name]
        failure = {8: [76]} if depth < 4 else {8: [9]}
        ctx = {"history": [], "reserves": 1.0, "failure_paths": failure}
        passes = brings_joy(8, ctx)
        scan_results[name] = {"depth": depth, "passes": passes}
        if passes and depth > chosen_depth:
            chosen_dir   = d
            chosen_name  = name
            chosen_depth = depth

    if chosen_dir is None:
        best = max(depths, key=depths.get)
        chosen_dir  = options[best]
        chosen_name = best
        chosen_depth = depths[best]
        scan_results[best]["forced"] = True

    # schema weight based on game state
    if chosen_depth <= 2:
        weight = 5          # friction — very close to wall
    elif chosen_name != "straight":
        weight = 4          # door — turning decision
    elif chosen_depth >= 12:
        weight = 8          # new octave — open road
    else:
        weight = 7          # settled — holding course

    return chosen_dir, weight, scan_results


# ── render helpers ─────────────────────────────────────────────────────────────
def draw_text(surf, text, x, y, color=TEXT_C, size=14, bold=False):
    font = pygame.font.SysFont("monospace", size, bold=bold)
    surf.blit(font.render(text, True, color), (x, y))


def draw_panel(surf, weight, scan_results, direction, score, lives):
    px = GAME_W
    surf.fill(PANEL_BG, (px, 0, PANEL_W, WIN_H))

    y = 20
    draw_text(surf, "mishmaath", px + 16, y, ACCENT, 16, bold=True)
    y += 30
    draw_text(surf, "─" * 22, px + 8, y, DIM_C, 13)
    y += 22

    name  = WEIGHT_NAMES.get(weight, "?")
    color = WARN_C if weight in {5, 9, 76} else GOOD_C if weight in {7, 8} else ACCENT
    draw_text(surf, f"weight  {weight}", px + 16, y, TEXT_C, 13)
    y += 18
    draw_text(surf, f"        {name}", px + 16, y, color, 13, bold=True)
    y += 30

    draw_text(surf, "─" * 22, px + 8, y, DIM_C, 13)
    y += 22
    draw_text(surf, "pathway scan", px + 16, y, TEXT_C, 13, bold=True)
    y += 20

    for name in ("straight", "left", "right"):
        r = scan_results.get(name, {})
        depth   = r.get("depth", 0)
        passes  = r.get("passes", False)
        forced  = r.get("forced", False)
        bar_len = min(depth, 18)
        bar     = "█" * bar_len + "░" * (18 - bar_len)
        status  = "FORCED" if forced else ("PASS" if passes else "STOP")
        sc      = WARN_C if not passes else GOOD_C
        draw_text(surf, f"{name[:8]:<8} {status}", px + 16, y, sc, 12)
        y += 16
        draw_text(surf, f"  {bar}  {depth:2}c", px + 16, y, DIM_C, 11)
        y += 20

    y += 10
    draw_text(surf, "─" * 22, px + 8, y, DIM_C, 13)
    y += 22
    draw_text(surf, f"heading  {DIR_NAMES[direction]}", px + 16, y, TEXT_C, 13)
    y += 22
    draw_text(surf, f"score    {score}", px + 16, y, TEXT_C, 13)
    y += 22
    draw_text(surf, f"lives    {lives}", px + 16, y, TEXT_C, 13)
    y += 40

    draw_text(surf, "─" * 22, px + 8, y, DIM_C, 13)
    y += 22
    draw_text(surf, "e   schema turn", px + 16, y, DIM_C, 12)
    y += 18
    draw_text(surf, "↑↓  speed", px + 16, y, DIM_C, 12)
    y += 18
    draw_text(surf, "r   restart", px + 16, y, DIM_C, 12)
    y += 18
    draw_text(surf, "q   quit", px + 16, y, DIM_C, 12)


def draw_game(surf, grid, trail, pos, weight):
    surf.fill(BG, (0, 0, GAME_W, GAME_H))

    for gy in range(ROWS):
        for gx in range(COLS):
            rx, ry = gx * CELL, gy * CELL
            pygame.draw.rect(surf, GRID_C, (rx, ry, CELL - 1, CELL - 1), 1)
            if grid[gy][gx]:
                pygame.draw.rect(surf, TRAIL_C, (rx + 1, ry + 1, CELL - 2, CELL - 2))

    hx, hy = pos
    glow = WARN_C if weight in {5, 9} else GOOD_C if weight == 8 else HEAD_C
    pygame.draw.rect(surf, glow, (hx * CELL, hy * CELL, CELL, CELL))


# ── game state ─────────────────────────────────────────────────────────────────
def new_game():
    grid = [[False] * COLS for _ in range(ROWS)]
    pos  = (COLS // 2, ROWS // 2)
    grid[pos[1]][pos[0]] = True
    return grid, list(), pos, RIGHT, 7


# ── main ───────────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    surf  = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("gltron — mishmaath pilot")
    clock = pygame.time.Clock()

    grid, trail, pos, direction, weight = new_game()
    scan_results = {}
    score  = 0
    lives  = 3
    fps    = FPS
    alive  = True
    paused = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    pygame.quit(); sys.exit()
                if event.key == pygame.K_r:
                    grid, trail, pos, direction, weight = new_game()
                    scan_results = {}
                    score = 0; alive = True
                if event.key == pygame.K_e and alive:
                    direction, weight, scan_results = pilot(pos, direction, grid)
                if event.key == pygame.K_UP:
                    fps = min(fps + 2, 30)
                if event.key == pygame.K_DOWN:
                    fps = max(fps - 2, 2)
                if event.key == pygame.K_SPACE:
                    paused = not paused

        if alive and not paused:
            direction, weight, scan_results = pilot(pos, direction, grid)
            nx, ny = pos[0] + direction[0], pos[1] + direction[1]

            if nx < 0 or nx >= COLS or ny < 0 or ny >= ROWS or grid[ny][nx]:
                weight = 9
                lives -= 1
                alive  = lives > 0
                if alive:
                    grid, trail, pos, direction, _ = new_game()
                    scan_results = {}
            else:
                pos = (nx, ny)
                grid[ny][nx] = True
                trail.append(pos)
                score += 1

        draw_game(surf, grid, trail, pos, weight)
        draw_panel(surf, weight, scan_results, direction, score, lives)
        pygame.display.flip()
        clock.tick(fps)


if __name__ == "__main__":
    main()
