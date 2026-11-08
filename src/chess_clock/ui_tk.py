"""Touch-friendly chess clock for an 800 × 480 screen."""

import argparse
from time import monotonic
from tkinter import Canvas, StringVar, ttk
from tkinter.font import Font

from ttkthemes import ThemedTk

from chess_clock.clock import ChessClock, format_time


class ClockUI:
    def __init__(self, window: ThemedTk, clock: ChessClock):
        self.window = window
        self.clock = clock
        self._job = None
        window.title("Chess Clock")
        window.geometry("800x480")
        window.minsize(800, 480)
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
        self.times = []
        self.fractions = []
        self.time_shadows = []
        self.fraction_shadows = []
        self.timer_fonts = []
        self.timer_areas = []
        self.timer_layouts = [None, None]
        self.indicators = []
        self.time_bars = []
        self.time_bar_fills = []
        for player, name in enumerate(("LEFT", "RIGHT")):
            field = ttk.Frame(content, style=f"Player{player}.TFrame")
            field.grid(row=0, column=player, sticky="nsew")
            field.columnconfigure(0, weight=1)
            field.rowconfigure(1, weight=1)
            bar = Canvas(field, height=24, width=1, background="#505050",
                         borderwidth=0, highlightthickness=0)
            bar.grid(row=0, column=0, sticky="ew")
            fill = bar.create_rectangle(0, 0, 0, 24, fill="#c8c8c8", outline="")
            self.time_bars.append(bar)
            self.time_bar_fills.append(fill)
            bar.bind("<Configure>", lambda event, side=player: self.draw_time_bar(side))
            card = ttk.Frame(field, padding=18, style=f"Player{player}.TFrame")
            card.grid(row=1, column=0, sticky="nsew")
            card.columnconfigure(0, weight=1)
            card.rowconfigure(1, weight=1)
            title = ttk.Label(card, text=name, font=("DejaVu Sans", 16, "bold"),
                              anchor="center", style=f"Player{player}.TLabel")
            title.grid(row=0, column=0, sticky="ew")
            timer_area = Canvas(card, width=1, height=1, borderwidth=0, highlightthickness=0)
            timer_area.grid(row=1, column=0, sticky="nsew")
            large_font = Font(window, family="Liberation Sans Narrow", size=-160, weight="bold")
            small_font = Font(window, family="Liberation Sans Narrow", size=-64, weight="bold")
            # Create both shadows first so all foreground text sits above them.
            time_shadow = timer_area.create_text(0, 0, anchor="nw", font=large_font, fill="#000000")
            fraction_shadow = timer_area.create_text(0, 0, anchor="nw", font=small_font, fill="#000000")
            timer = timer_area.create_text(0, 0, anchor="nw", font=large_font)
            fraction = timer_area.create_text(0, 0, anchor="nw", font=small_font)
            indicator = ttk.Label(card, anchor="center", font=("DejaVu Sans", 12),
                                  style=f"Player{player}.TLabel")
            indicator.grid(row=2, column=0, sticky="ew")
            self.cards.append(card)
            self.names.append(title)
            self.times.append(timer)
            self.fractions.append(fraction)
            self.time_shadows.append(time_shadow)
            self.fraction_shadows.append(fraction_shadow)
            self.timer_fonts.append((large_font, small_font))
            self.timer_areas.append(timer_area)
            self.indicators.append(indicator)

        divider = Canvas(content, width=4, height=1, background="#000000",
                         borderwidth=0, highlightthickness=0)
        divider.grid(row=0, column=0, columnspan=2, sticky="ns")
        bottom_line = Canvas(content, width=1, height=2, background="#000000",
                             borderwidth=0, highlightthickness=0)
        bottom_line.grid(row=1, column=0, columnspan=2, sticky="ew")

        self.status = ttk.Label(content, anchor="center", font=("DejaVu Sans", 12))
        self.status.grid(row=2, column=0, columnspan=2, sticky="ew", pady=10)
        self.rocker_buttons = []
        for side, label in enumerate(("Left player", "Right player")):
            button = ttk.Button(content, text=label, style="Touch.TButton",
                                command=lambda side=side: self.rocker(side))
            button.grid(row=3, column=side, sticky="ew", padx=4, pady=(0, 10))
            button.grid_remove()  # Retain the testing controls for later use.
            self.rocker_buttons.append(button)
        controls = ttk.Frame(content, padding=(12, 0, 12, 16))
        controls.grid(row=4, column=0, columnspan=2, sticky="ew")
        controls.columnconfigure((0, 1, 2, 3), weight=1, uniform="controls")
        self.start_button = ttk.Button(controls, text="Start", style="Touch.TButton", command=self.start)
        self.pause_button = ttk.Button(controls, text="Pause", style="Touch.TButton", command=self.pause)
        self.reset_button = ttk.Button(controls, text="Reset", style="Touch.TButton", command=self.reset)
        self.settings_button = ttk.Button(controls, text="Settings", style="Touch.TButton",
                                          command=self.show_settings)
        for column, button in enumerate((self.start_button, self.pause_button,
                                         self.reset_button, self.settings_button)):
            button.grid(row=0, column=column, sticky="ew", padx=4)
        window.bind("<Left>", lambda event: self.rocker(0))
        window.bind("<Right>", lambda event: self.rocker(1))
        window.bind("<Escape>", lambda event: window.attributes("-fullscreen", False))
        self.build_settings()
        self.show_settings()
        self.tick()

    def build_settings(self):
        self.settings_frame = ttk.Frame(self.window, padding=24)
        self.settings_frame.grid(row=0, column=0, sticky="nsew")
        self.settings_frame.columnconfigure((0, 1), weight=1, uniform="settings")
        self.settings_frame.rowconfigure(1, weight=1)
        self.settings_minutes = StringVar(self.window, value=str(max(1, round(self.clock.initial_seconds / 60))))
        self.settings_increment = StringVar(self.window, value=f"{int(self.clock.increment):+d}")
        ttk.Label(self.settings_frame, text="Game settings", font=("DejaVu Sans", 24, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 16))
        self.settings_readouts = []
        for column, (label, variable, minimum, maximum) in enumerate((
            ("Starting time · minutes", self.settings_minutes, 1, 180),
            ("Increment per move · seconds", self.settings_increment, 0, 60),
        )):
            setting = ttk.Frame(self.settings_frame)
            setting.grid(row=1, column=column, sticky="nsew", padx=8, pady=(8, 16))
            setting.columnconfigure((0, 1), weight=1, uniform="adjustments")
            setting.rowconfigure(1, weight=1)
            ttk.Label(setting, text=label, font=("DejaVu Sans", 15), anchor="center").grid(
                row=0, column=0, columnspan=2, sticky="ew")
            number_area = Canvas(setting, width=1, height=1, borderwidth=0, highlightthickness=0)
            number_area.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=8)
            number_font = Font(self.window, family="Liberation Sans Narrow", size=128, weight="bold")
            shadow = number_area.create_text(0, 0, font=number_font, fill="#000000")
            number = number_area.create_text(0, 0, font=number_font)
            self.settings_readouts.append((variable, number_area, number_font, shadow, number))
            number_area.bind("<Configure>", lambda event: self.draw_settings_numbers())
            variable.trace_add("write", lambda *_: self.draw_settings_numbers())
            for button_column, (text, delta) in enumerate((("−", -1), ("+", 1))):
                ttk.Button(setting, text=text, width=3, style="Touch.TButton",
                           command=lambda v=variable, d=delta, lo=minimum, hi=maximum:
                           self.adjust_setting(v, d, lo, hi)).grid(
                               row=2, column=button_column, sticky="ew", padx=4)
        rockers = ttk.Frame(self.settings_frame)
        rockers.grid(row=2, column=0, columnspan=2, sticky="ew")
        rockers.grid_remove()  # Retain the testing controls for later use.
        rockers.columnconfigure((0, 1), weight=1, uniform="rockers")
        for side, label in enumerate(("Left player", "Right player")):
            ttk.Button(rockers, text=label, style="Touch.TButton",
                       command=lambda side=side: self.rocker(side)).grid(row=0, column=side, sticky="ew", padx=4)
        self.ready_button = ttk.Button(self.settings_frame, text="Continue to clock", style="Touch.TButton",
                                      command=self.apply_settings)
        self.ready_button.grid(row=3, column=0, columnspan=2, sticky="ew")
        self.draw_settings_numbers()

    def draw_settings_numbers(self):
        style = ttk.Style(self.window)
        background = style.lookup("TFrame", "background") or self.window.cget("background")
        foreground = style.lookup("TLabel", "foreground") or "#ffffff"
        for variable, area, _font, shadow, number in self.settings_readouts:
            area.configure(background=background)
            x = (area.winfo_width() - 6) / 2
            y = (area.winfo_height() - 6) / 2
            area.coords(shadow, x + 6, y + 6)
            area.coords(number, x, y)
            area.itemconfigure(shadow, text=variable.get())
            area.itemconfigure(number, text=variable.get(), fill=foreground)

    def adjust_setting(self, variable, delta, minimum, maximum):
        value = max(minimum, min(maximum, int(variable.get()) + delta))
        variable.set(f"{value:+d}" if variable is self.settings_increment else str(value))

    def show_settings(self):
        if self.clock.started:
            return
        self.settings_visible = True
        self.game_frame.grid_remove()
        self.settings_frame.grid()

    def apply_settings(self):
        if self.clock.started:
            return
        self.clock.configure(int(self.settings_minutes.get()), int(self.settings_increment.get()))
        self.settings_visible = False
        self.settings_frame.grid_remove()
        self.game_frame.grid()
        self.render()

    def start(self):
        if self.settings_visible:
            return
        self.clock.start()
        self.render()

    def pause(self):
        self.clock.pause()
        self.render()

    def reset(self):
        self.clock.reset()
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
            color = "#ffeb3b" if active else "#e65c00"
            if active and self.clock.running and self.clock.remaining[player] < 10:
                color = "#ffeb3b" if int(monotonic() * 4) % 2 == 0 else "#e65c00"
        else:
            color = "#ffffff" if active else "#c8c8c8"
        bar.itemconfigure(fill, fill=color, state="normal" if fraction > 0 else "hidden")

    def draw_time_numbers(self, player, whole, fraction, background, foreground):
        area = self.timer_areas[player]
        area.configure(background=background)
        available_width = area.winfo_width() - 8
        available_height = area.winfo_height() - 8
        layout = (len(whole), len(fraction), available_width, available_height)
        large_font, small_font = self.timer_fonts[player]
        if available_width > 0 and available_height > 0 and layout != self.timer_layouts[player]:
            large_font.configure(size=-160)
            small_font.configure(size=-64)
            # Reserve the widest digit to keep the size stable as time changes.
            large_digit = max(large_font.measure(str(n)) for n in range(10))
            small_digit = max(small_font.measure(str(n)) for n in range(10))
            required_width = sum(large_digit if c.isdigit() else large_font.measure(c) for c in whole)
            required_width += sum(small_digit if c.isdigit() else small_font.measure(c) for c in fraction)
            scale = min(available_width / required_width,
                        available_height / large_font.metrics("linespace"))
            large_font.configure(size=-max(1, int(160 * scale)))
            small_font.configure(size=-max(1, int(64 * scale)))
            self.timer_layouts[player] = layout

        text_width = large_font.measure(whole) + small_font.measure(fraction)
        x = (area.winfo_width() - text_width - 6) / 2
        y = (area.winfo_height() - large_font.metrics("linespace") - 6) / 2
        fraction_x = x + large_font.measure(whole)
        fraction_y = y + large_font.metrics("ascent") - small_font.metrics("ascent")
        for text, front, shadow, left, top in (
            (whole, self.times[player], self.time_shadows[player], x, y),
            (fraction, self.fractions[player], self.fraction_shadows[player], fraction_x, fraction_y),
        ):
            state = "normal" if text else "hidden"
            area.coords(shadow, left + 6, top + 6)
            area.itemconfigure(shadow, text=text, state=state)
            area.coords(front, left, top)
            area.itemconfigure(front, text=text, fill=foreground, state=state)

    def render(self):
        clock = self.clock
        style = ttk.Style(self.window)
        style.configure("Touch.TButton", font=("DejaVu Sans", 14, "bold"),
                        padding=(12, 12), anchor="center", justify="center")
        self.settings_button.state(["disabled"] if clock.started else ["!disabled"])
        for player in (0, 1):
            self.draw_time_bar(player)
            selected = player == clock.active
            expired = player == clock.expired
            background = "#9b2638" if expired else "#14532d" if selected else "#303030"
            foreground = "#ffffff" if selected or expired else "#c8c8c8"
            style.configure(f"Player{player}.TFrame", background=background,
                            borderwidth=0, relief="flat")
            style.configure(f"Player{player}.TLabel", background=background, foreground=foreground)
            side_name = "LEFT" if player == 0 else "RIGHT"
            self.names[player].configure(text=f"{side_name} · {clock.color(player).upper()}")
            whole, separator, hundredths = format_time(clock.remaining[player]).partition(".")
            fraction = separator + hundredths
            self.draw_time_numbers(player, whole, fraction, background, foreground)
            indicator = "WAITING"
            if expired:
                indicator = "TIME EXPIRED"
            elif selected:
                if clock.running:
                    indicator = "YOUR TURN"
                elif not clock.started:
                    indicator = "READY"
                else:
                    indicator = "PAUSED"
            self.indicators[player].configure(text=indicator)
        if clock.expired is not None:
            message = f"{clock.color(clock.expired)} ran out of time — reset to play again"
        elif not clock.started:
            message = (f"{clock.initial_seconds // 60:g} min + {clock.increment:g} sec per move"
                       " · Last rocker pressed is Black")
        else:
            player = clock.color(clock.active)
            message = f"{player} to move" if clock.running else f"Paused — {player} to move"
        self.status.configure(text=message)
        self.start_button.configure(text="Resume" if clock.started else "Start")
        self.start_button.state(["disabled"] if clock.running or clock.expired is not None else ["!disabled"])
        self.pause_button.state(["!disabled"] if clock.running else ["disabled"])
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


def create_window(theme: str = "black", seconds: float = 300, increment: int = 0) -> ThemedTk:
    clock = ChessClock(seconds, increment=increment)
    window = ThemedTk()
    themes = sorted(window.get_themes())
    if theme not in themes:
        window.destroy()
        raise ValueError(f"Unknown theme {theme!r}. Available: {', '.join(themes)}")
    window.set_theme(theme)
    window.clock_ui = ClockUI(window, clock)
    return window


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", default="black", help="Initial ttk theme (default: black)")
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
