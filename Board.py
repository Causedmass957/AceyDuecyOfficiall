from Constants import *

class Board:
    def __init__(self):
        self.points = BOARD_COORDS # Dictionary of {index: (x, y)}

    def get_x_with_gap(self, index):
        """Universal source of truth for X coordinates."""
        # BOARD_COORDS already contains MARGIN_X and MIDDLE_BAR jumps
        return BOARD_COORDS[index][0] + BOARD_START_X

    def get_piece_coordinates(self, index, stack_idx):
        final_x = self.get_x_with_gap(index)
        base_y = BOARD_COORDS[index][1]
        
        offset_y = stack_idx * (PIECE_RADIUS * 2)
        final_y = base_y + PIECE_RADIUS + offset_y if index <= 11 else base_y - PIECE_RADIUS - offset_y
        return (final_x, final_y)

    def get_index_from_mouse(self, pos):
        mx, my = pos
        # 1. Check Jail Hitbox (Center Bar)
        bar_start = BOARD_START_X + BLOCK_WIDTH
        if bar_start <= mx <= bar_start + MIDDLE_BAR:
            return -1

        # 2. Check Triangle Hitboxes
        for i in range(24):
            bx = self.get_x_with_gap(i)
            if abs(mx - bx) < (PIPE_WIDTH // 2):
                if i <= 11 and my < PIPE_HEIGHT + MARGIN_Y: return i
                elif i >= 12 and my > SCREEN_HEIGHT - (PIPE_HEIGHT + MARGIN_Y): return i
        return None

    def is_top_row(self, index):
        return index <= 11    
    
    