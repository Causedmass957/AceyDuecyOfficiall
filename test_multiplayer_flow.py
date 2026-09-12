"""
End-to-end test of the full multiplayer slice built on top of
Networking.py/test_networking.py: the lobby handshake (HostLobbyScreen /
JoinLobbyScreen / NetSession), then a full 2-player game driven through
main.py's real `_dispatch`/`_my_turn` helpers - the same functions the
actual mouse-click handlers call - so this exercises the exact code path
a real host+client pairing would use, not just the raw transport.

Run directly: python test_multiplayer_flow.py
"""
import time

import pygame

pygame.init()

import main  # noqa: E402  (must follow pygame.init())
import NetSession  # noqa: E402
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


def main_test():
    profile_manager = ProfileManager()

    host_session = NetSession.HostSession(port=0)
    host_lobby = HostLobbyScreen(profile_manager, host_session)
    host_lobby.set_num_players(2)  # seat 1 defaults LOCAL, seat 2 defaults OPEN

    join_lobby = JoinLobbyScreen(profile_manager)
    join_lobby.address_text = f"127.0.0.1:{host_session.port}"
    join_lobby._try_connect()
    assert join_lobby.session is not None, join_lobby.error
    client_session = join_lobby.session

    def lobby_settled():
        host_lobby.poll_net()
        join_lobby.poll_net()
        return host_lobby.seat_mode.get(2) == "connected"

    assert wait_until(lobby_settled), f"lobby never settled: seat modes = {host_lobby.seat_mode}"
    assert host_lobby.is_ready()
    print(f"Lobby settled: seat modes = {host_lobby.seat_mode}, names = {host_lobby.player_profiles()}")

    engine = main._build_hosted_engine(host_lobby, profile_manager)
    host_session.start_game(engine)

    client_engine_holder = {}

    def client_started():
        result = join_lobby.poll_net()
        if result == "start":
            client_engine_holder["engine"] = client_session.engine
            return True
        return client_session.engine is not None

    assert wait_until(client_started), "client never received the start snapshot"
    client_engine = client_session.engine
    client_engine.set_profile_manager(profile_manager)
    assert engine.to_dict() == client_engine.to_dict()

    host_state = {"net_session": host_session, "my_seats": set(host_session.local_seats)}
    client_state = {"net_session": client_session, "my_seats": {client_session.my_seat}}
    assert host_state["my_seats"] == {1}
    assert client_state["my_seats"] == {2}

    step_count = 0

    def step(cmd, args, seat):
        nonlocal step_count
        step_count += 1

        if seat in host_state["my_seats"]:
            main._dispatch(host_state, engine, cmd, args)
        else:
            main._dispatch(client_state, client_engine, cmd, args)

        def converged():
            host_session.poll_game()
            client_session.poll_game()
            return engine.to_dict() == client_engine.to_dict()

        if not wait_until(converged, timeout=TIMEOUT):
            raise AssertionError(
                f"DIVERGED after step {step_count} ({cmd}{args}, seat {seat})\n"
                f"host={engine.to_dict()}\nclient={client_engine.to_dict()}"
            )

    # ---- initial roll phase ----
    while engine.phase == "INITIAL_ROLL":
        for pid in (1, 2):
            if pid not in engine.player_rolls:
                step("record_initial_roll", [pid], pid)

    print(f"Initial roll settled after {step_count} steps; turn order = {engine.turn_order}")

    # ---- play the game out to completion ----
    while not engine.game_over and step_count < MAX_STEPS:
        pid = engine.current_player

        if not engine.has_rolled_this_turn or engine.waiting_for_doubles_roll:
            step("roll_dice", [], pid)
            continue

        sources = engine.movable_sources(pid)
        if sources:
            src = sources[0]
            dests = engine.legal_destinations(pid, src)
            dst = dests[0]
            step("select_piece", [pid, src], pid)
            step("attempt_move", [pid, src, dst], pid)
            continue

        if engine.moves_available:
            step("pass_turn", [], pid)
        else:
            step("end_turn", [], pid)

    assert engine.game_over, f"game did not finish within {MAX_STEPS} steps"
    assert engine.to_dict() == client_engine.to_dict()

    print(f"Game finished after {step_count} networked steps via main._dispatch.")
    print(f"Final standings: {engine.get_standings()}")
    print("Host and client engines are byte-identical. PASS")

    host_session.close()
    client_session.close()


def test_lobby_and_full_game_over_loopback():
    """Pytest entry point for the manual script's main_test() above."""
    main_test()


if __name__ == "__main__":
    main_test()
