"""
HOST_LOBBY / JOIN_LOBBY screens for online multiplayer.

HostLobbyScreen lets the hosting player pick a seat count, assign each
seat as "local" (played on this machine, hotseat-style) or leave it
"open" for a remote friend to connect into, and shows connections as
they arrive. JoinLobbyScreen lets a joining player type the host's
address and pick a display name, then waits for the host to start.

Both are mouse-driven only (no controller support yet) and follow the
visual style of PauseMenu.py / MenuManager.py.
"""
import pygame

from Constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, BLACK, GRAY, PANEL_BG, PANEL_BORDER,
    PLAYER_COLORS, BG_COLOR,
)

SEAT_MODE_LOCAL = "local"
SEAT_MODE_OPEN = "open"
SEAT_MODE_CONNECTING = "connecting"
SEAT_MODE_CONNECTED = "connected"


class HostLobbyScreen:
    def __init__(self, profile_manager, host_session):
        self.profile_manager = profile_manager
        self.host_session = host_session

        self.title_font = pygame.font.SysFont("Arial", 36, bold=True)
        self.font = pygame.font.SysFont("Arial", 22, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 16, bold=False)

        self.num_players = 2
        self.seat_mode = {}
        self.seat_name = {}
        self.local_profile_idx = {}
        self.error = ""

        self._apply_num_players(2)

        self.count_buttons = {}
        self.seat_rects = {}
        self.kick_rects = {}
        self.start_button = pygame.Rect(0, 0, 0, 0)
        self.back_button = pygame.Rect(0, 0, 0, 0)

    # ------------------------------------------------------------------
    # SEAT / PLAYER-COUNT MANAGEMENT
    # ------------------------------------------------------------------
    def _local_display_name(self, seat):
        profiles = self.profile_manager.get_all_profiles()
        idx = self.local_profile_idx.get(seat, 0)
        if profiles and idx < len(profiles):
            return profiles[idx]
        return f"Player {seat}"

    def _apply_num_players(self, n):
        old_mode = self.seat_mode
        for seat in list(self.seat_mode.keys()):
            if seat > n and self.seat_mode.get(seat) in (SEAT_MODE_CONNECTING, SEAT_MODE_CONNECTED):
                self.host_session.kick_seat(seat)

        self.num_players = n
        self.seat_mode = {}
        for seat in range(1, n + 1):
            if seat in old_mode:
                self.seat_mode[seat] = old_mode[seat]
            elif seat == 1:
                self.seat_mode[seat] = SEAT_MODE_LOCAL
                self.host_session.assign_local_seat(seat)
            else:
                self.seat_mode[seat] = SEAT_MODE_OPEN

    def set_num_players(self, n):
        if n != self.num_players:
            self._apply_num_players(n)

    def _toggle_seat(self, seat):
        mode = self.seat_mode.get(seat)
        if mode == SEAT_MODE_LOCAL:
            self.seat_mode[seat] = SEAT_MODE_OPEN
            self.host_session.unassign_local_seat(seat)
        elif mode == SEAT_MODE_OPEN:
            self.seat_mode[seat] = SEAT_MODE_LOCAL
            self.host_session.assign_local_seat(seat)
            if seat not in self.local_profile_idx:
                self.local_profile_idx[seat] = 0

    def _cycle_local_profile(self, seat):
        profiles = self.profile_manager.get_all_profiles()
        span = max(1, len(profiles))
        self.local_profile_idx[seat] = (self.local_profile_idx.get(seat, 0) + 1) % span

    def _next_open_seat(self):
        for seat in range(1, self.num_players + 1):
            if self.seat_mode.get(seat) == SEAT_MODE_OPEN:
                return seat
        return None

    def poll_net(self):
        for ev in self.host_session.poll_lobby():
            if ev["type"] == "new_connection":
                seat = self._next_open_seat()
                if seat is None:
                    try:
                        ev["sock"].close()
                    except OSError:
                        pass
                    continue
                self.seat_mode[seat] = SEAT_MODE_CONNECTING
                self.host_session.assign_remote_seat(ev["sock"], ev["addr"], seat)
                self.host_session.welcome(seat)
            elif ev["type"] == "join":
                seat = ev["seat"]
                if seat in self.seat_mode:
                    self.seat_mode[seat] = SEAT_MODE_CONNECTED
                    self.seat_name[seat] = ev["name"]
            elif ev["type"] == "disconnect":
                seat = ev["seat"]
                if seat in self.seat_mode and self.seat_mode[seat] in (SEAT_MODE_CONNECTING, SEAT_MODE_CONNECTED):
                    self.seat_mode[seat] = SEAT_MODE_OPEN
                    self.seat_name.pop(seat, None)

    def is_ready(self):
        return all(self.seat_mode.get(s) in (SEAT_MODE_LOCAL, SEAT_MODE_CONNECTED)
                   for s in range(1, self.num_players + 1))

    def player_profiles(self):
        profiles = {}
        for seat in range(1, self.num_players + 1):
            if self.seat_mode[seat] == SEAT_MODE_LOCAL:
                profiles[seat] = self._local_display_name(seat)
            else:
                profiles[seat] = self.seat_name.get(seat, f"Player {seat}")
        return profiles

    # ------------------------------------------------------------------
    # DRAW
    # ------------------------------------------------------------------
    def draw(self, screen):
        screen.fill(BG_COLOR)

        title = self.title_font.render("HOST GAME", True, WHITE)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 60)))

        addr_text = f"Your address:  {self.host_session.local_ip}:{self.host_session.port}"
        addr = self.font.render(addr_text, True, (255, 214, 10))
        screen.blit(addr, addr.get_rect(center=(SCREEN_WIDTH // 2, 105)))

        hint = self.small_font.render(
            "Same network: friends enter this address. Remote friends: use your Tailscale IP "
            "instead, same port.",
            True, (180, 180, 180))
        screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 132)))

        # ---- player count ----
        count_label = self.font.render("Players", True, WHITE)
        screen.blit(count_label, (SCREEN_WIDTH // 2 - 220, 175))

        self.count_buttons = {}
        x = SCREEN_WIDTH // 2 - 60
        for count in (2, 3, 4):
            rect = pygame.Rect(x, 165, 70, 46)
            self.count_buttons[count] = rect
            fill = PLAYER_COLORS[1] if count == self.num_players else GRAY
            pygame.draw.rect(screen, fill, rect, border_radius=8)
            txt = self.font.render(str(count), True, BLACK if count == self.num_players else WHITE)
            screen.blit(txt, txt.get_rect(center=rect.center))
            x += 82

        # ---- seat rows ----
        self.seat_rects = {}
        self.kick_rects = {}
        self.profile_chip_rects = {}
        row_h, gap = 64, 12
        top = 240
        panel_w = 640
        panel_x = SCREEN_WIDTH // 2 - panel_w // 2

        for i, seat in enumerate(range(1, self.num_players + 1)):
            rect = pygame.Rect(panel_x, top + i * (row_h + gap), panel_w, row_h)
            self.seat_rects[seat] = rect

            pygame.draw.rect(screen, (45, 45, 45), rect, border_radius=8)
            pygame.draw.rect(screen, PLAYER_COLORS[seat], rect, 3, border_radius=8)

            swatch = pygame.Rect(rect.x + 14, rect.y + 14, 36, 36)
            pygame.draw.rect(screen, PLAYER_COLORS[seat], swatch, border_radius=6)
            num_txt = self.font.render(str(seat), True, BLACK)
            screen.blit(num_txt, num_txt.get_rect(center=swatch.center))

            mode = self.seat_mode[seat]
            if mode == SEAT_MODE_LOCAL:
                label = "LOCAL"
                sub = "click row to make it Open  -  click name to change profile"
                color = WHITE
            elif mode == SEAT_MODE_OPEN:
                label = "OPEN  -  waiting for a player to join..."
                sub = "click to make this seat Local instead"
                color = (200, 200, 200)
            elif mode == SEAT_MODE_CONNECTING:
                label = "CONNECTING..."
                sub = ""
                color = (200, 200, 120)
            else:
                label = f"CONNECTED  -  {self.seat_name.get(seat, 'Guest')}"
                sub = "click X to disconnect this player"
                color = (140, 230, 160)

            txt = self.font.render(label, True, color)
            screen.blit(txt, (rect.x + 64, rect.y + 10))
            if sub:
                sub_txt = self.small_font.render(sub, True, (150, 150, 150))
                screen.blit(sub_txt, (rect.x + 64, rect.y + 36))

            if mode == SEAT_MODE_CONNECTED:
                kick_rect = pygame.Rect(rect.right - 46, rect.y + rect.height // 2 - 15, 30, 30)
                self.kick_rects[seat] = kick_rect
                pygame.draw.rect(screen, (150, 40, 40), kick_rect, border_radius=6)
                x_txt = self.font.render("X", True, WHITE)
                screen.blit(x_txt, x_txt.get_rect(center=kick_rect.center))
            elif mode == SEAT_MODE_LOCAL:
                # A separate clickable chip for the profile name, distinct
                # from clicking the rest of the row (which toggles Open) -
                # they used to be the same click target, which meant there
                # was no way to turn a Local seat back to Open.
                chip = pygame.Rect(rect.right - 180, rect.y + rect.height // 2 - 16, 166, 32)
                self.profile_chip_rects[seat] = chip
                pygame.draw.rect(screen, (60, 60, 60), chip, border_radius=6)
                pygame.draw.rect(screen, PLAYER_COLORS[seat], chip, 2, border_radius=6)
                name_txt = self.small_font.render(self._local_display_name(seat), True, WHITE)
                screen.blit(name_txt, name_txt.get_rect(center=chip.center))

        # ---- bottom buttons ----
        bottom_y = top + self.num_players * (row_h + gap) + 20
        self.back_button = pygame.Rect(panel_x, bottom_y, 180, 50)
        self.start_button = pygame.Rect(panel_x + panel_w - 220, bottom_y, 220, 50)

        pygame.draw.rect(screen, GRAY, self.back_button, border_radius=8)
        back_txt = self.font.render("Back", True, WHITE)
        screen.blit(back_txt, back_txt.get_rect(center=self.back_button.center))

        ready = self.is_ready()
        start_color = (46, 204, 113) if ready else GRAY
        pygame.draw.rect(screen, start_color, self.start_button, border_radius=8)
        start_txt = self.font.render("Start Game", True, BLACK if ready else (170, 170, 170))
        screen.blit(start_txt, start_txt.get_rect(center=self.start_button.center))

        if self.error:
            err = self.small_font.render(self.error, True, (231, 76, 60))
            screen.blit(err, err.get_rect(center=(SCREEN_WIDTH // 2, bottom_y + 70)))

    # ------------------------------------------------------------------
    # INPUT
    # ------------------------------------------------------------------
    def handle_click(self, pos):
        """Returns 'start', 'cancel', or None."""
        for count, rect in self.count_buttons.items():
            if rect.collidepoint(pos):
                self.set_num_players(count)
                return None

        for seat, kick_rect in self.kick_rects.items():
            if kick_rect.collidepoint(pos):
                self.host_session.kick_seat(seat)
                self.seat_mode[seat] = SEAT_MODE_OPEN
                self.seat_name.pop(seat, None)
                return None

        # Checked before the row-toggle below since the chip sits on top of
        # (a small area of) the Local row it belongs to.
        for seat, chip_rect in self.profile_chip_rects.items():
            if chip_rect.collidepoint(pos):
                self._cycle_local_profile(seat)
                return None

        for seat, rect in self.seat_rects.items():
            if rect.collidepoint(pos):
                if self.seat_mode[seat] in (SEAT_MODE_LOCAL, SEAT_MODE_OPEN):
                    self._toggle_seat(seat)
                return None

        if self.back_button.collidepoint(pos):
            return "cancel"

        if self.start_button.collidepoint(pos):
            if self.is_ready():
                return "start"
            self.error = "Every seat must be Local or Connected before starting."
        return None


class JoinLobbyScreen:
    def __init__(self, profile_manager):
        self.profile_manager = profile_manager

        self.title_font = pygame.font.SysFont("Arial", 36, bold=True)
        self.font = pygame.font.SysFont("Arial", 22, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 16, bold=False)

        self.address_text = ""
        self.input_active = False
        self.cursor_visible = True
        self.cursor_timer = 0

        self.name_idx = 0
        self.error = ""
        self.status = ""

        self.session = None  # ClientSession once Connect succeeds

        self.address_rect = pygame.Rect(SCREEN_WIDTH // 2 - 220, 200, 440, 50)
        self.name_rect = pygame.Rect(SCREEN_WIDTH // 2 - 220, 280, 440, 50)
        self.connect_button = pygame.Rect(SCREEN_WIDTH // 2 - 110, 360, 220, 50)
        self.back_button = pygame.Rect(40, SCREEN_HEIGHT - 80, 140, 50)

    def display_name(self):
        profiles = self.profile_manager.get_all_profiles()
        if profiles and self.name_idx < len(profiles):
            return profiles[self.name_idx]
        return "Guest"

    def update(self, dt):
        if self.input_active:
            self.cursor_timer += dt
            if self.cursor_timer >= 500:
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = 0
        else:
            self.cursor_visible = False

    def poll_net(self):
        """Returns 'start' once the host has begun the game, else None."""
        if self.session is None:
            return None
        for ev in self.session.poll_lobby():
            if ev["type"] == "welcome":
                self.status = f"Connected as Player {ev['seat']}. Waiting for host to start..."
            elif ev["type"] == "disconnect":
                self.error = "Lost connection to host."
                self.session = None
            elif ev["type"] == "start":
                return "start"
        return None

    def _try_connect(self):
        import NetSession

        raw = self.address_text.strip()
        if not raw:
            self.error = "Enter the host's address."
            return
        host, sep, port_str = raw.partition(":")
        if not host:
            self.error = f"Format is address or address:port (default port {NetSession.DEFAULT_PORT})."
            return
        if not sep:
            port = NetSession.DEFAULT_PORT
        else:
            try:
                port = int(port_str)
            except ValueError:
                self.error = "Port must be a number."
                return

        try:
            self.session = NetSession.ClientSession(host, port, self.display_name())
        except OSError as exc:
            self.error = f"Could not connect: {exc}"
            self.session = None
            return
        self.error = ""
        self.status = "Connecting..."

    def handle_keydown(self, event):
        if not self.input_active:
            return
        if event.key == pygame.K_BACKSPACE:
            self.address_text = self.address_text[:-1]
        elif event.key == pygame.K_RETURN:
            self.input_active = False
            self._try_connect()
        elif event.key == pygame.K_ESCAPE:
            self.input_active = False
        else:
            ch = event.unicode
            if ch.isprintable() and len(self.address_text) < 40:
                self.address_text += ch
        self.cursor_visible = True
        self.cursor_timer = 0

    def handle_click(self, pos):
        """Returns 'cancel' or None."""
        if self.session is not None:
            if self.back_button.collidepoint(pos):
                self.session.close()
                self.session = None
                return "cancel"
            return None

        if self.address_rect.collidepoint(pos):
            self.input_active = True
            return None
        self.input_active = False

        if self.name_rect.collidepoint(pos):
            profiles = self.profile_manager.get_all_profiles()
            span = max(1, len(profiles))
            self.name_idx = (self.name_idx + 1) % span
            return None

        if self.connect_button.collidepoint(pos):
            self._try_connect()
            return None

        if self.back_button.collidepoint(pos):
            return "cancel"
        return None

    def draw(self, screen):
        screen.fill(BG_COLOR)

        title = self.title_font.render("JOIN GAME", True, WHITE)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 90)))

        if self.session is None:
            label = self.font.render("Host address (address, or address:port)", True, WHITE)
            screen.blit(label, (self.address_rect.x, self.address_rect.y - 30))

            box_color = WHITE if self.input_active else (220, 220, 220)
            pygame.draw.rect(screen, box_color, self.address_rect, border_radius=6)
            pygame.draw.rect(screen, BLACK, self.address_rect, 2, border_radius=6)

            display_text = self.address_text
            if self.input_active and self.cursor_visible:
                display_text += "|"
            elif not display_text:
                display_text = "e.g. 192.168.1.20"

            text_color = BLACK if (self.address_text or self.input_active) else GRAY
            txt = self.font.render(display_text, True, text_color)
            screen.blit(txt, (self.address_rect.x + 12, self.address_rect.y + 12))

            name_label = self.font.render("Your name (click to change)", True, WHITE)
            screen.blit(name_label, (self.name_rect.x, self.name_rect.y - 30))
            pygame.draw.rect(screen, (60, 60, 60), self.name_rect, border_radius=6)
            pygame.draw.rect(screen, PLAYER_COLORS[1], self.name_rect, 2, border_radius=6)
            name_txt = self.font.render(self.display_name(), True, WHITE)
            screen.blit(name_txt, name_txt.get_rect(center=self.name_rect.center))

            pygame.draw.rect(screen, (46, 120, 200), self.connect_button, border_radius=8)
            connect_txt = self.font.render("Connect", True, WHITE)
            screen.blit(connect_txt, connect_txt.get_rect(center=self.connect_button.center))

            if self.error:
                err = self.small_font.render(self.error, True, (231, 76, 60))
                screen.blit(err, err.get_rect(center=(SCREEN_WIDTH // 2, 440)))
        else:
            status = self.font.render(self.status, True, (140, 230, 160))
            screen.blit(status, status.get_rect(center=(SCREEN_WIDTH // 2, 240)))
            if self.error:
                err = self.small_font.render(self.error, True, (231, 76, 60))
                screen.blit(err, err.get_rect(center=(SCREEN_WIDTH // 2, 280)))

        pygame.draw.rect(screen, GRAY, self.back_button, border_radius=8)
        back_txt = self.font.render("Back", True, WHITE)
        screen.blit(back_txt, back_txt.get_rect(center=self.back_button.center))
