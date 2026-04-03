import pygame
import sys
from Constants import *
from GameEngine import GameEngine
from Board import Board
from Renderer import Renderer
from ProfileManager import ProfileManager

profile_manager = ProfileManager()
engine = GameEngine()

engine.set_profile_manager(profile_manager)

player_profiles = {
    1: "Arnie",
    2: "Danny",
    3: "Zach",
    4: "GreenPlayer"
}

for name in player_profiles.values():
    profile_manager.create_profile(name)

engine.set_player_profiles(player_profiles)


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Acey Duecy - 4 Player Strategy")
    clock = pygame.time.Clock()

    engine = GameEngine()
    board_logic = Board()
    view = Renderer(screen)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                handle_mouse_click(event.pos, engine, board_logic)

        draw_game(screen, engine, board_logic, view)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


def handle_mouse_click(mouse_pos, engine, board_logic):
    if engine.phase == "PLAYER_SELECTION":
        handle_player_selection(mouse_pos, engine)
        return

    if engine.phase == "INITIAL_ROLL":
        handle_initial_roll(mouse_pos, engine)
        return

    if engine.phase == "SHOW_INITIAL_WINNER":
        engine.phase = "PLAYING"
        return

    if engine.phase == "PLAYING":
        handle_playing_click(mouse_pos, engine, board_logic)


def handle_player_selection(mouse_pos, engine):
    for count, rect in SELECTION_BUTTONS.items():
        if rect.collidepoint(mouse_pos):
            engine.set_player_count(count)
            return


def handle_initial_roll(mouse_pos, engine):
    for p_id in range(1, engine.num_players + 1):
        if p_id not in engine.player_rolls and is_clicking_start(mouse_pos, p_id):
            engine.record_initial_roll(p_id)
            if len(engine.player_rolls) == engine.num_players:
                engine.phase = "SHOW_INITIAL_WINNER"
            return


def handle_playing_click(mouse_pos, engine, board_logic):
    # Bonus single-die roll after Acey-Deucey should only happen from button click
    if engine.waiting_for_doubles_roll:
        if ROLL_BUTTON_RECT.collidepoint(mouse_pos):
            engine.roll_dice()
        return

    # Roll / pass button
    if ROLL_BUTTON_RECT.collidepoint(mouse_pos):
        passed = False
        if not engine.moves_available:
            engine.roll_dice()
        else:
            passed = engine.pass_turn()
            if not passed:
                engine.selected_index = None

        print(
            f"PASS attempted={passed} -> current_player={engine.current_player}, "
            f"moves={engine.moves_available}, "
            f"acey={engine.is_acey_duecy_pending}, "
            f"waiting_doubles={engine.waiting_for_doubles_roll}, "
            f"extra_roll={engine.has_extra_roll}"
        )
        return

    clicked_idx = resolve_click_target(mouse_pos, engine, board_logic)

    print(
        f"PLAYER {engine.current_player} clicked {clicked_idx} | "
        f"selected={engine.selected_index} | moves={engine.moves_available}"
    )

    # No current selection yet
    if engine.selected_index is None:
        if engine.select_piece(engine.current_player, clicked_idx):
            print(f"Selected: {clicked_idx}")
        return

    # Double click selected checker = attempt to score off board
    if clicked_idx == engine.selected_index:
        if engine.attempt_move(engine.current_player, engine.selected_index, 24):
            print(f"Scored from: {clicked_idx}")

            if not engine.moves_available:
                engine.next_turn()
            else:
                engine.selected_index = None
            return

        engine.selected_index = None
        print("Deselected piece")
        return

    # Try moving first
    if engine.attempt_move(engine.current_player, engine.selected_index, clicked_idx):
        print(f"Moved to: {clicked_idx}")

        if not engine.moves_available:
            engine.next_turn()
        else:
            engine.selected_index = None
        return

    # If move failed, try switching selection
    if engine.select_piece(engine.current_player, clicked_idx):
        print(f"Reselected: {clicked_idx}")
        return

    print(f"Illegal move from {engine.selected_index} to {clicked_idx}")


def resolve_click_target(mouse_pos, engine, board_logic):
    # Board/jail has priority
    clicked_idx = board_logic.get_index_from_mouse(mouse_pos)

    # Only treat as start-pool click if no board/jail target was found
    if clicked_idx is None and is_clicking_start(mouse_pos, engine.current_player):
        return -2

    return clicked_idx


def draw_game(screen, engine, board_logic, view):
    if engine.phase == "PLAYER_SELECTION":
        view.draw_player_selection()
        return

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


def is_clicking_start(mouse_pos, player_id):
    if player_id not in START_AREAS:
        return False

    start_x, start_y = START_AREAS[player_id]
    dist = ((mouse_pos[0] - start_x) ** 2 + (mouse_pos[1] - start_y) ** 2) ** 0.5
    return dist < 40


def draw_setup_overlay(screen, font, rolls):
    y_offset = 200
    title = font.render("Initial Roll Phase - Click Corners to Roll", True, WHITE)
    screen.blit(title, (SCREEN_WIDTH // 2 - 200, 150))

    for p_id, total in rolls.items():
        txt = font.render(f"Player {p_id}: {total}", True, PLAYER_COLORS[p_id])
        screen.blit(txt, (SCREEN_WIDTH // 2 - 50, y_offset))
        y_offset += 40


if __name__ == "__main__":
    main()