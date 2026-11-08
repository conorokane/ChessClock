"""Theme integration checks; skipped when no graphical display is available."""

from tkinter import TclError, ttk
from tkinter.font import Font

import pytest
from ttkthemes import ThemedTk

from chess_clock import theme
from chess_clock.clock import ChessClock
from chess_clock.ui_tk import ClockUI


@pytest.fixture
def window():
    try:
        root = ThemedTk()
    except TclError as error:
        pytest.skip(f"Tk display unavailable: {error}")
    root.withdraw()
    yield root
    if hasattr(root, "clock_ui"):
        root.clock_ui.close()
    else:
        root.destroy()


def build_ui(window, selected=theme.THEME_NAME):
    theme.install_theme(window, selected)
    ui = window.clock_ui = ClockUI(window, ChessClock())
    return ui


def test_custom_theme_preserves_black_parent(window):
    window.set_theme("black")
    style = ttk.Style(window)
    original_button = style.configure("TButton")
    original_label = style.configure("TLabel")
    original_layout = style.layout("TButton")
    theme.install_theme(window)
    assert style.theme_use() == "chess-clock"
    assert style.layout("TButton") == original_layout
    assert style.lookup("Touch.TButton", "font")
    style.theme_use("black")
    assert style.configure("TButton") == original_button
    assert style.configure("TLabel") == original_label
    assert not style.configure("Touch.TButton")


def test_ui_fonts_and_button_layout_come_from_theme(window, monkeypatch):
    monkeypatch.setitem(theme.FONTS, "button", ("Courier", 18, "bold"))
    ui = build_ui(window)
    ui.apply_settings()
    ui.render()  # Rendering must not restore a hardcoded button font.
    style = ttk.Style(window)
    actual = Font(window, font=style.lookup("Touch.TButton", "font"))
    expected = theme.create_font(window, "button")
    assert actual.actual() == expected.actual()
    for role, widget in (("player_title", ui.names[0]), ("body", ui.indicators[0]),
                         ("body", ui.status)):
        actual = Font(window, font=style.lookup(widget["style"], "font"))
        expected = theme.create_font(window, role)
        assert actual.actual() == expected.actual()
    buttons = (ui.settings_button, ui.play_pause_button, ui.reset_button)
    assert [int(button.grid_info()["column"]) for button in buttons] == [0, 1, 2]
    assert int(ui.play_pause_button.master.columnconfigure(1)["weight"]) == 2
    assert ui.timer_fonts[0][0].name != ui.timer_fonts[1][0].name
    assert ui.settings_readouts[0][2].actual("family") == theme.create_font(
        window, "settings_number").actual("family")


def test_player_colours_and_playback_states(window):
    ui = build_ui(window)
    ui.apply_settings()
    button = ui.play_pause_button
    assert str(button["text"]) == "Play"
    button.invoke()
    assert str(button["text"]) == "Pause" and ui.clock.running
    button.invoke()
    assert str(button["text"]) == "Resume" and not ui.clock.running
    button.invoke()
    ui.rocker(0)
    assert ui.timer_areas[1]["background"] == theme.COLORS["active_background"]
    assert ui.timer_areas[0]["background"] == theme.COLORS["inactive_background"]
    ui.clock.remaining[1] = 0
    ui.clock.update()
    ui.render()
    assert button.instate(["disabled"])
    assert ui.timer_areas[1]["background"] == theme.COLORS["expired_background"]
    ui.reset()
    assert str(button["text"]) == "Play" and button.instate(["!disabled"])


@pytest.mark.parametrize("white_side", [0, 1])
def test_white_timer_is_grey_until_play_and_after_reset(window, white_side):
    ui = build_ui(window)
    ui.apply_settings()
    ui.rocker(1 - white_side)
    assert ui.timer_areas[white_side]["background"] == theme.COLORS["ready_background"]
    assert ui.timer_areas[1 - white_side]["background"] == theme.COLORS["inactive_background"]
    ui.play_pause_button.invoke()
    assert ui.timer_areas[white_side]["background"] == theme.COLORS["active_background"]
    ui.play_pause_button.invoke()
    assert ui.timer_areas[white_side]["background"] == theme.COLORS["active_background_paused"]
    assert ui.timer_areas[1 - white_side]["background"] == theme.COLORS["inactive_background"]
    ui.play_pause_button.invoke()
    assert ui.timer_areas[white_side]["background"] == theme.COLORS["active_background"]
    ui.reset_button.invoke()
    ui.reset_button.invoke()
    assert ui.timer_areas[white_side]["background"] == theme.COLORS["ready_background"]


