import pygame
import sys
import os
import traceback
from datetime import datetime

from Constants import *
from GameEngine import GameEngine
from Layout import Layout
from Renderer import Renderer
from MenuManager import MenuManager
from ProfileManager import ProfileManager
from StatsMenu import StatsMenu
from PauseMenu import PauseMenu
from Settings import Settings, MIN_WINDOW_SIZE
from Controller import ControllerManager
import SaveManager as save

BASE_W, BASE_H = SCREEN_WIDTH, SCREEN_HEIGHT
CRASH_LOG = "crash.log"

# Screens the game pad drives with high-level intents rather than a cursor.
INTENT_MODES = {"GAME", "PAUSE", "RULES"}


def log_crash(exc, context=""):
    """Append a full traceback to crash.log so failures are never silent."""
    try:
        with open(CRASH_LOG, "a", encoding="utf-8") as fh:
            fh.write(f"\n{'=' * 70}\n{datetime.now().isoformat()}  {context}\n")
            fh.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    except OSError:
        pass
    traceback.print_exc()


# ================================================================
# WINDOW / CANVAS SCALING
# Everything is drawn to a fixed-size canvas which is then scaled
# (aspect-preserving, letterboxed) onto the real window.  Fullscreen
# and resizing therefore never touch any game-side coordinates.
# ================================================================
def make_window(settings):
    if settings.get("fullscreen"):
        # Borderless desktop-sized window rather than an exclusive video-mode
        # change: it covers the screen but stays alt-tab friendly and does not
        # thrash the display mode when focus is lost.
        info = pygame.display.Info()
        w, h = info.current_w, info.current_h
        if w <= 0 or h <= 0:
            w, h = BASE_W, BASE_H
        try:
            return pygame.display.set_mode((w, h), pygame.NOFRAME)
        except pygame.error:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    size = settings.get("window_size") or [BASE_W, BASE_H]
    size = (max(MIN_WINDOW_SIZE[0], int(size[0])), max(MIN_WINDOW_SIZE[1], int(size[1])))
    return pygame.display.set_mode(size, pygame.RESIZABLE)


def present(window, canvas):
    ww, wh = window.get_size()
    cw, ch = canvas.get_size()
    # A minimised window can report a zero (or tiny) size - keep the maths sane.
    if ww < 1 or wh < 1:
        return None
    scale = min(ww / cw, wh / ch)
    if scale <= 0:
        return None
    dw, dh = max(1, int(cw * scale)), max(1, int(ch * scale))
    ox, oy = (ww - dw) // 2, (wh - dh) // 2
    window.fill((0, 0, 0))
    window.blit(pygame.transform.smoothscale(canvas, (dw, dh)), (ox, oy))
    pygame.display.flip()
    return scale, ox, oy


def to_canvas(pos, transform):
    if not transform or transform[0] <= 0:
        return pos
    scale, ox, oy = transform
    return (int((pos[0] - ox) / scale), int((pos[1] - oy) / scale))


def remap_event(event, transform):
    """Return a copy of a mouse event with its position in canvas space."""
    if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
        data = dict(event.dict)
        data["pos"] = to_canvas(event.pos, transform)
        if "rel" in data and transform and transform[0] > 0:
            data["rel"] = (data["rel"][0] / transform[0], data["rel"][1] / transform[0])
        return pygame.event.Event(event.type, data)
    return event


