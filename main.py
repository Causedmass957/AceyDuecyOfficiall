import pygame
import sys
from Constants import *
from GameEngine import GameEngine
from Board import Board
from Renderer import Renderer
from MenuManager import MenuManager
from ProfileManager import ProfileManager


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Acey Duecy - 4 Player Strategy")
    clock = pygame.time.Clock()

    profile_manager = ProfileManager()
    menu_manager = MenuManager(profile_manager)

    engine = None
    board_logic = None
    view = Renderer(screen)

    app_mode = "MENU"
    running = True

    while running:
        dt = clock.tick(FPS)
        menu_manager.update(dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif app_mode == "MENU":
                if event.type == pygame.KEYDOWN:
                    menu_result = menu_manager.handle_keydown(event)

                    if menu_result and menu_result.get("action") == "profile_created":
                        print(f"Created profile: {menu_result['name']}")

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    menu_result = menu_manager.handle_mouse_click(event.pos)

                    if not menu_result:
                        continue

                    action = menu_result.get("action")

                    if action == "exit":
                        running = False

                    elif action == "open_stats":
                        print("Stats menu not wired yet.")

                    elif action == "start_game":
                        engine = GameEngine()
                        board_logic = Board()

                        num_players = menu_result["num_players"]
                        player_profiles = menu_result["player_profiles"]

                        engine.set_player_count(num_players)
                        engine.set_profile_manager(profile_manager)
                        engine.set_player_profiles(player_profiles)

                        app_mode = "GAME"

            elif app_mode == "GAME":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    handle_mouse_click(event.pos, engine, board_logic, profile_manager)

        if app_mode == "MENU":
            menu_manager.draw(screen)

        elif app_mode == "GAME":
            draw_game(screen, engine, board_logic, view)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


def handle_mouse_click(mouse_pos, engine, board_logic, profile_manager):
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
        handle_playing_click(mouse_pos, engine, board_logic, profile_manager)


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


def handle_playing_click(mouse_pos, engine, board_logic, profile_manager):
    if engine.waiting_for_doubles_roll:
        if ROLL_BUTTON_RECT.collidepoint(mouse_pos):
            engine.roll_dice()
        return

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

    if engine.selected_index is None:
        if engine.select_piece(engine.current_player, clicked_idx):
            print(f"Selected: {clicked_idx}")
        return

    if clicked_idx == engine.selected_index:
        if engine.attempt_move(engine.current_player, engine.selected_index, 24):
            print(f"Scored from: {clicked_idx}")

            if engine.game_over:
                handle_game_finish(engine, profile_manager)
                return

            if not engine.moves_available:
                engine.next_turn()
            else:
                engine.selected_index = None
            return

        engine.selected_index = None
        print("Deselected piece")
        return

    if engine.attempt_move(engine.current_player, engine.selected_index, clicked_idx):
        print(f"Moved to: {clicked_idx}")

        if engine.game_over:
            handle_game_finish(engine, profile_manager)
            return

        if not engine.moves_available:
            engine.next_turn()
        else:
            engine.selected_index = None
        return

    if engine.select_piece(engine.current_player, clicked_idx):
        print(f"Reselected: {clicked_idx}")
        return

    print(f"Illegal move from {engine.selected_index} to {clicked_idx}")


def resolve_click_target(mouse_pos, engine, board_logic):
    clicked_idx = board_logic.get_index_from_mouse(mouse_pos)

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
        draw_setup_overlay(screen, view.font, engine)
    elif engine.phase == "SHOW_INITIAL_WINNER":
        view.draw_initial_winner_screen(engine)


def is_clicking_start(mouse_pos, player_id):
    if player_id not in START_AREAS:
        return False

    start_x, start_y = START_AREAS[player_id]
    dist = ((mouse_pos[0] - start_x) ** 2 + (mouse_pos[1] - start_y) ** 2) ** 0.5
    return dist < 40


def draw_setup_overlay(screen, font, engine):
    y_offset = 200
    title = font.render("Initial Roll Phase - Click Corners to Roll", True, WHITE)
    screen.blit(title, (SCREEN_WIDTH // 2 - 200, 150))

    for p_id, total in engine.player_rolls.items():
        player_name = engine.get_player_name(p_id)
        txt = font.render(f"{player_name}: {total}", True, PLAYER_COLORS[p_id])
        screen.blit(txt, (SCREEN_WIDTH // 2 - 100, y_offset))
        y_offset += 40


def handle_game_finish(engine, profile_manager):
    if not engine.game_over or not engine.winner_id:
        return

    standings = engine.final_standings[:]
    winner_id = standings[0]

    winner_name = engine.player_profiles.get(winner_id)
    if winner_name:
        profile_manager.record_win(winner_name)

    for player_id in range(1, engine.num_players + 1):
        if player_id == winner_id:
            continue

        player_name = engine.player_profiles.get(player_id)
        if not player_name:
            continue

        profile_manager.record_loss(player_name)

        if engine.finished_pool.get(player_id, 0) == 0:
            profile_manager.increment_stat(player_name, "times_skunked", 1)

    for place, player_id in enumerate(standings[1:], start=2):
        player_name = engine.player_profiles.get(player_id)
        if not player_name:
            continue

        if place == 2:
            profile_manager.increment_stat(player_name, "second_place", 1)
        elif place == 3:
            profile_manager.increment_stat(player_name, "third_place", 1)


if __name__ == "__main__":
    main()