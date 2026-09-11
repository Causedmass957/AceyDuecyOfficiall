"""Xbox-style game controller support.

Two modes, switched by main.py per screen:

  CURSOR  (menus, settings, stats)
      The pad drives an on-screen virtual cursor and its buttons are
      translated into the mouse / keyboard events those screens already
      handle.  Synthetic mouse events are posted in REAL window
      coordinates so main.remap_event scales them back to canvas space.

  INTENT  (in-game, pause, rules)
      No cursor.  The pad emits high-level intent strings that main.py
      maps onto the game:

          NAV_PREV / NAV_NEXT ... cycle the highlighted piece / target
          CONFIRM  (A) .......... pick the highlight / confirm the move
          CANCEL   (B) .......... deselect / close overlay
          ACTION   (X) .......... Roll / Pass / End Turn
          HISTORY  (Y) .......... open the turn-log overlay
          RULES    (View) ....... open the rules
          PAUSE    (Menu) ....... open the pause menu
          UNDO     (LB) ......... take back the last move
"""

import pygame

# Xbox pad button numbers under SDL2 / pygame 2 (stable on Windows + Linux).
BTN_A = 0
BTN_B = 1
BTN_X = 2
BTN_Y = 3
BTN_LB = 4
BTN_RB = 5
BTN_VIEW = 6     # the small "back / select" button (two squares)
BTN_MENU = 7     # the small "start / menu" button (three lines)

DEADZONE = 0.35          # a bit high: this is a discrete nav stick, not a cursor
CURSOR_SPEED = 950.0     # canvas px / second at full deflection (CURSOR mode)
NAV_FIRST_MS = 360.0     # hold delay before the highlight starts repeating
NAV_REPEAT_MS = 150.0

_INTENT_BUTTONS = {
    BTN_A: "CONFIRM",
    BTN_B: "CANCEL",
    BTN_X: "ACTION",
    BTN_Y: "HISTORY",
    BTN_VIEW: "RULES",
    BTN_MENU: "PAUSE",
    BTN_LB: "UNDO",
}