def main():
    pygame.init()
    settings = Settings()
    window = make_window(settings)
    pygame.display.set_caption("Acey Duecy - 2 to 4 Player Strategy")
    canvas = pygame.Surface((BASE_W, BASE_H))
    clock = pygame.time.Clock()

    profile_manager = ProfileManager()
    menu_manager = MenuManager(profile_manager)
    stats_menu = StatsMenu(profile_manager)
    pause_menu = PauseMenu()
    layout = Layout(BASE_W, BASE_H)
    view = Renderer(canvas, layout)
    controller = ControllerManager((BASE_W, BASE_H))

    engine = None

    state = {
        "app_mode": "MENU",       # MENU | GAME | RULES | SETTINGS | STATS | PAUSE
        "overlay": None,          # None | "HISTORY"  (GAME only)
        "rules_page": 0,
        "return_mode": "MENU",    # where RULES / SETTINGS / STATS return to
        "stats_flushed": False,
        "focus_source_i": 0,      # game-pad highlight: which movable piece
        "focus_dest_i": 0,        # game-pad highlight: which legal target
    }

    transform = (1.0, 0, 0)
    transform = present(window, canvas) or transform
    running = True

    while running:
        dt = clock.tick(FPS)
        menu_manager.update(dt)
        controller.set_mode("INTENT" if state["app_mode"] in INTENT_MODES else "CURSOR")
        controller.update(dt)

        try:
            for raw_event in pygame.event.get():
                if raw_event.type == pygame.QUIT:
                    running = False
                    continue

                if raw_event.type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP,
                                      pygame.JOYAXISMOTION, pygame.JOYHATMOTION,
                                      pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                    controller.handle_event(raw_event)
                    continue

                if raw_event.type == pygame.MOUSEMOTION and any(raw_event.rel):
                    controller.on_mouse_activity()

                if raw_event.type == pygame.VIDEORESIZE and not settings.get("fullscreen"):
                    settings.set("window_size", [max(MIN_WINDOW_SIZE[0], raw_event.w),
                                                 max(MIN_WINDOW_SIZE[1], raw_event.h)])
                    window = make_window(settings)
                    continue

                if raw_event.type == pygame.KEYDOWN and raw_event.key == pygame.K_F11:
                    settings.toggle("fullscreen")
                    window = make_window(settings)
                    continue

                event = remap_event(raw_event, transform)

                if state["app_mode"] == "MENU":
                    handle_menu_event(event, state, menu_manager, stats_menu, profile_manager)
                    if state.pop("_quit", False):
                        running = False
                    if "_new_engine" in state:
                        engine = state.pop("_new_engine")

                elif state["app_mode"] == "RULES":
                    handle_rules_event(event, state, view)

                elif state["app_mode"] == "STATS":
                    handle_stats_event(event, state, stats_menu)

                elif state["app_mode"] == "PAUSE":
                    handle_pause_event(event, state, pause_menu, engine, menu_manager)

                elif state["app_mode"] == "SETTINGS":
                    if handle_settings_event(event, state, view, settings):
                        window = make_window(settings)

                elif state["app_mode"] == "GAME":
                    handle_game_event(event, state, engine, view, profile_manager,
                                      menu_manager, pause_menu)

            # ---- game-pad intents (INTENT-mode screens) ----
            for intent in controller.take_intents():
                if state["app_mode"] == "GAME":
                    handle_game_intent(intent, state, engine, view, profile_manager,
                                       menu_manager, pause_menu)
                elif state["app_mode"] == "PAUSE":
                    handle_pause_intent(intent, state, pause_menu, engine, menu_manager)
                elif state["app_mode"] == "RULES":
                    handle_rules_intent(intent, state)

            # ---- draw to canvas ----
            if state["app_mode"] == "MENU":
                menu_manager.draw(canvas)
            elif state["app_mode"] == "RULES":
                _draw_backdrop(canvas, menu_manager, engine, view, state)
                view.draw_rules_overlay(state["rules_page"])
            elif state["app_mode"] == "STATS":
                stats_menu.draw(canvas)
            elif state["app_mode"] == "PAUSE":
                if engine is not None:
                    draw_game(canvas, engine, view, {"overlay": None})
                pause_menu.draw(canvas)
            elif state["app_mode"] == "SETTINGS":
                view.draw_settings_overlay(
                    settings, backdrop="menu" if state["return_mode"] == "MENU" else "game")
            elif state["app_mode"] == "GAME":
                draw_game(canvas, engine, view, state, show_focus=controller.connected())

            controller.draw_cursor(canvas)
            transform = present(window, canvas) or transform
            controller.set_transform(transform)

        except Exception as exc:  # noqa: BLE001 - last-resort: log and bail cleanly
            log_crash(exc, f"app_mode={state.get('app_mode')} "
                           f"phase={getattr(engine, 'phase', None)} "
                           f"player={getattr(engine, 'current_player', None)}")
            running = False

    pygame.quit()
    sys.exit()


