import pygame
from Constants import *


class MenuManager:
    def __init__(self, profile_manager):
        # ============================================================
        # PROFILE DATA / EXTERNAL MANAGERS
        # Handles database-backed profile creation, loading, deletion
        # ============================================================
        self.profile_manager = profile_manager

        # ============================================================
        # TOP-LEVEL MENU STATE
        # Controls which screen is currently visible
        # ============================================================
        self.state = "MAIN_MENU"

        # ============================================================
        # NEW GAME SETUP STATE
        # Stores player count and selected saved profiles for game start
        # ============================================================
        self.num_players = 2
        self.selected_profiles = {}      # Example: {1: "David", 2: "Arnie"}
        self.profile_click_rects = []    # Clickable saved-profile entries
        self.highlighted_profile_name = None

        # ============================================================
        # CREATE PROFILE INPUT STATE
        # Handles typed profile-name input box and text cursor behavior
        # ============================================================
        self.new_profile_name = ""
        self.create_error = ""
        self.create_success = ""
        self.input_active = False
        self.cursor_visible = True
        self.cursor_timer = 0
        self.cursor_interval = 500  # milliseconds

        # ============================================================
        # DELETE PROFILE CONFIRMATION STATE
        # Shows confirmation overlay before permanently deleting profile
        # ============================================================
        self.confirm_delete = False
        self.pending_delete_profile = None

        # ============================================================
        # FONTS USED BY MENU UI
        # ============================================================
        self.title_font = pygame.font.SysFont("Arial", 40, bold=True)
        self.header_font = pygame.font.SysFont("Arial", 28, bold=True)
        self.font = pygame.font.SysFont("Arial", 24, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 18, bold=False)

        # ============================================================
        # MAIN MENU BUTTONS
        # Buttons for landing screen navigation
        # ============================================================
        self.main_menu_buttons = {
            "new_game": pygame.Rect(SCREEN_WIDTH // 2 - 120, 220, 240, 60),
            "stats": pygame.Rect(SCREEN_WIDTH // 2 - 120, 310, 240, 60),
            "exit": pygame.Rect(SCREEN_WIDTH // 2 - 120, 400, 240, 60),
        }

        # ============================================================
        # PLAYER COUNT SELECTION BUTTONS
        # Used in new game setup to choose 2 / 3 / 4 players
        # ============================================================
        self.player_count_buttons = {
            2: pygame.Rect(220, 180, 100, 60),
            3: pygame.Rect(360, 180, 100, 60),
            4: pygame.Rect(500, 180, 100, 60),
        }

        # ============================================================
        # PROFILE SELECTION SCREEN BUTTONS
        # Used while selecting saved profiles before starting a game
        # ============================================================
        self.profile_select_buttons = {
            "back": pygame.Rect(40, SCREEN_HEIGHT - 80, 140, 50),
            "create_profile": pygame.Rect(SCREEN_WIDTH - 240, SCREEN_HEIGHT - 80, 200, 50),
            "start_game": pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 80, 200, 50),
            "clear": pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 145, 200, 45),
            "delete_profile": pygame.Rect(SCREEN_WIDTH - 240, SCREEN_HEIGHT - 145, 200, 45),
        }

        # ============================================================
        # CREATE PROFILE SCREEN BUTTONS
        # Buttons used in profile creation UI
        # ============================================================
        self.create_profile_buttons = {
            "save": pygame.Rect(SCREEN_WIDTH // 2 - 150, 320, 120, 50),
            "cancel": pygame.Rect(SCREEN_WIDTH // 2 + 30, 320, 120, 50),
        }

        # ============================================================
        # DELETE CONFIRMATION BUTTONS
        # Buttons shown in overlay before deleting a profile
        # ============================================================
        self.delete_confirm_buttons = {
            "yes": pygame.Rect(SCREEN_WIDTH // 2 - 140, SCREEN_HEIGHT // 2 + 40, 120, 50),
            "no": pygame.Rect(SCREEN_WIDTH // 2 + 20, SCREEN_HEIGHT // 2 + 40, 120, 50),
        }

        # ============================================================
        # CREATE PROFILE INPUT BOX RECTANGLE
        # Defines where the user clicks/types the new profile name
        # ============================================================
        self.profile_input_rect = pygame.Rect(
            SCREEN_WIDTH // 2 - 180,
            205,
            360,
            50
        )

    # ============================================================
    # PUBLIC MENU INTERFACE
    # Methods main.py will call every frame / input event
    # ============================================================
    def draw(self, screen):
        if self.state == "MAIN_MENU":
            self.draw_main_menu(screen)
        elif self.state == "PROFILE_SELECT":
            self.draw_profile_select(screen)
        elif self.state == "CREATE_PROFILE":
            self.draw_create_profile(screen)

    def handle_mouse_click(self, mouse_pos):
        if self.state == "MAIN_MENU":
            return self._handle_main_menu_click(mouse_pos)
        elif self.state == "PROFILE_SELECT":
            return self._handle_profile_select_click(mouse_pos)
        elif self.state == "CREATE_PROFILE":
            return self._handle_create_profile_click(mouse_pos)
        return None

    def handle_keydown(self, event):
        # ------------------------------------------------------------
        # Keyboard input is only used while creating a new profile
        # ------------------------------------------------------------
        if self.state != "CREATE_PROFILE":
            return None

        if not self.input_active:
            return None

        self.create_error = ""
        self.create_success = ""

        if event.key == pygame.K_BACKSPACE:
            self.new_profile_name = self.new_profile_name[:-1]

        elif event.key == pygame.K_RETURN:
            return self._save_new_profile()

        elif event.key == pygame.K_ESCAPE:
            self.input_active = False

        else:
            ch = event.unicode
            if (
                ch.isprintable()
                and ch not in ("\r", "\n", "\t")
                and len(self.new_profile_name) < 20
            ):
                self.new_profile_name += ch

        self.cursor_visible = True
        self.cursor_timer = 0
        return None

    def update(self, dt):
        # ------------------------------------------------------------
        # Blinking cursor update for create-profile text input
        # ------------------------------------------------------------
        if self.state == "CREATE_PROFILE" and self.input_active:
            self.cursor_timer += dt
            if self.cursor_timer >= self.cursor_interval:
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = 0
        else:
            self.cursor_visible = False
            self.cursor_timer = 0

    def reset_for_new_game(self):
        # ------------------------------------------------------------
        # Clears temporary selection/input state before starting setup
        # ------------------------------------------------------------
        self.selected_profiles = {}
        self.num_players = 2
        self.profile_click_rects = []
        self.highlighted_profile_name = None

        self.new_profile_name = ""
        self.create_error = ""
        self.create_success = ""
        self.input_active = False
        self.cursor_visible = True
        self.cursor_timer = 0

        self.confirm_delete = False
        self.pending_delete_profile = None

    def is_ready_to_start(self):
        return len(self.selected_profiles) == self.num_players

    def get_player_profiles(self):
        return dict(self.selected_profiles)

    # ============================================================
    # MAIN MENU DRAWING
    # Landing screen with New Game / Stats / Exit
    # ============================================================
    def draw_main_menu(self, screen):
        screen.fill(BG_COLOR)

        title = self.title_font.render("ACEY DUECY", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 110))
        screen.blit(title, title_rect)

        subtitle = self.small_font.render("Point-and-click menu system", True, WHITE)
        subtitle_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, 150))
        screen.blit(subtitle, subtitle_rect)

        labels = {
            "new_game": "New Game",
            "stats": "Stats",
            "exit": "Exit",
        }

        for key, rect in self.main_menu_buttons.items():
            pygame.draw.rect(screen, GRAY, rect, border_radius=8)
            text = self.font.render(labels[key], True, WHITE)
            text_rect = text.get_rect(center=rect.center)
            screen.blit(text, text_rect)

    # ============================================================
    # PROFILE SELECTION SCREEN DRAWING
    # Lets user choose player count and assign saved profiles to slots
    # ============================================================
    def draw_profile_select(self, screen):
        screen.fill(BG_COLOR)

        title = self.header_font.render("NEW GAME - SELECT PROFILES", True, WHITE)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 50)))

        # ----------------------------
        # Player count selector row
        # ----------------------------
        count_label = self.font.render("Player Count", True, WHITE)
        screen.blit(count_label, (70, 190))

        for count, rect in self.player_count_buttons.items():
            color = PLAYER_COLORS[count] if self.num_players == count else GRAY
            pygame.draw.rect(screen, color, rect, border_radius=8)

            txt = self.font.render(str(count), True, BLACK if self.num_players == count else WHITE)
            screen.blit(txt, txt.get_rect(center=rect.center))

        # ----------------------------
        # Saved profile list
        # ----------------------------
        profiles_title = self.font.render("Saved Profiles", True, WHITE)
        screen.blit(profiles_title, (70, 285))

        profile_names = self.profile_manager.get_all_profiles()
        self.profile_click_rects = []

        y = 330
        for name in profile_names[:8]:
            rect = pygame.Rect(70, y, 320, 42)
            self.profile_click_rects.append((name, rect))

            fill_color = GRAY
            if name == self.highlighted_profile_name:
                fill_color = PLAYER_COLORS[2]

            pygame.draw.rect(screen, fill_color, rect, border_radius=6)

            txt = self.font.render(name, True, WHITE)
            screen.blit(txt, (rect.x + 12, rect.y + 8))
            y += 52

        if not profile_names:
            empty = self.small_font.render("No profiles yet. Create one first.", True, WHITE)
            screen.blit(empty, (70, 335))

        # ----------------------------
        # Selected player slots
        # ----------------------------
        slots_title = self.font.render("Player Slots", True, WHITE)
        screen.blit(slots_title, (500, 285))

        for slot in range(1, self.num_players + 1):
            rect = pygame.Rect(500, 330 + (slot - 1) * 60, 350, 42)
            pygame.draw.rect(screen, PLAYER_COLORS[slot], rect, border_radius=6)

            chosen = self.selected_profiles.get(slot, "[Empty]")
            txt = self.font.render(f"Player {slot}: {chosen}", True, BLACK)
            screen.blit(txt, (rect.x + 12, rect.y + 8))

        # ----------------------------
        # Bottom / side buttons
        # ----------------------------
        for key, rect in self.profile_select_buttons.items():
            pygame.draw.rect(screen, GRAY, rect, border_radius=8)

        back_txt = self.font.render("Back", True, WHITE)
        screen.blit(back_txt, back_txt.get_rect(center=self.profile_select_buttons["back"].center))

        create_txt = self.font.render("Create Profile", True, WHITE)
        screen.blit(create_txt, create_txt.get_rect(center=self.profile_select_buttons["create_profile"].center))

        delete_txt = self.font.render("Delete Profile", True, WHITE)
        screen.blit(delete_txt, delete_txt.get_rect(center=self.profile_select_buttons["delete_profile"].center))

        start_color = (46, 204, 113) if self.is_ready_to_start() else GRAY
        pygame.draw.rect(screen, start_color, self.profile_select_buttons["start_game"], border_radius=8)

        start_txt = self.font.render("Start Game", True, BLACK if self.is_ready_to_start() else WHITE)
        screen.blit(start_txt, start_txt.get_rect(center=self.profile_select_buttons["start_game"].center))

        clear_txt = self.font.render("Clear Slots", True, WHITE)
        screen.blit(clear_txt, clear_txt.get_rect(center=self.profile_select_buttons["clear"].center))

        help_text = self.small_font.render(
            "Click a saved profile to assign it to the next empty slot.",
            True,
            WHITE
        )
        screen.blit(help_text, (500, 585))

        selected_help = self.small_font.render(
            "Selected profile can be deleted with confirmation.",
            True,
            WHITE
        )
        screen.blit(selected_help, (500, 555))

        # ----------------------------
        # Delete confirmation overlay
        # ----------------------------
        if self.confirm_delete and self.pending_delete_profile:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))

            panel = pygame.Rect(SCREEN_WIDTH // 2 - 220, SCREEN_HEIGHT // 2 - 100, 440, 220)
            pygame.draw.rect(screen, (60, 60, 60), panel, border_radius=10)
            pygame.draw.rect(screen, WHITE, panel, 2, border_radius=10)

            msg1 = self.font.render("Delete this profile?", True, WHITE)
            msg2 = self.small_font.render(self.pending_delete_profile, True, WHITE)

            screen.blit(msg1, msg1.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30)))
            screen.blit(msg2, msg2.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 5)))

            for rect in self.delete_confirm_buttons.values():
                pygame.draw.rect(screen, GRAY, rect, border_radius=8)

            yes_txt = self.font.render("Yes", True, WHITE)
            no_txt = self.font.render("Cancel", True, WHITE)

            screen.blit(yes_txt, yes_txt.get_rect(center=self.delete_confirm_buttons["yes"].center))
            screen.blit(no_txt, no_txt.get_rect(center=self.delete_confirm_buttons["no"].center))

    # ============================================================
    # CREATE PROFILE SCREEN DRAWING
    # Draws text input box and Save / Cancel controls
    # ============================================================
    def draw_create_profile(self, screen):
        screen.fill(BG_COLOR)

        title = self.header_font.render("CREATE PROFILE", True, WHITE)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 80)))

        prompt = self.font.render("Enter profile name:", True, WHITE)
        screen.blit(prompt, (SCREEN_WIDTH // 2 - 180, 160))

        # ----------------------------
        # Input box with blinking cursor
        # ----------------------------
        box_color = WHITE if self.input_active else (220, 220, 220)

        pygame.draw.rect(
            screen,
            box_color,
            self.profile_input_rect,
            border_radius=6
        )

        pygame.draw.rect(
            screen,
            BLACK,
            self.profile_input_rect,
            2,
            border_radius=6
        )

        display_text = self.new_profile_name
        if self.input_active and self.cursor_visible:
            display_text += "|"

        name_surface = self.font.render(display_text, True, BLACK)

        screen.blit(
            name_surface,
            (self.profile_input_rect.x + 12, self.profile_input_rect.y + 11)
        )

        if not self.new_profile_name and not self.input_active:
            hint = self.small_font.render(
                "Click here to type profile name",
                True,
                GRAY
            )
            screen.blit(
                hint,
                (self.profile_input_rect.x + 12, self.profile_input_rect.y + 15)
            )

        # ----------------------------
        # Create profile buttons
        # ----------------------------
        for key, rect in self.create_profile_buttons.items():
            pygame.draw.rect(screen, GRAY, rect, border_radius=8)

        save_txt = self.font.render("Save", True, WHITE)
        screen.blit(save_txt, save_txt.get_rect(center=self.create_profile_buttons["save"].center))

        cancel_txt = self.font.render("Cancel", True, WHITE)
        screen.blit(cancel_txt, cancel_txt.get_rect(center=self.create_profile_buttons["cancel"].center))

        # ----------------------------
        # Error / success messages
        # ----------------------------
        if self.create_error:
            err = self.small_font.render(self.create_error, True, (231, 76, 60))
            screen.blit(err, err.get_rect(center=(SCREEN_WIDTH // 2, 400)))

        if self.create_success:
            ok = self.small_font.render(self.create_success, True, (46, 204, 113))
            screen.blit(ok, ok.get_rect(center=(SCREEN_WIDTH // 2, 400)))

    # ============================================================
    # MAIN MENU CLICK HANDLER
    # Handles clicks on New Game / Stats / Exit
    # ============================================================
    def _handle_main_menu_click(self, mouse_pos):
        if self.main_menu_buttons["new_game"].collidepoint(mouse_pos):
            self.reset_for_new_game()
            self.state = "PROFILE_SELECT"
            return {"action": "open_profile_select"}

        if self.main_menu_buttons["stats"].collidepoint(mouse_pos):
            return {"action": "open_stats"}

        if self.main_menu_buttons["exit"].collidepoint(mouse_pos):
            return {"action": "exit"}

        return None

    # ============================================================
    # PROFILE SELECTION CLICK HANDLER
    # Handles player count, profile assignment, deletion, start game
    # ============================================================
    def _handle_profile_select_click(self, mouse_pos):
        # ----------------------------
        # Delete confirmation overlay clicks
        # ----------------------------
        if self.confirm_delete:
            if self.delete_confirm_buttons["yes"].collidepoint(mouse_pos):
                if self.pending_delete_profile:
                    deleted_name = self.pending_delete_profile
                    self.profile_manager.delete_profile(deleted_name)

                    # Remove deleted profile from assigned slots
                    self.selected_profiles = {
                        slot: name
                        for slot, name in self.selected_profiles.items()
                        if name != deleted_name
                    }

                    if self.highlighted_profile_name == deleted_name:
                        self.highlighted_profile_name = None

                    self.pending_delete_profile = None
                    self.confirm_delete = False

                    return {"action": "profile_deleted", "name": deleted_name}

            if self.delete_confirm_buttons["no"].collidepoint(mouse_pos):
                self.pending_delete_profile = None
                self.confirm_delete = False
                return {"action": "delete_cancelled"}

            return None

        # ----------------------------
        # Player count selection
        # ----------------------------
        for count, rect in self.player_count_buttons.items():
            if rect.collidepoint(mouse_pos):
                self.num_players = count
                self.selected_profiles = {
                    slot: name
                    for slot, name in self.selected_profiles.items()
                    if slot <= self.num_players
                }
                return {"action": "set_player_count", "count": count}

        # ----------------------------
        # Navigation / utility buttons
        # ----------------------------
        if self.profile_select_buttons["back"].collidepoint(mouse_pos):
            self.state = "MAIN_MENU"
            return {"action": "back_to_main"}

        if self.profile_select_buttons["create_profile"].collidepoint(mouse_pos):
            self.new_profile_name = ""
            self.create_error = ""
            self.create_success = ""
            self.input_active = True
            self.cursor_visible = True
            self.cursor_timer = 0
            self.state = "CREATE_PROFILE"
            return {"action": "open_create_profile"}

        if self.profile_select_buttons["delete_profile"].collidepoint(mouse_pos):
            if self.highlighted_profile_name:
                self.pending_delete_profile = self.highlighted_profile_name
                self.confirm_delete = True
                return {"action": "confirm_delete", "name": self.highlighted_profile_name}
            return {"action": "no_profile_selected_for_delete"}

        if self.profile_select_buttons["clear"].collidepoint(mouse_pos):
            self.selected_profiles = {}
            return {"action": "clear_slots"}

        if self.profile_select_buttons["start_game"].collidepoint(mouse_pos):
            if self.is_ready_to_start():
                return {
                    "action": "start_game",
                    "num_players": self.num_players,
                    "player_profiles": self.get_player_profiles()
                }
            return {"action": "not_ready"}

        # ----------------------------
        # Saved profile list clicks
        # ----------------------------
        for name, rect in self.profile_click_rects:
            if rect.collidepoint(mouse_pos):
                self.highlighted_profile_name = name

                # Prevent duplicates in assigned slots
                if name in self.selected_profiles.values():
                    return {"action": "duplicate_profile", "name": name}

                for slot in range(1, self.num_players + 1):
                    if slot not in self.selected_profiles:
                        self.selected_profiles[slot] = name
                        return {"action": "assign_profile", "slot": slot, "name": name}

                return {"action": "profile_highlighted", "name": name}

        return None

    # ============================================================
    # CREATE PROFILE CLICK HANDLER
    # Handles input-box focus plus Save / Cancel buttons
    # ============================================================
    def _handle_create_profile_click(self, mouse_pos):
        if self.profile_input_rect.collidepoint(mouse_pos):
            self.input_active = True
            self.cursor_visible = True
            self.cursor_timer = 0
            return {"action": "input_focus"}

        # Clicking outside the box removes typing focus
        self.input_active = False

        if self.create_profile_buttons["save"].collidepoint(mouse_pos):
            return self._save_new_profile()

        if self.create_profile_buttons["cancel"].collidepoint(mouse_pos):
            self.new_profile_name = ""
            self.create_error = ""
            self.create_success = ""
            self.input_active = False
            self.state = "PROFILE_SELECT"
            return {"action": "cancel_create_profile"}

        return None

    # ============================================================
    # PROFILE CREATION HELPER
    # Validates name and attempts to save a new profile
    # ============================================================
    def _save_new_profile(self):
        name = self.new_profile_name.strip()

        if not name:
            self.create_error = "Profile name cannot be empty."
            self.create_success = ""
            return {"action": "create_failed", "reason": "empty_name"}

        if len(name) > 20:
            self.create_error = "Profile name must be 20 characters or less."
            self.create_success = ""
            return {"action": "create_failed", "reason": "name_too_long"}

        created = self.profile_manager.create_profile(name)

        if not created:
            self.create_error = "That profile already exists."
            self.create_success = ""
            return {"action": "create_failed", "reason": "duplicate"}

        self.create_error = ""
        self.create_success = f"Created profile: {name}"
        self.new_profile_name = ""
        self.input_active = False
        self.cursor_visible = True
        self.cursor_timer = 0
        self.state = "PROFILE_SELECT"

        return {"action": "profile_created", "name": name}