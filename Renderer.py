import pygame
from Constants import *


class Renderer:
    def __init__(self, screen):
        # ============================================================
        # CORE SCREEN / FONT SETUP
        # Stores the pygame surface and fonts used throughout the UI
        # ============================================================
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", TEXT_SIZE, bold=True)
        self.big_font = pygame.font.SysFont("Arial", 22, bold=True)

    # ============================================================
    # HELPER: SAFE PLAYER DISPLAY NAME LOOKUP
    # Uses profile names when available, otherwise falls back to Player X
    # ============================================================
    def _get_player_name(self, engine, player_id):
        if hasattr(engine, "get_player_name"):
            return engine.get_player_name(player_id)
        return f"Player {player_id}"

    # ============================================================
    # MAIN MENU / PLAYER COUNT SCREEN DRAWING
    # Old in-game player selection screen, still available if needed
    # ============================================================
    def draw_player_selection(self):
        self.screen.fill(BG_COLOR)

        title = self.font.render("Select Number of Players", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - 140, SCREEN_HEIGHT // 2 - 100))

        for count, rect in SELECTION_BUTTONS.items():
            pygame.draw.rect(self.screen, GRAY, rect, border_radius=5)

            txt = self.font.render(str(count), True, WHITE)
            self.screen.blit(txt, (rect.centerx - 10, rect.centery - 12))

    # ============================================================
    # BOARD BACKGROUND DRAWING
    # Draws the wooden background and the central jail bar
    # ============================================================
    def draw_background(self):
        self.screen.fill(BG_COLOR)

        bar_x = BOARD_START_X + BLOCK_WIDTH
        pygame.draw.rect(self.screen, BLACK, (bar_x, 0, MIDDLE_BAR, SCREEN_HEIGHT))

    # ============================================================
    # TRIANGLE / POINT DRAWING
    # Draws the 24 board points using board coordinate logic
    # ============================================================
    def draw_points(self, board_logic):
        for i in range(24):
            final_x = board_logic.get_x_with_gap(i)
            base_y = BOARD_COORDS[i][1]
            color = BOARD_LIGHT if i % 2 == 0 else BOARD_DARK

            if i <= 11:
                pts = [
                    (final_x - 40, base_y),
                    (final_x + 40, base_y),
                    (final_x, base_y + 300)
                ]
            else:
                pts = [
                    (final_x - 40, base_y),
                    (final_x + 40, base_y),
                    (final_x, base_y - 300)
                ]

            pygame.draw.polygon(self.screen, color, pts)

    # ============================================================
    # JAIL DISPLAY DRAWING
    # Draws jailed pieces in the center bar and highlights selected jail
    # ============================================================
    def draw_jail(self, engine):
        for p_id, count in engine.jail.items():
            if count > 0:
                color = PLAYER_COLORS[p_id]
                x, y = SCREEN_WIDTH // 2, 200 + (p_id * 60)

                pygame.draw.circle(self.screen, color, (x, y), PIECE_RADIUS)

                # Highlight selected jail checker for current player
                if engine.selected_index == -1 and engine.current_player == p_id:
                    pygame.draw.circle(self.screen, WHITE, (x, y), PIECE_RADIUS + 6, 3)

                if count > 1:
                    txt = self.font.render(f"x{count}", True, WHITE)
                    self.screen.blit(txt, (x + 25, y - 10))

                # Optional player/profile name beside jail stack
                player_name = self._get_player_name(engine, p_id)
                name_txt = self.small_label(player_name, color)
                self.screen.blit(name_txt, (x - 90, y - 12))

    # ============================================================
    # BOARD CHECKER DRAWING
    # Draws all pieces currently on board points and selected highlights
    # ============================================================
    def draw_player_pieces(self, engine, board_logic):
        for idx, occupants in enumerate(engine.board):
            counts = {}
            for p in occupants:
                counts[p] = counts.get(p, 0) + 1

            for p_id, count in counts.items():
                for s in range(min(count, MAX_VISUAL_STACK)):
                    pos = board_logic.get_piece_coordinates(idx, s)

                    # Draw checker
                    pygame.draw.circle(self.screen, PLAYER_COLORS[p_id], pos, PIECE_RADIUS)

                    # Highlight selected point for current player
                    if idx == engine.selected_index and p_id == engine.current_player:
                        pygame.draw.circle(self.screen, WHITE, pos, PIECE_RADIUS + 6, 3)

                    # Draw stack count if stack is larger than visual limit
                    if s == MAX_VISUAL_STACK - 1 and count > MAX_VISUAL_STACK:
                        txt = self.font.render(f"x{count}", True, WHITE)
                        self.screen.blit(txt, (pos[0] - 10, pos[1] - 10))

    # ============================================================
    # START POOL DRAWING
    # Draws each player's remaining start pool and selection highlight
    # ============================================================
    def draw_start_pools(self, engine):
        for p_id, count in engine.start_pool.items():
            if count > 0:
                x, y = START_AREAS[p_id]

                pygame.draw.circle(self.screen, PLAYER_COLORS[p_id], (x, y), 40, 2)

                # Highlight selected start pool
                if engine.selected_index == -2 and engine.current_player == p_id:
                    pygame.draw.circle(self.screen, WHITE, (x, y), 48, 3)

                txt = self.font.render(str(count), True, PLAYER_COLORS[p_id])
                self.screen.blit(txt, (x - 10, y - 10))

    # ============================================================
    # IN-GAME UI DRAWING
    # Draws turn banner, current player name, button, move text, and hints
    # ============================================================
    def draw_ui(self, engine):
        if engine.current_player is None:
            return

        # ----------------------------
        # Current turn banner
        # ----------------------------
        turn_color = PLAYER_COLORS[engine.current_player]
        player_name = self._get_player_name(engine, engine.current_player)
        turn_text = f"{player_name}'s Turn"

        turn_surf = self.big_font.render(turn_text, True, turn_color)
        turn_rect = turn_surf.get_rect(center=(SCREEN_WIDTH // 2, 50))

        bg_rect = turn_rect.inflate(40, 10)
        pygame.draw.rect(self.screen, (20, 20, 20), bg_rect, border_radius=5)
        self.screen.blit(turn_surf, turn_rect)

        # ----------------------------
        # Current player corner highlight
        # ----------------------------
        sx, sy = START_AREAS[engine.current_player]
        pygame.draw.circle(self.screen, turn_color, (sx, sy), 55, 3)

        # ----------------------------
        # Roll / Pass button
        # ----------------------------
        if not engine.moves_available:
            label = "ROLL"
            button_color = (46, 204, 113)
        else:
            label = "PASS"
            button_color = (149, 165, 166)

        pygame.draw.rect(self.screen, button_color, ROLL_BUTTON_RECT, border_radius=10)

        btn_text = self.font.render(label, True, BLACK)
        text_rect = btn_text.get_rect(center=ROLL_BUTTON_RECT.center)
        self.screen.blit(btn_text, text_rect)

        # ----------------------------
        # Moves / dice display at bottom
        # ----------------------------
        dice_text = f"Moves: {engine.moves_available}" if engine.moves_available else "Roll the dice!"
        dice_surf = self.font.render(dice_text, True, WHITE)
        dice_rect = dice_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 95))
        self.screen.blit(dice_surf, dice_rect)

        # ----------------------------
        # Selected piece/status readout
        # ----------------------------
        if engine.selected_index is not None:
            if engine.selected_index == -2:
                sel_text = "Selected: START"
            elif engine.selected_index == -1:
                sel_text = "Selected: JAIL"
            else:
                sel_text = f"Selected: POINT {engine.selected_index}"

            sel_surf = self.font.render(sel_text, True, WHITE)
            self.screen.blit(sel_surf, (40, SCREEN_HEIGHT - 100))

        # ----------------------------
        # Start-pool rule reminder
        # ----------------------------
        if engine.start_pool.get(engine.current_player, 0) > 0:
            msg = self.font.render("MUST ENTER PIECES FROM START", True, (231, 76, 60))
            msg_rect = msg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 130))
            self.screen.blit(msg, msg_rect)

    # ============================================================
    # INITIAL ROLL WINNER SCREEN
    # Shows initial roll totals using saved profile names
    # ============================================================
    def draw_initial_winner_screen(self, engine):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        title = self.big_font.render("Initial Roll Results", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 100)))

        y = 170
        for p_id, roll in engine.player_rolls.items():
            player_name = self._get_player_name(engine, p_id)
            txt = self.font.render(f"{player_name} rolled: {roll}", True, PLAYER_COLORS[p_id])
            self.screen.blit(txt, (SCREEN_WIDTH // 2 - 160, y))
            y += 45

    # ============================================================
    # SMALL TEXT HELPER
    # Convenience method for small labels like jail names
    # ============================================================
    def small_label(self, text, color):
        return self.small_font().render(text, True, color)

    # ============================================================
    # SMALL FONT HELPER
    # Creates a smaller font on demand for compact labels
    # ============================================================
    def small_font(self):
        return pygame.font.SysFont("Arial", 16, bold=False)