def test_buttons_have_no_focus_outline_and_dim_disabled_text(window):
    ui = build_ui(window)
    style = ttk.Style(window)

    def elements(layout):
        for name, options in layout:
            yield name
            yield from elements(options.get("children", []))

    for name in ("Touch.TButton", "Adjustment.Touch.TButton"):
        assert "Button.focus" not in elements(style.layout(name))
        assert style.lookup(name, "foreground", ("disabled", "pressed", "focus")) == theme.COLORS["disabled_foreground"]
        assert style.lookup(name, "foreground", ("focus",)) == theme.COLORS["muted_foreground"]
        assert style.lookup(name, "background", ("pressed", "focus", "active")) == theme.COLORS["pressed_background"]
        assert style.lookup(name, "background", ("focus",)) == theme.COLORS["inactive_background"]

    ui.apply_settings()
    ui.play_pause_button.invoke()
    assert ui.settings_button.instate(["disabled"])
    assert style.lookup(ui.settings_button["style"], "foreground", ui.settings_button.state()) == theme.COLORS["disabled_foreground"]


@pytest.mark.parametrize("selected", ["black", "breeze"])
def test_other_themes_still_work(window, selected):
    ui = build_ui(window, selected)
    ui.apply_settings()
    assert ttk.Style(window).theme_use() == selected
    assert str(ui.play_pause_button["text"]) == "Play"


@pytest.fixture
def reset_ui(window, monkeypatch):
    elapsed = [100.0]
    monkeypatch.setattr("chess_clock.ui_tk.monotonic", lambda: elapsed[0])
    ui = build_ui(window)
    ui.clock._now = lambda: elapsed[0]
    ui.clock.reset()
    ui.apply_settings()
    return ui, elapsed


def test_reset_countdown_expires_without_resetting_or_pausing(reset_ui):
    ui, elapsed = reset_ui
    ui.play_pause_button.invoke()
    ui.reset_button.invoke()
    assert str(ui.reset_button["text"]) == "Reset? 5"
    for second, label in ((1, "Reset? 4"), (2, "Reset? 3"), (3, "Reset? 2"),
                          (4, "Reset? 1"), (5, "Reset")):
        elapsed[0] = 100 + second
        ui.window.after_cancel(ui._job)
        ui.tick()
        assert str(ui.reset_button["text"]) == label
        assert ui.clock.running
        assert ui.clock.remaining == [300 - second, 300]
    assert ui._reset_deadline is None


@pytest.mark.parametrize("state", ["running", "paused"])
def test_second_reset_press_confirms_and_retains_game_settings(reset_ui, state):
    ui, elapsed = reset_ui
    ui.clock.configure(10, 5)
    ui.rocker(0)  # White is on the right.
    ui.play_pause_button.invoke()
    elapsed[0] += 2
    ui.clock.update()
    if state == "paused":
        ui.play_pause_button.invoke()
    previous = ui.clock.remaining.copy()
    ui.reset_button.invoke()
    assert ui.clock.remaining == previous
    assert ui.clock.started
    elapsed[0] += 4.999
    ui.reset_button.invoke()
    assert ui.clock.remaining == [600, 600]
    assert ui.clock.increment == 5 and ui.clock.white_side == 1
    assert not ui.clock.started and not ui.clock.running
    assert ui.clock.expired is None
    assert str(ui.reset_button["text"]) == "Reset"
    assert str(ui.play_pause_button["text"]) == "Play"
    # Confirmation is consumed: another press must arm a new countdown.
    ui.reset_button.invoke()
    assert str(ui.reset_button["text"]) == "Reset? 5"


@pytest.mark.parametrize("armed", [False, True])
def test_ended_game_resets_on_first_press_even_before_timeout_redraw(reset_ui, armed):
    ui, elapsed = reset_ui
    ui.clock.configure(1, 5)
    ui.rocker(0)
    ui.play_pause_button.invoke()
    if armed:
        ui.reset_button.invoke()
    elapsed[0] += 60
    ui.reset_button.invoke()
    assert ui.clock.remaining == [60, 60]
    assert ui.clock.increment == 5 and ui.clock.white_side == 1
    assert not ui.clock.started and not ui.clock.running
    assert ui.clock.expired is None and ui._reset_deadline is None
    assert str(ui.reset_button["text"]) == "Reset"
    assert str(ui.play_pause_button["text"]) == "Play"
    assert ui.settings_button.instate(["!disabled"])