# ================================================================
# MENU
# ================================================================
def handle_menu_event(event, state, menu_manager, stats_menu, profile_manager):
    if event.type == pygame.KEYDOWN:
        # Esc / controller B steps back one level through the menu screens.
        if event.key == pygame.K_ESCAPE and not menu_manager.input_active:
            if menu_manager.state == "CREATE_PROFILE":
                menu_manager.state = "PROFILE_SELECT"
            elif menu_manager.state == "PROFILE_SELECT":
                menu_manager.state = "MAIN_MENU"
            return
        menu_manager.handle_keydown(event)
        return
    if event.type != pygame.MOUSEBUTTONDOWN:
        return

    result = menu_manager.handle_mouse_click(event.pos)
    if not result:
        return
    action = result.get("action")

    if action == "exit":
        state["_quit"] = True
    elif action == "open_rules":
        state["rules_page"] = 0
        state["return_mode"] = "MENU"
        state["app_mode"] = "RULES"
    elif action == "open_settings":
        state["return_mode"] = "MENU"
        state["app_mode"] = "SETTINGS"
    elif action == "open_stats":
        stats_menu.reset()
        state["return_mode"] = "MENU"
        state["app_mode"] = "STATS"
    elif action == "start_game":
        engine = GameEngine()
        engine.set_player_count(result["num_players"])
        engine.set_player_profiles(result["player_profiles"])
        engine.set_profile_manager(profile_manager)
        _enter_game(state, engine)
    elif action == "resume_game":
        engine = save.load_engine()
        if engine is not None:
            engine.set_profile_manager(profile_manager)
            save.clear_save()
            _enter_game(state, engine)


def _enter_game(state, engine):
    state["_new_engine"] = engine
    state["overlay"] = None
    state["stats_flushed"] = False
    state["focus_source_i"] = 0
    state["focus_dest_i"] = 0
    state["app_mode"] = "GAME"


# ================================================================
# RULES
# ================================================================
def handle_rules_event(event, state, view):
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            state["app_mode"] = state["return_mode"]
        elif event.key in (pygame.K_LEFT, pygame.K_PAGEUP):
            state["rules_page"] = max(0, state["rules_page"] - 1)
        elif event.key in (pygame.K_RIGHT, pygame.K_PAGEDOWN):
            state["rules_page"] = min(len(RULES_PAGES) - 1, state["rules_page"] + 1)
        return

    if event.type == pygame.MOUSEBUTTONDOWN:
        left_rect, right_rect = view.draw_rules_overlay(state["rules_page"])
        if left_rect.collidepoint(event.pos):
            state["rules_page"] = max(0, state["rules_page"] - 1)
        elif right_rect.collidepoint(event.pos):
            state["rules_page"] = min(len(RULES_PAGES) - 1, state["rules_page"] + 1)
        else:
            panel = pygame.Rect(120, 60, SCREEN_WIDTH - 240, SCREEN_HEIGHT - 150)
            if not panel.collidepoint(event.pos):
                state["app_mode"] = state["return_mode"]


def handle_rules_intent(intent, state):
    if intent == "NAV_NEXT":
        state["rules_page"] = min(len(RULES_PAGES) - 1, state["rules_page"] + 1)
    elif intent == "NAV_PREV":
        state["rules_page"] = max(0, state["rules_page"] - 1)
    elif intent in ("CANCEL", "RULES", "PAUSE"):
        state["app_mode"] = state["return_mode"]


# ================================================================
# PAUSE  (in-game; save & quit / resume)
# ================================================================
def handle_pause_event(event, state, pause_menu, engine, menu_manager):
    if event.type == pygame.KEYDOWN:
        if event.key in (pygame.K_ESCAPE, pygame.K_p):
            state["app_mode"] = "GAME"
        elif event.key in (pygame.K_UP, pygame.K_LEFT):
            pause_menu.move(-1)
        elif event.key in (pygame.K_DOWN, pygame.K_RIGHT):
            pause_menu.move(1)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            _apply_pause_action(pause_menu.current_action(), state, engine, menu_manager)
        return

    if event.type == pygame.MOUSEBUTTONDOWN:
        action = pause_menu.handle_click(event.pos)
        if action:
            _apply_pause_action(action, state, engine, menu_manager)


