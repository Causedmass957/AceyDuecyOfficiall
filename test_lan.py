"""
Same host+join flow as test_multiplayer_flow.py, but the client connects
to this machine's actual LAN-facing IP instead of 127.0.0.1. Loopback
traffic bypasses the OS network stack's normal interface/firewall path on
Windows; routing through the real LAN IP exercises that path for real -
in particular, whether Windows Firewall blocks or prompts for the
listening socket, which loopback can't reveal.

A fast raw-socket preflight (short timeout) checks reachability first, so
a firewall silently dropping packets fails in ~5s instead of hanging on
the OS's full TCP connect timeout.

Run directly: python test_lan.py
"""
import os

os.environ["ACEYDUECY_CHANNEL"] = "claude_lan_test"

import socket  # noqa: E402
import time  # noqa: E402

import pygame  # noqa: E402

pygame.init()

import main  # noqa: E402
import NetSession  # noqa: E402
from ProfileManager import ProfileManager  # noqa: E402

TIMEOUT = 3.0
MAX_STEPS = 20000


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def wait_until(cond, timeout=TIMEOUT):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if cond():
            return True
        time.sleep(0.002)
    return False


def preflight(host, port, timeout=5.0):
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True, None
    except OSError as exc:
        return False, exc


def main_test():
    ip = lan_ip()
    profile_manager = ProfileManager()

    host_session = NetSession.HostSession(port=0)
    port = host_session.port
    print(f"Host listening on 0.0.0.0:{port} (this machine's LAN IP: {ip})")

    ok, err = preflight(ip, port)
    if not ok:
        print(f"PREFLIGHT FAILED connecting to {ip}:{port} over the real LAN interface: {err}")
        print("This points at Windows Firewall (or another network policy) blocking the inbound "
              "connection on this interface - loopback wouldn't have shown this.")
        host_session.close()
        raise SystemExit(1)
    print(f"Preflight OK: reached {ip}:{port} over the real network interface (not loopback).")

    host_session.assign_local_seat(1)
    engine = None

    def new_conn_and_join():
        events = host_session.poll_lobby()
        for ev in events:
            if ev["type"] == "new_connection":
                host_session.assign_remote_seat(ev["sock"], ev["addr"], 2)
                host_session.welcome(2)
        return any(True for ev in events if ev["type"] == "new_connection")

    client_session = NetSession.ClientSession(ip, port, "LanTestClient")
    assert wait_until(new_conn_and_join), "host never saw the LAN connection arrive"

    def joined():
        host_session.poll_lobby()
        for ev in client_session.poll_lobby():
            if ev["type"] == "welcome":
                pass
        return client_session.my_seat == 2

    assert wait_until(joined), "client never received its seat over the LAN connection"
    print(f"Client assigned seat {client_session.my_seat} over the real LAN socket.")

    engine = main.GameEngine()
    engine.set_player_count(2)
    engine.set_player_profiles({1: "Host", 2: "LanTestClient"})
    engine.set_profile_manager(profile_manager)
    host_session.start_game(engine)

    def client_started():
        for ev in client_session.poll_lobby():
            if ev["type"] == "start":
                return True
        return client_session.engine is not None

    assert wait_until(client_started), "client never received the start snapshot over LAN"
    client_engine = client_session.engine
    client_engine.set_profile_manager(profile_manager)
    assert engine.to_dict() == client_engine.to_dict()
    print("Snapshot received over LAN, engines match.")

    host_state = {"net_session": host_session, "my_seats": {1}}
    client_state = {"net_session": client_session, "my_seats": {2}}
    step_count = 0

    def step(cmd, args, seat):
        nonlocal step_count
        step_count += 1
        if seat == 1:
            main._dispatch(host_state, engine, cmd, args)
        else:
            main._dispatch(client_state, client_engine, cmd, args)

        def converged():
            host_session.poll_game()
            client_session.poll_game()
            return engine.to_dict() == client_engine.to_dict()

        if not wait_until(converged):
            raise AssertionError(f"DIVERGED over LAN after step {step_count} ({cmd}{args}, seat {seat})")

    while engine.phase == "INITIAL_ROLL":
        for pid in (1, 2):
            if pid not in engine.player_rolls:
                step("record_initial_roll", [pid], pid)

    print(f"Initial roll settled after {step_count} steps over LAN; turn order = {engine.turn_order}")

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

    assert engine.game_over
    print(f"Game finished over the real LAN interface after {step_count} steps.")
    print(f"Standings: {engine.get_standings()}")
    print("Host and client engines byte-identical over LAN. PASS")

    host_session.close()
    client_session.close()


if __name__ == "__main__":
    main_test()
