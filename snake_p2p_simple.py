# ==============================================================================
# GROUP MEMBERS: Adrian R., Christian V., Kamy A. and Vanessa F.
# ASGT: Project
# ORGN: CMPS 3640
# FILE: snake_p2p_simple.py
# DATE:
# DESCRIPTION: A peer-to-peer versus snake game using simple socket networking
#              with a polished Pygame UI and countdown / pause / reset.
# ==============================================================================

# === Libraries ===
import pygame
import time
import random
import json
import socket
import threading

# === Settings ===
snake_speed = 10  # speed of snake (logic FPS)
screen_width = 720
screen_height = 480
CELL = 10  # grid size

# --- UI Colors ---
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

# Game state constants
STATE_COUNTDOWN = "COUNTDOWN"
STATE_RUNNING = "RUNNING"
STATE_PAUSED = "PAUSED"

COUNTDOWN_SECONDS = 3

# === Setup ===
pygame.init()
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("P2P Versus Snake Game")
fps = pygame.time.Clock()

# Pre-create fonts
FONT_SCORE = pygame.font.SysFont('consolas', 22, bold=True)
FONT_STATUS = pygame.font.SysFont('consolas', 16)
FONT_MENU_TITLE = pygame.font.SysFont('times new roman', 50)
FONT_MENU_OPTION = pygame.font.SysFont('times new roman', 30)
FONT_TITLE = pygame.font.SysFont('consolas', 26, bold=True)
FONT_COUNTDOWN = pygame.font.SysFont('consolas', 56, bold=True)
FONT_SUB = pygame.font.SysFont('consolas', 20)

# === Network Variables ===
server_socket = None
client_socket = None
peer_connected = False
is_host = False
local_player = None  # 1 or 2
remote_snake_data = None
data_lock = threading.Lock()
running = True