class ControllerManager:
    def __init__(self, canvas_size):
        self.cw, self.ch = canvas_size
        self.mode = "CURSOR"

        # CURSOR-mode state
        self.cursor_x = self.cw / 2.0
        self.cursor_y = self.ch / 2.0
        self.transform = (1.0, 0, 0)
        self.visible = False

        # INTENT-mode state
        self._intents = []
        self._nav_dir = 0
        self._nav_repeat_at = 0.0
        self._clock = 0.0

        self.joysticks = {}
        pygame.joystick.init()
        for i in range(pygame.joystick.get_count()):
            self._add(i)

    # ------------------------------------------------------------------
    # Device management
    # ------------------------------------------------------------------
    def _add(self, index):
        try:
            js = pygame.joystick.Joystick(index)
            js.init()
        except pygame.error:
            return
        self.joysticks[js.get_instance_id()] = js

    def _remove(self, instance_id):
        self.joysticks.pop(instance_id, None)
        if not self.joysticks:
            self.visible = False

    def connected(self):
        return bool(self.joysticks)

    # ------------------------------------------------------------------
    # Wiring from main.py
    # ------------------------------------------------------------------
    def set_mode(self, mode):
        if mode != self.mode:
            self.mode = mode
            self._nav_dir = 0
            if mode == "INTENT":
                self.visible = False

    def set_transform(self, transform):
        if transform and transform[0] > 0:
            self.transform = transform

    def on_mouse_activity(self):
        self.visible = False

    def take_intents(self):
        out = self._intents
        self._intents = []
        return out

    # ------------------------------------------------------------------
    # Event translation
    # ------------------------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.JOYDEVICEADDED:
            self._add(event.device_index)
        elif event.type == pygame.JOYDEVICEREMOVED:
            self._remove(event.instance_id)
        elif event.type == pygame.JOYBUTTONDOWN:
            self._button(event.button)

    def _button(self, button):
        if self.mode == "INTENT":
            intent = _INTENT_BUTTONS.get(button)
            if intent:
                self._intents.append(intent)
            return

        # CURSOR mode -> mouse / keyboard
        self.visible = True
        if button == BTN_A:
            self._post_click()
        elif button in (BTN_B, BTN_VIEW, BTN_MENU):
            self._post_key(pygame.K_ESCAPE)
        elif button == BTN_LB:
            self._post_wheel(-1)
        elif button == BTN_RB:
            self._post_wheel(1)

    # ------------------------------------------------------------------
    # Per-frame polling
    # ------------------------------------------------------------------
    def update(self, dt):
        self._clock += dt
        if not self.joysticks:
            return
        if self.mode == "CURSOR":
            self._update_cursor(dt)
        else:
            self._update_nav()

    def _update_cursor(self, dt):
        dx = dy = 0.0
        for js in self.joysticks.values():
            ax, ay = self._stick(js, 0, 1)
            dx += ax
            dy += ay
            if js.get_numhats() > 0:
                hx, hy = js.get_hat(0)
                dx += hx
                dy -= hy
        dx = max(-1.0, min(1.0, dx))
        dy = max(-1.0, min(1.0, dy))
        if dx or dy:
            self.visible = True
            step = CURSOR_SPEED * dt / 1000.0
            self.cursor_x = max(0.0, min(float(self.cw), self.cursor_x + dx * step))
            self.cursor_y = max(0.0, min(float(self.ch), self.cursor_y + dy * step))

    def _update_nav(self):
        direction = self._read_nav_dir()

        if direction != self._nav_dir:
            self._nav_dir = direction
            if direction:
                self._emit_nav(direction)
                self._nav_repeat_at = self._clock + NAV_FIRST_MS
        elif direction and self._clock >= self._nav_repeat_at:
            self._emit_nav(direction)
            self._nav_repeat_at = self._clock + NAV_REPEAT_MS

    def _emit_nav(self, direction):
        self._intents.append("NAV_NEXT" if direction > 0 else "NAV_PREV")

    def _read_nav_dir(self):
        """Fold the left stick and D-pad into a single -1 / 0 / +1 step.
        Right / down = next, left / up = previous."""
        val_x = val_y = 0.0
        for js in self.joysticks.values():
            ax, ay = self._stick(js, 0, 1)
            val_x += ax
            val_y += ay
            if js.get_numhats() > 0:
                hx, hy = js.get_hat(0)
                val_x += hx
                val_y -= hy          # hat "up" is +1 -> previous
        val = val_x if abs(val_x) >= abs(val_y) else val_y
        if val > 0.5:
            return 1
        if val < -0.5:
            return -1
        return 0

    def _stick(self, js, ax_x, ax_y):
        try:
            x = js.get_axis(ax_x)
            y = js.get_axis(ax_y)
        except pygame.error:
            return 0.0, 0.0
        x = 0.0 if abs(x) < DEADZONE else x
        y = 0.0 if abs(y) < DEADZONE else y
        return x, y

    # ------------------------------------------------------------------
    # Synthetic events (CURSOR mode)
    # ------------------------------------------------------------------
    def _to_window(self, cx, cy):
        scale, ox, oy = self.transform
        if scale <= 0:
            return cx, cy
        return cx * scale + ox, cy * scale + oy

    def _post_click(self):
        wx, wy = self._to_window(self.cursor_x, self.cursor_y)
        pos = (int(wx), int(wy))
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1, "touch": False}))
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEBUTTONUP, {"pos": pos, "button": 1, "touch": False}))

    def _post_key(self, key):
        pygame.event.post(pygame.event.Event(
            pygame.KEYDOWN, {"key": key, "mod": 0, "unicode": "", "scancode": 0}))
        pygame.event.post(pygame.event.Event(
            pygame.KEYUP, {"key": key, "mod": 0, "unicode": "", "scancode": 0}))

    def _post_wheel(self, y):
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEWHEEL,
            {"x": 0, "y": y, "flipped": False, "which": 0,
             "precise_x": 0.0, "precise_y": float(y), "touch": False}))

    # ------------------------------------------------------------------
    # Rendering (CURSOR mode only)
    # ------------------------------------------------------------------
    def draw_cursor(self, canvas):
        if self.mode != "CURSOR" or not self.visible or not self.joysticks:
            return
        x, y = int(self.cursor_x), int(self.cursor_y)
        pygame.draw.circle(canvas, (0, 0, 0), (x, y), 11)
        pygame.draw.circle(canvas, (255, 255, 255), (x, y), 9)
        pygame.draw.circle(canvas, (0, 0, 0), (x, y), 3)
