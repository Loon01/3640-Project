# ==============================================================================
# GROUP MEMBERS: Adrian R., Christian V., Kamy A. and Vanessa F.
# ASGT: Project
# ORGN: CMPS 3640
# FILE: snake.py
# DESCRIPTION:
#   Local two-player versus Snake game (WASD vs Arrows) using Pygame.
#   Visual polish:
#     - Gradient-style background stripes + grid
#     - Rounded snake segments with outline
#     - Circular fruit
#     - Shadowed text for HUD, countdown, and messages
#     - Pause / Restart / Countdown / Game over screens
# ==============================================================================

import pygame
import random
from typing import List

# --- Settings ---
FPS_LOGIC = 12             # logic ticks per second (snake speed)
SCREEN_WIDTH = 720
SCREEN_HEIGHT = 480
CELL = 20                  # a bit bigger so it looks nicer

BORDER_COLOR = (90, 90, 90)
GRID_COLOR = (35, 35, 35)
BG_DARK = (15, 15, 20)
BG_STRIPE = (22, 22, 30)
P1_COLOR = (80, 230, 140)
P1_OUTLINE = (30, 150, 80)
P2_COLOR = (100, 150, 255)
P2_OUTLINE = (40, 90, 190)
FRUIT_COLOR = (255, 230, 80)
FRUIT_GLOW = (255, 200, 80)
TEXT_COLOR = (240, 240, 240)
TEXT_SHADOW = (0, 0, 0)

COUNTDOWN_SECONDS = 3

STATE_COUNTDOWN = "COUNTDOWN"
STATE_RUNNING = "RUNNING"
STATE_PAUSED = "PAUSED"
STATE_GAMEOVER = "GAMEOVER"