# === Snake + Fruit State (will be reset by reset_game_state) ===
snake1_pos = [screen_width // 4, screen_height // 2]
snake1_body = []
snake1_direction = 'RIGHT'
snake1_change_to = snake1_direction
snake1_score = 0

snake2_pos = [screen_width * 3 // 4, screen_height // 2]
snake2_body = []
snake2_direction = 'LEFT'
snake2_change_to = snake2_direction
snake2_score = 0

fruit_pos = [0, 0]
fruit_spawn = True

# === Game state variables ===
game_state = STATE_COUNTDOWN
countdown_start_ms = 0        # SET AFTER PEER CONNECTS
connection_initialized = False  # RUN RESET/COUNTDOWNN AFTER CONNECT?
paused_by = None  # WHO PAUSED ("P1"/"P2")


# === UI Helper Functions ===
def draw_background(surface: pygame.Surface):
    """Gradient stripes + grid + border."""
    stripe_width = 80
    for x in range(0, screen_width, stripe_width):
        rect = pygame.Rect(x, 0, stripe_width, screen_height)
        color = BG_DARK if (x // stripe_width) % 2 == 0 else BG_STRIPE
        surface.fill(color, rect)

    # grid
    for x in range(0, screen_width, CELL):
        pygame.draw.line(surface, GRID_COLOR, (x, 0), (x, screen_height), 1)
    for y in range(0, screen_height, CELL):
        pygame.draw.line(surface, GRID_COLOR, (0, y), (screen_width, y), 1)

    # border
    pygame.draw.rect(surface, BORDER_COLOR, (0, 0, screen_width, screen_height), 3)


def draw_snake(surface, body, fill_color, outline_color):
    for seg in body:
        x, y = seg
        rect = pygame.Rect(x, y, CELL, CELL)
        pygame.draw.rect(surface, outline_color, rect, border_radius=4)
        inner = rect.inflate(-4, -4)
        pygame.draw.rect(surface, fill_color, inner, border_radius=4)


def draw_fruit(surface, pos):
    cx = pos[0] + CELL // 2
    cy = pos[1] + CELL // 2
    pygame.draw.circle(surface, FRUIT_GLOW, (cx, cy), CELL // 2)
    pygame.draw.circle(surface, FRUIT_COLOR, (cx, cy), CELL // 3)


def draw_center_text(surface, font, text, y_offset=0):
    shadow = font.render(text, True, TEXT_SHADOW)
    surf = font.render(text, True, TEXT_COLOR)
    rect = surf.get_rect()
    rect.center = (screen_width // 2, screen_height // 2 + y_offset)
    surface.blit(shadow, (rect.x + 2, rect.y + 2))
    surface.blit(surf, rect)


# === Network Functions ===
def receive_messages(sock):
    """Continuously receive messages from peer"""
    global remote_snake_data, peer_connected, running, game_state, countdown_start_ms, paused_by
    buffer = ""
    
    while running:
        try:
            data = sock.recv(4096).decode('utf-8')
            if not data:
                print("Connection closed by peer")
                peer_connected = False
                break
            
            buffer += data
            # Process complete JSON messages (separated by newlines)
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if line.strip():
                    try:
                        msg = json.loads(line)
                        with data_lock:
                            msg_type = msg.get('type') 
                            if msg_type == 'game_state':
                                remote_snake_data = msg
                            elif msg_type == 'connect':
                                peer_connected = True
                                print(f"Peer connected: Player {msg.get('player_id')}")
                            elif msg_type == 'pause':
                                game_state = STATE_PAUSED
                                sender = msg.get('by')
                                if sender in (1, 2):
                                    paused_by = f"Player {sender}"
                                else:
                                    paused_by = "Peer"
                            elif msg_type == 'resume':
                                game_state = STATE_RUNNING
                                paused_by = None
                            elif msg_type == 'reset':
                                # Peer requested a reset – sync our state
                                reset_game_state()
                                game_state = STATE_COUNTDOWN
                                countdown_start_ms = pygame.time.get_ticks()
                    except json.JSONDecodeError:
                        pass
        except socket.timeout:
            continue
        except Exception as e:
            if running:
                print(f"Error receiving: {e}")
            break

# DEBUGGER FUNCTION
def send_control_message(msg_type: str):
    """Send a simple control message (e.g., pause, resume, reset) to peer."""
    global client_socket, local_player
    if client_socket and peer_connected:
        try:
            msg = json.dumps({'type': msg_type, 'by': local_player}) + '\n'
            client_socket.sendall(msg.encode('utf-8'))
        except Exception as e:
            print(f"Error sending control message: {e}")

def send_game_state():
    """Send local snake state to peer"""
    global client_socket, game_state
    
    if client_socket and peer_connected:
        if local_player == 1:
            state = {
                'type': 'game_state',
                'player': 1,
                'pos': snake1_pos,
                'body': snake1_body,
                'direction': snake1_direction,
                'score': snake1_score,
                'fruit_pos': fruit_pos if is_host else None
            }
        else:
            # FOR CLIENT (P2), ALSO TELL HOST IF WE ATE FRUIT  
            ate = (list(snake2_pos) == fruit_pos and game_state == STATE_RUNNING)
            state = {
                'type': 'game_state',
                'player': 2,
                'pos': snake2_pos,
                'body': snake2_body,
                'direction': snake2_direction,
                'score': snake2_score,
                "ate_fruit": ate
            }
        
        try:
            msg = json.dumps(state) + '\n'
            client_socket.sendall(msg.encode('utf-8'))
        except Exception as e:
            print(f"Error sending: {e}")


def update_remote_snake():
    """Update the remote snake from received data"""
    global snake1_pos, snake1_body, snake1_direction, snake1_score
    global snake2_pos, snake2_body, snake2_direction, snake2_score
    global fruit_pos, fruit_spawn, is_host
    
    with data_lock:
        if remote_snake_data:
            if remote_snake_data['player'] == 1:
                snake1_pos = remote_snake_data['pos']
                snake1_body = remote_snake_data['body']
                snake1_direction = remote_snake_data['direction']
                snake1_score = remote_snake_data['score']
                if remote_snake_data.get('fruit_pos'):
                    fruit_pos = remote_snake_data['fruit_pos']
            else:
                snake2_pos = remote_snake_data['pos']
                snake2_body = remote_snake_data['body']
                snake2_direction = remote_snake_data['direction']
                snake2_score = remote_snake_data['score']
                # ON HOST, MAKE SURE WE RESPAWN FRUIT IF P2 ATE
                if is_host:
                    ate_flag = remote_snake_data.get('ate_fruit', False)
                    # CHECK POSITION MATCH
                    if ate_flag or list(snake2_pos) == fruit_pos:
                        fruit_spawn = False


def init_host(port=8468):
    """Initialize as host (Player 1)"""
    global server_socket, client_socket, is_host, local_player, peer_connected
    
    is_host = True
    local_player = 1
    
    print(f"Starting host on port {port}...")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen(1)
    server_socket.settimeout(1.0)
    
    # Get local IP
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "Unable to get IP"
    
    print(f"Host started!")
    print(f"Local IP: {local_ip}")
    print(f"Port: {port}")
    print("Waiting for peer to connect...")
    
    # Wait for connection in separate thread
    def accept_connection():
        global client_socket, peer_connected
        while running and not peer_connected:
            try:
                client_socket, addr = server_socket.accept()
                client_socket.settimeout(1.0)
                print(f"Peer connected from {addr}")
                
                # Send connection confirmation
                connect_msg = json.dumps({'type': 'connect', 'player_id': 1}) + '\n'
                client_socket.sendall(connect_msg.encode('utf-8'))
                peer_connected = True
                
                # Start receiving thread
                recv_thread = threading.Thread(target=receive_messages, args=(client_socket,), daemon=True)
                recv_thread.start()
                break
            except socket.timeout:
                continue
            except Exception as e:
                if running:
                    print(f"Error accepting connection: {e}")
                break
    
    accept_thread = threading.Thread(target=accept_connection, daemon=True)
    accept_thread.start()


def init_client(host_ip, host_port=8468):
    """Initialize as client (Player 2)"""
    global client_socket, is_host, local_player, peer_connected
    
    is_host = False
    local_player = 2
    
    print(f"Connecting to {host_ip}:{host_port}...")
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(5.0)
    
    try:
        client_socket.connect((host_ip, host_port))
        client_socket.settimeout(1.0)
        print("Connected to host!")
        
        # Send connection message
        connect_msg = json.dumps({'type': 'connect', 'player_id': 2}) + '\n'
        client_socket.sendall(connect_msg.encode('utf-8'))
        peer_connected = True
        
        # Start receiving thread
        recv_thread = threading.Thread(target=receive_messages, args=(client_socket,), daemon=True)
        recv_thread.start()
    except Exception as e:
        print(f"Error connecting: {e}")
        client_socket = None
        raise


# === Score display ===
def show_score():
    font = FONT_SCORE
    s1 = font.render('P1: ' + str(snake1_score), True, TEXT_COLOR)
    s2 = font.render('P2: ' + str(snake2_score), True, TEXT_COLOR)

    screen.blit(font.render('P1: ' + str(snake1_score), True, TEXT_SHADOW), (11, 46))
    screen.blit(s1, (10, 45))

    x2 = screen_width - 10 - s2.get_width()
    screen.blit(font.render('P2: ' + str(snake2_score), True, TEXT_SHADOW), (x2 + 1, 46))
    screen.blit(s2, (x2, 45))


# === Connection Status Display ===
def show_connection_status():
    status = "Connected" if peer_connected else "Waiting for peer..."
    color = (100, 255, 120) if peer_connected else (255, 220, 100)

    shadow = FONT_STATUS.render(status, True, TEXT_SHADOW)
    surf = FONT_STATUS.render(status, True, color)
    rect = surf.get_rect()
    rect.midtop = (screen_width // 2, 5)
    screen.blit(shadow, (rect.x + 1, rect.y + 1))
    screen.blit(surf, rect)


def draw_controls():
    text = "P1: WASD   P2: Arrows   P: Pause   R: Reset   ESC: Quit"
    shadow = FONT_STATUS.render(text, True, TEXT_SHADOW)
    surf = FONT_STATUS.render(text, True, TEXT_COLOR)
    rect = surf.get_rect()
    rect.midbottom = (screen_width // 2, screen_height - 6)
    screen.blit(shadow, (rect.x + 1, rect.y + 1))
    screen.blit(surf, rect)


# === Reset Game State ===
def reset_game_state():
    global snake1_pos, snake1_body, snake1_direction, snake1_change_to, snake1_score
    global snake2_pos, snake2_body, snake2_direction, snake2_change_to, snake2_score
    global fruit_pos, fruit_spawn

    # Snake 1
    snake1_pos = [screen_width // 4, screen_height // 2]
    snake1_pos[0] = (snake1_pos[0] // CELL) * CELL
    snake1_pos[1] = (snake1_pos[1] // CELL) * CELL
    snake1_body = [
        [snake1_pos[0], snake1_pos[1]],
        [snake1_pos[0] - CELL, snake1_pos[1]],
        [snake1_pos[0] - 2*CELL, snake1_pos[1]],
        [snake1_pos[0] - 3*CELL, snake1_pos[1]],
    ]
    snake1_direction = 'RIGHT'
    snake1_change_to = snake1_direction
    snake1_score = 0

    # Snake 2
    snake2_pos = [screen_width * 3 // 4, screen_height // 2]
    snake2_pos[0] = (snake2_pos[0] // CELL) * CELL
    snake2_pos[1] = (snake2_pos[1] // CELL) * CELL
    snake2_body = [
        [snake2_pos[0], snake2_pos[1]],
        [snake2_pos[0] + CELL, snake2_pos[1]],
        [snake2_pos[0] + 2*CELL, snake2_pos[1]],
        [snake2_pos[0] + 3*CELL, snake2_pos[1]],
    ]
    snake2_direction = 'LEFT'
    snake2_change_to = snake2_direction
    snake2_score = 0

    fruit_pos[:] = [
        random.randrange(1, (screen_width // CELL)) * CELL,
        random.randrange(1, (screen_height // CELL)) * CELL,
    ]
    fruit_spawn = True


# === Game Over ===
def game_over(winner=None):
    global running
    my_font = pygame.font.SysFont('times new roman', 50)
    msg = "Draw!" if not winner else f"{winner} Wins!"
    
    # Draw final frame UI
    draw_background(screen)
    draw_snake(screen, snake1_body, P1_COLOR, P1_OUTLINE)
    draw_snake(screen, snake2_body, P2_COLOR, P2_OUTLINE)
    draw_fruit(screen, fruit_pos)
    show_score()
    show_connection_status()
    draw_controls()

    # Overlay message with shadow
    shadow = my_font.render(msg, True, TEXT_SHADOW)
    text_surf = my_font.render(msg, True, (255, 80, 80))
    rect = text_surf.get_rect()
    rect.midtop = (screen_width / 2, screen_height / 4)
    screen.blit(shadow, (rect.x + 2, rect.y + 2))
    screen.blit(text_surf, rect)
    
    pygame.display.flip()
    
    time.sleep(2)
    
    # Clean up network
    running = False
    if client_socket:
        try:
            client_socket.close()
        except:
            pass
    if server_socket:
        try:
            server_socket.close()
        except:
            pass
    
    pygame.quit()
    quit()


# === Main Menu ===
def main_menu():
    """Display main menu for connection setup"""
    draw_background(screen)
    
    title = FONT_MENU_TITLE.render("P2P Snake Game", True, "white")
    option1 = FONT_MENU_OPTION.render("Press H to HOST (Player 1)", True, "green")
    option2 = FONT_MENU_OPTION.render("Press J to JOIN (Player 2)", True, "blue")
    
    screen.blit(FONT_MENU_TITLE.render("P2P Snake Game", True, TEXT_SHADOW),
                (screen_width // 2 - 200 + 2, 100 + 2))
    screen.blit(title, (screen_width // 2 - 200, 100))

    screen.blit(FONT_MENU_OPTION.render("Press H to HOST (Player 1)", True, TEXT_SHADOW),
                (screen_width // 2 - 220 + 2, 250 + 2))
    screen.blit(option1, (screen_width // 2 - 220, 250))

    screen.blit(FONT_MENU_OPTION.render("Press J to JOIN (Player 2)", True, TEXT_SHADOW),
                (screen_width // 2 - 220 + 2, 300 + 2))
    screen.blit(option2, (screen_width // 2 - 220, 300))
    
    pygame.display.flip()
    
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_h:
                    init_host()
                    waiting = False
                elif event.key == pygame.K_j:
                    print("\nEnter host IP address:")
                    host_ip = input("Host IP: ").strip()
                    try:
                        init_client(host_ip)
                        waiting = False
                    except:
                        print("Failed to connect. Press J to try again.")
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    quit()


# === Main Function ===
def main():
    global snake1_pos, snake1_body, snake1_direction, snake1_change_to, snake1_score
    global snake2_pos, snake2_body, snake2_direction, snake2_change_to, snake2_score
    global fruit_pos, fruit_spawn, running, game_state, countdown_start_ms, connection_initialized, paused_by
    
    # Show menu and setup connection
    main_menu()
    # reset_game_state()
    game_state = STATE_COUNTDOWN
    # countdown_start_ms = pygame.time.get_ticks()
    countdown_start_ms = 0      # WILL BE SET AFTER PEER CONNECTS
    connection_initialized = False
    
    # Main game loop
    while running:
        # --- Handling key events ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                if client_socket:
                    client_socket.close()
                if server_socket:
                    server_socket.close()
                pygame.quit()
                quit()
            elif event.type == pygame.KEYDOWN:
                # ESC always quits
                if event.key == pygame.K_ESCAPE:
                    running = False
                    if client_socket:
                        client_socket.close()
                    if server_socket:
                        server_socket.close()
                    pygame.quit()
                    quit()

                # Pause / resume (local)
                if event.key == pygame.K_p and peer_connected:
                    if game_state == STATE_RUNNING:
                        game_state = STATE_PAUSED
                        paused_by = f"Player {local_player}"
                        send_control_message('pause')
                    elif game_state == STATE_PAUSED:
                        if paused_by == f"Player {local_player}":
                            game_state = STATE_RUNNING
                            paused_by = None
                            send_control_message('resume')

                # Reset: re-center snakes, scores, fruit, restart countdown
                if event.key == pygame.K_r and peer_connected:
                    reset_game_state()
                    game_state = STATE_COUNTDOWN
                    countdown_start_ms = pygame.time.get_ticks()
                    paused_by = None
                    send_control_message('reset')

                # Movement only when actively RUNNINNG
                if game_state == STATE_RUNNING:
                    if local_player == 1:
                        if event.key == pygame.K_w:
                            snake1_change_to = 'UP'
                        if event.key == pygame.K_s:
                            snake1_change_to = 'DOWN'
                        if event.key == pygame.K_a:
                            snake1_change_to = 'LEFT'
                        if event.key == pygame.K_d:
                            snake1_change_to = 'RIGHT'
                    
                    elif local_player == 2:
                        if event.key == pygame.K_UP:
                            snake2_change_to = 'UP'
                        elif event.key == pygame.K_DOWN:
                            snake2_change_to = 'DOWN'
                        elif event.key == pygame.K_LEFT:
                            snake2_change_to = 'LEFT'
                        elif event.key == pygame.K_RIGHT:
                            snake2_change_to = 'RIGHT'

        # Only proceed with game logic if peer is connected
        if not peer_connected:
            draw_background(screen)
            show_connection_status()
            draw_controls()
            pygame.display.update()
            fps.tick(10)
            continue

        # FIRST TIME WE DETECT CONNECTION: RESET AND RESTART COUNTDOWN ON BOTH SIDES
        if not connection_initialized:
            reset_game_state()
            countdown_start_ms = pygame.time.get_ticks()
            connection_initialized = True

        # countdown state
        if game_state == STATE_COUNTDOWN:
            now = pygame.time.get_ticks()
            elapsed = (now - countdown_start_ms) / 1000.0
            if elapsed >= COUNTDOWN_SECONDS:
                game_state = STATE_RUNNING

        # Update remote snake state (always read network)
        update_remote_snake()

        # --- Local player controls & movement (only when RUNNING) ---
        if game_state == STATE_RUNNING:
            if local_player == 1:
                # Prevents 180 degree turns
                if snake1_change_to == 'UP' and snake1_direction != 'DOWN':
                    snake1_direction = 'UP'
                if snake1_change_to == 'DOWN' and snake1_direction != 'UP':
                    snake1_direction = 'DOWN'
                if snake1_change_to == 'LEFT' and snake1_direction != 'RIGHT':
                    snake1_direction = 'LEFT'
                if snake1_change_to == 'RIGHT' and snake1_direction != 'LEFT':
                    snake1_direction = 'RIGHT'
                
                # Moving the snake
                if snake1_direction == 'UP':
                    snake1_pos[1] -= CELL
                if snake1_direction == 'DOWN':
                    snake1_pos[1] += CELL
                if snake1_direction == 'LEFT':
                    snake1_pos[0] -= CELL
                if snake1_direction == 'RIGHT':
                    snake1_pos[0] += CELL
                
                # Grow Snake / Eat fruit
                snake1_body.insert(0, list(snake1_pos))
                
                if list(snake1_pos) == fruit_pos:
                    snake1_score += 10
                    fruit_spawn = False
                else:
                    snake1_body.pop()

            elif local_player == 2:
                # Prevents 180 degree turns
                if snake2_change_to == 'UP' and snake2_direction != 'DOWN':
                    snake2_direction = 'UP'
                if snake2_change_to == 'DOWN' and snake2_direction != 'UP':
                    snake2_direction = 'DOWN'
                if snake2_change_to == 'LEFT' and snake2_direction != 'RIGHT':
                    snake2_direction = 'LEFT'
                if snake2_change_to == 'RIGHT' and snake2_direction != 'LEFT':
                    snake2_direction = 'RIGHT'
                
                # Moving the snake
                if snake2_direction == 'UP':
                    snake2_pos[1] -= CELL
                if snake2_direction == 'DOWN':
                    snake2_pos[1] += CELL
                if snake2_direction == 'LEFT':
                    snake2_pos[0] -= CELL
                if snake2_direction == 'RIGHT':
                    snake2_pos[0] += CELL
                
                # Grow Snake / Eat fruit
                snake2_body.insert(0, list(snake2_pos))
                
                if list(snake2_pos) == fruit_pos:
                    snake2_score += 10
                    fruit_spawn = False
                else:
                    snake2_body.pop()

            # Host handles fruit spawning
            if is_host and not fruit_spawn:
                fruit_pos[:] = [
                    random.randrange(1, (screen_width // CELL)) * CELL,
                    random.randrange(1, (screen_height // CELL)) * CELL
                ]
                fruit_spawn = True

        # Send local state to peer (during countdown + running so they see reset)
        if game_state in (STATE_RUNNING, STATE_COUNTDOWN):
            send_game_state()

        # --- Draw Everything ---
        draw_background(screen)

        # Title
        title_shadow = FONT_TITLE.render("P2P Versus Snake", True, TEXT_SHADOW)
        title_surf = FONT_TITLE.render("P2P Versus Snake", True, TEXT_COLOR)
        screen.blit(title_shadow, (screen_width//2 - title_surf.get_width()//2 + 2, 18 + 2))
        screen.blit(title_surf, (screen_width//2 - title_surf.get_width()//2, 18))

        draw_snake(screen, snake1_body, P1_COLOR, P1_OUTLINE)
        draw_snake(screen, snake2_body, P2_COLOR, P2_OUTLINE)
        draw_fruit(screen, fruit_pos)

        # Collisions only in RUNNING state
        if game_state == STATE_RUNNING:
            # Collision: Walls
            for snake, pos, name in [
                (snake1_body, snake1_pos, "Player 2"),
                (snake2_body, snake2_pos, "Player 1")
            ]:
                if pos[0] < 0 or pos[0] > screen_width - CELL or pos[1] < 0 or pos[1] > screen_height - CELL:
                    game_over(name)
            
            # Collision: Self
            for block in snake1_body[1:]:
                if snake1_pos[0] == block[0] and snake1_pos[1] == block[1]:
                    game_over("Player 2")
            for block in snake2_body[1:]:
                if snake2_pos[0] == block[0] and snake2_pos[1] == block[1]:
                    game_over("Player 1")

            # Collision between snakes
            for block in snake1_body:
                if snake2_pos[0] == block[0] and snake2_pos[1] == block[1]:
                    game_over("Player 1")
            for block in snake2_body:
                if snake1_pos[0] == block[0] and snake1_pos[1] == block[1]:
                    game_over("Player 2")

        # HUD
        show_score()
        show_connection_status()
        draw_controls()

        # Overlays for countdown / pause
        if game_state == STATE_COUNTDOWN:
            now = pygame.time.get_ticks()
            elapsed = (now - countdown_start_ms) / 1000.0
            remaining = max(0.0, COUNTDOWN_SECONDS - elapsed)
            if remaining > 0.5:
                num = int(remaining) + 1
                msg = str(num)
            else:
                msg = "GO!"
            draw_center_text(screen, FONT_COUNTDOWN, msg, y_offset=-10)
            draw_center_text(screen, FONT_SUB, "Round starting...", y_offset=40)

        elif game_state == STATE_PAUSED:
            draw_center_text(screen, FONT_COUNTDOWN, "PAUSED", y_offset=-10)
            info = f"{paused_by} paused the game" if paused_by else "Game paused"
            draw_center_text(screen, FONT_SUB, info, y_offset=40)
            draw_center_text(screen, FONT_SUB, "Press P to resume or R to reset", y_offset=80)

        pygame.display.update()
        fps.tick(snake_speed)


if __name__ == "__main__":
    main()
