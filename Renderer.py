import pygame
from Constants import *

class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", TEXT_SIZE, bold=True)
        self.big_font = pygame.font.SysFont("Arial", 22, bold=True)

    def draw_player_selection(self):
        self.screen.fill(BG_COLOR)
        title = self.font.render("Select Number of Players", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - 140, SCREEN_HEIGHT // 2 - 100))
        for count, rect in SELECTION_BUTTONS.items():
            pygame.draw.rect(self.screen, GRAY, rect, border_radius=5)
            txt = self.font.render(str(count), True, WHITE)
            self.screen.blit(txt, (rect.centerx - 10, rect.centery - 12))

    def draw_background(self):
        self.screen.fill(BG_COLOR)
        bar_x = BOARD_START_X + BLOCK_WIDTH
        pygame.draw.rect(self.screen, BLACK, (bar_x, 0, MIDDLE_BAR, SCREEN_HEIGHT))

    def draw_points(self, board_logic):
        for i in range(24):
            final_x = board_logic.get_x_with_gap(i)
            base_y = BOARD_COORDS[i][1]
            color = BOARD_LIGHT if i % 2 == 0 else BOARD_DARK
            if i <= 11: pts = [(final_x - 40, base_y), (final_x + 40, base_y), (final_x, base_y + 300)]
            else: pts = [(final_x - 40, base_y), (final_x + 40, base_y), (final_x, base_y - 300)]
            pygame.draw.polygon(self.screen, color, pts)

    def draw_jail(self, engine):
        for p_id, count in engine.jail.items():
            if count > 0:
                color = PLAYER_COLORS[p_id]
                x, y = SCREEN_WIDTH // 2, 200 + (p_id * 60)
                pygame.draw.circle(self.screen, color, (x, y), PIECE_RADIUS)
                if count > 1:
                    txt = self.font.render(f"x{count}", True, WHITE)
                    self.screen.blit(txt, (x + 25, y - 10))

    def draw_player_pieces(self, engine, board_logic):
        for idx, occupants in enumerate(engine.board):
            counts = {}
            for p in occupants: counts[p] = counts.get(p, 0) + 1
            for p_id, count in counts.items():
                for s in range(min(count, MAX_VISUAL_STACK)):
                    pos = board_logic.get_piece_coordinates(idx, s)
                    pygame.draw.circle(self.screen, PLAYER_COLORS[p_id], pos, PIECE_RADIUS)
                    if s == MAX_VISUAL_STACK - 1 and count > MAX_VISUAL_STACK:
                        txt = self.font.render(f"x{count}", True, WHITE)
                        self.screen.blit(txt, (pos[0] - 10, pos[1] - 10))

    def draw_start_pools(self, engine):
        for p_id, count in engine.start_pool.items():
            if count > 0:
                x, y = START_AREAS[p_id]
                pygame.draw.circle(self.screen, PLAYER_COLORS[p_id], (x, y), 40, 2)
                txt = self.font.render(str(count), True, PLAYER_COLORS[p_id])
                self.screen.blit(txt, (x - 10, y - 10))

    def draw_ui(self, engine):
        if engine.current_player is None:
            return

        # 1. NEW: PROMINENT TURN INDICATOR
        turn_color = PLAYER_COLORS[engine.current_player]
        turn_text = f"PLAYER {engine.current_player}'S TURN"
        turn_surf = self.big_font.render(turn_text, True, turn_color)
        turn_rect = turn_surf.get_rect(center=(SCREEN_WIDTH // 2, 50))
        
        # Draw a subtle backing for the text
        bg_rect = turn_rect.inflate(40, 10)
        pygame.draw.rect(self.screen, (20, 20, 20), bg_rect, border_radius=5)
        self.screen.blit(turn_surf, turn_rect)

        # 2. HIGHLIGHT CURRENT PLAYER CORNER
        sx, sy = START_AREAS[engine.current_player]
        pygame.draw.circle(self.screen, turn_color, (sx, sy), 55, 3)

        # 3. REVISED BUTTON LOGIC
        if not engine.moves_available:
            label = "ROLL"
            button_color = (46, 204, 113) # Bright Green
        else:
            label = "PASS"
            button_color = (149, 165, 166) # Grey-ish
            
        pygame.draw.rect(self.screen, button_color, ROLL_BUTTON_RECT, border_radius=10)
        btn_text = self.font.render(label, True, BLACK)
        text_rect = btn_text.get_rect(center=ROLL_BUTTON_RECT.center)
        self.screen.blit(btn_text, text_rect)

        # 4. DICE & PHASE INFO
        dice_text = f"Moves: {engine.moves_available}" if engine.moves_available else "Roll the dice!"
        dice_surf = self.font.render(dice_text, True, WHITE)
        self.screen.blit(dice_surf, (SCREEN_WIDTH // 2 - 60, SCREEN_HEIGHT // 2 + 30))

        # Entry Requirement Warning
        if engine.start_pool.get(engine.current_player, 0) > 0:
            msg = self.font.render("MUST ENTER PIECES FROM START", True, (231, 76, 60))
            msg_rect = msg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60))
            self.screen.blit(msg, msg_rect)

    def draw_initial_winner_screen(self, engine):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        for p_id, roll in engine.player_rolls.items():
            txt = self.font.render(f"Player {p_id} rolled: {roll}", True, PLAYER_COLORS[p_id])
            self.screen.blit(txt, (SCREEN_WIDTH // 2 - 100, 150 + (p_id * 40)))
