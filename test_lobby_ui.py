"""
Exercises the actual lobby UI click/typing code paths - not just the
underlying networking - standing in for "another machine" by running
multiple HostSession/ClientSession pairs inside one process, all talking
over real loopback TCP sockets. This is the piece test_multiplayer_flow.py
didn't cover: real pixel-coordinate clicks against HostLobbyScreen /
JoinLobbyScreen's own drawn rects (button hit-testing, text typing, the
kick button), a 4-player mixed local+remote game, and the NET_PAUSE
disconnect/save flow.

Uses an isolated ACEYDUECY_CHANNEL so nothing here touches the user's
real profiles/stats/settings/save data - must be set before any project
module is imported (Paths.py reads it at import time).

Run directly: python test_lobby_ui.py
"""
import os

os.environ["ACEYDUECY_CHANNEL"] = "claude_lobby_test"

import time  # noqa: E402

import pygame  # noqa: E402

pygame.init()

import main  # noqa: E402
import NetSession  # noqa: E402
import SaveManager as save  # noqa: E402
from Constants import SCREEN_WIDTH, SCREEN_HEIGHT  # noqa: E402
from MultiplayerLobby import HostLobbyScreen, JoinLobbyScreen  # noqa: E402
from ProfileManager import ProfileManager  # noqa: E402

TIMEOUT = 3.0
MAX_STEPS = 20000


def wait_until(cond, timeout=TIMEOUT):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if cond():
            return True
        time.sleep(0.002)
    return False


def type_text(screen, text):
    for ch in text:
        screen.handle_keydown(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE, "unicode": ch}))


