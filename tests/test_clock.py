"""Deterministic checks for timing and rocker input without a GUI."""

import pytest

from chess_clock.clock import ChessClock, format_time


@pytest.fixture
def timer():
    elapsed = [0.0]
    clock = ChessClock(300, now=lambda: elapsed[0])
    return clock, elapsed


def test_only_active_player_counts_down_and_switch_charges_elapsed_time(timer):
    clock, time = timer
    clock.start()
    time[0] = 1.25
    clock.switch(0)
    assert clock.remaining == [298.75, 300]
    assert clock.active == 1
    time[0] = 3.5
    clock.update()
    assert clock.remaining == [298.75, 297.75]


def test_rocker_ignores_inactive_player_and_repeated_same_side(timer):
    clock, time = timer
    clock.start()
    clock.switch(1)
    assert clock.active == 0
    clock.switch(0)
    clock.switch(0)
    assert clock.active == 1
    clock.switch(1)
    assert clock.active == 0


def test_pause_and_resume_exclude_paused_time(timer):
    clock, time = timer
    clock.start()
    time[0] = 2
    clock.pause()
    time[0] = 100
    clock.switch(0)
    assert clock.active == 0
    clock.start()
    time[0] = 103
    clock.update()
    assert clock.remaining == [295, 300]


def test_start_while_running_does_not_discard_elapsed_time(timer):
    clock, time = timer
    clock.start()
    time[0] = 4
    clock.start()
    assert clock.remaining == [296, 300]


def test_timeout_blocks_switching_and_restart(timer):
    clock, time = timer
    clock.start()
    time[0] = 301
    clock.switch(0)
    clock.start()
    assert clock.remaining == [0, 300]
    assert clock.expired == 0
    assert clock.active == 0
    assert not clock.running


def test_reset_restores_both_timers_and_white_to_move(timer):
    clock, time = timer
    clock.start()
    clock.switch(0)
    time[0] = 500
    clock.update()
    clock.reset()
    assert clock.remaining == [300, 300]
    assert clock.active == 0
    assert clock.expired is None
    assert not clock.running


@pytest.mark.parametrize('seconds, expected', [(300, '05:00'), (59.1, '01:00'),
                                              (0.1, '00:01'), (0, '00:00')])
def test_time_format(seconds, expected):
    assert format_time(seconds) == expected


@pytest.mark.parametrize('seconds', [0, -1, float('nan'), float('inf')])
def test_invalid_starting_time(seconds):
    with pytest.raises(ValueError):
        ChessClock(seconds)


@pytest.mark.parametrize('presses, white_side', [([0], 1), ([1], 0),
                                               ([0, 1, 0], 1), ([1, 0, 1], 0)])
def test_last_pregame_rocker_press_assigns_black(timer, presses, white_side):
    clock, time = timer
    for side in presses:
        clock.press_rocker(side)
        assert clock.color(side) == 'Black'
        assert clock.color(1 - side) == 'White'
    assert clock.white_side == white_side
    assert clock.active == white_side
    assert clock.remaining == [300, 300]
    assert not clock.running and not clock.started
    clock.start()
    time[0] = 2
    clock.update()
    assert clock.remaining[white_side] == 298
    assert clock.remaining[1 - white_side] == 300
    clock.press_rocker(white_side)
    assert clock.active == 1 - white_side
    assert clock.white_side == white_side


def test_pause_does_not_reopen_color_selection_even_without_elapsed_time(timer):
    clock, time = timer
    clock.press_rocker(0)
    clock.start()
    clock.pause()
    clock.press_rocker(1)
    assert clock.white_side == 1 and clock.active == 1
    assert not clock.running
    clock.start()
    clock.press_rocker(1)
    assert clock.active == 0
    assert clock.color(0) == 'Black'


def test_reset_reopens_color_selection(timer):
    clock, time = timer
    clock.start()
    clock.reset()
    assert not clock.started
    clock.press_rocker(0)
    assert clock.white_side == 1
    assert clock.active == 1


def test_expired_game_preserves_assignments(timer):
    clock, time = timer
    clock.press_rocker(0)
    clock.start()
    time[0] = 301
    clock.press_rocker(1)
    assert clock.expired == 1
    assert clock.color(clock.expired) == 'White'
    clock.press_rocker(0)
    assert clock.white_side == 1


def test_shared_settings_preserve_colors_and_reset_uses_settings(timer):
    clock, time = timer
    clock.press_rocker(0)
    clock.configure(10, 5)
    assert clock.remaining == [600, 600]
    assert clock.increment == 5
    assert clock.white_side == clock.active == 1
    clock.start()
    time[0] = 2
    clock.press_rocker(1)
    assert clock.remaining == [600, 603]
    time[0] = 5
    clock.press_rocker(0)
    assert clock.remaining == [602, 603]
    clock.reset()
    assert clock.remaining == [600, 600]
    assert clock.increment == 5
    assert clock.white_side == clock.active == 1
    assert not clock.started and not clock.running


def test_increment_is_not_awarded_for_setup_inactive_or_paused_presses(timer):
    clock, time = timer
    clock.configure(5, 3)
    clock.press_rocker(1)
    assert clock.remaining == [300, 300]
    clock.start()
    clock.press_rocker(1)
    assert clock.remaining == [300, 300]
    clock.pause()
    clock.press_rocker(0)
    assert clock.remaining == [300, 300]
    clock.start()
    time[0] = 1
    clock.press_rocker(0)
    clock.press_rocker(0)
    assert clock.remaining == [302, 300]


def test_increment_cannot_rescue_expired_player(timer):
    clock, time = timer
    clock.configure(1, 10)
    clock.start()
    time[0] = 60
    clock.press_rocker(0)
    assert clock.remaining == [0, 60]
    assert clock.expired == 0 and not clock.running


def test_cannot_change_settings_once_game_has_started(timer):
    clock, time = timer
    clock.start()
    clock.pause()
    with pytest.raises(ValueError):
        clock.configure(10, 5)
    assert clock.initial_seconds == 300 and clock.increment == 0


@pytest.mark.parametrize('minutes, increment', [(0, 0), (1.5, 0), (True, 0),
                                               (5, -1), (5, 0.5), (5, True)])
def test_invalid_settings_do_not_mutate_clock(timer, minutes, increment):
    clock, time = timer
    with pytest.raises(ValueError):
        clock.configure(minutes, increment)
    assert clock.remaining == [300, 300]
    assert clock.initial_seconds == 300 and clock.increment == 0


@pytest.mark.parametrize('increment', [-1, float('nan'), float('inf')])
def test_invalid_increment(increment):
    with pytest.raises(ValueError):
        ChessClock(increment=increment)