def handle_pause_intent(intent, state, pause_menu, engine, menu_manager):
    if intent == "NAV_NEXT":
        pause_menu.move(1)
    elif intent == "NAV_PREV":
        pause_menu.move(-1)
    elif intent == "CONFIRM":
        _apply_pause_action(pause_menu.current_action(), state, engine, menu_manager)
    elif intent in ("CANCEL", "PAUSE"):
        state["app_mode"] = "GAME"


def _apply_pause_action(action, state, engine, menu_manager):
    if action == "resume":
        state["app_mode"] = "GAME"
        return

    if action == "save_quit" and engine is not None:
        save.write_save(engine)

    # save_quit and quit both drop back to the main menu.
    state["app_mode"] = "MENU"
    state["overlay"] = None
    menu_manager.state = "MAIN_MENU"


# ================================================================
# STATS
# ================================================================
def handle_stats_event(event, state, stats_menu):
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE and not stats_menu.go_back():
            state["app_mode"] = state["return_mode"]
        return

    if event.type == pygame.MOUSEWHEEL:
        stats_menu.scroll_by(event.y)
        return

    if event.type == pygame.MOUSEBUTTONDOWN:
        if stats_menu.handle_click(event.pos) == "close":
            state["app_mode"] = state["return_mode"]


# ================================================================
# SETTINGS
# ================================================================
def handle_settings_event(event, state, view, settings):
    """Return True if the window must be recreated."""
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        state["app_mode"] = state["return_mode"]
        return False

    if event.type != pygame.MOUSEBUTTONDOWN:
        return False

    widgets = view.draw_settings_overlay(
        settings, backdrop="menu" if state["return_mode"] == "MENU" else "game")

    if widgets["back"].collidepoint(event.pos):
        state["app_mode"] = state["return_mode"]
        return False

    for key, rect in widgets["rows"]:
        if rect.collidepoint(event.pos):
            settings.toggle(key)
            return key == "fullscreen"

    return False


def _draw_backdrop(canvas, menu_manager, engine, view, state):
    if state["return_mode"] == "GAME" and engine is not None:
        draw_game(canvas, engine, view, {"overlay": None})
    else:
        menu_manager.draw(canvas)


# ================================================================
# GAME
# ================================================================
def handle_game_event(event, state, engine, view, profile_manager, menu_manager, pause_menu):
    if engine is None:
        return

    if event.type == pygame.MOUSEWHEEL and state["overlay"] == "HISTORY":
        view.history_scroll = max(0, view.history_scroll + event.y)
        return

    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_h:
            state["overlay"] = None if state["overlay"] == "HISTORY" else "HISTORY"
            view.history_scroll = 0
        elif event.key == pygame.K_p and not engine.game_over:
            pause_menu.reset()
            state["app_mode"] = "PAUSE"
        elif event.key == pygame.K_ESCAPE:
            state["overlay"] = None
        elif event.key == pygame.K_u and engine.phase == "PLAYING" and not engine.game_over:
            engine.undo_last_move()
        return

    if event.type != pygame.MOUSEBUTTONDOWN:
        return

    if engine.game_over:
        _finish_and_exit_game(state, engine, profile_manager, menu_manager)
        return

    if state["overlay"] == "HISTORY":
        state["overlay"] = None
        return

    if view.layout.rules_button.collidepoint(event.pos):
        state["rules_page"] = 0
        state["return_mode"] = "GAME"
        state["app_mode"] = "RULES"
        return

    dispatch_playing_click(event.pos, engine, view.layout, state)


def dispatch_playing_click(pos, engine, layout, state):
    if engine.phase == "PLAYER_SELECTION":
        for count, rect in layout.selection_buttons.items():
            if rect.collidepoint(pos):
                engine.set_player_count(count)
        return

    if engine.phase == "INITIAL_ROLL":
        for p_id in range(1, engine.num_players + 1):
            if p_id not in engine.player_rolls and layout.chip_at(pos, p_id):
                engine.record_initial_roll(p_id)
                if engine.phase == "PLAYING":
                    engine.phase = "SHOW_INITIAL_WINNER"
                return
        return

    if engine.phase == "SHOW_INITIAL_WINNER":
        engine.phase = "PLAYING"
        return

    if engine.phase == "PLAYING":
        handle_playing_click(pos, engine, layout, state)


