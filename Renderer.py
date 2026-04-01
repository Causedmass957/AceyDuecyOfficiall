import pygame
from Constants import *

class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", TEXT_SIZE, bold=True)

    def draw_background(self):
        self.screen.fill(BG_COLOR)
        pygame.draw.rect(self.screen, BLACK, (SCREEN_WIDTH//2 - MIDDLE_BAR//2, 0, MIDDLE_BAR, SCREEN_HEIGHT))

    def draw_points(self):
        for i in range(24):
            base_x, base_y = BOARD_COORDS[i]
            color = BOARD_LIGHT if i % 2 == 0 else BOARD_DARK
            if i <= 11:
                pts = [(base_x - PIPE_WIDTH//2, base_y), (base_x + PIPE_WIDTH//2, base_y), (base_x, base_y + PIPE_HEIGHT)]
            else:
                pts = [(base_x - PIPE_WIDTH//2, base_y), (base_x + PIPE_WIDTH//2, base_y), (base_x, base_y - PIPE_HEIGHT)]
            pygame.draw.polygon(self.screen, color, pts)

    def draw_player_pieces(self, engine, board_logic):
        """
        Pass the WHOLE engine so we can check engine.selected_index
        """
        for i, occupants in enumerate(engine.board):
            if not occupants:
                continue
            
            player_id = occupants[0]
            count = len(occupants)
            color = PLAYER_COLORS[player_id]
            display_count = min(count, MAX_VISUAL_STACK)
            
            for stack_idx in range(display_count):
                pos = board_logic.get_piece_coordinates(i, stack_idx)
                
                # --- FIXED SELECTION GLOW ---
                # We check if this specific triangle (i) is what the engine has selected
                if engine.selected_index == i and stack_idx == display_count - 1:
                    pygame.draw.circle(self.screen, (255, 255, 0), pos, PIECE_RADIUS + 5, 3)

                pygame.draw.circle(self.screen, color, pos, PIECE_RADIUS)
                pygame.draw.circle(self.screen, WHITE, pos, PIECE_RADIUS, 2)

            if count > MAX_VISUAL_STACK:
                text_surf = self.font.render(f"{count}", True, WHITE)
                last_pos = board_logic.get_piece_coordinates(i, display_count - 1)
                text_rect = text_surf.get_rect(center=last_pos)
                self.screen.blit(text_surf, text_rect)

    def draw_start_pools(self, engine):
        """Move this INSIDE the class and indent it!"""
        for p_id, count in engine.start_pool.items():
            if count <= 0: continue
            
            base_x, base_y = START_AREAS[p_id]
            color = PLAYER_COLORS[p_id]
            
            # Draw Selection Glow for Start Pool
            if engine.selected_index == -2 and engine.current_player == p_id:
                pygame.draw.circle(self.screen, (255, 255, 0), (base_x, base_y), PIECE_RADIUS + 10, 3)

            display_count = min(count, 3)
            for i in range(display_count):
                pos = (base_x, base_y + (i * 10))
                pygame.draw.circle(self.screen, color, pos, PIECE_RADIUS)
                pygame.draw.circle(self.screen, WHITE, pos, PIECE_RADIUS, 2)
            
            if count > 1:
                text_surf = self.font.render(f"{count}", True, WHITE)
                self.screen.blit(text_surf, (base_x - 10, base_y - 30))

    def draw_ui(self, engine):
        # Draw current dice
        dice_text = f"Dice: {engine.moves_available}"
        dice_surf = self.font.render(dice_text, True, WHITE)
        self.screen.blit(dice_surf, (SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT - 80))

        status_text = f"Phase: {engine.phase} | Current Player: {engine.current_player}"
        surf = self.font.render(status_text, True, WHITE)
        self.screen.blit(surf, (20, SCREEN_HEIGHT - 40))