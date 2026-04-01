from Constants import *

class Board:
    def __init__(self):
        self.points = BOARD_COORDS # Dictionary of {index: (x, y)}

    def get_index_from_mouse(self, pos):
        """Returns the 0-23 index if a triangle was clicked, else None."""
        mx, my = pos
        for i in range(24):
            # USE THE UNIVERSAL X FOR HITBOXES
            bx = self.get_x_with_gap(i)
            
            # Check if mouse is within half a pipe-width of the calculated center x
            if abs(mx - bx) < (PIPE_WIDTH // 2):
                # Vertical check: Top row vs Bottom row
                if i <= 11 and my < PIPE_HEIGHT + MARGIN_Y:
                    return i
                elif i >= 12 and my > SCREEN_HEIGHT - PIPE_HEIGHT - MARGIN_Y:
                    return i
        return None

    def get_piece_coordinates(self, index, stack_idx):
        # Use the universal helper to ensure pieces align with triangles
        final_x = self.get_x_with_gap(index)
        
        base_y = BOARD_COORDS[index][1]
        offset_y = stack_idx * (PIECE_RADIUS * 2)
        
        if index <= 11:
            final_y = base_y + PIECE_RADIUS + offset_y
        else:
            final_y = base_y - PIECE_RADIUS - offset_y
            
        return (final_x, final_y)

    def is_top_row(self, index):
        return index <= 11    
    
    def get_x_with_gap(self, index):
        """
        Calculates the X coordinate for any triangle or piece.
        This is the 'Source of Truth'.
        """
        # 1. Start with the raw base coordinate from your list
        base_x = BOARD_COORDS[index][0]
        
        # 2. Add the global centering offset
        x = base_x + HORIZONTAL_OFFSET
        
        # 3. Add the gap if it's on the right half
        # (Using 6-17 as the right-side indices)
        if 6 <= index <= 17:
            x += MIDDLE_BAR_WIDTH
            
        return x