@pytest.mark.parametrize("delay", [5, 8])
def test_late_second_press_rearms_even_before_countdown_redraw(reset_ui, delay):
    ui, elapsed = reset_ui
    ui.play_pause_button.invoke()
    ui.reset_button.invoke()
    elapsed[0] += delay
    ui.reset_button.invoke()
    assert ui.clock.running and ui.clock.started
    assert str(ui.reset_button["text"]) == "Reset? 5"
    ui.reset_button.invoke()
    assert not ui.clock.started


def test_opening_settings_cancels_pending_reset(reset_ui):
    ui, elapsed = reset_ui
    ui.reset_button.invoke()
    ui.settings_button.invoke()
    ui.apply_settings()
    ui.reset_button.invoke()
    assert str(ui.reset_button["text"]) == "Reset? 5"


def test_status_shows_turn_number_and_reset_restores_turn_one(reset_ui):
    ui, elapsed = reset_ui
    assert ". Turn " not in str(ui.status["text"])
    ui.play_pause_button.invoke()
    assert str(ui.status["text"]) == "White to move. Turn 1"
    ui.rocker(0)
    assert str(ui.status["text"]) == "Black to move. Turn 1"
    ui.rocker(1)
    assert str(ui.status["text"]) == "White to move. Turn 2"
    ui.play_pause_button.invoke()
    assert str(ui.status["text"]).endswith("White to move. Turn 2")
    ui.reset_button.invoke()
    assert str(ui.status["text"]).endswith(". Turn 2")
    ui.reset_button.invoke()
    assert ". Turn " not in str(ui.status["text"])
    ui.play_pause_button.invoke()
    assert str(ui.status["text"]).endswith(". Turn 1")


def test_statistics_replace_player_indicators_when_paused_or_ended(reset_ui):
    ui, elapsed = reset_ui
    ui.play_pause_button.invoke()
    elapsed[0] += 2
    ui.rocker(0)
    elapsed[0] += 3
    ui.rocker(1)
    elapsed[0] += 4
    ui.rocker(0)
    ui.play_pause_button.invoke()
    assert str(ui.indicators[0]["text"]) == (
        "Move statistics:\nAverage: 3.00s Fastest: 2.00s Slowest: 4.00s")
    assert str(ui.indicators[1]["text"]) == (
        "Move statistics:\nAverage: 3.00s Fastest: 3.00s Slowest: 3.00s")
    ui.play_pause_button.invoke()
    assert str(ui.indicators[0]["text"]) == "Waiting"
    assert str(ui.indicators[1]["text"]) == "Your turn"
    elapsed[0] += 400
    ui.clock.update()
    ui.render()
    assert "Average: 3.00s" in str(ui.indicators[0]["text"])
    assert "Fastest: 3.00s" in str(ui.indicators[1]["text"])
    ui.reset_button.invoke()
    assert str(ui.indicators[0]["text"]) == "Ready"
    assert str(ui.indicators[1]["text"]) == "Waiting"


def test_statistics_show_dashes_until_a_move_is_completed(reset_ui):
    ui, elapsed = reset_ui
    ui.play_pause_button.invoke()
    elapsed[0] += 2
    ui.play_pause_button.invoke()
    for label in ui.indicators:
        assert str(label["text"]) == "Move statistics:\nAverage: - Fastest: - Slowest: -"


def test_starting_time_buttons_step_through_subminute_options(window):
    ui = build_ui(window)
    setting = ui.settings_readouts[0][1].master
    minus = setting.grid_slaves(row=2, column=0)[0]
    plus = setting.grid_slaves(row=2, column=1)[0]
    ui.settings_minutes.set("1")
    for expected in ("0:45", "0:30", "0:30"):
        minus.invoke()
        assert ui.settings_minutes.get() == expected
    for expected in ("0:45", "1", "2", "3"):
        plus.invoke()
        assert ui.settings_minutes.get() == expected
    ui.settings_minutes.set("180")
    plus.invoke()
    assert ui.settings_minutes.get() == "180"


@pytest.mark.parametrize("seconds", [30, 45])
def test_subminute_selection_starts_and_resets_correctly(window, seconds):
    ui = build_ui(window)
    ui.settings_minutes.set(f"0:{seconds}")
    ui.ready_button.invoke()
    assert ui.clock.remaining == [seconds, seconds]
    assert str(ui.status["text"]).startswith(f"{seconds} sec +")
    ui.play_pause_button.invoke()
    assert ui.clock.running
    ui.reset_button.invoke()
    ui.reset_button.invoke()
    assert ui.clock.remaining == [seconds, seconds]
    ui.settings_button.invoke()
    assert ui.settings_minutes.get() == f"0:{seconds}"


