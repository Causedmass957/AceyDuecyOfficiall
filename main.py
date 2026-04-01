import pygame
import sys
from Constants import *
from GameEngine import GameEngine
from Entities import Player
from Board import Board
from Renderer import Renderer

def main():
    # 1. Initialize Pygame
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Acey Duecy - 4 Player Strategy")
    clock = pygame.time.Clock()

    # 2. Initialize Modular Components
    engine = GameEngine(num_players=4)
    board_logic = Board()
    view = Renderer(screen)

    # 3. Create Player Objects
    # We pass the paths defined in the engine to the Player entities
    players = {}
    for i in range(1, 5):
        path = engine.get_player_path(i)
        players[i] = Player(i, PLAYER_COLORS[i], path)

    # --- Main Game Loop ---
    running = True
    while running:
        # A. Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # Handle Mouse Clicks for Rolls
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()

                if engine.phase == "INITIAL_ROLL":
                    # ... your existing initial roll logic ...
                    for p_id in range(1, 5):
                        if p_id not in engine.player_rolls:
                            engine.record_initial_roll(p_id)
                            # TRIGGER FIRST ROLL IMMEDIATELY IF PHASE CHANGES
                            if engine.phase == "PLAYING":
                                engine.roll_dice() 
                            break
                
                elif engine.phase == "PLAYING":
                    # A. Identify click location
                    clicked_idx = board_logic.get_index_from_mouse(mouse_pos)
                    if is_clicking_start(mouse_pos, engine.current_player):
                        clicked_idx = -2
                    # Quick check for your main loop:
                    if abs(mouse_pos[0] - (BOARD_START_X + BLOCK_WIDTH + MIDDLE_BAR//2)) < (MIDDLE_BAR // 2):
                        clicked_idx = -1
                    # Inside main.py PLAYING phase click handling:
                    if engine.waiting_for_doubles_roll:
                        engine.roll_dice()
                        # Don't try to select pieces this click
                        continue 
                    # B. Selection vs Movement
                    if engine.selected_index is None:
                        if engine.select_piece(engine.current_player, clicked_idx):
                            print(f"Selected: {clicked_idx}")
                    else:
                        # Attempt the move
                        if engine.attempt_move(engine.current_player, engine.selected_index, clicked_idx):
                            print(f"Moved to: {clicked_idx}")
                        
                        # ALWAYS reset selection after a second click (success or fail)
                        engine.selected_index = None

                    # C. Check if turn is over
                    if not engine.moves_available:
                        engine.next_turn()
                        engine.roll_dice() # Roll for the next player automatically

        # B. Update Logic
        # (The Engine handles the state; we just need to keep the UI in sync)

       # C. Drawing
        # Inside main.py while loop
        view.draw_background()
        view.draw_points(board_logic) # Updated this line
        view.draw_player_pieces(engine, board_logic)
        
        # Pass 'engine' instead of 'engine.board' to draw_player_pieces
        view.draw_player_pieces(engine, board_logic)
        view.draw_start_pools(engine)
        
        view.draw_ui(engine)

        # Draw specific Start/Jail info for the "Initial Roll" phase
        if engine.phase == "INITIAL_ROLL":
            draw_setup_overlay(screen, view.font, engine.player_rolls)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

def is_clicking_start(mouse_pos, player_id):
    start_x, start_y = START_AREAS[player_id]
    # Check if mouse is within 40 pixels of the start center
    dist = ((mouse_pos[0] - start_x)**2 + (mouse_pos[1] - start_y)**2)**0.5
    return dist < 40

def draw_setup_overlay(screen, font, rolls):
    """Temporary helper to see who has rolled during the start phase."""
    y_offset = 200
    title = font.render("Initial Roll Phase - Click to Roll for each Player", True, WHITE)
    screen.blit(title, (SCREEN_WIDTH//2 - 200, 150))
    
    for p_id, total in rolls.items():
        txt = font.render(f"Player {p_id}: {total}", True, PLAYER_COLORS[p_id])
        screen.blit(txt, (SCREEN_WIDTH//2 - 50, y_offset))
        y_offset += 40

if __name__ == "__main__":
    main()