# --- Helper functions ---
def align_to_grid(x: int) -> int:
    return (x // CELL) * CELL


def spawn_fruit(blocked: List[list]) -> list:
    """Spawn fruit not overlapping any snake segment."""
    blocked_set = set((b[0], b[1]) for b in blocked)
    cols = SCREEN_WIDTH // CELL
    rows = SCREEN_HEIGHT // CELL
    while True:
        fx = random.randrange(0, cols) * CELL
        fy = random.randrange(0, rows) * CELL
        if (fx, fy) not in blocked_set:
            return [fx, fy]


def init_snakes():
    """Return initial positions & bodies for both snakes and scores."""
    # Player 1 (left side, facing RIGHT)
    p1_x = align_to_grid(SCREEN_WIDTH // 4)
    p1_y = align_to_grid(SCREEN_HEIGHT // 2)
    snake1_pos = [p1_x, p1_y]
    snake1_body = [
        [p1_x, p1_y],
        [p1_x - CELL, p1_y],
        [p1_x - 2 * CELL, p1_y],
        [p1_x - 3 * CELL, p1_y],
    ]
    snake1_direction = "RIGHT"
    snake1_change_to = "RIGHT"
    snake1_score = 0

    # Player 2 (right side, facing LEFT)
    p2_x = align_to_grid(SCREEN_WIDTH * 3 // 4)
    p2_y = align_to_grid(SCREEN_HEIGHT // 2)
    snake2_pos = [p2_x, p2_y]
    snake2_body = [
        [p2_x, p2_y],
        [p2_x + CELL, p2_y],
        [p2_x + 2 * CELL, p2_y],
        [p2_x + 3 * CELL, p2_y],
    ]
    snake2_direction = "LEFT"
    snake2_change_to = "LEFT"
    snake2_score = 0

    return (snake1_pos, snake1_body, snake1_direction, snake1_change_to, snake1_score,
            snake2_pos, snake2_body, snake2_direction, snake2_change_to, snake2_score)


def draw_background(screen: pygame.Surface):
    """Gradient-like stripes + grid."""
    # stripes
    stripe_width = 80
    for x in range(0, SCREEN_WIDTH, stripe_width):
        rect = pygame.Rect(x, 0, stripe_width, SCREEN_HEIGHT)
        color = BG_DARK if (x // stripe_width) % 2 == 0 else BG_STRIPE
        screen.fill(color, rect)

    # grid
    for x in range(0, SCREEN_WIDTH, CELL):
        pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, SCREEN_HEIGHT), 1)
    for y in range(0, SCREEN_HEIGHT, CELL):
        pygame.draw.line(screen, GRID_COLOR, (0, y), (SCREEN_WIDTH, y), 1)

    # border
    pygame.draw.rect(
        screen,
        BORDER_COLOR,
        pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT),
        width=3
    )


def show_score(screen, font, snake1_score, snake2_score):
    s1 = font.render(f"P1: {snake1_score}", True, TEXT_COLOR)
    s2 = font.render(f"P2: {snake2_score}", True, TEXT_COLOR)

    # soft shadow
    screen.blit(font.render(f"P1: {snake1_score}", True, TEXT_SHADOW), (11, 6))
    screen.blit(s1, (10, 5))

    x2 = SCREEN_WIDTH - 10 - s2.get_width()
    screen.blit(font.render(f"P2: {snake2_score}", True, TEXT_SHADOW), (x2 + 1, 6))
    screen.blit(s2, (x2, 5))


def draw_controls(screen, small_font):
    text = "P1: WASD   P2: Arrows   P: Pause/Resume   R: Restart   ESC: Quit"
    shadow = small_font.render(text, True, TEXT_SHADOW)
    surf = small_font.render(text, True, TEXT_COLOR)
    rect = surf.get_rect()
    rect.midbottom = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 6)
    screen.blit(shadow, (rect.x + 1, rect.y + 1))
    screen.blit(surf, rect)


def draw_center_text(screen, font, msg, y_offset=0):
    shadow = font.render(msg, True, TEXT_SHADOW)
    surf = font.render(msg, True, TEXT_COLOR)
    rect = surf.get_rect()
    rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + y_offset)
    screen.blit(shadow, (rect.x + 2, rect.y + 2))
    screen.blit(surf, rect)


def handle_input(event,
                 state,
                 snake1_change_to,
                 snake2_change_to):
    """Handle keyboard events: returns updated (state, snake1_change_to, snake2_change_to)."""
    if event.type == pygame.QUIT:
        pygame.quit()
        raise SystemExit

    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            pygame.quit()
            raise SystemExit

        # Pause / resume
        if event.key == pygame.K_p and state in (STATE_RUNNING, STATE_PAUSED):
            state = STATE_PAUSED if state == STATE_RUNNING else STATE_RUNNING

        # Restart
        if event.key == pygame.K_r:
            state = "RESTART"

        # Movement input only when running or countdown
        if state in (STATE_RUNNING, STATE_COUNTDOWN):
            # Player 1 (WASD)
            if event.key == pygame.K_w:
                snake1_change_to = "UP"
            elif event.key == pygame.K_s:
                snake1_change_to = "DOWN"
            elif event.key == pygame.K_a:
                snake1_change_to = "LEFT"
            elif event.key == pygame.K_d:
                snake1_change_to = "RIGHT"

            # Player 2 (Arrows)
            elif event.key == pygame.K_UP:
                snake2_change_to = "UP"
            elif event.key == pygame.K_DOWN:
                snake2_change_to = "DOWN"
            elif event.key == pygame.K_LEFT:
                snake2_change_to = "LEFT"
            elif event.key == pygame.K_RIGHT:
                snake2_change_to = "RIGHT"

    return state, snake1_change_to, snake2_change_to


def apply_direction_change(curr_dir, change_to):
    """Prevent 180° opposite direction."""
    if change_to == "UP" and curr_dir != "DOWN":
        return "UP"
    if change_to == "DOWN" and curr_dir != "UP":
        return "DOWN"
    if change_to == "LEFT" and curr_dir != "RIGHT":
        return "LEFT"
    if change_to == "RIGHT" and curr_dir != "LEFT":
        return "RIGHT"
    return curr_dir


def move_snake(pos, direction):
    if direction == "UP":
        pos[1] -= CELL
    elif direction == "DOWN":
        pos[1] += CELL
    elif direction == "LEFT":
        pos[0] -= CELL
    elif direction == "RIGHT":
        pos[0] += CELL
    return pos


def draw_snake(screen, body, fill_color, outline_color):
    for seg in body:
        x, y = seg
        rect = pygame.Rect(x, y, CELL, CELL)
        # outline
        pygame.draw.rect(screen, outline_color, rect, border_radius=5)
        # inner
        inner = rect.inflate(-4, -4)
        pygame.draw.rect(screen, fill_color, inner, border_radius=5)


def draw_fruit(screen, pos):
    # glow circle behind
    cx = pos[0] + CELL // 2
    cy = pos[1] + CELL // 2
    pygame.draw.circle(screen, FRUIT_GLOW, (cx, cy), CELL // 2)
    pygame.draw.circle(screen, FRUIT_COLOR, (cx, cy), CELL // 3)


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Versus Snake Game — Local")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("consolas", 24, bold=True)
    small_font = pygame.font.SysFont("consolas", 18)
    big_font = pygame.font.SysFont("consolas", 56, bold=True)
    title_font = pygame.font.SysFont("consolas", 28, bold=True)

    # --- Initial game state ---
    (snake1_pos, snake1_body, snake1_direction, snake1_change_to, snake1_score,
     snake2_pos, snake2_body, snake2_direction, snake2_change_to, snake2_score) = init_snakes()

    fruit_pos = spawn_fruit(snake1_body + snake2_body)

    state = STATE_COUNTDOWN
    countdown_start_ms = pygame.time.get_ticks()
    winner = None

    while True:
        # --- Event Handling ---
        for event in pygame.event.get():
            state, snake1_change_to, snake2_change_to = handle_input(
                event, state, snake1_change_to, snake2_change_to
            )

        # Restart requested
        if state == "RESTART":
            (snake1_pos, snake1_body, snake1_direction, snake1_change_to, snake1_score,
             snake2_pos, snake2_body, snake2_direction, snake2_change_to, snake2_score) = init_snakes()
            fruit_pos = spawn_fruit(snake1_body + snake2_body)
            state = STATE_COUNTDOWN
            countdown_start_ms = pygame.time.get_ticks()
            winner = None

        # --- Logic update ---
        if state == STATE_COUNTDOWN:
            now_ms = pygame.time.get_ticks()
            elapsed = (now_ms - countdown_start_ms) / 1000.0
            if elapsed >= COUNTDOWN_SECONDS:
                state = STATE_RUNNING

        elif state == STATE_RUNNING:
            # apply buffered direction changes
            snake1_direction = apply_direction_change(snake1_direction, snake1_change_to)
            snake2_direction = apply_direction_change(snake2_direction, snake2_change_to)

            # move snakes
            snake1_pos = move_snake(snake1_pos, snake1_direction)
            snake2_pos = move_snake(snake2_pos, snake2_direction)

            snake1_body.insert(0, list(snake1_pos))
            snake2_body.insert(0, list(snake2_pos))

            grew1 = (snake1_pos == fruit_pos)
            grew2 = (snake2_pos == fruit_pos)

            if grew1:
                snake1_score += 10
            if grew2:
                snake2_score += 10

            if grew1 or grew2:
                fruit_pos = spawn_fruit(snake1_body + snake2_body)

            if not grew1:
                snake1_body.pop()
            if not grew2:
                snake2_body.pop()

            # --- Collisions ---
            # Walls
            out1 = not (0 <= snake1_pos[0] < SCREEN_WIDTH and 0 <= snake1_pos[1] < SCREEN_HEIGHT)
            out2 = not (0 <= snake2_pos[0] < SCREEN_WIDTH and 0 <= snake2_pos[1] < SCREEN_HEIGHT)

            # Self
            self1 = snake1_pos in snake1_body[1:]
            self2 = snake2_pos in snake2_body[1:]

            # Head-to-head
            head_to_head = (snake1_pos == snake2_pos)

            # Head into other body
            into2 = snake1_pos in snake2_body[1:]
            into1 = snake2_pos in snake1_body[1:]

            # Determine result
            p1_dead = out1 or self1 or into2
            p2_dead = out2 or self2 or into1

            if head_to_head:
                p1_dead = True
                p2_dead = True

            if p1_dead or p2_dead:
                state = STATE_GAMEOVER
                if p1_dead and p2_dead:
                    winner = None
                elif p1_dead:
                    winner = "Player 2"
                elif p2_dead:
                    winner = "Player 1"

        # --- Drawing ---
        draw_background(screen)

        # title at top
        title_shadow = title_font.render("Versus Snake (Local Engine)", True, TEXT_SHADOW)
        title_surf = title_font.render("Versus Snake (Local Engine)", True, TEXT_COLOR)
        screen.blit(title_shadow, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2 + 2, 30 + 2))
        screen.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 30))

        # draw snakes & fruit
        draw_snake(screen, snake1_body, P1_COLOR, P1_OUTLINE)
        draw_snake(screen, snake2_body, P2_COLOR, P2_OUTLINE)
        draw_fruit(screen, fruit_pos)

        # scores + controls
        show_score(screen, font, snake1_score, snake2_score)
        draw_controls(screen, small_font)

        # overlays based on state
        if state == STATE_COUNTDOWN:
            now_ms = pygame.time.get_ticks()
            elapsed = (now_ms - countdown_start_ms) / 1000.0
            remaining = max(0.0, COUNTDOWN_SECONDS - elapsed)
            if remaining > 0.5:
                num = int(remaining) + 1
                msg = str(num)
            else:
                msg = "GO!"
            draw_center_text(screen, big_font, msg, y_offset=-10)

        elif state == STATE_PAUSED:
            draw_center_text(screen, big_font, "PAUSED", -20)
            draw_center_text(screen, font, "Press P to resume or R to restart", 20)

        elif state == STATE_GAMEOVER:
            if winner is None:
                msg = "Draw!"
            else:
                msg = f"{winner} Wins!"
            draw_center_text(screen, big_font, msg, -20)
            draw_center_text(screen, font, "Press R to restart or ESC to quit", 20)

        pygame.display.flip()
        clock.tick(FPS_LOGIC)


if __name__ == "__main__":
    main()
