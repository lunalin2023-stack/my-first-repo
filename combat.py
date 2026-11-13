# ==========================================
# combat.py - Combat System
# ==========================================

# Responsibilities:
# 1. Process player attacks.
# 2. Process computer attacks.
# 3. Determine hits and misses.
# 4. Award cash for successful attacks.
# 5. Check victory and defeat conditions.

from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from ship import BOARD_SIZE, Ship, all_sunk, format_coordinate, in_bounds

# Outcomes
HIT = "hit"
SUNK = "sunk"
MISS = "miss"
REPEAT = "repeat"
INVALID = "invalid"

# Winners returned by check_victory()
PLAYER_WINS = "player"
COMPUTER_WINS = "computer"

# Cash rewards (shop.py is allowed to use its own table instead).
HIT_REWARD = 20
SINK_BONUS = 50

VALID_OUTCOMES = (HIT, SUNK, MISS)


@dataclass
class ShotResult:
    """Everything main.py / display.py / shop.py needs to know about one shot."""

    row: int
    col: int
    outcome: str
    ship: Optional[Ship] = None
    clue: Optional[int] = None
    reward: int = 0
    message: str = ""

    @property
    def coordinate(self) -> str:
        return format_coordinate(self.row, self.col)

    @property
    def is_hit(self) -> bool:
        return self.outcome in (HIT, SUNK)

    @property
    def is_sunk(self) -> bool:
        return self.outcome == SUNK

    @property
    def is_miss(self) -> bool:
        return self.outcome == MISS

    @property
    def is_repeat(self) -> bool:
        return self.outcome == REPEAT

    @property
    def is_valid(self) -> bool:
        """True for a real shot (hit / sunk / miss); false for repeat/invalid."""
        return self.outcome in VALID_OUTCOMES

    @property
    def consumes_turn(self) -> bool:
        return self.is_valid

    @property
    def cash_awarded(self) -> int:
        """Cash this shot gives the player (0 for a computer shot)."""
        return self.reward

    @property
    def ship_name(self) -> Optional[str]:
        return self.ship.name if self.ship is not None else None

    def as_dict(self) -> dict:
        """Plain dict, for teammates who prefer dictionaries to objects."""
        return {
            "row": self.row,
            "col": self.col,
            "coordinate": self.coordinate,
            "outcome": self.outcome,
            "ship": self.ship_name,
            "clue": self.clue,
            "reward": self.reward,
            "message": self.message,
        }

    def __str__(self) -> str:
        return self.message


def ship_at(
    ships: Sequence[Ship],
    row: int,
    col: int,
) -> Optional[Ship]:
    """The ship covering ``(row, col)``, or None for open water (a miss)."""
    for ship in ships:
        if ship.occupies(row, col):
            return ship
    return None


def calculate_clue(
    ships: Sequence[Ship],
    row: int,
    col: int,
    exclude_sunk: bool = True,
) -> int:
    """Number of ship segments in the 8 neighbours of ``(row, col)`` (0..8).

    Diagonals count, out-of-board squares are ignored and the square itself is
    not counted.  With ``exclude_sunk=True`` (the team rule) segments of ships
    that have already sunk are ignored.

    logic.py owns the official clue algorithm.  This copy exists so that
    combat.py can be tested before logic.py is finished; when logic.py is
    ready, pass ``clue_fn=logic.calculate_clue`` to :func:`attack`.
    """
    occupied = set()
    for ship in ships:
        if exclude_sunk and ship.is_sunk():
            continue
        occupied.update(ship.positions)
    total = 0
    for step_row in (-1, 0, 1):
        for step_col in (-1, 0, 1):
            if step_row == 0 and step_col == 0:
                continue
            neighbour_row = row + step_row
            neighbour_col = col + step_col
            if in_bounds(neighbour_row, neighbour_col, BOARD_SIZE):
                if (neighbour_row, neighbour_col) in occupied:
                    total += 1
    return total


def _record_shot(shots, row: int, col: int) -> None:
    """Add the square to the attack record (set or list)."""
    square = (row, col)
    try:
        shots.add(square)
    except AttributeError:
        if square not in shots:
            shots.append(square)