def handle_playing_click(pos, engine, layout, state):
    if layout.undo_button.collidepoint(pos):
        engine.undo_last_move()
        return

    if layout.history_button.collidepoint(pos):
        state["overlay"] = "HISTORY"
        view_scroll_reset(state)
        return

    if layout.roll_button.collidepoint(pos):
        if engine.waiting_for_doubles_roll or not engine.has_rolled_this_turn:
            engine.roll_dice()
        elif engine.moves_available:
            engine.pass_turn()
        else:
            engine.end_turn()
        return

    clicked_idx = resolve_click_target(pos, engine, layout)

    if engine.selected_index is None:
        engine.select_piece(engine.current_player, clicked_idx)
        return

    if clicked_idx == engine.selected_index:
        engine.attempt_move(engine.current_player, engine.selected_index, 24)
        # Drop the selection once the source point no longer holds one of the
        # player's checkers (failed move, or the last one just borne off).
        idx = engine.selected_index
        if idx is None or idx < 0 or idx >= 24 or engine.current_player not in engine.board[idx]:
            engine.selected_index = None
        return

    if engine.attempt_move(engine.current_player, engine.selected_index, clicked_idx):
        engine.selected_index = None
        return

    if engine.select_piece(engine.current_player, clicked_idx):
        return


def resolve_click_target(pos, engine, layout):
    clicked_idx = layout.click_target(pos)
    if clicked_idx is None and layout.chip_at(pos, engine.current_player):
        return -2
    return clicked_idx


def view_scroll_reset(state):
    state["_scroll_reset"] = True


# ================================================================
# GAME  -  controller intents
# The pad cycles a highlight through the current player's movable
# pieces, then (once one is picked) through that piece's legal targets.
# ================================================================
def handle_game_intent(intent, state, engine, view, profile_manager, menu_manager, pause_menu):
    if engine is None:
        return

    if intent == "PAUSE" and not engine.game_over:
        pause_menu.reset()
        state["app_mode"] = "PAUSE"
        return

    if state["overlay"] == "HISTORY":
        if intent == "NAV_PREV":
            view.history_scroll += 1
        elif intent == "NAV_NEXT":
            view.history_scroll = max(0, view.history_scroll - 1)
        elif intent in ("CANCEL", "HISTORY"):
            state["overlay"] = None
        return

    if engine.game_over:
        if intent in ("CONFIRM", "ACTION"):
            _finish_and_exit_game(state, engine, profile_manager, menu_manager)
        return

    if intent == "RULES":
        state["rules_page"] = 0
        state["return_mode"] = "GAME"
        state["app_mode"] = "RULES"
        return

    if intent == "HISTORY":
        state["overlay"] = "HISTORY"
        view.history_scroll = 0
        return

    if engine.phase == "INITIAL_ROLL":
        if intent in ("CONFIRM", "ACTION"):
            for p_id in range(1, engine.num_players + 1):
                if p_id not in engine.player_rolls:
                    engine.record_initial_roll(p_id)
                    if engine.phase == "PLAYING":
                        engine.phase = "SHOW_INITIAL_WINNER"
                    break
        return

    if engine.phase == "SHOW_INITIAL_WINNER":
        if intent in ("CONFIRM", "ACTION"):
            engine.phase = "PLAYING"
        return

    if engine.phase != "PLAYING":
        return

    if intent == "UNDO":
        engine.undo_last_move()
        _reset_focus(state)
    elif intent == "ACTION":
        if engine.waiting_for_doubles_roll or not engine.has_rolled_this_turn:
            engine.roll_dice()
        elif engine.moves_available:
            engine.pass_turn()
        else:
            engine.end_turn()
        _reset_focus(state)
    elif intent == "CANCEL":
        if engine.selected_index is not None:
            engine.selected_index = None
            state["focus_dest_i"] = 0
    elif intent in ("NAV_NEXT", "NAV_PREV"):
        _move_focus(state, engine, 1 if intent == "NAV_NEXT" else -1)
    elif intent == "CONFIRM":
        _confirm_focus(state, engine)


