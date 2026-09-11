"""Statistics screen reached from the main menu.

Two views:
  LIST    - every saved profile with a one-line win/loss summary
  DETAIL  - a single profile's full stat breakdown plus head-to-head record

Drawn onto the shared logical canvas like every other screen; main.py routes
mouse / keyboard (and, via Controller.py, the game pad) events in here.
"""

import pygame
from Constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BG_COLOR, WHITE, GRAY, BLACK,
    PANEL_BG, PANEL_BORDER, PLAYER_COLORS,
)


# (stat column, label) in the order they should appear on the detail screen.
STAT_DISPLAY = [
    ("wins", "Wins"),
    ("losses", "Losses"),
    ("second_place", "2nd place"),
    ("third_place", "3rd place"),
    ("fourth_place", "4th place"),
    ("times_skunked", "Times skunked"),
    ("biggest_win_margin", "Biggest win margin"),
    ("total_turns", "Total turns"),
    ("moves_made", "Moves made"),
    ("pieces_entered_from_start", "Entered from start"),
    ("pieces_scored", "Checkers borne off"),
    ("captures", "Opponents hit"),
    ("times_sent_to_jail", "Sent to jail"),
    ("times_jailed", "Times jailed"),
    ("jail_exits", "Jail breaks"),
    ("doubles_rolled", "Doubles rolled"),
    ("acey_duecy_rolls", "Acey-Deucey rolls"),
    ("bonus_rolls_earned", "Bonus rolls earned"),
    ("bonus_rolls_forfeited", "Bonus rolls forfeited"),
    ("times_blocked", "Turns blocked"),
    ("longest_block_zone_created", "Longest block zone"),
    ("block_zones_created_7_plus", "7+ block zones built"),
    ("block_zones_faced_7_plus", "7+ block zones faced"),
]


