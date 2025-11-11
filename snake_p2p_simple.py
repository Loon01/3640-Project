# ==============================================================================
# GROUP MEMBERS: Adrian R., Christian V., Kamy A. and Vanessa F.
# ASGT: Project
# ORGN: CMPS 3640
# FILE: snake_p2p_simple.py
# DATE: 
# DESCRIPTION: A peer-to-peer versus snake game using simple socket networking.
# ==============================================================================

# === Libraries ===
import pygame
import time
import random
import json
import socket
import threading

# === Settings ===
snake_speed = 15  # speed of snake
screen_width = 720
screen_height = 480

# === Setup ===
pygame.init()
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("P2P Versus Snake Game")
fps = pygame.time.Clock()

# === Network Variables ===
server_socket = None
client_socket = None
peer_connected = False
is_host = False
local_player = None  # Will be 1 or 2
remote_snake_data = None
data_lock = threading.Lock()
running = True

# === Snake 1 (WASD) ===
snake1_pos = [screen_width // 4, screen_height // 2]
snake1_body = [[100, 50], [90, 50], [80, 50], [70, 50]]
snake1_direction = 'RIGHT'
snake1_change_to = snake1_direction
snake1_score = 0

# === Snake 2 (Arrow Keys) ===
snake2_pos = [screen_width * 3 // 4, screen_height // 2]
snake2_body = [[600, 50], [610, 50], [620, 50], [630, 50]]
snake2_direction = 'LEFT'
snake2_change_to = snake2_direction
snake2_score = 0

# === Fruit ===
fruit_pos = [random.randrange(1, (screen_width // 10)) * 10,
             random.randrange(1, (screen_height // 10)) * 10]
fruit_spawn = True


# === Network Functions ===
def receive_messages(sock):
    """Continuously receive messages from peer"""
    global remote_snake_data, peer_connected, running
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
                            if msg.get('type') == 'game_state':
                                remote_snake_data = msg
                            elif msg.get('type') == 'connect':
                                peer_connected = True
                                print(f"Peer connected: Player {msg.get('player_id')}")
                    except json.JSONDecodeError:
                        pass
        except socket.timeout:
            continue
        except Exception as e:
            if running:
                print(f"Error receiving: {e}")
            break


def send_game_state():
    """Send local snake state to peer"""
    global client_socket
    
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
            state = {
                'type': 'game_state',
                'player': 2,
                'pos': snake2_pos,
                'body': snake2_body,
                'direction': snake2_direction,
                'score': snake2_score
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
    global fruit_pos
    
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
def show_score(color, font, size):
    score_font = pygame.font.SysFont(font, size)
    
    score_surface1 = score_font.render('P1 Score: ' + str(snake1_score), True, color)
    score_surface2 = score_font.render('P2 Score: ' + str(snake2_score), True, color)
    
    screen.blit(score_surface1, (10, 5))
    screen.blit(score_surface2, (screen_width - 160, 5))


# === Connection Status Display ===
def show_connection_status():
    font = pygame.font.SysFont('times new roman', 16)
    status = "Connected" if peer_connected else "Waiting for peer..."
    color = "green" if peer_connected else "yellow"
    
    status_surface = font.render(status, True, color)
    screen.blit(status_surface, (screen_width // 2 - 60, 5))


# === Game Over ===
def game_over(winner=None):
    global running
    my_font = pygame.font.SysFont('times new roman', 50)
    msg = "Draw!" if not winner else f"{winner} Wins!"
    
    game_over_surface = my_font.render(msg, True, "red")
    rect = game_over_surface.get_rect()
    rect.midtop = (screen_width / 2, screen_height / 4)
    
    screen.blit(game_over_surface, rect)
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
    screen.fill("black")
    font_title = pygame.font.SysFont('times new roman', 50)
    font_option = pygame.font.SysFont('times new roman', 30)
    
    title = font_title.render("P2P Snake Game", True, "white")
    option1 = font_option.render("Press H to HOST (Player 1)", True, "green")
    option2 = font_option.render("Press J to JOIN (Player 2)", True, "blue")
    
    screen.blit(title, (screen_width // 2 - 200, 100))
    screen.blit(option1, (screen_width // 2 - 220, 250))
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
    global fruit_pos, fruit_spawn, running
    
    # Show menu and setup connection
    main_menu()
    
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
                # Only handle controls for local player
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
                
                if event.key == pygame.K_ESCAPE:
                    running = False
                    if client_socket:
                        client_socket.close()
                    if server_socket:
                        server_socket.close()
                    pygame.quit()
                    quit()

        # Only proceed with game logic if peer is connected
        if not peer_connected:
            screen.fill("black")
            show_connection_status()
            pygame.display.update()
            fps.tick(10)
            continue

        # Update remote snake state
        update_remote_snake()

        # --- Local player controls ---
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
                snake1_pos[1] -= 10
            if snake1_direction == 'DOWN':
                snake1_pos[1] += 10
            if snake1_direction == 'LEFT':
                snake1_pos[0] -= 10
            if snake1_direction == 'RIGHT':
                snake1_pos[0] += 10
            
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
                snake2_pos[1] -= 10
            if snake2_direction == 'DOWN':
                snake2_pos[1] += 10
            if snake2_direction == 'LEFT':
                snake2_pos[0] -= 10
            if snake2_direction == 'RIGHT':
                snake2_pos[0] += 10
            
            # Grow Snake / Eat fruit
            snake2_body.insert(0, list(snake2_pos))
            
            if list(snake2_pos) == fruit_pos:
                snake2_score += 10
                fruit_spawn = False
            else:
                snake2_body.pop()

        # Host handles fruit spawning
        if is_host and not fruit_spawn:
            fruit_pos = [random.randrange(1, (screen_width // 10)) * 10,
                        random.randrange(1, (screen_height // 10)) * 10]
            fruit_spawn = True

        # Send local state to peer
        send_game_state()

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

        # --- Display Scores and Status ---
        show_score("white", 'times new roman', 20)
        show_connection_status()
        pygame.display.update()
        fps.tick(snake_speed)


if __name__ == "__main__":
    main()
