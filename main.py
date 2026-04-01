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

                # --- Inside your main loop in main.py ---

                if engine.phase == "INITIAL_ROLL":
                    for p_id in range(1, engine.num_players + 1):
                        if p_id not in engine.player_rolls:
                            if is_clicking_start(mouse_pos, p_id):
                                # FIX: Match the method name in GameEngine.py
                                engine.record_initial_roll(p_id) 
                                
                                if len(engine.player_rolls) == engine.num_players:
                                    # The Engine already calls _determine_turn_order 
                                    # inside record_initial_roll when everyone is done.
                                    engine.phase = "SHOW_INITIAL_WINNER" 
                                break

                # B. Handle the "Click-Through" to start the game
                elif engine.phase == "SHOW_INITIAL_WINNER":
                    # Any click during the victory screen starts the actual game
                    engine.phase = "PLAYING"
                
                # main.py - Inside the event loop

                elif engine.phase == "PLAYING":
                    # 1. HANDLE BUTTON (Roll/Pass)
                    if ROLL_BUTTON_RECT.collidepoint(mouse_pos):
                        if not engine.moves_available:
                            engine.roll_dice()
                        else:
                            engine.pass_turn()
                        continue  # FIX: 'continue' stays in the loop, 'return' crashes it.

                    # 2. HANDLE ACEY-DEUCEY BONUS ROLL
                    if engine.waiting_for_doubles_roll:
                        engine.roll_dice()
                        continue 

                    # 3. IDENTIFY CLICK LOCATION
                    clicked_idx = board_logic.get_index_from_mouse(mouse_pos)
                    if is_clicking_start(mouse_pos, engine.current_player):
                        clicked_idx = -2
                    
                    # 4. SELECTION & MOVEMENT
                    if engine.selected_index is None:
                        if engine.select_piece(engine.current_player, clicked_idx):
                            print(f"Selected: {clicked_idx}")
                    else:
                        # Attempt to move the piece
                        if engine.attempt_move(engine.current_player, engine.selected_index, clicked_idx):
                            print(f"Moved to: {clicked_idx}")
                            
                            # ONLY check if the turn is over after a successful move
                            if not engine.moves_available:
                                engine.next_turn()
                        
                        # Reset selection after any movement attempt
                        engine.selected_index = None              

                    

        # B. Update Logic
        # (The Engine handles the state; we just need to keep the UI in sync)

       # C. Drawing
        view.draw_background()
        view.draw_jail(engine) # Draw jail early so pieces are on top
        view.draw_points(board_logic)
        view.draw_player_pieces(engine, board_logic)
        view.draw_start_pools(engine)
        view.draw_ui(engine)
                

        # Draw specific Start/Jail info for the "Initial Roll" phase
        if engine.phase == "INITIAL_ROLL":
            draw_setup_overlay(screen, view.font, engine.player_rolls)
        elif engine.phase == "SHOW_INITIAL_WINNER":
            view.draw_initial_winner_screen(engine)

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