class StatsMenu:
    def __init__(self, profile_manager):
        self.profile_manager = profile_manager

        self.title_font = pygame.font.SysFont("Arial", 38, bold=True)
        self.header_font = pygame.font.SysFont("Arial", 26, bold=True)
        self.font = pygame.font.SysFont("Arial", 22, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 18, bold=False)

        self.state = "LIST"           # LIST | DETAIL
        self.selected_name = None
        self.scroll = 0

        self.names = []
        self.row_rects = []           # [(name, Rect)] rebuilt every draw

        self.back_button = pygame.Rect(40, SCREEN_HEIGHT - 74, 150, 48)

    # ------------------------------------------------------------------
    # Called by main.py when the screen is opened
    # ------------------------------------------------------------------
    def reset(self):
        self.state = "LIST"
        self.selected_name = None
        self.scroll = 0
        self._refresh()

    def _refresh(self):
        self.names = self.profile_manager.get_all_profiles()

    # ------------------------------------------------------------------
    # INPUT
    # ------------------------------------------------------------------
    def handle_click(self, pos):
        """Return "close" when the screen should hand control back to the menu."""
        if self.back_button.collidepoint(pos):
            if self.state == "DETAIL":
                self.state = "LIST"
                self.scroll = 0
                return None
            return "close"

        if self.state == "LIST":
            for name, rect in self.row_rects:
                if rect.collidepoint(pos):
                    self.selected_name = name
                    self.state = "DETAIL"
                    self.scroll = 0
                    return None

        return None

    def go_back(self):
        """Esc / B button.  Return True if handled internally."""
        if self.state == "DETAIL":
            self.state = "LIST"
            self.scroll = 0
            return True
        return False

    def scroll_by(self, dy):
        if self.state == "DETAIL":
            self.scroll = max(0, min(self._max_scroll, self.scroll - dy))

    # ------------------------------------------------------------------
    # DRAW
    # ------------------------------------------------------------------
    def draw(self, screen):
        screen.fill(BG_COLOR)
        title = self.title_font.render("STATISTICS", True, WHITE)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 54)))

        if self.state == "DETAIL" and self.selected_name:
            self._draw_detail(screen)
        else:
            self._draw_list(screen)

        pygame.draw.rect(screen, GRAY, self.back_button, border_radius=8)
        label = "Back" if self.state == "LIST" else "< Profiles"
        btxt = self.font.render(label, True, WHITE)
        screen.blit(btxt, btxt.get_rect(center=self.back_button.center))

    def _draw_list(self, screen):
        self.row_rects = []

        if not self.names:
            msg = self.font.render("No profiles yet - create one from New Game.", True, WHITE)
            screen.blit(msg, msg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
            return

        hint = self.small_font.render("Click a profile for the full breakdown.", True, (190, 190, 190))
        screen.blit(hint, (SCREEN_WIDTH // 2 - 300, 100))

        y = 132
        for name in self.names[:9]:
            rect = pygame.Rect(SCREEN_WIDTH // 2 - 300, y, 600, 58)
            self.row_rects.append((name, rect))

            pygame.draw.rect(screen, PANEL_BG, rect, border_radius=8)
            pygame.draw.rect(screen, PANEL_BORDER, rect, 1, border_radius=8)

            profile = self.profile_manager.get_profile(name) or {}
            games = profile.get("games_played", 0)
            wins = profile.get("wins", 0)
            losses = profile.get("losses", 0)
            win_rate = self.profile_manager.get_win_rate(name)

            screen.blit(self.header_font.render(name, True, WHITE), (rect.x + 16, rect.y + 6))
            noun = "game" if games == 1 else "games"
            summary = f"{games} {noun}   {wins}W - {losses}L   {win_rate:g}% win rate"
            screen.blit(self.small_font.render(summary, True, (200, 200, 200)),
                        (rect.x + 16, rect.y + 34))
            y += 66

    def _draw_detail(self, screen):
        name = self.selected_name
        profile = self.profile_manager.get_profile(name)

        if not profile:
            msg = self.font.render("That profile no longer exists.", True, WHITE)
            screen.blit(msg, msg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
            self._max_scroll = 0
            return

        games = profile.get("games_played", 0)
        win_rate = self.profile_manager.get_win_rate(name)

        noun = "game" if games == 1 else "games"
        screen.blit(self.header_font.render(name, True, WHITE), (80, 96))
        screen.blit(self.small_font.render(
            f"{games} {noun} played   -   {win_rate:g}% win rate", True, (200, 200, 200)),
            (80, 128))

        panel = pygame.Rect(60, 160, SCREEN_WIDTH - 120, SCREEN_HEIGHT - 250)
        pygame.draw.rect(screen, PANEL_BG, panel, border_radius=10)
        pygame.draw.rect(screen, PANEL_BORDER, panel, 1, border_radius=10)
        prev_clip = screen.get_clip()
        screen.set_clip(panel)

        line_h = 30
        col_x = (panel.x + 30, panel.x + panel.width // 2 + 10)
        rows_per_col = (len(STAT_DISPLAY) + 1) // 2
        top = panel.y + 20 - self.scroll

        for i, (key, label) in enumerate(STAT_DISPLAY):
            cx = col_x[i // rows_per_col]
            ry = top + (i % rows_per_col) * line_h
            value = profile.get(key, 0)
            screen.blit(self.font.render(label, True, (210, 210, 210)), (cx, ry))
            vsurf = self.font.render(str(value), True, WHITE)
            screen.blit(vsurf, vsurf.get_rect(topright=(cx + panel.width // 2 - 70, ry)))

        h2h_y = top + rows_per_col * line_h + 16
        h2h = self.profile_manager.get_head_to_head(name)
        screen.blit(self.header_font.render("Head-to-head", True, WHITE), (panel.x + 30, h2h_y))
        h2h_y += 36
        if not h2h:
            screen.blit(self.small_font.render("No recorded matchups yet.", True, (180, 180, 180)),
                        (panel.x + 30, h2h_y))
            h2h_y += 26
        else:
            for entry in h2h:
                text = f"vs {entry['opponent']}:  {entry['wins']}W - {entry['losses']}L"
                screen.blit(self.font.render(text, True, (210, 210, 210)), (panel.x + 30, h2h_y))
                h2h_y += line_h

        screen.set_clip(prev_clip)

        content_bottom = h2h_y + self.scroll
        self._max_scroll = max(0, int(content_bottom - (panel.bottom - 20)))

    # Fallback so scroll clamping works before the first detail draw.
    _max_scroll = 0