@pytest.mark.parametrize("expired_side", [0, 1])
def test_end_of_game_headings_and_reset(reset_ui, expired_side):
    ui, elapsed = reset_ui
    original = [str(label["text"]) for label in ui.names]
    ui.play_pause_button.invoke()
    if expired_side == 1:
        ui.rocker(0)
    ui.clock.remaining[1 - expired_side] = 3.25
    elapsed[0] += 301
    ui.clock.update()
    ui.render()
    assert str(ui.names[expired_side]["text"]).startswith("Time expired!")
    assert str(ui.names[1 - expired_side]["text"]).startswith("Winner!")
    assert str(ui.names[1 - expired_side]["text"]).endswith("Wins: 1")
    loser_area = ui.timer_areas[expired_side]
    winner_area = ui.timer_areas[1 - expired_side]
    assert loser_area.itemcget(ui.times[expired_side], "text") == "0:00"
    assert loser_area.itemcget(ui.times[expired_side], "fill") == theme.COLORS["muted_foreground"]
    assert loser_area.itemcget(ui.fractions[expired_side], "state") == "hidden"
    assert loser_area.itemcget(ui.fraction_shadows[expired_side], "state") == "hidden"
    assert winner_area.itemcget(ui.times[1 - expired_side], "fill") == theme.COLORS["foreground"]
    assert winner_area.itemcget(ui.fractions[1 - expired_side], "fill") == theme.COLORS["foreground"]
    assert winner_area.itemcget(ui.fractions[1 - expired_side], "text") == ".25"
    ui.reset_button.invoke()
    assert [str(label["text"]) for label in ui.names] == [
        f"{heading.rsplit(':', 1)[0]}: {ui.clock.wins[side]}"
        for side, heading in enumerate(original)]


@pytest.mark.parametrize("expired_side", [0, 1])
def test_expired_digits_flash_once_per_second_until_reset(reset_ui, expired_side):
    ui, elapsed = reset_ui
    ui.play_pause_button.invoke()
    if expired_side == 1:
        ui.rocker(0)
    elapsed[0] += 301
    ui.clock.update()
    ui.render()
    started = elapsed[0]
    for offset, state in ((0, "normal"), (.49, "normal"), (.5, "hidden"),
                          (1, "normal"), (1.5, "hidden"), (10, "normal"), (10.5, "hidden")):
        elapsed[0] = started + offset
        ui.render()
        loser = ui.timer_areas[expired_side]
        assert loser.itemcget(ui.times[expired_side], "state") == state
        assert loser.itemcget(ui.time_shadows[expired_side], "state") == state
        assert loser.itemcget(ui.fractions[expired_side], "state") == "hidden"
        assert ui.timer_areas[1 - expired_side].itemcget(ui.times[1 - expired_side], "state") == "normal"
    ui.reset_button.invoke()
    elapsed[0] += .5
    ui.render()
    assert ui._timeout_flash_started is None
    for player, area in enumerate(ui.timer_areas):
        assert area.itemcget(ui.times[player], "state") == "normal"


@pytest.mark.parametrize("winner", [0, 1])
@pytest.mark.parametrize("paused", [False, True])
def test_reset_allows_declaring_a_winner_once(reset_ui, winner, paused):
    ui, elapsed = reset_ui
    ui.play_pause_button.invoke()
    if paused:
        ui.play_pause_button.invoke()
    assert not any(button.place_info() for button in ui.winner_buttons)
    ui.reset_button.invoke()
    assert all(button.place_info() for button in ui.winner_buttons)
    assert not any(label.place_info() for label in ui.names)
    assert [str(button["text"]) for button in ui.winner_buttons] == ["Winner - Left", "Winner - Right"]
    elapsed[0] += 4.999
    ui.winner_buttons[winner].invoke()
    assert ui.clock.wins[winner] == 1 and ui.clock.wins[1 - winner] == 0
    assert not ui.clock.started and not ui.clock.running
    assert ui._reset_deadline is None
    assert not any(button.place_info() for button in ui.winner_buttons)
    assert str(ui.names[winner]["text"]).endswith("Wins: 1")
    ui.winner_buttons[winner].invoke()
    assert ui.clock.wins[winner] == 1


@pytest.mark.parametrize("delay", [5, 6])
def test_expired_winner_selection_cannot_award_win(reset_ui, delay):
    ui, elapsed = reset_ui
    ui.play_pause_button.invoke()
    ui.play_pause_button.invoke()
    ui.reset_button.invoke()
    elapsed[0] += delay
    ui.winner_buttons[0].invoke()  # Check deadline even before redraw.
    assert ui.clock.wins == [0, 0]
    assert ui.clock.started and not ui.clock.running
    assert not any(button.place_info() for button in ui.winner_buttons)
    assert all(label.place_info() for label in ui.names)


