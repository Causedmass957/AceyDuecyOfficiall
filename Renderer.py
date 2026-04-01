import pygame
from Constants import *

class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", TEXT_SIZE, bold=True)

    def draw_background(self):
        self.screen.fill(BG_COLOR)
        # Bar is precisely after the first 6 triangles
        bar_x = BOARD_START_X + BLOCK_WIDTH
        pygame.draw.rect(self.screen, BLACK, (bar_x, 0, MIDDLE_BAR, SCREEN_HEIGHT))

    def draw_points(self, board_logic):
        for i in range(24):
            final_x = board_logic.get_x_with_gap(i)
            base_y = BOARD_COORDS[i][1]
            color = BOARD_LIGHT if i % 2 == 0 else BOARD_DARK
            
            # Triangle points
            if i <= 11: pts = [(final_x - 40, base_y), (final_x + 40, base_y), (final_x, base_y + 300)]
            else: pts = [(final_x - 40, base_y), (final_x + 40, base_y), (final_x, base_y - 300)]
            pygame.draw.polygon(self.screen, color, pts)

    def draw_jail(self, engine):
        # Center of the bar
        center_x = BOARD_START_X + BLOCK_WIDTH + (MIDDLE_BAR // 2)
        for p_id, count in engine.jail.items():
            if count <= 0: continue
            color = PLAYER_COLORS[p_id]
            base_y = (SCREEN_HEIGHT // 5) * p_id 
            
            if engine.selected_index == -1 and engine.current_player == p_id:
                pygame.draw.circle(self.screen, (255, 255, 0), (center_x, base_y), PIECE_RADIUS + 5, 3)

            pygame.draw.circle(self.screen, color, (center_x, base_y), PIECE_RADIUS)
            pygame.draw.circle(self.screen, (255,255,255), (center_x, base_y), PIECE_RADIUS, 2)

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
        # 1. Safety Check: Make sure there is actually a player active
        if engine.current_player is None:
            return

        # 2. Safety Check: Make sure the player exists in the pool dictionary
        if engine.current_player in engine.start_pool:
            if engine.start_pool[engine.current_player] > 0:
                # Use a slightly softer color for the "Must enter" message
                msg = self.font.render("Must enter all pieces from Start!", True, (200, 80, 80))
                # Position it near the bottom center
                msg_rect = msg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
                self.screen.blit(msg, msg_rect)
                
        # Draw current dice
        dice_text = f"Dice: {engine.moves_available}"
        dice_surf = self.font.render(dice_text, True, WHITE)
        self.screen.blit(dice_surf, (SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT - 80))

        status_text = f"Phase: {engine.phase} | Current Player: {engine.current_player}"
        surf = self.font.render(status_text, True, WHITE)
        self.screen.blit(surf, (20, SCREEN_HEIGHT - 40))
        
        if engine.start_pool[engine.current_player] > 0:
            msg = self.font.render("Must enter all pieces from Start!", True, (255, 100, 100))
            self.screen.blit(msg, (500, SCREEN_HEIGHT - 40))
    
    