def _reset_focus(state):
    state["focus_source_i"] = 0
    state["focus_dest_i"] = 0


def _move_focus(state, engine, delta):
    pid = engine.current_player
    if engine.selected_index is None:
        n = len(engine.movable_sources(pid))
        if n:
            state["focus_source_i"] = (state.get("focus_source_i", 0) + delta) % n
    else:
        n = len(engine.legal_destinations(pid, engine.selected_index))
        if n:
            state["focus_dest_i"] = (state.get("focus_dest_i", 0) + delta) % n


def _confirm_focus(state, engine):
    pid = engine.current_player

    if engine.selected_index is None:
        sources = engine.movable_sources(pid)
        if sources:
            engine.select_piece(pid, sources[state.get("focus_source_i", 0) % len(sources)])
            state["focus_dest_i"] = 0
        return

    dests = engine.legal_destinations(pid, engine.selected_index)
    if not dests:
        return
    target = dests[state.get("focus_dest_i", 0) % len(dests)]
    if engine.attempt_move(pid, engine.selected_index, target):
        engine.selected_index = None
        _reset_focus(state)


def _finish_and_exit_game(state, engine, profile_manager, menu_manager):
    if not state["stats_flushed"]:
        handle_game_finish(engine, profile_manager)
        state["stats_flushed"] = True
    save.clear_save()
    state["app_mode"] = "MENU"
    state["overlay"] = None
    menu_manager.state = "MAIN_MENU"


# ================================================================
# DRAW
# ================================================================
def draw_game(canvas, engine, view, state, show_focus=False):
    if engine.phase == "PLAYER_SELECTION":
        view.draw_player_selection()
        return

    view.draw_background()
    view.draw_points()
    view.draw_jail(engine)
    view.draw_player_pieces(engine)
    view.draw_status_chips(engine)

    if engine.phase == "INITIAL_ROLL":
        view.draw_setup_overlay(engine, pad=show_focus)
        return

    if engine.phase == "SHOW_INITIAL_WINNER":
        view.draw_initial_winner_screen(engine, pad=show_focus)
        return

    view.draw_ui(engine, pad=show_focus)

    if state.get("_scroll_reset"):
        view.history_scroll = 0
        state["_scroll_reset"] = False

    if engine.game_over:
        view.draw_game_over(engine, pad=show_focus)
    elif state.get("overlay") == "HISTORY":
        view.draw_history_overlay(engine)
    elif show_focus:
        view.draw_controller_focus(engine, state)


# ================================================================
# STAT FLUSH  (runs once when a game finishes)
# ================================================================
def handle_game_finish(engine, profile_manager):
    standings = engine.get_standings()
    profiles = engine.player_profiles

    for rank, player_id in enumerate(standings, start=1):
        name = profiles.get(player_id)
        if not name:
            continue

        bucket = engine.game_stats.get(player_id, {})
        for stat_name, value in bucket.items():
            if stat_name.startswith("_") or not value:
                continue
            try:
                profile_manager.increment_stat(name, stat_name, value)
            except ValueError:
                pass

        block_max = bucket.get("_block_zone_max", 0)
        if block_max:
            profile_manager.update_max_stat(name, "longest_block_zone_created", block_max)

        profile_manager.increment_stat(name, "games_played", 1)

        if rank == 1:
            profile_manager.increment_stat(name, "wins", 1)
        else:
            profile_manager.increment_stat(name, "losses", 1)
            profile_manager.record_placement(name, rank)
            if engine.finished_pool.get(player_id, 0) == 0:
                profile_manager.increment_stat(name, "times_skunked", 1)

    if len(standings) >= 2:
        winner_name = profiles.get(standings[0])
        runner_off = engine.finished_pool.get(standings[1], 0)
        if winner_name:
            profile_manager.update_max_stat(winner_name, "biggest_win_margin", 15 - runner_off)

    for i, better in enumerate(standings):
        for worse in standings[i + 1:]:
            bn, wn = profiles.get(better), profiles.get(worse)
            if bn and wn:
                profile_manager.record_head_to_head(bn, wn)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        log_crash(exc, "fatal (outside main loop)")
        raise
