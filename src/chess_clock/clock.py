"""Clock timing and game state, independent of UI and hardware."""

from collections.abc import Callable
import math
from time import monotonic


class ChessClock:
    """Two countdowns using elapsed monotonic time rather than UI tick counts."""

    def __init__(self, seconds: float = 300, *, increment: float = 0,
                 now: Callable[[], float] = monotonic):
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("Starting time must be a positive, finite number.")
        self.initial_seconds = seconds
        if not math.isfinite(increment) or increment < 0:
            raise ValueError("Increment must be a nonnegative, finite number.")
        self.increment = increment
        self._now = now
        self.white_side = 0  # Default: left is White, right is Black.
        self.wins = [0, 0]  # Session totals belong to physical left/right players.
        self.reset()

    def reset(self) -> None:
        self.remaining = [self.initial_seconds, self.initial_seconds]
        self.turn_number = 1
        self.move_times: list[list[float]] = [[], []]
        self._move_elapsed = 0.0
        self.active = self.white_side
        self.started = False
        self.running = False
        self.expired: int | None = None
        self._last = self._now()

    def update(self) -> None:
        current = self._now()
        if self.running:
            self._move_elapsed += min(current - self._last, self.remaining[self.active])
            self.remaining[self.active] = max(
                0.0, self.remaining[self.active] - (current - self._last)
            )
            if self.remaining[self.active] == 0:
                self.running = False
                self.expired = self.active
                self.wins[1 - self.expired] += 1
        self._last = current

    def start(self) -> None:
        self.update()
        if self.expired is None:
            self.started = True
            self.running = True

    def pause(self) -> None:
        self.update()
        self.running = False

    def switch(self, player: int | None = None) -> None:
        """End the active player's turn; ignore an inactive rocker's press."""
        self.update()
        if self.running and (player is None or player == self.active):
            self.move_times[self.active].append(self._move_elapsed)
            self._move_elapsed = 0.0
            self.remaining[self.active] += self.increment
            self.active = 1 - self.active
            if self.active == self.white_side:
                self.turn_number += 1

    def move_statistics(self, player: int) -> dict[str, float | None]:
        """Summarize completed moves; unfinished moves are excluded."""
        moves = self.move_times[player]
        return {
            "average": sum(moves) / len(moves) if moves else None,
            "longest": max(moves) if moves else None,
            "shortest": min(moves) if moves else None,
        }

    def declare_winner(self, player: int) -> bool:
        """Award an unfinished game once, then prepare the next game."""
        if player not in (0, 1):
            raise ValueError("Player must be 0 (left) or 1 (right).")
        self.update()
        if not self.started or self.expired is not None:
            return False
        self.wins[player] += 1
        self.reset()
        return True

    def reset_win_counts(self) -> None:
        self.wins = [0, 0]

    def configure(self, minutes: int, increment: int) -> None:
        """Apply shared settings before play, preserving the selected colors."""
        if self.started:
            raise ValueError("Reset the game before changing time settings.")
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Starting minutes must be a positive whole number.")
        self.configure_seconds(minutes * 60, increment)

    def configure_seconds(self, seconds: int, increment: int) -> None:
        """Apply a starting time in seconds, including sub-minute games."""
        if self.started:
            raise ValueError("Reset the game before changing time settings.")
        if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds <= 0:
            raise ValueError("Starting seconds must be a positive whole number.")
        if isinstance(increment, bool) or not isinstance(increment, int) or increment < 0:
            raise ValueError("Increment seconds must be a nonnegative whole number.")
        self.initial_seconds = seconds
        self.increment = increment
        self.remaining = [self.initial_seconds, self.initial_seconds]
        self._last = self._now()

    def color(self, side: int) -> str:
        """Return the piece color assigned to a physical side (0=left, 1=right)."""
        return "White" if side == self.white_side else "Black"

    def press_rocker(self, side: int) -> None:
        """Before Start, the pressed side is Black; during play, end its turn."""
        if side not in (0, 1):
            raise ValueError("Rocker side must be 0 (left) or 1 (right).")
        if not self.started:
            self.white_side = 1 - side
            self.active = self.white_side
        else:
            self.switch(side)


def format_time(seconds: float) -> str:
    """Round up, showing hundredths only when less than ten seconds remain."""
    seconds = max(0, seconds)
    if seconds < 10:
        whole_seconds, hundredths = divmod(math.ceil(seconds * 100), 100)
        return f"0:{whole_seconds:02d}.{hundredths:02d}"
    minutes, whole_seconds = divmod(math.ceil(seconds), 60)
    return f"{minutes}:{whole_seconds:02d}"
