"""In-game pause overlay.

Opened with the controller's Menu button or the P key.  Options:
    Resume              - back to the game
    Save & Quit to Menu - write savegame.json, return to the main menu
    Quit to Menu        - abandon the game, no save

Driven by either the mouse or controller intents (NAV / CONFIRM / CANCEL).
"""

import pygame
from Constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, BLACK, PANEL_BG, PANEL_BORDER,
)

OPTIONS = [
    ("resume", "Resume"),
    ("save_quit", "Save & Quit to Menu"),
    ("quit", "Quit to Menu"),
]


class PauseMenu:
    def __init__(self):
        self.title_font = pygame.font.SysFont("Arial", 36, bold=True)
        self.font = pygame.font.SysFont("Arial", 24, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 16, bold=False)

        self.selected = 0
        self.buttons = []          # [(action, Rect)] rebuilt each draw

    def reset(self):
        self.selected = 0

    # ------------------------------------------------------------------
    # INPUT
    # ------------------------------------------------------------------
    def move(self, delta):
        self.selected = (self.selected + delta) % len(OPTIONS)

    def current_action(self):
        return OPTIONS[self.selected][0]

    def handle_click(self, pos):
        """Return an action string if a button was hit, else None."""
        for i, (action, rect) in enumerate(self.buttons):
            if rect.collidepoint(pos):
                self.selected = i
                return action
        return None

    # ------------------------------------------------------------------
    # DRAW
    # ------------------------------------------------------------------
    def draw(self, screen):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        screen.blit(overlay, (0, 0))

        panel = pygame.Rect(0, 0, 460, 360)
        panel.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        pygame.draw.rect(screen, PANEL_BG, panel, border_radius=12)
        pygame.draw.rect(screen, PANEL_BORDER, panel, 2, border_radius=12)

        title = self.title_font.render("Paused", True, WHITE)
        screen.blit(title, title.get_rect(center=(panel.centerx, panel.y + 46)))

        self.buttons = []
        y = panel.y + 104
        for i, (action, label) in enumerate(OPTIONS):
            rect = pygame.Rect(panel.x + 50, y, panel.width - 100, 56)
            self.buttons.append((action, rect))

            focused = (i == self.selected)
            fill = (70, 110, 90) if focused else (70, 70, 70)
            pygame.draw.rect(screen, fill, rect, border_radius=8)
            if focused:
                pygame.draw.rect(screen, (255, 214, 10), rect, 3, border_radius=8)

            txt = self.font.render(label, True, WHITE)
            screen.blit(txt, txt.get_rect(center=rect.center))
            y += 70

        hint = self.small_font.render(
            "Stick / D-pad to move   -   A or click to choose   -   B / Menu to resume",
            True, (180, 180, 180))
        screen.blit(hint, hint.get_rect(center=(panel.centerx, panel.bottom - 26)))
