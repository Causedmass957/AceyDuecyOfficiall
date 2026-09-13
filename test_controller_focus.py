"""Regression coverage for the game-pad highlight path (main._move_focus /
main._confirm_focus / Layout.order_for_focus).

This is a direct repro of a real crash: main.py called
`layout.order_for_focus(...)` for months of feature work before that method
actually existed on Layout, and `pytest -m "not manual"` still went green
the whole time because nothing exercised handle_game_intent's NAV_NEXT/
CONFIRM branches. The break only showed up as a frozen exe closing the
instant a player with a controller connected rolled dice and touched the
stick - see %APPDATA%\\AceyDuecy\\<channel>\\crash.log for the
AttributeError this reproduces.

Run directly: python -m pytest test_controller_focus.py
"""
import pygame

pygame.init()

import main  # noqa: E402  (must follow pygame.init())
from GameEngine import GameEngine  # noqa: E402
from Layout import Layout  # noqa: E402


class _StubView:
    def __init__(self):
        self.layout = Layout()


def _fresh_state():
    """Mirrors the subset of main()'s real `state` dict that
    handle_game_intent touches in the GAME/PLAYING branches."""
    return {
        "app_mode": "GAME",
        "overlay": None,
        "focus_source_i": 0,
        "focus_dest_i": 0,
        "net_session": None,
        "my_seats": None,
    }


def _engine_ready_to_roll(num_players=2):
    """A hotseat engine sitting in PLAYING, before its very first roll --
    the exact moment the crash fired (movable_sources() only has the -2
    start-pool pseudo-target, which is the code path that touches
    layout.chip_rects via focus_sort_key)."""
    engine = GameEngine(num_players=num_players)
    engine.set_player_count(num_players)
    while engine.phase != "PLAYING":
        for pid in range(1, num_players + 1):
            if pid not in engine.player_rolls:
                engine.record_initial_roll(pid)
    return engine


def test_nav_next_after_first_roll_does_not_crash():
    engine = _engine_ready_to_roll()
    engine.roll_dice()
    assert engine.movable_sources(engine.current_player) == [-2]

    state = _fresh_state()
    view = _StubView()

    main.handle_game_intent("NAV_NEXT", state, engine, view, None, None, None)

    assert state["focus_source_i"] == 0  # only one candidate (-2) to land on


def test_confirm_focus_selects_the_start_pool_after_first_roll():
    engine = _engine_ready_to_roll()
    engine.roll_dice()
    pid = engine.current_player
    state = _fresh_state()
    view = _StubView()

    main.handle_game_intent("CONFIRM", state, engine, view, None, None, None)

    assert engine.selected_index == -2
    assert pid == engine.current_player


def test_nav_prev_then_confirm_cycles_destinations_without_crashing():
    engine = _engine_ready_to_roll()
    engine.roll_dice()
    state = _fresh_state()
    view = _StubView()

    main.handle_game_intent("CONFIRM", state, engine, view, None, None, None)  # pick -2
    assert engine.selected_index == -2

    main.handle_game_intent("NAV_PREV", state, engine, view, None, None, None)
    main.handle_game_intent("CONFIRM", state, engine, view, None, None, None)  # commit a move

    assert engine.selected_index is None  # attempt_move clears it either way


def test_order_for_focus_sorts_left_to_right_on_screen():
    """The bug this method was written to fix: raw board indices 12..23 run
    right -> left on screen, so cycling in raw order felt backwards on the
    bottom row. Sorting by actual x must undo that."""
    layout = Layout()
    # 20 and 15 both sit on the bottom row (12..23), where board index
    # DEScends left-to-right on screen (see Layout's module docstring).
    raw_order = [15, 20]
    sorted_order = layout.order_for_focus(raw_order, player_id=1)

    x_15 = layout.point_base_x(15)
    x_20 = layout.point_base_x(20)
    assert x_15 != x_20
    expected = sorted(raw_order, key=lambda i: layout.point_base_x(i))
    assert sorted_order == expected


def test_order_for_focus_handles_jail_and_start_pseudo_targets():
    layout = Layout()
    # -1 = jail, -2 = start pool, 24 = bear-off: order_for_focus must be able
    # to key all three without a KeyError/AttributeError, for every seat.
    for player_id in (1, 2, 3, 4):
        result = layout.order_for_focus([-1, -2, 24], player_id)
        assert set(result) == {-1, -2, 24}
