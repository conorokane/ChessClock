"""Touch-friendly chess clock for an 800 × 480 screen."""

import argparse
from math import ceil
from time import monotonic
from tkinter import Canvas, StringVar, ttk

from ttkthemes import ThemedTk

from chess_clock.clock import ChessClock, format_time
from chess_clock import theme as appearance
from chess_clock.theme import COLORS, FONTS, PADDING, SIZES

STARTING_TIMES = (30, 45, *range(60, 180 * 60 + 1, 60))


def starting_time_label(seconds: int) -> str:
    return f"0:{seconds:02d}" if seconds < 60 else str(seconds // 60)


class ClockUI:
    def __init__(self, window: ThemedTk, clock: ChessClock):
        self.window = window
        self.clock = clock
        self._job = None
        self._reset_deadline = None
        self._winner_selection_armed = False
        self._timeout_flash_started = None
        self._resume_flash_started = None
        window.title("Chess Clock")
        window.geometry(f"{SIZES['window_width']}x{SIZES['window_height']}")
        window.minsize(SIZES["window_width"], SIZES["window_height"])
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)
        window.protocol("WM_DELETE_WINDOW", self.close)

        content = ttk.Frame(window, padding=0, borderwidth=0)
        self.game_frame = content
        content.grid(sticky="nsew")
        content.columnconfigure((0, 1), weight=1, uniform="players")
        content.rowconfigure(0, weight=1)

        self.cards = []
        self.names = []
        self.winner_buttons = []
        self.times = []
        self.fractions = []
        self.time_shadows = []
        self.fraction_shadows = []
        self.timer_fonts = []
        self.timer_areas = []
        self.timer_layouts = [None, None]
        self.indicators = []
        self.statistics_areas = []
        self.statistics_fonts = [
            (appearance.create_font(window, "statistics"),
             appearance.create_font(window, "statistics_value")) for _ in range(2)]
        self.time_bars = []
        self.time_bar_fills = []
        body_font = appearance.create_font(window, "body")
        self.indicator_text_height = body_font.metrics("linespace") + 2
        heading_font = appearance.create_font(window, "player_title")
        button_font = appearance.create_font(window, "button")
        heading_height = max(heading_font.metrics("linespace") + 2,
                             button_font.metrics("linespace") + 4)
        statistics_font = appearance.create_font(window, "statistics")
        indicator_height = max(body_font.metrics("linespace"),
                               3 * statistics_font.metrics("linespace")) + 4
        for player, name in enumerate(("Left", "Right")):
            field = ttk.Frame(content, style=f"Player{player}.TFrame")
            field.grid(row=0, column=player, sticky="nsew")
            field.columnconfigure(0, weight=1)
            field.rowconfigure(1, weight=1)
            bar = Canvas(field, height=SIZES["bar_height"], width=1, background=COLORS["bar_background"],
                         borderwidth=0, highlightthickness=0)
            bar.grid(row=0, column=0, sticky="ew")
            fill = bar.create_rectangle(0, 0, 0, SIZES["bar_height"], fill=COLORS["muted_foreground"], outline="")
            self.time_bars.append(bar)
            self.time_bar_fills.append(fill)
            bar.bind("<Configure>", lambda event, side=player: self.draw_time_bar(side))
            card = ttk.Frame(field, padding=PADDING["card"], style=f"Player{player}.TFrame")
            card.grid(row=1, column=0, sticky="nsew")
            card.columnconfigure(0, weight=1)
            card.rowconfigure(1, weight=1)
            heading_area = ttk.Frame(card, height=heading_height, style=f"Player{player}.TFrame")
            heading_area.grid(row=0, column=0, sticky="ew")
            heading_area.grid_propagate(False)
            title = ttk.Label(heading_area, text=name,
                              anchor="center", style=f"Title.Player{player}.TLabel")
            title.place(x=0, y=0, relwidth=1, relheight=1)
            winner_button = ttk.Button(heading_area, text=f"Winner - {'Left' if player == 0 else 'Right'}",
                                       style="Winner.Touch.TButton",
                                       command=lambda side=player: self.declare_winner(side))
            self.winner_buttons.append(winner_button)
            timer_area = Canvas(card, width=1, height=1, borderwidth=0, highlightthickness=0)
            timer_area.grid(row=1, column=0, sticky="nsew")
            large_font = appearance.create_font(window, "timer")
            small_font = appearance.create_font(window, "fraction")
            # Create both shadows first so all foreground text sits above them.
            time_shadow = timer_area.create_text(0, 0, anchor="nw", font=large_font, fill=COLORS["shadow"])
            fraction_shadow = timer_area.create_text(0, 0, anchor="nw", font=small_font, fill=COLORS["shadow"])
            timer = timer_area.create_text(0, 0, anchor="nw", font=large_font)
            fraction = timer_area.create_text(0, 0, anchor="nw", font=small_font)
            # Keep the same space in every state so statistics cannot resize
            # the timer canvas or trigger a different fitted clock font.
            indicator_area = ttk.Frame(card, height=indicator_height,
                                       style=f"Player{player}.TFrame")
            indicator_area.grid(row=2, column=0, sticky="ew")
            indicator_area.grid_propagate(False)
            indicator = ttk.Label(indicator_area, anchor="center",
                                  style=f"Indicator.Player{player}.TLabel")
            indicator.place(x=0, rely=.5, y=SIZES["indicator_offset_y"], anchor="w",
                            relwidth=1, height=self.indicator_text_height)
            statistics_area = Canvas(indicator_area, width=1, height=1,
                                     borderwidth=0, highlightthickness=0)
            statistics_area.bind("<Configure>", lambda event, side=player: self.draw_statistics(side))
            self.statistics_areas.append(statistics_area)
            self.cards.append(card)
            self.names.append(title)
            self.times.append(timer)
            self.fractions.append(fraction)
            self.time_shadows.append(time_shadow)
            self.fraction_shadows.append(fraction_shadow)
            self.timer_fonts.append((large_font, small_font))
            self.timer_areas.append(timer_area)
            self.indicators.append(indicator)

        divider = Canvas(content, width=SIZES["divider_width"], height=1, background=COLORS["divider"],
                         borderwidth=0, highlightthickness=0)
        divider.grid(row=0, column=0, columnspan=2, sticky="ns")
        bottom_line = Canvas(content, width=1, height=SIZES["bottom_line_height"], background=COLORS["divider"],
                             borderwidth=0, highlightthickness=0)
        bottom_line.grid(row=1, column=0, columnspan=2, sticky="ew")

        self.status = ttk.Label(content, anchor="center", style="Status.TLabel")
        self.status.grid(row=4, column=0, columnspan=2, sticky="ew", pady=PADDING["status_vertical"])
        self.rocker_buttons = []
        for side, label in enumerate(("Left player", "Right player")):
            button = ttk.Button(content, text=label, style="Touch.TButton",
                                command=lambda side=side: self.rocker(side))
            button.grid(row=3, column=side, sticky="ew", padx=PADDING["button_gap"], pady=PADDING["rocker_vertical"])
            button.grid_remove()  # Retain the testing controls for later use.
            self.rocker_buttons.append(button)
        controls = ttk.Frame(content, padding=PADDING["controls"])
        controls.grid(row=2, column=0, columnspan=2, sticky="ew")
        controls.columnconfigure((0, 1, 2), weight=1, uniform="controls")
        controls.columnconfigure(1, weight=SIZES["play_button_weight"])
        self.button_icons = appearance.create_button_icons(window)
        self.play_pause_button = ttk.Button(controls, text="Play", style="Touch.TButton",
                                            compound="left", command=self.toggle_playback)
        self.reset_button = ttk.Button(controls, text="Reset", style="Touch.TButton", compound="left",
                                       image=(self.button_icons["reset", "normal"],
                                              "disabled", self.button_icons["reset", "disabled"]),
                                       command=self.reset)
        self.settings_button = ttk.Button(controls, text="Settings", style="Touch.TButton",
                                          compound="left",
                                          image=(self.button_icons["settings", "normal"],
                                                 "disabled", self.button_icons["settings", "disabled"]),
                                          command=self.show_settings)
        for column, button in enumerate((self.settings_button,
                                         self.play_pause_button, self.reset_button)):
            button.grid(row=0, column=column, sticky="ew", padx=PADDING["button_gap"])
        window.bind("<Left>", lambda event: self.rocker(0))
        window.bind("<Right>", lambda event: self.rocker(1))
        window.bind("<Escape>", lambda event: window.attributes("-fullscreen", False))
        self.build_settings()
        self.show_settings()
        self.tick()

    def build_settings(self):
        self.settings_frame = ttk.Frame(self.window, padding=PADDING["settings"])
        self.settings_frame.grid(row=0, column=0, sticky="nsew")
        self.settings_frame.columnconfigure((0, 1), weight=1, uniform="settings")
        self.settings_frame.rowconfigure(0, weight=1)
        starting_seconds = min(STARTING_TIMES, key=lambda seconds: abs(seconds - self.clock.initial_seconds))
        self.settings_minutes = StringVar(self.window, value=starting_time_label(starting_seconds))
        self.settings_increment = StringVar(self.window, value=f"{int(self.clock.increment):+d}")
        self.settings_readouts = []
        for column, (label, variable, minimum, maximum) in enumerate((
            ("Starting time · minutes", self.settings_minutes, 1, 180),
            ("Increment per move · seconds", self.settings_increment, 0, 60),
        )):
            setting = ttk.Frame(self.settings_frame)
            setting.grid(row=0, column=column, sticky="nsew", padx=PADDING["setting_horizontal"], pady=PADDING["setting_vertical"])
            setting.columnconfigure((0, 1), weight=1, uniform="adjustments")
            setting.rowconfigure(1, weight=1)
            ttk.Label(setting, text=label, style="SettingsLabel.TLabel",
                      anchor="center", justify="center").grid(
                row=0, column=0, columnspan=2, sticky="ew")
            number_area = Canvas(setting, width=1, height=1, borderwidth=0, highlightthickness=0)
            number_area.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=PADDING["settings_number_vertical"])
            number_font = appearance.create_font(self.window, "settings_number")
            shadow = number_area.create_text(0, 0, anchor="nw", font=number_font, fill=COLORS["shadow"])
            number = number_area.create_text(0, 0, anchor="nw", font=number_font)
            self.settings_readouts.append((variable, number_area, number_font, shadow, number))
            number_area.bind("<Configure>", lambda event: self.draw_settings_numbers())
            variable.trace_add("write", lambda *_: self.draw_settings_numbers())
            for button_column, (text, delta) in enumerate((("−", -1), ("+", 1))):
                ttk.Button(setting, text=text, width=SIZES["adjustment_button_width"],
                           style="Adjustment.Touch.TButton",
                           command=lambda v=variable, d=delta, lo=minimum, hi=maximum:
                           self.adjust_setting(v, d, lo, hi)).grid(
                               row=2, column=button_column, sticky="ew", padx=PADDING["button_gap"])
        rockers = ttk.Frame(self.settings_frame)
        rockers.grid(row=1, column=0, columnspan=2, sticky="ew")
        rockers.grid_remove()  # Retain the testing controls for later use.
        rockers.columnconfigure((0, 1), weight=1, uniform="rockers")
        for side, label in enumerate(("Left player", "Right player")):
            ttk.Button(rockers, text=label, style="Touch.TButton",
                       command=lambda side=side: self.rocker(side)).grid(row=0, column=side, sticky="ew", padx=PADDING["button_gap"])
        self.ready_button = ttk.Button(self.settings_frame, text="Ready to play", style="Touch.TButton",
                                      command=self.apply_settings)
        self.reset_wins_button = ttk.Button(self.settings_frame, text="Reset win count",
                                            style="Touch.TButton", command=self.reset_win_counts)
        self.reset_wins_button.grid(row=2, column=0, sticky="ew", padx=PADDING["button_gap"])
        self.ready_button.grid(row=2, column=1, sticky="ew", padx=PADDING["button_gap"])
        self.draw_settings_numbers()

    def draw_settings_numbers(self):
        style = ttk.Style(self.window)
        background = style.lookup("TFrame", "background") or self.window.cget("background")
        foreground = style.lookup("TLabel", "foreground") or COLORS["foreground"]
        for variable, area, font, shadow, number in self.settings_readouts:
            area.configure(background=background)
            width = area.winfo_width() - SIZES["timer_inset"]
            height = area.winfo_height() - SIZES["timer_inset"]
            if width > 0 and height > 0:
                base_size = abs(FONTS["settings_number"][1])
                font.configure(size=-base_size)
                samples = ("180", "0:45", "0:30") if variable is self.settings_minutes else ("+60",)
                required_width = max(font.measure(sample) for sample in samples)
                scale = min(width / required_width,
                            height / (base_size * SIZES["number_cap_height_ratio"]))
                font.configure(size=-max(1, int(base_size * scale)))
            ink_height = abs(font.cget("size")) * SIZES["number_cap_height_ratio"]
            x = (area.winfo_width() - font.measure(variable.get()) - SIZES["shadow_offset"]) / 2
            y = ((area.winfo_height() - SIZES["shadow_offset"] + ink_height) / 2
                 - font.metrics("ascent"))
            area.coords(shadow, x + SIZES["shadow_offset"], y + SIZES["shadow_offset"])
            area.coords(number, x, y)
            area.itemconfigure(shadow, text=variable.get())
            area.itemconfigure(number, text=variable.get(), fill=foreground)

    def adjust_setting(self, variable, delta, minimum, maximum):
        if variable is self.settings_minutes:
            index = STARTING_TIMES.index(self.starting_seconds())
            index = max(0, min(len(STARTING_TIMES) - 1, index + delta))
            variable.set(starting_time_label(STARTING_TIMES[index]))
            return
        value = max(minimum, min(maximum, int(variable.get()) + delta))
        variable.set(f"{value:+d}" if variable is self.settings_increment else str(value))

    def starting_seconds(self):
        value = self.settings_minutes.get()
        return int(value.split(":")[1]) if ":" in value else int(value) * 60

    def show_settings(self):
        if self.clock.started:
            return
        self.cancel_reset_confirmation()
        self.settings_visible = True
        self.game_frame.grid_remove()
        self.settings_frame.grid()

    def apply_settings(self):
        if self.clock.started:
            return
        self.clock.configure_seconds(self.starting_seconds(), int(self.settings_increment.get()))
        self.settings_visible = False
        self.settings_frame.grid_remove()
        self.game_frame.grid()
        self.render()

    def toggle_playback(self):
        if self.settings_visible:
            return
        if self.clock.running:
            self.clock.pause()
        else:
            self.cancel_reset_confirmation()
            self.clock.start()
        self.render()

    def reset(self):
        self.clock.update()
        current = monotonic()
        if self.clock.expired is not None or (
                self._reset_deadline is not None and current < self._reset_deadline):
            self.cancel_reset_confirmation()
            self.clock.reset()
        else:
            self._reset_deadline = current + 5
            self._winner_selection_armed = self.clock.started
        self.render()

    def cancel_reset_confirmation(self):
        self._reset_deadline = None
        self._winner_selection_armed = False

    def declare_winner(self, player):
        self.clock.update()
        if (self._winner_selection_armed and self._reset_deadline is not None
                and monotonic() < self._reset_deadline):
            if self.clock.declare_winner(player):
                self.cancel_reset_confirmation()
        self.render()

    def reset_win_counts(self):
        self.clock.reset_win_counts()
        self.render()

    def rocker(self, player):
        self.clock.press_rocker(player)
        self.render()
        return "break"

    def draw_time_bar(self, player):
        bar = self.time_bars[player]
        fill = self.time_bar_fills[player]
        fraction = max(0, min(1, self.clock.remaining[player] / self.clock.initial_seconds))
        width = bar.winfo_width()
        # Each bar remains anchored at the center seam as its outer end recedes.
        left, right = (width * (1 - fraction), width) if player == 0 else (0, width * fraction)
        bar.coords(fill, left, 0, right, bar.winfo_height())
        active = player == self.clock.active
        if self.clock.remaining[player] < 30:
            color = COLORS["warning_active" if active else "warning_inactive"]
            if active and self.clock.running and self.clock.remaining[player] < 10:
                color = COLORS["warning_active" if int(monotonic() * 4) % 2 == 0 else "warning_inactive"]
        else:
            color = COLORS["foreground" if active else "muted_foreground"]
        bar.itemconfigure(fill, fill=color, state="normal" if fraction > 0 else "hidden")

    def draw_time_numbers(self, player, whole, fraction, background, foreground):
        area = self.timer_areas[player]
        area.configure(background=background)
        available_width = area.winfo_width() - SIZES["timer_inset"]
        available_height = area.winfo_height() - SIZES["timer_inset"]
        layout = (len(whole), len(fraction), available_width, available_height)
        large_font, small_font = self.timer_fonts[player]
        if available_width > 0 and available_height > 0 and layout != self.timer_layouts[player]:
            large_font.configure(size=FONTS["timer"][1])
            small_font.configure(size=FONTS["fraction"][1])
            # Reserve the widest digit to keep the size stable as time changes.
            large_digit = max(large_font.measure(str(n)) for n in range(10))
            small_digit = max(small_font.measure(str(n)) for n in range(10))
            required_width = sum(large_digit if c.isdigit() else large_font.measure(c) for c in whole)
            required_width += sum(small_digit if c.isdigit() else small_font.measure(c) for c in fraction)
            scale = min(available_width / required_width,
                        available_height / large_font.metrics("linespace"))
            # Enlarge the fitted digits while retaining the width limit for
            # long times and fractional seconds.
            scale = min(scale * SIZES["timer_scale"], available_width / required_width)
            if fraction or sum(character.isdigit() for character in whole) == 3:
                # Short times can fill the area using the visible digit height,
                # rather than reserving the font's large ascent/descent margins.
                digit_height = abs(FONTS["timer"][1]) * (
                    SIZES["number_cap_height_ratio"] + SIZES["number_overshoot_ratio"])
                scale = min(available_width / required_width, available_height / digit_height)
            large_font.configure(size=-max(1, int(abs(FONTS["timer"][1]) * scale)))
            small_font.configure(size=-max(1, int(abs(FONTS["fraction"][1]) * scale)))
            self.timer_layouts[player] = layout

        text_width = large_font.measure(whole) + small_font.measure(fraction)
        x = (area.winfo_width() - text_width - SIZES["shadow_offset"]) / 2
        ink_height = abs(large_font.cget("size")) * SIZES["number_cap_height_ratio"]
        y = ((area.winfo_height() - SIZES["shadow_offset"] + ink_height) / 2
             - large_font.metrics("ascent"))
        fraction_x = x + large_font.measure(whole)
        fraction_y = y + large_font.metrics("ascent") - small_font.metrics("ascent")
        for text, front, shadow, left, top in (
            (whole, self.times[player], self.time_shadows[player], x, y),
            (fraction, self.fractions[player], self.fraction_shadows[player], fraction_x, fraction_y),
        ):
            state = "normal" if text else "hidden"
            area.coords(shadow, left + SIZES["shadow_offset"], top + SIZES["shadow_offset"])
            area.itemconfigure(shadow, text=text, state=state)
            area.coords(front, left, top)
            area.itemconfigure(front, text=text, fill=foreground, state=state)

    def statistics_parts(self, player):
        stats = self.clock.move_statistics(player)
        return [(label, f"{stats[key]:.2f}s" if stats[key] is not None else "-")
                for key, label in (("average", "Average"), ("shortest", "Fastest"),
                                   ("longest", "Slowest"))]

    def draw_statistics(self, player):
        area = self.statistics_areas[player]
        normal_font, bold_font = self.statistics_fonts[player]
        normal_font.configure(size=FONTS["statistics"][1])
        bold_font.configure(size=FONTS["statistics_value"][1])
        parts = self.statistics_parts(player)
        runs = []
        for index, (label, value) in enumerate(parts):
            runs.extend(((f"{' ' if index else ''}{label}: ", normal_font), (value, bold_font)))
        width = sum(font.measure(text) for text, font in runs)
        # Fit the compact row independently of the main clock digits.
        available_width = max(1, area.winfo_width() - 4)
        if width > available_width:
            scale = available_width / width
            normal_font.configure(size=max(1, int(FONTS["statistics"][1] * scale)))
            bold_font.configure(size=max(1, int(FONTS["statistics_value"][1] * scale)))
            width = sum(font.measure(text) for text, font in runs)
            while width > available_width and normal_font.cget("size") > 1:
                normal_font.configure(size=normal_font.cget("size") - 1)
                bold_font.configure(size=max(1, bold_font.cget("size") - 1))
                width = sum(font.measure(text) for text, font in runs)
        line_height = max(normal_font.metrics("linespace"), bold_font.metrics("linespace"))
        center_x, center_y = area.winfo_width() / 2, area.winfo_height() / 2
        foreground = COLORS["muted_foreground"]
        area.delete("all")
        area.create_text(center_x, center_y - line_height / 2, text="Move statistics:",
                         font=normal_font, fill=foreground, anchor="center")
        x = center_x - width / 2
        for text, font in runs:
            area.create_text(x, center_y + line_height / 2, text=text,
                             font=font, fill=foreground, anchor="w")
            x += font.measure(text)

    def render(self):
        clock = self.clock
        current = monotonic()
        paused = clock.started and not clock.running and clock.expired is None
        if not paused:
            self._resume_flash_started = None
        elif self._resume_flash_started is None:
            self._resume_flash_started = current
        hide_resume = (self._resume_flash_started is not None
                       and int((current - self._resume_flash_started) * 2) % 2 == 1)
        if clock.expired is None:
            self._timeout_flash_started = None
        elif self._timeout_flash_started is None:
            self._timeout_flash_started = current
        hide_expired = (self._timeout_flash_started is not None
                        and int((current - self._timeout_flash_started) * 2) % 2 == 1)
        reset_seconds = 0
        if self._reset_deadline is not None:
            reset_seconds = max(0, ceil(self._reset_deadline - current))
            if reset_seconds == 0:
                self.cancel_reset_confirmation()
        show_winner_buttons = (self._winner_selection_armed and reset_seconds > 0
                               and clock.started and clock.expired is None)
        self.reset_button.configure(text=f"Reset? {reset_seconds}" if reset_seconds else "Reset")
        style = ttk.Style(self.window)
        self.settings_button.state(["disabled"] if clock.started else ["!disabled"])
        for player in (0, 1):
            self.draw_time_bar(player)
            selected = player == clock.active
            expired = player == clock.expired
            background, foreground = appearance.configure_player(
                style, player, active=selected, expired=expired, started=clock.started,
                game_ended=clock.expired is not None,
                paused=clock.started and not clock.running and clock.expired is None)
            side_name = "Left" if player == 0 else "Right"
            if clock.expired is not None:
                heading = "Time expired!" if expired else "Winner!"
            else:
                heading = f"{side_name} · {clock.color(player)}"
            self.names[player].configure(text=f"{heading} · Wins: {clock.wins[player]}")
            if show_winner_buttons:
                self.names[player].place_forget()
                self.winner_buttons[player].place(x=0, y=0, relwidth=1, relheight=1)
            else:
                self.winner_buttons[player].place_forget()
                self.names[player].place(x=0, y=0, relwidth=1, relheight=1)
            if expired:
                whole, fraction = "0:00", ""
            else:
                whole, separator, hundredths = format_time(clock.remaining[player]).partition(".")
                if clock.remaining[player] < 10:
                    whole = whole.partition(":")[2].lstrip("0") or "0"
                fraction = separator + hundredths
            self.draw_time_numbers(player, whole, fraction, background, foreground)
            if expired and hide_expired:
                # Hide both the digits and shadow without altering their layout.
                self.timer_areas[player].itemconfigure(self.times[player], state="hidden")
                self.timer_areas[player].itemconfigure(self.time_shadows[player], state="hidden")
            indicator = "Waiting"
            show_statistics = clock.started and not clock.running
            if show_statistics:
                indicator = "Move statistics:\n" + " ".join(
                    f"{label}: {value}" for label, value in self.statistics_parts(player))
            elif selected:
                if clock.running:
                    indicator = "Your turn"
                elif not clock.started:
                    indicator = "Ready"
                else:
                    indicator = "Paused"
            self.indicators[player].configure(text=indicator,
                                               style=f"Statistics.Player{player}.TLabel" if show_statistics
                                               else f"Indicator.Player{player}.TLabel",
                                               justify="center")
            statistics_area = self.statistics_areas[player]
            if show_statistics:
                self.indicators[player].place_forget()
                statistics_area.configure(background=background)
                statistics_area.place(x=0, y=0, relwidth=1, relheight=1)
                self.draw_statistics(player)
            else:
                statistics_area.place_forget()
                self.indicators[player].place(x=0, rely=.5, y=SIZES["indicator_offset_y"],
                                               anchor="w", relwidth=1, relheight=0,
                                               height=self.indicator_text_height)
        if clock.expired is not None:
            message = f"{clock.color(clock.expired)} ran out of time — reset to play again"
        elif not clock.started:
            starting_time = (f"{clock.initial_seconds:g} sec" if clock.initial_seconds < 60
                             else f"{clock.initial_seconds // 60:g} min")
            message = (f"{starting_time} + {clock.increment:g} sec per move"
                       " · Last rocker pressed is Black")
        else:
            player = clock.color(clock.active)
            message = f"{player} to move" if clock.running else f"Paused — {player} to move"
        if clock.started:
            message += f". Turn {clock.turn_number}"
        self.status.configure(text=message)
        symbol = "pause" if clock.running else "play"
        self.play_pause_button.configure(
            style="PlaybackHidden.Touch.TButton" if hide_resume else "Touch.TButton",
            text="Pause" if clock.running else "Resume" if clock.started else "Play",
            image=(self.button_icons[symbol, "hidden" if hide_resume else "normal"],
                   "disabled", self.button_icons[symbol, "disabled"]))
        self.play_pause_button.state(["disabled"] if clock.expired is not None else ["!disabled"])
        for button in self.rocker_buttons:
            button.state(["!disabled"] if not clock.started or clock.running else ["disabled"])

    def tick(self):
        self.clock.update()
        self.render()
        interval = 10 if self.clock.running and self.clock.remaining[self.clock.active] < 10 else 50
        self._job = self.window.after(interval, self.tick)

    def close(self):
        if self._job is not None:
            self.window.after_cancel(self._job)
        self.window.destroy()


def create_window(theme: str = appearance.THEME_NAME, seconds: float = 300, increment: int = 0) -> ThemedTk:
    clock = ChessClock(seconds, increment=increment)
    window = ThemedTk()
    try:
        appearance.install_theme(window, theme)
    except ValueError:
        window.destroy()
        raise
    window.clock_ui = ClockUI(window, clock)
    return window


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", default=appearance.THEME_NAME,
                        help=f"Initial ttk theme (default: {appearance.THEME_NAME})")
    parser.add_argument("--minutes", type=int, choices=range(1, 181), metavar="1-180",
                        default=5, help="Starting minutes per player (default: 5)")
    parser.add_argument("--increment", type=int, choices=range(0, 61), metavar="0-60",
                        default=0, help="Increment seconds per move (default: 0)")
    parser.add_argument("--fullscreen", action="store_true", help="Fill the TFT display; Escape exits fullscreen")
    args = parser.parse_args()
    try:
        window = create_window(args.theme, seconds=args.minutes * 60, increment=args.increment)
    except ValueError as error:
        parser.error(str(error))
    if args.fullscreen:
        window.attributes("-fullscreen", True)
    window.mainloop()


if __name__ == "__main__":
    main()
