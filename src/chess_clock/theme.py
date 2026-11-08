"""Chess Clock appearance, including ttk widgets and custom canvas drawings.

Edit the fonts, colours and dimensions here to customize the application.
Positive font sizes are points; negative sizes are pixels (for fitted timers).
"""

from math import cos, pi, sin
from tkinter import ttk
from tkinter.font import Font

from PIL import Image, ImageDraw, ImageTk


THEME_NAME = "chess-clock"
BASE_THEME = "black"

FONTS = {
    "player_title": ("Inter", 16, "bold"),
    "body": ("Inter", 12),
    "statistics": ("Inter", 12),
    "statistics_value": ("Inter", 12, "bold"),
    "button": ("Inter", 14, "bold"),
    "adjustment_button": ("Inter", 28, "bold"),
    "settings_title": ("Inter", 24, "bold"),
    "settings_label": ("Inter", 15),
    "settings_number": ("Bebas Neue", -240, "normal"),
    "timer": ("Bebas Neue", -160, "normal"),
    "fraction": ("Bebas Neue", -64, "normal"),
}

COLORS = {
    "background": "#1a1a1a",  # 10% grey.
    "active_background": "#14532d",
    "active_background_paused": "#0b301a",
    "ready_background": "#606060",
    "inactive_background": "#303030",
    "winner_button_background": "#606060",
    "pressed_background": "#1d355c",
    "expired_background": "#9b2638",
    "foreground": "#ffffff",
    "muted_foreground": "#c8c8c8",
    "disabled_foreground": "#777777",
    "shadow": "#000000",
    "divider": "#000000",
    "bar_background": "#1a1a1a",
    "warning_active": "#ffeb3b",
    "warning_inactive": "#e65c00",
}

SIZES = {
    "window_width": 800,
    "window_height": 480,
    "bar_height": 24,
    "divider_width": 4,
    "bottom_line_height": 4,
    "shadow_offset": 6,
    "timer_inset": 8,
    "timer_scale": 1.2,
    "number_cap_height_ratio": 0.7,  # Bebas Neue: 700-unit capitals / 1000 units per em.
    "number_overshoot_ratio": 0.03,  # Room for round digits extending past the cap height.
    "indicator_offset_y": 10,
    "adjustment_button_width": 3,
    "play_button_weight": 2,
    "button_icon_size": 18,
}

PADDING = {
    "card": (18, 9, 18, 12),
    "button": (12, 12),
    "controls": (12, 16, 12, 16),
    "button_gap": 4,
    "icon_gap": 8,
    "status_vertical": (0, 10),
    "rocker_vertical": (0, 10),
    "settings": 24,
    "settings_title_vertical": (0, 16),
    "setting_horizontal": 8,
    "setting_vertical": (8, 16),
    "settings_number_vertical": 8,
}


def create_font(window, role: str) -> Font:
    """Return an independent font so fitting one timer cannot resize another."""
    return Font(window, font=FONTS[role])


def create_button_icons(window):
    """Draw monochrome button symbols without relying on font glyphs."""
    size = SIZES["button_icon_size"]
    scale = 4
    icons = {}
    for symbol in ("play", "pause", "settings", "reset"):
        for state, color in (("normal", COLORS["muted_foreground"]),
                             ("disabled", COLORS["disabled_foreground"])):
            image = Image.new("RGBA", (size * scale, size * scale))
            draw = ImageDraw.Draw(image)
            extent = size * scale - 1
            if symbol == "play":
                draw.polygon([(extent * .2, extent * .1),
                              (extent * .9, extent * .5),
                              (extent * .2, extent * .9)], fill=color)
            elif symbol == "pause":
                for left, right in ((.15, .4), (.6, .85)):
                    draw.rectangle((extent * left, extent * .1,
                                    extent * right, extent * .9), fill=color)
            elif symbol == "settings":
                teeth = []
                for step in range(32):
                    angle = 2 * pi * step / 32
                    radius = extent * (.46 if step % 4 in (1, 2) else .35)
                    teeth.append((extent / 2 + radius * cos(angle),
                                  extent / 2 + radius * sin(angle)))
                draw.polygon(teeth, fill=color)
                draw.ellipse((extent * .34, extent * .34,
                              extent * .66, extent * .66), fill=(0, 0, 0, 0))
            else:
                # Arrowhead at the upper-left end points down the left side:
                # following the circle from the top gives anticlockwise motion.
                draw.arc((extent * .14, extent * .14,
                          extent * .86, extent * .86),
                         start=225, end=495, fill=color, width=max(1, round(extent * .12)))
                draw.polygon([(extent * .10, extent * .43),
                              (extent * .12, extent * .08),
                              (extent * .43, extent * .32)], fill=color)
            image = image.resize((size, size), Image.Resampling.LANCZOS)
            icons[symbol, state] = ImageTk.PhotoImage(image, master=window)
    icons["play", "hidden"] = ImageTk.PhotoImage(
        Image.new("RGBA", (size, size)), master=window)
    return icons


