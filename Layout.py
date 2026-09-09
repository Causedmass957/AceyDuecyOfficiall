"""Single source of truth for every on-screen coordinate.

Everything is drawn onto a fixed logical canvas (SCREEN_WIDTH x SCREEN_HEIGHT).
main.py scales that canvas to the real window, so fullscreen / resizing never
touches any of the maths here.

Board point indices (unchanged - the movement paths depend on them):
    0  = top-left corner        11 = top-right corner
    12 = bottom-right corner    23 = bottom-left corner
Top row 0..11 runs left -> right, bottom row 12..23 runs right -> left.
"""

import pygame
from Constants import SCREEN_WIDTH, SCREEN_HEIGHT


class Layout:
    # Reserved bands around the board (logical px).
    TOP_RESERVE = 92
    BOTTOM_RESERVE = 124
    SIDE_RESERVE = 28

    # Board proportions, measured in "units" (one unit = one point column width).
    #   width  = 6 columns + 1 bar + 6 columns          = 13 units
    #   height = triangle + centre gap + triangle
    TRI_UNITS = 3.35
    GAP_UNITS = 1.05

    def __init__(self, width=SCREEN_WIDTH, height=SCREEN_HEIGHT):
        self.recompute(width, height)

    # ------------------------------------------------------------------
    def recompute(self, width, height):
        self.w = width
        self.h = height

        avail_w = width - 2 * self.SIDE_RESERVE
        avail_h = height - self.TOP_RESERVE - self.BOTTOM_RESERVE

        board_units_w = 13.0
        board_units_h = 2 * self.TRI_UNITS + self.GAP_UNITS

        unit = min(avail_w / board_units_w, avail_h / board_units_h)

        self.unit = unit
        self.pipe_w = unit
        self.bar_w = unit
        self.tri_h = unit * self.TRI_UNITS

        self.board_w = unit * board_units_w
        self.board_h = unit * board_units_h
        self.board_left = self.SIDE_RESERVE + (avail_w - self.board_w) / 2
        self.board_top = self.TOP_RESERVE + (avail_h - self.board_h) / 2
        self.board_right = self.board_left + self.board_w
        self.board_bottom = self.board_top + self.board_h
        self.mid_y = self.board_top + self.board_h / 2

        self.bar_left = self.board_left + 6 * unit
        self.bar_right = self.bar_left + self.bar_w

        self.piece_r = unit * 0.38
        self.stack_step = self.piece_r * 1.8
        self.max_visual_stack = max(3, int((self.tri_h - self.piece_r) / self.stack_step))

        # Text rows for dice / move info, in the band below the board.
        self.status_line_y = self.board_bottom + 15
        self.hint_y = max(56, self.board_top - 22)

        self._build_widgets()

    # ------------------------------------------------------------------
    def _build_widgets(self):
        w, h = self.w, self.h

        chip_w = max(212, min(252, int(self.board_left) - self.SIDE_RESERVE + 130))
        chip_h = 46
        self.chip_rects = {
            1: pygame.Rect(14, 10, chip_w, chip_h),
            2: pygame.Rect(14, h - chip_h - 10, chip_w, chip_h),
            3: pygame.Rect(w - chip_w - 14, h - chip_h - 10, chip_w, chip_h),
            4: pygame.Rect(w - chip_w - 14, 10, chip_w, chip_h),
        }

        btn_y = h - 74
        self.roll_button = pygame.Rect(w // 2 - 66, btn_y, 132, 50)
        self.undo_button = pygame.Rect(w // 2 - 214, btn_y, 140, 50)
        self.history_button = pygame.Rect(w // 2 + 82, btn_y, 140, 50)
        self.rules_button = pygame.Rect(int(self.board_right) + 14, int(self.mid_y) - 26, 44, 52)
        if self.rules_button.right > w - 6:
            self.rules_button = pygame.Rect(w - 52, int(self.mid_y) - 26, 44, 52)

        cx = w // 2
        self.selection_buttons = {
            2: pygame.Rect(cx - 200, self.h // 2, 100, 60),
            3: pygame.Rect(cx - 50, self.h // 2, 100, 60),
            4: pygame.Rect(cx + 100, self.h // 2, 100, 60),
        }

    # ------------------------------------------------------------------
    # Board point geometry
    # ------------------------------------------------------------------
    def is_top(self, index):
        return index <= 11

    def _column(self, index):
        """0 (far left) .. 11 (far right) regardless of row."""
        return index if index <= 11 else 11 - (index - 12)

    def point_base_x(self, index):
        col = self._column(index)
        x = self.board_left + col * self.unit + self.unit / 2
        if col >= 6:
            x += self.bar_w
        return x

    def point_base_y(self, index):
        return self.board_top if self.is_top(index) else self.board_bottom

    def triangle(self, index):
        bx = self.point_base_x(index)
        by = self.point_base_y(index)
        half = self.pipe_w / 2 * 0.90
        if self.is_top(index):
            return [(bx - half, by), (bx + half, by), (bx, by + self.tri_h)]
        return [(bx - half, by), (bx + half, by), (bx, by - self.tri_h)]

    def piece_pos(self, index, stack_idx):
        bx = self.point_base_x(index)
        by = self.point_base_y(index)
        if self.is_top(index):
            return (bx, by + self.piece_r + stack_idx * self.stack_step)
        return (bx, by - self.piece_r - stack_idx * self.stack_step)

    # ------------------------------------------------------------------
    # Jail (centre bar)
    # ------------------------------------------------------------------
    def jail_pos(self, player_id, num_players):
        cx = (self.bar_left + self.bar_right) / 2
        span = self.board_h - 2 * self.piece_r - 24
        slot = (player_id - 0.5) / max(1, num_players)
        cy = self.board_top + self.piece_r + 12 + slot * span
        return (cx, cy)

    # ------------------------------------------------------------------
    # Hit testing
    # ------------------------------------------------------------------
    def click_target(self, pos):
        """Return -1 for the jail bar, 0..23 for a point, or None."""
        mx, my = pos

        if self.bar_left <= mx <= self.bar_right and self.board_top <= my <= self.board_bottom:
            return -1

        for i in range(24):
            bx = self.point_base_x(i)
            if abs(mx - bx) <= self.pipe_w / 2:
                if self.is_top(i):
                    if self.board_top <= my <= self.board_top + self.tri_h:
                        return i
                else:
                    if self.board_bottom - self.tri_h <= my <= self.board_bottom:
                        return i
        return None

    def chip_at(self, pos, player_id):
        rect = self.chip_rects.get(player_id)
        return bool(rect and rect.collidepoint(pos))
