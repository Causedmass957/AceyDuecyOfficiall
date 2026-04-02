import pygame
import sys
from Constants import *
from GameEngine import GameEngine
from Entities import Player
from Board import Board
from Renderer import Renderer

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Acey Duecy - 4 Player Strategy")
    clock = pygame.time.Clock()

    engine = GameEngine()
    board_logic = Board()
    view = Renderer(screen)
    players = {}

    last_click_time = 0
    DOUBLE_CLICK_THRESHOLD = 500

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                current_time = pygame.time.get_ticks()

                if engine.phase == "PLAYER_SELECTION":
                    for count, rect in SELECTION_BUTTONS.items():
                        if rect.collidepoint(mouse_pos):
                            engine.set_player_count(count)
                            for i in range(1, count + 1):
                                path = engine.get_player_path(i)
                                players[i] = Player(i, PLAYER_COLORS[i], path)
                            break
                    continue

                if engine.phase == "INITIAL_ROLL":
                    for p_id in range(1, engine.num_players + 1):
                        if p_id not in engine.player_rolls:
                            if is_clicking_start(mouse_pos, p_id):
                                engine.record_initial_roll(p_id)
                                if len(engine.player_rolls) == engine.num_players:
                                    engine.phase = "SHOW_INITIAL_WINNER"
                                break
                    continue

                elif engine.phase == "SHOW_INITIAL_WINNER":
                    engine.phase = "PLAYING"
                    continue

                elif engine.phase == "PLAYING":
                    # 1. HANDLE BUTTON (Roll/Pass)
                    if ROLL_BUTTON_RECT.collidepoint(mouse_pos):
                        if not engine.moves_available:
                            engine.roll_dice()
                        else:
                            engine.pass_turn()
                        continue 

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
                        if engine.attempt_move(engine.current_player, engine.selected_index, clicked_idx):
                            print(f"Moved to: {clicked_idx}")
                            
                            # ONLY check if the turn is over after a successful move
                            if not engine.moves_available:
                                engine.next_turn()
                        
                        engine.selected_index = None

        if engine.phase == "PLAYER_SELECTION":
            view.draw_player_selection()
        else:
            view.draw_background()
            view.draw_jail(engine)
            view.draw_points(board_logic)
            view.draw_player_pieces(engine, board_logic)
            view.draw_start_pools(engine)
            view.draw_ui(engine)
            if engine.phase == "INITIAL_ROLL":
                draw_setup_overlay(screen, view.font, engine.player_rolls)
            elif engine.phase == "SHOW_INITIAL_WINNER":
                view.draw_initial_winner_screen(engine)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

def is_clicking_start(mouse_pos, player_id):
    if player_id not in START_AREAS: return False
    start_x, start_y = START_AREAS[player_id]
    dist = ((mouse_pos[0] - start_x)**2 + (mouse_pos[1] - start_y)**2)**0.5
    return dist < 40

def draw_setup_overlay(screen, font, rolls):
    y_offset = 200
    title = font.render("Initial Roll Phase - Click Corners to Roll", True, WHITE)
    screen.blit(title, (SCREEN_WIDTH//2 - 200, 150))
    for p_id, total in rolls.items():
        txt = font.render(f"Player {p_id}: {total}", True, PLAYER_COLORS[p_id])
        screen.blit(txt, (SCREEN_WIDTH//2 - 50, y_offset))
        y_offset += 40

if __name__ == "__main__":
    main()