def configure_player(style: ttk.Style, player: int, *, active: bool, expired: bool,
                     started: bool = True, game_ended: bool = False, paused: bool = False):
    ready = active and not started and not expired
    background = COLORS["expired_background" if expired else
                        "ready_background" if ready else
                        "active_background_paused" if active and paused else
                        "active_background" if active else "inactive_background"]
    highlighted = not expired if game_ended else active
    foreground = COLORS["foreground" if highlighted else "muted_foreground"]
    style.configure(f"Player{player}.TFrame", background=background,
                    borderwidth=0, relief="flat")
    style.configure(f"Player{player}.TLabel", background=background,
                    foreground=COLORS["muted_foreground"])
    return background, foreground


def install_theme(window, selected: str = THEME_NAME) -> None:
    """Register the black-derived theme and apply the selected theme's app styles.

Keep --theme compatible with the other ttkthemes themes. Their app-specific
styles are initialized separately, without changing the black parent theme.
"""
    window.set_theme(BASE_THEME)  # Load the parent's elements and image assets.
    style = ttk.Style(window)
    if THEME_NAME not in style.theme_names():
        style.theme_create(THEME_NAME, parent=BASE_THEME)
    themes = sorted(set(window.get_themes()) | {THEME_NAME})
    if selected not in themes:
        raise ValueError(f"Unknown theme {selected!r}. Available: {', '.join(themes)}")
    if selected == THEME_NAME:
        style.theme_use(selected)
        window.configure(background=COLORS["background"])
        style.configure("TFrame", background=COLORS["background"])
        style.configure(".", foreground=COLORS["muted_foreground"], font=FONTS["body"])
        style.configure("TLabel", background=COLORS["background"],
                        foreground=COLORS["muted_foreground"])
        style.configure("TButton", background=COLORS["inactive_background"],
                        foreground=COLORS["muted_foreground"], focusthickness=0)
        # Override the black parent's hover/disabled background mappings.
        style.map("TButton", background=[("disabled", COLORS["inactive_background"]),
                                         ("pressed", COLORS["pressed_background"]),
                                         ("active", COLORS["inactive_background"])],
                  foreground=[("disabled", COLORS["disabled_foreground"]),
                              ("!disabled", COLORS["muted_foreground"])])
        # Omit Button.focus entirely: the inherited focus element can still
        # draw its dotted rectangle on Windows despite focusthickness=0.
        style.layout("Touch.TButton", [
            ("Button.border", {"sticky": "nswe", "border": "1", "children": [
                ("Button.padding", {"sticky": "nswe", "children": [
                    ("Button.label", {"sticky": "nswe"}),
                ]}),
            ]}),
        ])
    else:
        window.set_theme(selected)
    style.configure("Touch.TButton", font=FONTS["button"], padding=PADDING["button"],
                    anchor="center", justify="center", space=PADDING["icon_gap"])
    # Match the button background to hide only its text, retaining its layout.
    style.configure("PlaybackHidden.Touch.TButton",
                    foreground=style.lookup("Touch.TButton", "background"))
    style.map("PlaybackHidden.Touch.TButton", foreground=[
        ("pressed", style.lookup("Touch.TButton", "background", ("pressed",))),
        ("active", style.lookup("Touch.TButton", "background", ("active",))),
        ("", style.lookup("Touch.TButton", "background")),
    ])
    style.configure("Adjustment.Touch.TButton", font=FONTS["adjustment_button"])
    style.configure("Winner.Touch.TButton", padding=(8, 0),
                    background=COLORS["winner_button_background"])
    style.map("Winner.Touch.TButton", background=[
        ("disabled", COLORS["winner_button_background"]),
        ("pressed", COLORS["pressed_background"]),
        ("", COLORS["winner_button_background"]),
    ])
    style.configure("Status.TLabel", font=FONTS["body"])
    style.configure("SettingsTitle.TLabel", font=FONTS["settings_title"])
    style.configure("SettingsLabel.TLabel", font=FONTS["settings_label"], anchor="center")
    for player in (0, 1):
        style.configure(f"Title.Player{player}.TLabel", font=FONTS["player_title"])
        style.configure(f"Indicator.Player{player}.TLabel", font=FONTS["body"])
        style.configure(f"Statistics.Player{player}.TLabel", font=FONTS["statistics"])
        configure_player(style, player, active=player == 0, expired=False, started=False)
