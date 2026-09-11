"""
Online multiplayer transport: host-authoritative lockstep command
replication over plain TCP sockets (stdlib only, so PyInstaller packaging
stays simple).

The host runs the one real GameEngine and is the only side that ever
mutates it directly - both from its own local-seat input and from
validated client intents. Every applied command is then broadcast to all
peers (including whichever client sent the intent, if any), and clients
only ever apply commands that arrive from the host. This keeps every
screen byte-identical with no reconciliation/desync logic.

Messages are length-prefixed JSON: a 4-byte big-endian length header
followed by that many bytes of UTF-8 JSON.
"""
import contextlib
import json
import queue
import random
import socket
import struct
import threading

_HEADER = struct.Struct(">I")

# Networked commands -> whether the engine method's first positional
# argument names the acting player (used for host-side seat validation).
# Every command here is an existing GameEngine method name; the network
# layer never duplicates game logic, only dispatches to it.
COMMANDS = {
    "set_player_count": False,
    "record_initial_roll": True,
    "roll_dice": False,
    "select_piece": True,
    "attempt_move": True,
    "pass_turn": False,
    "end_turn": False,
    "undo_last_move": False,
}

# Commands whose engine method draws from `random` internally. The host's
# real call is the only true roll; its return value is broadcast alongside
# the command so every other peer can force random.randint(...) to hand
# back that exact sequence during replay instead of drawing its own -
# otherwise dice/turn-order would diverge between screens immediately.
RANDOM_COMMANDS = {"roll_dice", "record_initial_roll"}


@contextlib.contextmanager
def _forced_random_sequence(values):
    it = iter(values)
    original = random.randint

    def _fake(a, b):
        return next(it)

    random.randint = _fake
    try:
        yield
    finally:
        random.randint = original


def _send_msg(sock, obj):
    data = json.dumps(obj).encode("utf-8")
    sock.sendall(_HEADER.pack(len(data)) + data)


def _recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def _recv_msg(sock):
    header = _recv_exact(sock, _HEADER.size)
    if header is None:
        return None
    (length,) = _HEADER.unpack(header)
    data = _recv_exact(sock, length)
    if data is None:
        return None
    return json.loads(data.decode("utf-8"))


class Peer:
    """One connected client, as seen by the host."""

    def __init__(self, sock, addr, seat, incoming):
        self.sock = sock
        self.addr = addr
        self.seat = seat
        self.alive = True
        self._incoming = incoming
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self):
        try:
            while True:
                msg = _recv_msg(self.sock)
                if msg is None:
                    break
                msg["seat"] = self.seat
                self._incoming.put(msg)
        except OSError:
            pass
        finally:
            self.alive = False
            self._incoming.put({"type": "disconnect", "seat": self.seat})

    def send(self, obj):
        try:
            _send_msg(self.sock, obj)
        except OSError:
            self.alive = False

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class NetHost:
    """Listens for connections and routes framed JSON messages. Pure
    transport - seat assignment and command validation live one layer up
    (in the lobby / game glue code), not here."""

    def __init__(self, port):
        self.port = port
        self.incoming = queue.Queue()
        self.peers = {}  # seat -> Peer
        self._listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listen_sock.bind(("0.0.0.0", port))
        self._listen_sock.listen()
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()

    def _accept_loop(self):
        while True:
            try:
                sock, addr = self._listen_sock.accept()
            except OSError:
                return
            self.incoming.put({"type": "_new_connection", "_sock": sock, "_addr": addr})

    def assign_seat(self, sock, addr, seat):
        """Wrap a freshly-accepted socket (from a '_new_connection'
        message) as a seated Peer once the lobby decides which seat it
        controls."""
        peer = Peer(sock, addr, seat, self.incoming)
        self.peers[seat] = peer
        return peer

    def broadcast(self, obj, exclude_seat=None):
        for seat, peer in list(self.peers.items()):
            if seat != exclude_seat and peer.alive:
                peer.send(obj)

    def send_to(self, seat, obj):
        peer = self.peers.get(seat)
        if peer and peer.alive:
            peer.send(obj)

    def poll(self):
        """Drain and return every queued message since the last poll."""
        msgs = []
        while True:
            try:
                msgs.append(self.incoming.get_nowait())
            except queue.Empty:
                break
        return msgs

    def close(self):
        try:
            self._listen_sock.close()
        except OSError:
            pass
        for peer in self.peers.values():
            peer.close()


class NetClient:
    """Connects to a host and exchanges framed JSON messages."""

    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.incoming = queue.Queue()
        self.connected = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self):
        try:
            while True:
                msg = _recv_msg(self.sock)
                if msg is None:
                    break
                self.incoming.put(msg)
        except OSError:
            pass
        finally:
            self.connected = False
            self.incoming.put({"type": "disconnect"})

    def send(self, obj):
        try:
            _send_msg(self.sock, obj)
        except OSError:
            self.connected = False

    def poll(self):
        msgs = []
        while True:
            try:
                msgs.append(self.incoming.get_nowait())
            except queue.Empty:
                break
        return msgs

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def validate_command(engine, cmd, args, seat):
    """Host-side check that `seat` is allowed to issue this command right
    now: commands that name the acting player must be acting as
    themselves; commands that act on the engine's current player must
    come from whoever is actually on turn."""
    if cmd not in COMMANDS:
        return False
    if cmd == "set_player_count":
        return True  # lobby-only setup, not turn-gated
    if COMMANDS[cmd]:
        return bool(args) and args[0] == seat
    return engine.current_player == seat


def apply_command(engine, cmd, args, result=None):
    """Dispatch a networked command to the real GameEngine method of the
    same name. This is the entire protocol - no game logic is duplicated
    here. For the host's own local application, call with `result=None`
    (the method draws real randomness and its return value is what gets
    broadcast). For replay on any other peer, pass the `result` the host
    broadcast so roll_dice/record_initial_roll reach the identical
    outcome instead of drawing new random numbers."""
    if cmd not in COMMANDS:
        return None
    method = getattr(engine, cmd)
    if cmd in RANDOM_COMMANDS and result is not None:
        with _forced_random_sequence(result):
            return method(*args)
    return method(*args)