def test_resume_cancels_winner_selection_and_normal_reset_does_not_award(reset_ui):
    ui, elapsed = reset_ui
    ui.play_pause_button.invoke()
    ui.reset_button.invoke()
    assert all(button.place_info() for button in ui.winner_buttons)
    ui.reset_button.invoke()
    assert ui.clock.wins == [0, 0]
    ui.play_pause_button.invoke()
    ui.play_pause_button.invoke()
    ui.reset_button.invoke()
    ui.play_pause_button.invoke()
    ui.winner_buttons[1].invoke()
    assert ui.clock.running and ui.clock.wins == [0, 0]
    assert not any(button.place_info() for button in ui.winner_buttons)


def test_settings_reset_win_count_clears_both_players(reset_ui):
    ui, elapsed = reset_ui
    ui.clock.wins = [3, 2]
    ui.settings_button.invoke()
    assert int(ui.reset_wins_button.grid_info()["column"]) < int(ui.ready_button.grid_info()["column"])
    ui.reset_wins_button.invoke()
    assert ui.clock.wins == [0, 0]
    ui.ready_button.invoke()
    assert all(str(label["text"]).endswith("Wins: 0") for label in ui.names)


def test_running_game_continues_when_winner_selection_expires(reset_ui):
    ui, elapsed = reset_ui
    ui.play_pause_button.invoke()
    ui.reset_button.invoke()
    elapsed[0] += 5
    ui.clock.update()
    ui.render()
    assert ui.clock.running and ui.clock.remaining == [295, 300]
    assert ui.clock.wins == [0, 0]
    assert not any(button.place_info() for button in ui.winner_buttons)


def test_timeout_during_winner_selection_cannot_award_second_win(reset_ui):
    ui, elapsed = reset_ui
    ui.play_pause_button.invoke()
    ui.clock.remaining[0] = 1
    ui.reset_button.invoke()
    elapsed[0] += 1
    ui.winner_buttons[0].invoke()
    assert ui.clock.expired == 0
    assert ui.clock.wins == [0, 1]
    assert not any(button.place_info() for button in ui.winner_buttons)


def test_resume_text_blinks_while_paused_and_remains_clickable(reset_ui):
    ui, elapsed = reset_ui
    ui.play_pause_button.invoke()
    ui.play_pause_button.invoke()
    started = elapsed[0]
    style = ttk.Style(ui.window)
    for offset, hidden in ((0, False), (.49, False), (.5, True), (1, False),
                           (1.5, True), (10.5, True)):
        elapsed[0] = started + offset
        ui.render()
        button = ui.play_pause_button
        assert str(button["text"]) == "Resume"
        assert button.instate(["!disabled"])
        expected_icon = ui.button_icons["play", "hidden" if hidden else "normal"]
        assert str(button["image"][0]) == str(expected_icon)
        for state in ((), ("active",), ("pressed",)):
            foreground = style.lookup(button["style"], "foreground", state)
            background = style.lookup(button["style"], "background", state)
            assert (foreground == background) == hidden
    ui.play_pause_button.invoke()  # Resume during the hidden phase.
    assert ui.clock.running and ui._resume_flash_started is None
    assert str(ui.play_pause_button["style"]) == "Touch.TButton"
    assert str(ui.play_pause_button["text"]) == "Pause"


def test_reset_stops_resume_blink_and_next_pause_starts_visible(reset_ui):
    ui, elapsed = reset_ui
    ui.play_pause_button.invoke()
    ui.play_pause_button.invoke()
    elapsed[0] += .5
    ui.render()
    ui.reset_button.invoke()
    ui.reset_button.invoke()
    assert ui._resume_flash_started is None
    assert str(ui.play_pause_button["style"]) == "Touch.TButton"
    assert str(ui.play_pause_button["text"]) == "Play"
    ui.play_pause_button.invoke()
    ui.play_pause_button.invoke()
    assert str(ui.play_pause_button["style"]) == "Touch.TButton"


def test_clock_hides_minutes_below_ten_seconds(reset_ui):
    ui, elapsed = reset_ui
    for seconds, expected in ((10.01, "0:11"), (10, "0:10"), (9.999, "10.00"),
                              (9.99, "9.99"), (3.25, "3.25"), (.1, "0.10")):
        ui.clock.remaining = [seconds, seconds]
        ui.render()
        for player, area in enumerate(ui.timer_areas):
            whole = area.itemcget(ui.times[player], "text")
            fraction = area.itemcget(ui.fractions[player], "text")
            assert whole + fraction == expected