def attack(
    ships: Sequence[Ship],
    row: int,
    col: int,
    shots,
    clue_fn: Optional[Callable[[Sequence[Ship], int, int], int]] = None,
    exclude_sunk: bool = True,
    award_reward: bool = True,
) -> ShotResult:
    """Process one shot fired at ``(row, col)`` of the fleet ``ships``.

    ``shots`` is the set of squares already fired at; it is updated in place.
    ``clue_fn(ships, row, col)`` overrides the built-in clue counter.
    ``award_reward=False`` sets ``reward`` to 0 (used for computer shots).

    The function never raises for a bad square: an off-board or repeated shot
    comes back with ``outcome`` "invalid" / "repeat" and ``consumes_turn``
    False, so main.py can simply ask again.
    """
    if not in_bounds(row, col, BOARD_SIZE):
        return ShotResult(
            row=row,
            col=col,
            outcome=INVALID,
            message="That square is outside the board.",
        )
    if (row, col) in shots:
        return ShotResult(
            row=row,
            col=col,
            outcome=REPEAT,
            message="%s was already fired at." % format_coordinate(row, col),
        )

    _record_shot(shots, row, col)
    target = ship_at(ships, row, col)

    if target is None:
        clue = clue_fn(ships, row, col) if clue_fn is not None else calculate_clue(
            ships, row, col, exclude_sunk
        )
        return ShotResult(
            row=row,
            col=col,
            outcome=MISS,
            clue=clue,
            message="Miss at %s. Clue: %d ship segment(s) nearby."
            % (format_coordinate(row, col), clue),
        )

    target.take_hit(row, col)
    if target.is_sunk():
        return ShotResult(
            row=row,
            col=col,
            outcome=SUNK,
            ship=target,
            reward=HIT_REWARD + SINK_BONUS if award_reward else 0,
            message="Hit at %s! The %s has been sunk!"
            % (format_coordinate(row, col), target.name),
        )
    # Deliberately no ship name and no "squares left": a partial hit must not
    # tell the player which ship it was or how much of it is still afloat.
    # That information is what the clue numbers are for.
    return ShotResult(
        row=row,
        col=col,
        outcome=HIT,
        ship=target,
        reward=HIT_REWARD if award_reward else 0,
        message="Hit at %s!" % format_coordinate(row, col),
    )


# The assignment description calls this operation "process a shot".
process_shot = attack


# ----------------------------------------------------------- player / computer
def process_player_attack(
    enemy_ships: Sequence[Ship],
    row: int,
    col: int,
    player_shots,
    clue_fn: Optional[Callable[[Sequence[Ship], int, int], int]] = None,
) -> ShotResult:
    """Responsibility 1: the player fires at the enemy fleet.

    ``player_shots`` is the player's attack record.  The returned result
    carries the cash the player earns; use :func:`award_cash` to add it to the
    balance.
    """
    return attack(enemy_ships, row, col, player_shots, clue_fn=clue_fn)


def process_computer_attack(
    player_ships: Sequence[Ship],
    row: int,
    col: int,
    computer_shots,
    clue_fn: Optional[Callable[[Sequence[Ship], int, int], int]] = None,
) -> ShotResult:
    """Responsibility 2: the computer fires at the player's fleet.

    computer.py chooses ``(row, col)``; this function resolves the shot.
    The computer earns no cash, so ``reward`` is always 0.
    """
    return attack(
        player_ships,
        row,
        col,
        computer_shots,
        clue_fn=clue_fn,
        award_reward=False,
    )


# ------------------------------------------------------------------- economy
def award_cash(cash: int, result: ShotResult) -> int:
    """Responsibility 4: return the new balance after awarding this shot.

    >>> award_cash(100, result_hit)          # result_hit.reward == 20
    120
    """
    return cash + result.reward


# -------------------------------------------------------------- end of game
def check_victory(
    player_ships: Sequence[Ship],
    computer_ships: Sequence[Ship],
) -> Optional[str]:
    """Responsibility 5: return the winner, or None while the game goes on.

    The result is ``PLAYER_WINS`` when every computer ship is sunk and
    ``COMPUTER_WINS`` when every player ship is sunk.  Both fleets must be
    filled before the game starts, otherwise the check returns None.
    """
    if computer_ships and all_sunk(computer_ships):
        return PLAYER_WINS
    if player_ships and all_sunk(player_ships):
        return COMPUTER_WINS
    return None


def is_game_over(
    player_ships: Sequence[Ship],
    computer_ships: Sequence[Ship],
) -> bool:
    """True once one of the two fleets has been completely sunk."""
    return check_victory(player_ships, computer_ships) is not None
