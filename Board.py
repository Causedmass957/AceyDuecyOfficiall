from Constants import BOARD_COORDS, STACK_OFFSET, PIPE_HEIGHT, SCREEN_HEIGHT, PIPE_WIDTH, MARGIN_Y

class Board:
    def __init__(self):
        self.points = BOARD_COORDS # Dictionary of {index: (x, y)}

    def get_piece_coordinates(self, index, stack_index):
        """
        Calculates the (x, y) for a piece based on its position in a stack.
        index: 0-23
        stack_index: 0, 1, 2... (its position in the stack)
        """
        base_x, base_y = self.points[index]
        
        # Determine if we stack DOWN (top row) or UP (bottom row)
        # Top row is 0-11, Bottom row is 12-23
        direction = 1 if index <= 11 else -1
        
        offset_y = stack_index * STACK_OFFSET * direction
        return (base_x, base_y + offset_y)

    def is_top_row(self, index):
        return index <= 11
    
    def get_index_from_mouse(self, pos):
        """Returns the 0-23 index if a triangle was clicked, else None."""
        mx, my = pos
        for i, (bx, by) in self.points.items():
            # Check if mouse is within half a pipe-width of the center x
            if abs(mx - bx) < (PIPE_WIDTH // 2):
                # Check if it's in the top half or bottom half vertically
                if i <= 11 and my < PIPE_HEIGHT + MARGIN_Y:
                    return i
                elif i >= 12 and my > SCREEN_HEIGHT - PIPE_HEIGHT - MARGIN_Y:
                    return i
        return None