def main_test():
    canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    profile_manager = ProfileManager()
    for name in ("Alice", "Bob", "Carol", "Dave"):
        profile_manager.create_profile(name)

    # ---- A. HOST_LOBBY: real clicks against real drawn rects ----
    host_session = NetSession.HostSession(port=0)
    host_lobby = HostLobbyScreen(profile_manager, host_session)

    host_lobby.draw(canvas)
    assert set(host_lobby.count_buttons) == {2, 3, 4}
    host_lobby.handle_click(host_lobby.count_buttons[4].center)
    assert host_lobby.num_players == 4
    assert host_lobby.seat_mode == {1: "local", 2: "open", 3: "open", 4: "open"}

    host_lobby.draw(canvas)  # rects shift once there are 4 seat rows
    host_lobby.handle_click(host_lobby.seat_rects[2].center)  # open -> local
    assert host_lobby.seat_mode[2] == "local" and 2 in host_session.local_seats
    host_lobby.handle_click(host_lobby.seat_rects[2].center)  # local -> open
    assert host_lobby.seat_mode[2] == "open" and 2 not in host_session.local_seats

    before_idx = host_lobby.local_profile_idx.get(1, 0)
    assert 1 in host_lobby.profile_chip_rects
    host_lobby.handle_click(host_lobby.profile_chip_rects[1].center)  # chip cycles profile, doesn't toggle mode
    assert host_lobby.seat_mode[1] == "local"
    assert host_lobby.local_profile_idx.get(1, 0) != before_idx or len(profile_manager.get_all_profiles()) <= 1

    assert main.handle_host_lobby_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": host_lobby.back_button.center, "button": 1}),
        host_lobby,
    ) == "cancel"
    print("HOST_LOBBY click hit-testing: PASS (player count, seat toggle, profile cycle, back button)")

    # ---- B. JOIN_LOBBY: real clicks + real typing for one remote seat ----
    join1 = JoinLobbyScreen(profile_manager)
    join1.draw(canvas)
    join1.handle_click(join1.address_rect.center)
    assert join1.input_active
    type_text(join1, f"127.0.0.1:{host_session.port}")
    assert join1.address_text == f"127.0.0.1:{host_session.port}"

    join1.draw(canvas)
    name_before = join1.display_name()
    join1.handle_click(join1.name_rect.center)
    assert join1.display_name() != name_before

    join1.draw(canvas)
    join1.handle_click(join1.connect_button.center)
    assert join1.session is not None, join1.error
    print("JOIN_LOBBY click/typing hit-testing: PASS (address field, name cycle, connect button)")

    def lobby_settled(seat):
        host_lobby.poll_net()
        join1.poll_net()
        return host_lobby.seat_mode.get(seat) == "connected"

    assert wait_until(lambda: lobby_settled(2)), f"seat 2 never connected: {host_lobby.seat_mode}"

    # ---- Two more remote seats, driven directly (JOIN_LOBBY widget already proven above) ----
    client3 = NetSession.ClientSession("127.0.0.1", host_session.port, "Carol")
    client4 = NetSession.ClientSession("127.0.0.1", host_session.port, "Dave")

    def settled_all():
        host_lobby.poll_net()
        client3.poll_lobby()
        client4.poll_lobby()
        return host_lobby.seat_mode.get(3) == "connected" and host_lobby.seat_mode.get(4) == "connected"

    assert wait_until(settled_all), f"seats 3/4 never connected: {host_lobby.seat_mode}"
    print(f"3 remote peers connected: seat modes = {host_lobby.seat_mode}")

    # ---- C. Kick button: real click, then rejoin ----
    host_lobby.draw(canvas)
    assert 3 in host_lobby.kick_rects
    host_lobby.handle_click(host_lobby.kick_rects[3].center)
    assert host_lobby.seat_mode[3] == "open"
    client3.close()
    print("Kick button hit-testing: PASS (seat 3 disconnected, reopened)")

    client3b = NetSession.ClientSession("127.0.0.1", host_session.port, "Carol")

    def seat3_rejoined():
        host_lobby.poll_net()
        client3b.poll_lobby()
        return host_lobby.seat_mode.get(3) == "connected"

    assert wait_until(seat3_rejoined), f"seat 3 never rejoined: {host_lobby.seat_mode}"

    # ---- D. Start the game: real click on the real Start button ----
    host_lobby.draw(canvas)
    assert host_lobby.is_ready(), host_lobby.seat_mode
    action = host_lobby.handle_click(host_lobby.start_button.center)
    assert action == "start"

    engine = main._build_hosted_engine(host_lobby, profile_manager)
    host_session.start_game(engine)
    print(f"Game started: 4 players = {host_lobby.player_profiles()}")

    # ---- E. All three remote clients receive the snapshot ----
    clients = {2: join1.session, 3: client3b, 4: client4}

    def all_started():
        for c in clients.values():
            c.poll_lobby()
        return all(c.engine is not None for c in clients.values())

    assert wait_until(all_started), "not every client received the start snapshot"
    for seat, c in clients.items():
        c.engine.set_profile_manager(profile_manager)
        assert c.engine.to_dict() == engine.to_dict(), f"seat {seat} snapshot mismatch"

    # ---- F. Play a full 4-player game through main._dispatch, 4-way convergence ----
    host_state = {"net_session": host_session, "my_seats": set(host_session.local_seats)}
    client_states = {seat: {"net_session": c, "my_seats": {seat}} for seat, c in clients.items()}
    assert host_state["my_seats"] == {1}

    step_count = 0

    def all_engines():
        yield engine
        for c in clients.values():
            yield c.engine

    def step(cmd, args, seat):
        nonlocal step_count
        step_count += 1
        if seat == 1:
            main._dispatch(host_state, engine, cmd, args)
        else:
            main._dispatch(client_states[seat], clients[seat].engine, cmd, args)

        def converged():
            host_session.poll_game()
            for c in clients.values():
                c.poll_game()
            dicts = [e.to_dict() for e in all_engines()]
            return all(d == dicts[0] for d in dicts)

        if not wait_until(converged):
            dicts = {("host" if e is engine else seat): e.to_dict()
                     for seat, e in list(clients.items()) + [("host", engine)]}
            raise AssertionError(f"DIVERGED after step {step_count} ({cmd}{args}, seat {seat})\n{dicts}")

    while engine.phase == "INITIAL_ROLL":
        for pid in (1, 2, 3, 4):
            if pid not in engine.player_rolls:
                step("record_initial_roll", [pid], pid)

    print(f"Initial roll settled after {step_count} steps; turn order = {engine.turn_order}")

    while not engine.game_over and step_count < MAX_STEPS:
        pid = engine.current_player
        if not engine.has_rolled_this_turn or engine.waiting_for_doubles_roll:
            step("roll_dice", [], pid)
            continue
        sources = engine.movable_sources(pid)
        if sources:
            src = sources[0]
            dst = engine.legal_destinations(pid, src)[0]
            step("select_piece", [pid, src], pid)
            step("attempt_move", [pid, src, dst], pid)
            continue
        if engine.moves_available:
            step("pass_turn", [], pid)
        else:
            step("end_turn", [], pid)

    assert engine.game_over, f"4-player game did not finish within {MAX_STEPS} steps"
    print(f"4-player game finished after {step_count} steps. Standings: {engine.get_standings()}")
    print("All 4 engines byte-identical throughout. PASS")

    # ---- G. NET_PAUSE: disconnect + real click on the real Save button ----
    assert not save.has_save()
    clients[4].close()

    def host_saw_disconnect():
        host_session.poll_game()
        return host_session.disconnected_seat == 4

    assert wait_until(host_saw_disconnect), "host never noticed seat 4 drop"

    label = main._net_pause_label(host_state, engine)
    print(f"NET_PAUSE label: {label!r}")
    # handle_net_pause_event redraws internally to get its rects; draw once
    # here first just to know real pixel coordinates to click.
    rects = main.draw_net_pause_overlay(canvas, label)
    action = main.handle_net_pause_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": rects["save"].center, "button": 1}),
        host_state, engine, canvas,
    )
    assert action == "exit"
    assert save.has_save(), "Save & Exit click did not write a save file"

    reloaded = save.load_engine()
    assert reloaded is not None
    assert reloaded.to_dict() == engine.to_dict()
    print("NET_PAUSE disconnect + Save & Exit: PASS (save round-trips correctly)")

    save.clear_save()
    host_session.close()
    for c in clients.values():
        c.close()

    print("\nALL LOBBY/UI CHECKS PASSED")


def test_lobby_ui_full_flow():
    """Pytest entry point for the manual script's main_test() above."""
    main_test()


if __name__ == "__main__":
    main_test()
