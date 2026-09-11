"""
Frame-driven multiplayer session glue, sitting one layer above
Networking.py's raw transport. main.py drives these with one non-blocking
poll call per frame instead of the blocking waits test_networking.py uses
to prove the transport itself is correct.

HostSession runs on the hosting player's machine and holds the one
authoritative GameEngine. ClientSession runs on a joining machine and
only ever gets its engine mutated by commands the host echoes back - see
Networking.py's module docstring for why (lockstep replication, host is
the only side that mutates directly).
"""
import socket

import Networking
from GameEngine import GameEngine

# A fixed default so a hosting player's address stays the same game to
# game (a friend only has to remember one port). Pass port=0 to bind an
# OS-assigned ephemeral port instead (used by the automated tests so
# concurrent runs never collide).
DEFAULT_PORT = 51515


def local_ip_guess():
    """Best-effort LAN IP to show in the lobby (doesn't actually send
    anything - just asks the OS which interface would be used)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


class HostSession:
    is_host = True

    def __init__(self, port=DEFAULT_PORT):
        self.net = Networking.NetHost(port)
        self.local_seats = set()
        self.engine = None
        self.disconnected_seat = None

    @property
    def port(self):
        return self.net._listen_sock.getsockname()[1]

    @property
    def local_ip(self):
        return local_ip_guess()

    def assign_local_seat(self, seat):
        self.local_seats.add(seat)

    def unassign_local_seat(self, seat):
        self.local_seats.discard(seat)

    def assign_remote_seat(self, sock, addr, seat):
        self.net.assign_seat(sock, addr, seat)

    def kick_seat(self, seat):
        peer = self.net.peers.pop(seat, None)
        if peer:
            peer.close()

    def controls(self, seat):
        return seat in self.local_seats

    # ---- lobby phase ----
    def poll_lobby(self):
        """Returns a list of lobby-relevant events: new connections
        needing a seat, join handshakes, and disconnects."""
        events = []
        for msg in self.net.poll():
            t = msg["type"]
            if t == "_new_connection":
                events.append({"type": "new_connection", "sock": msg["_sock"], "addr": msg["_addr"]})
            elif t == "join":
                events.append({"type": "join", "seat": msg["seat"], "name": msg.get("name") or "Guest"})
            elif t == "disconnect":
                events.append({"type": "disconnect", "seat": msg["seat"]})
        return events

    def welcome(self, seat):
        self.net.send_to(seat, {"type": "welcome", "seat": seat})

    def start_game(self, engine):
        self.engine = engine
        self.net.broadcast({"type": "snapshot", "state": engine.to_dict()})

    # ---- game phase ----
    def perform(self, cmd, args):
        """Apply a command to the authoritative engine - from local input
        on a locally-controlled seat, or an already-validated remote
        intent - then broadcast the same command (and its real result,
        needed to replay roll_dice/record_initial_roll deterministically
        elsewhere) to every connected peer."""
        result = Networking.apply_command(self.engine, cmd, args)
        self.net.broadcast({"type": "cmd", "cmd": cmd, "args": args, "result": result})
        return result

    def poll_game(self):
        """Call once per frame during GAME. Applies any validated remote
        intents to the engine."""
        for msg in self.net.poll():
            t = msg["type"]
            if t == "disconnect":
                if msg["seat"] not in self.local_seats:
                    self.disconnected_seat = msg["seat"]
                continue
            if t != "intent":
                continue
            seat, cmd, args = msg["seat"], msg["cmd"], msg["args"]
            if Networking.validate_command(self.engine, cmd, args, seat):
                self.perform(cmd, args)

    def close(self):
        self.net.close()


class ClientSession:
    is_host = False

    def __init__(self, host, port, name):
        self.net = Networking.NetClient(host, port)
        self.name = name
        self.engine = None
        self.my_seat = None
        self.host_disconnected = False

    def controls(self, seat):
        return seat == self.my_seat

    # ---- lobby phase ----
    def poll_lobby(self):
        """Returns a list of lobby-relevant events: seat assignment,
        game start, or the host connection dropping."""
        events = []
        for msg in self.net.poll():
            t = msg["type"]
            if t == "welcome":
                self.my_seat = msg["seat"]
                self.net.send({"type": "join", "name": self.name})
                events.append({"type": "welcome", "seat": msg["seat"]})
            elif t == "snapshot":
                self.engine = GameEngine.from_dict(msg["state"])
                events.append({"type": "start"})
            elif t == "disconnect":
                self.host_disconnected = True
                events.append({"type": "disconnect"})
        return events

    # ---- game phase ----
    def request(self, cmd, args):
        """Send an intent to the host. Does not mutate the local engine -
        that only happens once the host echoes the applied command back
        via poll_game()."""
        self.net.send({"type": "intent", "cmd": cmd, "args": args})

    def poll_game(self):
        for msg in self.net.poll():
            t = msg["type"]
            if t == "disconnect":
                self.host_disconnected = True
            elif t == "cmd":
                Networking.apply_command(self.engine, msg["cmd"], msg["args"], result=msg.get("result"))

    def close(self):
        self.net.close()
