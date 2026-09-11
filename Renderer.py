import pygame
from Constants import *


class Renderer:
    def __init__(self, screen, layout):
        self.screen = screen
        self.layout = layout

        self.font = pygame.font.SysFont("Arial", TEXT_SIZE, bold=True)
        self.big_font = pygame.font.SysFont("Arial", 22, bold=True)
        self.chip_font = pygame.font.SysFont("Arial", 15, bold=True)
        self.chip_small_font = pygame.font.SysFont("Arial", 13, bold=False)
        self.mono_font = pygame.font.SysFont("Consolas", 15)
        self.title_font = pygame.font.SysFont("Arial", 34, bold=True)

        self.history_scroll = 0

    def set_layout(self, layout):
        self.layout = layout

    # ============================================================
    # HELPERS
    # ============================================================
    def _get_player_name(self, engine, player_id):
        if hasattr(engine, "get_player_name"):
            return engine.get_player_name(player_id)
        return f"Player {player_id}"

    def small_font(self):
        return pygame.font.SysFont("Arial", 16, bold=False)

    def small_label(self, text, color):
        return self.small_font().render(text, True, color)

    def _clip_text(self, text, font, max_width):
        if font.size(text)[0] <= max_width:
            return text
        while text and font.size(text + "...")[0] > max_width:
            text = text[:-1]
        return text + "..."

    # ============================================================
    # PLAYER COUNT SCREEN (legacy fallback)
    # ============================================================
    def draw_player_selection(self):
        self.screen.fill(BG_COLOR)
        title = self.font.render("Select Number of Players", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 90)))
        for count, rect in self.layout.selection_buttons.items():
            pygame.draw.rect(self.screen, GRAY, rect, border_radius=6)
            txt = self.font.render(str(count), True, WHITE)
            self.screen.blit(txt, txt.get_rect(center=rect.center))

    # ============================================================
    # BOARD
    # ============================================================
    def draw_background(self):
        lay = self.layout
        self.screen.fill(BG_COLOR)

        frame = pygame.Rect(lay.board_left - 16, lay.board_top - 16,
                            lay.board_w + 32, lay.board_h + 32)
        pygame.draw.rect(self.screen, BOARD_FRAME, frame, border_radius=12)

        felt = pygame.Rect(lay.board_left, lay.board_top, lay.board_w, lay.board_h)
        pygame.draw.rect(self.screen, BOARD_FELT, felt)

        bar = pygame.Rect(lay.bar_left, lay.board_top, lay.bar_w, lay.board_h)
        pygame.draw.rect(self.screen, BAR_COLOR, bar)
        pygame.draw.rect(self.screen, BOARD_FRAME, felt, 3)

    def draw_points(self, _=None):
        lay = self.layout
        for i in range(24):
            color = BOARD_LIGHT if (i % 2 == 0) else BOARD_DARK
            pygame.draw.polygon(self.screen, color, lay.triangle(i))
            pygame.draw.polygon(self.screen, (0, 0, 0), lay.triangle(i), 1)

    def draw_jail(self, engine):
        lay = self.layout
        for p_id, count in engine.jail.items():
            if count <= 0:
                continue
            color = PLAYER_COLORS[p_id]
            x, y = lay.jail_pos(p_id, engine.num_players)
            pygame.draw.circle(self.screen, color, (x, y), lay.piece_r)
            pygame.draw.circle(self.screen, WHITE, (x, y), lay.piece_r, 1)
            if engine.selected_index == -1 and engine.current_player == p_id:
                pygame.draw.circle(self.screen, WHITE, (x, y), lay.piece_r + 5, 3)
            if count > 1:
                txt = self.chip_font.render(f"x{count}", True, WHITE)
                self.screen.blit(txt, txt.get_rect(midleft=(x + lay.piece_r + 4, y)))

    def draw_player_pieces(self, engine, _=None):
        lay = self.layout
        r = lay.piece_r
        for idx, occupants in enumerate(engine.board):
            counts = {}
            for p in occupants:
                counts[p] = counts.get(p, 0) + 1
            for p_id, count in counts.items():
                shown = min(count, lay.max_visual_stack)
                for s in range(shown):
                    pos = lay.piece_pos(idx, s)
                    pygame.draw.circle(self.screen, PLAYER_COLORS[p_id], pos, r)
                    pygame.draw.circle(self.screen, (15, 15, 15), pos, r, 1)
                    if idx == engine.selected_index and p_id == engine.current_player and s == shown - 1:
                        pygame.draw.circle(self.screen, WHITE, pos, r + 5, 3)
                if count > lay.max_visual_stack:
                    pos = lay.piece_pos(idx, shown - 1)
                    txt = self.chip_font.render(f"x{count}", True, WHITE)
                    self.screen.blit(txt, txt.get_rect(center=pos))

    # ============================================================
    # PER-PLAYER STATUS CHIPS  (also the "enter from start" target)
    # ============================================================
    def draw_status_chips(self, engine):
        lay = self.layout
        for p_id in range(1, engine.num_players + 1):
            rect = lay.chip_rects[p_id]
            color = PLAYER_COLORS[p_id]

            pygame.draw.rect(self.screen, PANEL_BG, rect, border_radius=6)
            is_current = (engine.current_player == p_id and not engine.game_over)
            start_selected = (is_current and engine.selected_index == -2)
            border = 3 if is_current else 1
            pygame.draw.rect(self.screen, WHITE if start_selected else color, rect, border, border_radius=6)

            name = self._clip_text(self._get_player_name(engine, p_id), self.chip_font, rect.width - 62)
            self.screen.blit(self.chip_font.render(f"P{p_id}", True, color), (rect.x + 8, rect.y + 5))
            self.screen.blit(self.chip_font.render(name, True, WHITE), (rect.x + 36, rect.y + 5))

            off = engine.finished_pool.get(p_id, 0)
            on_board = engine.on_board_count(p_id)
            jailed = engine.jail.get(p_id, 0)
            in_start = engine.start_pool.get(p_id, 0)

            if p_id in engine.finished_players:
                place = engine.placements.index(p_id) + 1
                suffix = {1: "st", 2: "nd", 3: "rd", 4: "th"}.get(place, "th")
                line2 = f"FINISHED - {place}{suffix} place"
            else:
                parts = []
                if in_start:
                    parts.append(f"start {in_start}")
                parts.append(f"board {on_board}")
                if jailed:
                    parts.append(f"jail {jailed}")
                parts.append(f"off {off}/15")
                line2 = "   ".join(parts)

            self.screen.blit(self.chip_small_font.render(line2, True, (215, 215, 215)),
                             (rect.x + 8, rect.y + 27))

    # ============================================================
    # IN-GAME UI
    # ============================================================
    def draw_ui(self, engine, pad=False):
        if engine.current_player is None:
            return
        lay = self.layout

        turn_color = PLAYER_COLORS[engine.current_player]
        player_name = self._get_player_name(engine, engine.current_player)

        turn_surf = self.big_font.render(f"{player_name}'s Turn", True, turn_color)
        turn_rect = turn_surf.get_rect(center=(SCREEN_WIDTH // 2, 30))
        pygame.draw.rect(self.screen, (18, 18, 18), turn_rect.inflate(44, 12), border_radius=6)
        self.screen.blit(turn_surf, turn_rect)

        label, button_color = self._action_button(engine)
        pygame.draw.rect(self.screen, button_color, lay.roll_button, border_radius=10)
        self.screen.blit(self.font.render(label, True, BLACK),
                         self.font.render(label, True, BLACK).get_rect(center=lay.roll_button.center))

        can_undo = engine.can_undo()
        undo_color = (230, 170, 60) if can_undo else (70, 70, 70)
        pygame.draw.rect(self.screen, undo_color, lay.undo_button, border_radius=10)
        self.screen.blit(self.font.render("UNDO", True, BLACK if can_undo else (120, 120, 120)),
                         self.font.render("UNDO", True, BLACK).get_rect(center=lay.undo_button.center))

        pygame.draw.rect(self.screen, (120, 120, 150), lay.history_button, border_radius=10)
        self.screen.blit(self.font.render("HISTORY", True, BLACK),
                         self.font.render("HISTORY", True, BLACK).get_rect(center=lay.history_button.center))

        pygame.draw.rect(self.screen, (120, 120, 150), lay.rules_button, border_radius=8)
        self.screen.blit(self.big_font.render("?", True, BLACK),
                         self.big_font.render("?", True, BLACK).get_rect(center=lay.rules_button.center))

        if engine.moves_available:
            dice_text = f"Moves left: {sorted(engine.moves_available)}"
        elif engine.waiting_for_doubles_roll:
            dice_text = "Acey-Deucey: roll your bonus die"
        elif engine.has_rolled_this_turn:
            dice_text = "No dice left - press END TURN"
        else:
            dice_text = "Press ROLL to start your turn"
        surf = self.font.render(dice_text, True, WHITE)
        self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH // 2, lay.status_line_y)))

        if engine.current_turn_entry and engine.current_turn_entry["rolls"]:
            rolls = "  |  ".join(engine.current_turn_entry["rolls"][-3:])
            rs = self.chip_small_font.render(f"This turn: {rolls}", True, (200, 200, 160))
            self.screen.blit(rs, rs.get_rect(center=(SCREEN_WIDTH // 2, lay.status_line_y + 22)))

        if engine.selected_index is not None:
            if engine.selected_index == -2:
                sel_text = "Selected: START"
            elif engine.selected_index == -1:
                sel_text = "Selected: JAIL"
            else:
                sel_text = f"Selected: point {engine.selected_index}"
            ss = self.chip_small_font.render(sel_text, True, WHITE)
            self.screen.blit(ss, ss.get_rect(midright=(lay.undo_button.left - 12, lay.undo_button.centery)))

        if engine.jail.get(engine.current_player, 0) > 0:
            msg = "MUST RE-ENTER FROM JAIL"
        elif engine.start_pool.get(engine.current_player, 0) > 0:
            msg = ("SELECT YOUR PANEL TO ENTER FROM START" if pad
                   else "CLICK YOUR PANEL TO ENTER FROM START")
        else:
            msg = None
        if msg:
            ms = self.chip_small_font.render(msg, True, (231, 150, 110))
            self.screen.blit(ms, ms.get_rect(center=(SCREEN_WIDTH // 2, lay.hint_y)))

        if pad:
            legend = ("Stick: move highlight    A: select    B: cancel    "
                      "X: roll / pass    LB: undo    Y: history    Menu: pause")
            ls = self.chip_small_font.render(legend, True, (150, 150, 150))
            self.screen.blit(ls, ls.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 9)))

    # ============================================================
    # CONTROLLER FOCUS HIGHLIGHT
    # Drawn on top of the board when a game pad is connected: a yellow
    # ring around the piece / target the stick is currently pointing at.
    # ============================================================
    def draw_controller_focus(self, engine, state):
        if engine.current_player is None or engine.game_over:
            return
        if engine.phase != "PLAYING" or not engine.moves_available:
            return

        pid = engine.current_player
        color = (255, 214, 10)

        if engine.selected_index is None:
            sources = engine.movable_sources(pid)
            if not sources:
                return
            target = sources[state.get("focus_source_i", 0) % len(sources)]
            self._focus_ring(target, pid, engine, color)
        else:
            dests = engine.legal_destinations(pid, engine.selected_index)
            if not dests:
                return
            target = dests[state.get("focus_dest_i", 0) % len(dests)]
            self._focus_ring(target, pid, engine, color, is_dest=True)

    def _focus_ring(self, target, pid, engine, color, is_dest=False):
        lay = self.layout

        if target == -2:
            pygame.draw.rect(self.screen, color, lay.chip_rects[pid], 4, border_radius=6)
            tag = "ENTER FROM START"
        elif target == -1:
            x, y = lay.jail_pos(pid, engine.num_players)
            pygame.draw.circle(self.screen, color, (int(x), int(y)), int(lay.piece_r + 8), 4)
            tag = "LEAVE JAIL"
        elif target == 24:
            pygame.draw.rect(self.screen, color, lay.chip_rects[pid], 4, border_radius=6)
            tag = "BEAR OFF"
        else:
            px, py = lay.piece_pos(target, 0)
            pygame.draw.circle(self.screen, color, (int(px), int(py)), int(lay.piece_r + 7), 4)
            tag = "MOVE HERE" if is_dest else "SELECT THIS PIECE"

        # Pill on top of (and masking) the mouse-oriented hint line.
        surf = self.chip_font.render(tag, True, (20, 20, 20))
        pill = surf.get_rect(center=(SCREEN_WIDTH // 2, lay.hint_y)).inflate(28, 12)
        pygame.draw.rect(self.screen, color, pill, border_radius=10)
        self.screen.blit(surf, surf.get_rect(center=pill.center))

    def _action_button(self, engine):
        if not engine.has_rolled_this_turn or engine.waiting_for_doubles_roll:
            return "ROLL", (46, 204, 113)
        if engine.moves_available:
            if engine.has_legal_moves(engine.current_player):
                return "PASS", (149, 165, 166)
            return "PASS", (231, 126, 60)
        return "END TURN", (241, 196, 15)

    # ============================================================
    # HISTORY / TRACKING OVERLAY
    # ============================================================
    def draw_history_overlay(self, engine):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 215))
        self.screen.blit(overlay, (0, 0))

        self.screen.blit(self.title_font.render("Game Tracking", True, WHITE), (60, 26))
        self.screen.blit(self.chip_small_font.render(
            "scroll wheel to move through the log  -  click anywhere or press H / Esc to close",
            True, (180, 180, 180)), (62, 70))

        panel = pygame.Rect(SCREEN_WIDTH - 470, 96, 410, 320)
        pygame.draw.rect(self.screen, PANEL_BG, panel, border_radius=8)
        pygame.draw.rect(self.screen, PANEL_BORDER, panel, 1, border_radius=8)
        self.screen.blit(self.big_font.render("Live status", True, WHITE), (panel.x + 16, panel.y + 12))

        header = f"{'Player':<12}{'start':>6}{'board':>7}{'jail':>6}{'off':>6}{'turns':>7}"
        self.screen.blit(self.mono_font.render(header, True, (170, 170, 170)), (panel.x + 16, panel.y + 46))
        y = panel.y + 68
        for row in engine.compile_results():
            name = row["name"][:11]
            line = (f"{name:<12}{row['in_start']:>6}{row['on_board']:>7}"
                    f"{row['jailed']:>6}{row['borne_off']:>6}{row['turns']:>7}")
            self.screen.blit(self.mono_font.render(line, True, PLAYER_COLORS[row["player"]]),
                             (panel.x + 16, y))
            y += 22
            extra = f"    hits {row['captures']}   jailed {row['times_jailed']}   rank {row['rank']}"
            self.screen.blit(self.chip_small_font.render(extra, True, (170, 170, 170)), (panel.x + 16, y))
            y += 22

        log_panel = pygame.Rect(60, 96, SCREEN_WIDTH - 560, SCREEN_HEIGHT - 160)
        pygame.draw.rect(self.screen, PANEL_BG, log_panel, border_radius=8)
        pygame.draw.rect(self.screen, PANEL_BORDER, log_panel, 1, border_radius=8)
        self.screen.blit(self.big_font.render("Turn log", True, WHITE), (log_panel.x + 16, log_panel.y + 12))

        entries = list(engine.turn_log)
        if engine.current_turn_entry is not None:
            entries.append(engine.current_turn_entry)

        lines = []
        for entry in entries:
            rolls = ", ".join(entry["rolls"]) if entry["rolls"] else "-"
            moves = ", ".join(entry["moves"]) if entry["moves"] else "(no moves)"
            lines.append((f"T{entry['turn']:>3}  {entry['name'][:10]:<10}  {rolls}", entry["player"]))
            for chunk in self._wrap(f"        {moves}", 84):
                lines.append((chunk, entry["player"]))

        visible = (log_panel.height - 60) // 20
        max_scroll = max(0, len(lines) - visible)
        self.history_scroll = max(0, min(self.history_scroll, max_scroll))
        start = max(0, len(lines) - visible - self.history_scroll)
        end = start + visible

        y = log_panel.y + 48
        for text, pid in lines[start:end]:
            self.screen.blit(self.mono_font.render(text, True, PLAYER_COLORS.get(pid, WHITE)),
                             (log_panel.x + 16, y))
            y += 20

    def _wrap(self, text, width):
        out = []
        while len(text) > width:
            cut = text.rfind(", ", 0, width)
            cut = width if cut == -1 else cut + 1
            out.append(text[:cut])
            text = "        " + text[cut:].lstrip()
        out.append(text)
        return out

    # ============================================================
    # RULES OVERLAY
    # ============================================================
    def draw_rules_overlay(self, page_index):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 230))
        self.screen.blit(overlay, (0, 0))

        page_index = max(0, min(page_index, len(RULES_PAGES) - 1))
        title, body = RULES_PAGES[page_index]

        panel = pygame.Rect(120, 60, SCREEN_WIDTH - 240, SCREEN_HEIGHT - 150)
        pygame.draw.rect(self.screen, PANEL_BG, panel, border_radius=10)
        pygame.draw.rect(self.screen, PANEL_BORDER, panel, 2, border_radius=10)

        self.screen.blit(self.title_font.render(f"Rules  -  {title}", True, WHITE),
                         (panel.x + 30, panel.y + 22))
        self.screen.blit(self.chip_small_font.render(
            f"Page {page_index + 1} / {len(RULES_PAGES)}", True, (180, 180, 180)),
            (panel.right - 120, panel.y + 32))

        y = panel.y + 78
        for line in body:
            self.screen.blit(self.mono_font.render(line, True, (225, 225, 225)), (panel.x + 30, y))
            y += 22

        hint = self.chip_small_font.render(
            "<- / -> or click arrows to turn pages   -   Esc or click outside to close",
            True, (180, 180, 180))
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, panel.bottom - 26)))

        left = pygame.Rect(panel.x + 20, panel.bottom - 60, 120, 40)
        right = pygame.Rect(panel.right - 140, panel.bottom - 60, 120, 40)
        for r, lbl, active in ((left, "< Prev", page_index > 0),
                               (right, "Next >", page_index < len(RULES_PAGES) - 1)):
            pygame.draw.rect(self.screen, (120, 120, 150) if active else (60, 60, 60), r, border_radius=8)
            t = self.font.render(lbl, True, BLACK if active else (120, 120, 120))
            self.screen.blit(t, t.get_rect(center=r.center))
        return left, right

    # ============================================================
    # SETTINGS OVERLAY
    # ============================================================
    def draw_settings_overlay(self, settings, backdrop="menu"):
        if backdrop == "menu":
            self.screen.fill(BG_COLOR)
        else:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 220))
            self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 320, 120, 640, 420)
        pygame.draw.rect(self.screen, PANEL_BG, panel, border_radius=10)
        pygame.draw.rect(self.screen, PANEL_BORDER, panel, 2, border_radius=10)

        self.screen.blit(self.title_font.render("Settings", True, WHITE), (panel.x + 30, panel.y + 24))
        self.screen.blit(self.chip_small_font.render(
            "More options will be added here over time.", True, (170, 170, 170)),
            (panel.x + 32, panel.y + 66))

        rows = []

        # Fullscreen toggle
        row_y = panel.y + 110
        label = self.big_font.render("Fullscreen", True, WHITE)
        self.screen.blit(label, (panel.x + 32, row_y + 8))
        self.screen.blit(self.chip_small_font.render(
            "Also toggled any time with F11", True, (160, 160, 160)),
            (panel.x + 32, row_y + 34))
        toggle = pygame.Rect(panel.right - 150, row_y, 100, 44)
        on = bool(settings.get("fullscreen"))
        pygame.draw.rect(self.screen, (46, 204, 113) if on else (90, 90, 90), toggle, border_radius=22)
        knob = pygame.Rect(toggle.right - 40 if on else toggle.x + 4, toggle.y + 4, 36, 36)
        pygame.draw.ellipse(self.screen, WHITE, knob)
        state_txt = self.chip_font.render("ON" if on else "OFF", True, WHITE)
        self.screen.blit(state_txt, state_txt.get_rect(midright=(toggle.x - 14, toggle.centery)))
        rows.append(("fullscreen", toggle))

        back = pygame.Rect(panel.x + 30, panel.bottom - 62, 140, 44)
        pygame.draw.rect(self.screen, (120, 120, 150), back, border_radius=8)
        self.screen.blit(self.font.render("Back", True, BLACK),
                         self.font.render("Back", True, BLACK).get_rect(center=back.center))

        return {"rows": rows, "back": back}

    # ============================================================
    # GAME OVER SCREEN
    # ============================================================
    def draw_game_over(self, engine, pad=False):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 225))
        self.screen.blit(overlay, (0, 0))

        heading = self.title_font.render("Final Standings", True, WHITE)
        self.screen.blit(heading, heading.get_rect(center=(SCREEN_WIDTH // 2, 84)))

        results = engine.compile_results()
        winner = results[0]
        wtxt = self.big_font.render(f"{winner['name']} wins!", True, PLAYER_COLORS[winner["player"]])
        self.screen.blit(wtxt, wtxt.get_rect(center=(SCREEN_WIDTH // 2, 128)))

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 320, 164, 640, 56 + 70 * len(results))
        pygame.draw.rect(self.screen, PANEL_BG, panel, border_radius=10)
        pygame.draw.rect(self.screen, PANEL_BORDER, panel, 2, border_radius=10)

        medals = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}
        y = panel.y + 22
        for row in results:
            color = PLAYER_COLORS[row["player"]]
            pygame.draw.rect(self.screen, color, (panel.x + 20, y + 6, 10, 44))
            self.screen.blit(self.big_font.render(medals.get(row["rank"], f"{row['rank']}th"), True, WHITE),
                             (panel.x + 44, y + 14))
            self.screen.blit(self.big_font.render(row["name"], True, color), (panel.x + 110, y + 4))
            detail = (f"borne off {row['borne_off']}/15    turns {row['turns']}    "
                      f"hits {row['captures']}    times jailed {row['times_jailed']}")
            self.screen.blit(self.chip_small_font.render(detail, True, (200, 200, 200)),
                             (panel.x + 110, y + 32))
            y += 70

        hint_text = ("Press A / X to return to the menu" if pad
                     else "Click anywhere to return to the menu")
        hint = self.font.render(hint_text, True, (210, 210, 210))
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, panel.bottom + 40)))

    # ============================================================
    # INITIAL ROLL SCREENS
    # ============================================================
    def draw_setup_overlay(self, engine, pad=False):
        panel = pygame.Rect(0, 0, 560, 120 + 38 * engine.num_players)
        panel.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        pygame.draw.rect(self.screen, PANEL_BG, panel, border_radius=10)
        pygame.draw.rect(self.screen, PANEL_BORDER, panel, 2, border_radius=10)

        title = self.font.render("Initial Roll", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, panel.y + 30)))
        instruction = ("Press A / X to roll for the next player - highest total plays first"
                       if pad else
                       "Click your status panel to roll two dice - highest total plays first")
        sub = self.chip_small_font.render(instruction, True, (190, 190, 190))
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, panel.y + 58)))

        y = panel.y + 88
        for p_id in range(1, engine.num_players + 1):
            name = engine.get_player_name(p_id)
            total = engine.player_rolls.get(p_id)
            text = f"{name} ({SEAT_LABELS[p_id]}): {total if total is not None else '--'}"
            surf = self.font.render(text, True, PLAYER_COLORS[p_id])
            self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH // 2, y)))
            y += 38

    def draw_initial_winner_screen(self, engine, pad=False):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        title = self.big_font.render("Initial Roll Results", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 110)))

        y = 175
        for p_id, roll in engine.player_rolls.items():
            txt = self.font.render(f"{self._get_player_name(engine, p_id)} rolled: {roll}", True,
                                   PLAYER_COLORS[p_id])
            self.screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH // 2, y)))
            y += 42

        if engine.turn_order:
            order_names = " -> ".join(self._get_player_name(engine, p) for p in engine.turn_order)
            self.screen.blit(self.chip_small_font.render(f"Turn order: {order_names}", True, (210, 210, 210)),
                             self.chip_small_font.render(f"Turn order: {order_names}", True, (210, 210, 210))
                             .get_rect(center=(SCREEN_WIDTH // 2, y + 16)))

        hint = self.font.render("Press A / X to begin" if pad else "Click to begin", True, WHITE)
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, y + 66)))
