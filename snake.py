# libraries
import pygame
import time
import random

# speed of snake
snake_speed = 15

# window dimentions
screen_width = 720
screen_height = 480

# initialize pygame
pygame.init()

# initialize window
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Draw a Snake")

# fps controller
fps = pygame.time.Clock()

# snake position
snake_pos = pygame.Vector2(screen_width / 2, screen_height / 2)

# snake body, first 4 blocks
snake_body = [ [100,50],
               [90,50],
               [80,50],
               [70,50]
             ]

# position of fruit (random)
fruit_pos = [random.randrange(1, (screen_width//10)) * 10,
             random.randrange(1, (screen_height//10)) * 10]
fruit_spawn = True

# default snake direction
direction = 'RIGHT'
change_to = direction

# initial score
score = 0

# score function
def show_score(choice, color, font, size):
    
    # creating font score object 
    score_font = pygame.font.SysFont(font, size)
    
    # creating the display surface object
    score_surface = score_font.render('Score: ' + str(score), True, color)
    
    # creating a rectangular object for the text surface object
    score_rect = score_surface.get_rect()
    
    # display text
    screen.blit(score_surface,score_rect)
    
# game over function
def game_over():
    
    # creating font obj
    my_font = pygame.font.SysFont('times new roman', 50)
    
    # creating txt surface on which txt will be drawn
    game_over_surface = my_font.render('Your score is: ' + str(score), True, "red")
    
    # creating rect obj for the txt surface obj
    game_over_rect = game_over_surface.get_rect()
    
    # positioning text 
    game_over_rect.midtop = (screen_width / 2, screen_height / 4)
    
    # blit will draw the text on screen
    screen.blit(game_over_surface, game_over_rect)
    
    # flip() the display to put your work on screen
    # updates score
    pygame.display.flip()
    
    # waits 2 seconds
    time.sleep(2)
    
    # quits pygame library
    pygame.quit
    
    # quits program
    quit()

# Main Function
while True:
  
    # handling key events
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                change_to = 'UP'
            if event.key == pygame.K_s:
                change_to = 'DOWN'
            if event.key == pygame.K_a:
                change_to = 'LEFT'
            if event.key == pygame.K_d:
                change_to = 'RIGHT'
            if event.key == pygame.K_ESCAPE:
                quit()

    # If two keys pressed simultaneously 
    # we don't want snake to move into two directions
    # simultaneously
    if change_to == 'UP' and direction != 'DOWN':
        direction = 'UP'
    if change_to == 'DOWN' and direction != 'UP':
        direction = 'DOWN'
    if change_to == 'LEFT' and direction != 'RIGHT':
        direction = 'LEFT'
    if change_to == 'RIGHT' and direction != 'LEFT':
        direction = 'RIGHT'

    # Moving the snake
    if direction == 'UP':
        snake_pos[1] -= 10
    if direction == 'DOWN':
        snake_pos[1] += 10
    if direction == 'LEFT':
        snake_pos[0] -= 10
    if direction == 'RIGHT':
        snake_pos[0] += 10

    # Snake body growing mechanism 
    # if fruits and snakes collide then scores will be 
    # incremented by 10
    snake_body.insert(0, list(snake_pos))
    if snake_pos[0] == fruit_pos[0] and snake_pos[1] == fruit_pos[1]:
        score += 10
        fruit_spawn = False
    else:
        snake_body.pop()
        
    if not fruit_spawn:
        fruit_pos = [random.randrange(1, (screen_width//10)) * 10, 
                          random.randrange(1, (screen_height//10)) * 10]
        
    fruit_spawn = True
    screen.fill("black")
    
    for pos in snake_body:
        pygame.draw.rect(screen, "green", pygame.Rect(
          pos[0], pos[1], 10, 10))
        
    pygame.draw.rect(screen, "white", pygame.Rect(
      fruit_pos[0], fruit_pos[1], 10, 10))

    # Game Over conditions
    if snake_pos[0] < 0 or snake_pos[0] > screen_width-10:
        game_over()
    if snake_pos[1] < 0 or snake_pos[1] > screen_height-10:
        game_over()
    
    # Touching the snake body
    for block in snake_body[1:]:
        if snake_pos[0] == block[0] and snake_pos[1] == block[1]:
            game_over()
    
    # displaying score continuously
    show_score(1, "white", 'times new roman', 20)
    
    # Refresh game screen
    pygame.display.update()

    # Frame Per Second /Refresh Rate
    fps.tick(snake_speed)
    
    