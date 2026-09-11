"""
Manual/internal test for Networking.py: plays a full 2-player game end to
end over real TCP sockets (loopback), seat 1 acting as the host's own
local input and seat 2 acting as a remote client sending intents, and
asserts the two GameEngine instances stay byte-identical after every
single networked command.

Run directly: python test_networking.py
"""
import time

import Networking
from GameEngine import GameEngine

MAX_STEPS = 20000
TIMEOUT = 2.0


def wait_for_one(net, timeout=TIMEOUT):
    deadline = time.time() + timeout
    while time.time() < deadline:
        msgs = net.poll()
        if msgs:
            assert len(msgs) == 1, f"expected exactly one queued message, got {msgs}"
            return msgs[0]
        time.sleep(0.001)
    raise TimeoutError("no message received in time")


def main():
    engine_host = GameEngine(num_players=2)
    engine_host.set_player_count(2)

    host_net = Networking.NetHost(port=0)
    port = host_net._listen_sock.getsockname()[1]
    client_net = Networking.NetClient("127.0.0.1", port)

    conn_msg = wait_for_one(host_net)
    assert conn_msg["type"] == "_new_connection"
    host_net.assign_seat(conn_msg["_sock"], conn_msg["_addr"], seat=2)

    host_net.send_to(2, {"type": "snapshot", "state": engine_host.to_dict()})
    snap_msg = wait_for_one(client_net)
    assert snap_msg["type"] == "snapshot"
    engine_client = GameEngine.from_dict(snap_msg["state"])

    step_count = 0

    def step(cmd, args, seat):
        nonlocal step_count
        step_count += 1

        if seat == 1:
            result = Networking.apply_command(engine_host, cmd, args)
        else:
            client_net.send({"type": "intent", "cmd": cmd, "args": args})
            intent_msg = wait_for_one(host_net)
            assert intent_msg["type"] == "intent" and intent_msg["seat"] == seat, intent_msg
            assert Networking.validate_command(engine_host, cmd, args, seat), (
                f"host rejected {cmd}{args} from seat {seat}"
            )
            result = Networking.apply_command(engine_host, cmd, args)

        host_net.broadcast({"type": "cmd", "cmd": cmd, "args": args, "result": result})

        cmd_msg = wait_for_one(client_net)
        assert cmd_msg["type"] == "cmd" and cmd_msg["cmd"] == cmd, cmd_msg
        Networking.apply_command(engine_client, cmd_msg["cmd"], cmd_msg["args"], result=cmd_msg.get("result"))

        if engine_host.to_dict() != engine_client.to_dict():
            raise AssertionError(f"DIVERGED after step {step_count} ({cmd}{args}, seat {seat})")

        return result

    # ---- initial roll phase ----
    while engine_host.phase == "INITIAL_ROLL":
        for pid in (1, 2):
            if pid not in engine_host.player_rolls:
                step("record_initial_roll", [pid], pid)

    print(f"Initial roll settled after {step_count} steps; turn order = {engine_host.turn_order}")

    # ---- play the game out to completion ----
    while not engine_host.game_over and step_count < MAX_STEPS:
        pid = engine_host.current_player

        if not engine_host.has_rolled_this_turn or engine_host.waiting_for_doubles_roll:
            step("roll_dice", [], pid)
            continue

        sources = engine_host.movable_sources(pid)
        if sources:
            src = sources[0]
            dests = engine_host.legal_destinations(pid, src)
            dst = dests[0]
            step("select_piece", [pid, src], pid)
            result = step("attempt_move", [pid, src, dst], pid)
            assert result is True, f"attempt_move({pid},{src},{dst}) unexpectedly failed"
            continue

        if engine_host.moves_available:
            step("pass_turn", [], pid)
        else:
            step("end_turn", [], pid)

    assert engine_host.game_over, f"game did not finish within {MAX_STEPS} steps"
    assert engine_host.to_dict() == engine_client.to_dict()

    print(f"Game finished after {step_count} networked steps.")
    print(f"Final standings: {engine_host.get_standings()}")
    print("Host and client engines are byte-identical. PASS")

    host_net.close()
    client_net.close()


if __name__ == "__main__":
    main()
