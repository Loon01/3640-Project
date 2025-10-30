# ==============================================================================
# GROUP MEMBERS: Adrian R., Christian V., Kamy A. and Vanessa F.
# ASGT: Project
# ORGN: CMPS 3640
# FILE: snake.py
# DATE: 
# DESCRIPTION: A basic versus snake game for peer-to-peer connection.
# ==============================================================================

# === Libraries ===
import pygame
import time
import random

# === Settings ===
snake_speed = 15 # speed of snake
screen_width = 720
screen_height = 480

# === Setup ===
pygame.init()
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Versus Snake Game")
fps = pygame.time.Clock()

# === Snake 1 (WASD) ===
snake1_pos = pygame.Vector2(screen_width / 1/4, screen_height / 2) # snake position
snake1_body = [[100,50], [90,50], [80,50], [70,50]] # snake body, first 4 blocks
snake1_direction = 'RIGHT' # default snake direction
snake1_change_to = snake1_direction
snake1_score = 0 # initial score

# === Snake 2 (Arrow Keys) ===
snake2_pos = pygame.Vector2(screen_width * 3/4, screen_height / 2)
snake2_body = [[600, 50], [610, 50], [620, 50], [630, 50]]
snake2_direction = 'LEFT'
snake2_change_to = snake2_direction
snake2_score = 0

# === Fruit ===
# position of fruit (random)
fruit_pos = [random.randrange(1, (screen_width//10)) * 10,
             random.randrange(1, (screen_height//10)) * 10] 
fruit_spawn = True

# === Score display ===
def show_score(color, font, size):
    score_font = pygame.font.SysFont(font, size) # creating font score object 
    
    # creating the display surface object
    score_surface1 = score_font.render('P1 Score: ' + str(snake1_score), True, color) 
    score_surface2 = score_font.render('P2 Score: ' + str(snake2_score), True, color)
    
    screen.blit(score_surface1, (10, 5)) # display text
    screen.blit(score_surface2, (screen_width - 160, 5))
    
    
# === Game Over ===
def game_over(winner = None):
    my_font = pygame.font.SysFont('times new roman', 50) # creating font obj
    msg = "Draw!" if not winner else f"{winner} Wins!"
    
    # creating txt surface on which txt will be drawn
    game_over_surface = my_font.render(msg, True, "red") 
    
    # creating rect obj for the txt surface obj
    rect = game_over_surface.get_rect() 
    
    # positioning text
    rect.midtop = (screen_width / 2, screen_height / 4)  
    
    # blit will draw the text on screen
    screen.blit(game_over_surface, rect) 
    
    # flip() the display to put your work on screen, updates score
    pygame.display.flip() 
    
    time.sleep(2) # waits 2 seconds
    pygame.quit # quits pygame library
    quit() # quits program

# === Main Function ===
while True:
    # --- Handling key events ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            quit()
        elif event.type == pygame.KEYDOWN:
            # Player 1 controls (WASD)
            if event.key == pygame.K_w:
                snake1_change_to = 'UP'
            if event.key == pygame.K_s:
                snake1_change_to = 'DOWN'
            if event.key == pygame.K_a:
                snake1_change_to = 'LEFT'
            if event.key == pygame.K_d:
                snake1_change_to = 'RIGHT'
            
            # Player 2 controls (arrow keys)
            elif event.key == pygame.K_UP:
                snake2_change_to = 'UP'
            elif event.key == pygame.K_DOWN:
                snake2_change_to = 'DOWN'
            elif event.key == pygame.K_LEFT:
                snake2_change_to = 'LEFT'
            elif event.key == pygame.K_RIGHT:
                snake2_change_to = 'RIGHT'
        
            elif event.key == pygame.K_ESCAPE:
                pygame.quit()
                quit()

    # --- Prevents 180 degree turns ---
    if snake1_change_to == 'UP' and snake1_direction != 'DOWN':
        snake1_direction = 'UP'
    if snake1_change_to == 'DOWN' and snake1_direction != 'UP':
        snake1_direction = 'DOWN'
    if snake1_change_to == 'LEFT' and snake1_direction != 'RIGHT':
        snake1_direction = 'LEFT'
    if snake1_change_to == 'RIGHT' and snake1_direction != 'LEFT':
        snake1_direction = 'RIGHT'
    
    if snake2_change_to == 'UP' and snake2_direction != 'DOWN':
        snake2_direction = 'UP'
    if snake2_change_to == 'DOWN' and snake2_direction != 'UP':
        snake2_direction = 'DOWN'
    if snake2_change_to == 'LEFT' and snake2_direction != 'RIGHT':
        snake2_direction = 'LEFT'
    if snake2_change_to == 'RIGHT' and snake2_direction != 'LEFT':
        snake2_direction = 'RIGHT'

    # --- Moving the snakes ---
    if snake1_direction == 'UP':
        snake1_pos[1] -= 10
    if snake1_direction == 'DOWN':
        snake1_pos[1] += 10
    if snake1_direction == 'LEFT':
        snake1_pos[0] -= 10
    if snake1_direction == 'RIGHT':
        snake1_pos[0] += 10
    
    if snake2_direction == 'UP':
        snake2_pos[1] -= 10
    if snake2_direction == 'DOWN':
        snake2_pos[1] += 10
    if snake2_direction == 'LEFT':
        snake2_pos[0] -= 10
    if snake2_direction == 'RIGHT':
        snake2_pos[0] += 10

    # --- Grow Snakes / Eat fruit --- 
    snake1_body.insert(0, list(snake1_pos))
    snake2_body.insert(0, list(snake2_pos))
    
    # Check if either snake eats fruit
    if list(snake1_pos) == fruit_pos:
        snake1_score += 10
        fruit_spawn = False
    else:
        snake1_body.pop()

    if list(snake2_pos) == fruit_pos:
        snake2_score += 10
        fruit_spawn = False
    else:
        snake2_body.pop()

    if not fruit_spawn:
        fruit_pos = [random.randrange(1, (screen_width // 10)) * 10,
                     random.randrange(1, (screen_height // 10)) * 10]
        fruit_spawn = True

    # --- Draw Everything ---
    screen.fill("black")

    for pos in snake1_body:
        pygame.draw.rect(screen, "green", pygame.Rect(pos[0], pos[1], 10, 10))
    for pos in snake2_body:
        pygame.draw.rect(screen, "blue", pygame.Rect(pos[0], pos[1], 10, 10))

    pygame.draw.rect(screen, "white", pygame.Rect(fruit_pos[0], fruit_pos[1], 10, 10))

    # --- Collision: Walls ---
    for snake, pos, name in [
        (snake1_body, snake1_pos, "Player 2"),
        (snake2_body, snake2_pos, "Player 1")
    ]:
        if pos[0] < 0 or pos[0] > screen_width - 10 or pos[1] < 0 or pos[1] > screen_height - 10:
            game_over(name)
    
    # --- Collision: Self ---
    for block in snake1_body[1:]:
        if snake1_pos[0] == block[0] and snake1_pos[1] == block[1]:
            game_over("Player 2")
    for block in snake2_body[1:]:
        if snake2_pos[0] == block[0] and snake2_pos[1] == block[1]:
            game_over("Player 1")

    # --- Collision between snakes ---
    for block in snake1_body:
        if snake2_pos[0] == block[0] and snake2_pos[1] == block[1]:
            game_over("Player 1")
    for block in snake2_body:
        if snake1_pos[0] == block[0] and snake1_pos[1] == block[1]:
            game_over("Player 2")

    # --- Display Scores ---
    show_score("white", 'times new roman', 20)
    pygame.display.update()
    fps.tick(snake_speed)
