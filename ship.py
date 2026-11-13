# ==========================================
# ship.py - Ship Management
# ==========================================

# Responsibilities:
# 1. Define the different types of ships.
# 2. Place ships on the game board.
# 3. Check whether ship placement is valid.
# 4. Track damage to individual ships.
# 5. Determine whether a ship has sunk.

"""ship.py - fleet definition, ship placement and damage tracking.

Battleship: Tactical Command Edition - Member 2 module.

Coordinate convention (use this in every module)
------------------------------------------------
Every square is ``(row, col)`` with both values in ``range(10)``::

    row 0 -> printed "1"    ...  row 9 -> printed "10"
    col 0 -> printed "A"    ...  col 9 -> printed "J"

So "C4" is ``(3, 2)``.  Use :func:`parse_coordinate` and
:func:`format_coordinate` instead of hard-coding the conversion.

Fleet representation
--------------------
A fleet is a plain ``list`` of :class:`Ship` objects.  Each ship remembers the
squares it occupies, so the fleet itself is the authoritative record of where
the ships are.  ``board.py`` can build its 10x10 display grid from
``ship.positions`` or call :func:`stamp_on_board`.

Rules implemented here
----------------------
* Ships may touch each other (horizontally, vertically or diagonally).
* Ships may not overlap.
* A ship may not run off the board.
* A hit counts only once per square; a ship sinks when every square is hit.
"""

from typing import Callable, List, Optional, Sequence, Tuple

BOARD_SIZE = 10
HORIZONTAL = "H"
VERTICAL = "V"

# The five ship types of the game: name -> length in squares.
# Change a value here and the whole game (placement, fleet table, tests) follows.
SHIP_TYPES = {
    "Carrier": 5,
    "Battleship": 4,
    "Cruiser": 3,
    "Submarine": 3,
    "Destroyer": 2,
}

# (name, length) pairs in the order the player places them: 17 squares in total.
FLEET = tuple(SHIP_TYPES.items())

# direction -> (row step, col step)
_STEPS = {HORIZONTAL: (0, 1), VERTICAL: (1, 0)}


class PlacementError(Exception):
    """Raised when a ship cannot be placed (off board, overlap, bad input)."""


class Ship:
    """One ship: its name, length, squares and the squares already hit."""

    def __init__(
        self,
        name: str,
        length: int,
        ship_id: int = 0,
        positions: Optional[Sequence[Tuple[int, int]]] = None,
    ) -> None:
        if not isinstance(length, int) or length < 1:
            raise PlacementError("A ship must be at least 1 square long.")
        self.name = name
        self.length = length
        self.ship_id = ship_id
        self._positions: List[Tuple[int, int]] = []
        self._position_set = set()
        self._hits = set()
        if positions is not None:
            self.set_positions(positions)

    # ------------------------------------------------------------------ state
    def set_positions(self, positions: Sequence[Tuple[int, int]]) -> None:
        """Record where the ship is (called by place_ship)."""
        cells = list(positions)
        if len(cells) != self.length:
            raise PlacementError(
                "The %s needs %d squares, got %d." % (self.name, self.length, len(cells))
            )
        if len(set(cells)) != len(cells):
            raise PlacementError("A ship cannot occupy the same square twice.")
        self._positions = cells
        self._position_set = set(cells)
        self._hits.clear()

    @property
    def positions(self) -> List[Tuple[int, int]]:
        """The squares this ship occupies, as ``[(row, col), ...]``."""
        return list(self._positions)

    @property
    def hits(self) -> set:
        """The squares of this ship that have been hit."""
        return set(self._hits)

    @property
    def damage(self) -> int:
        return len(self._hits)

    @property
    def health(self) -> int:
        return self.length - len(self._hits)

    def occupies(self, row: int, col: int) -> bool:
        """True if the ship covers ``(row, col)``."""
        return (row, col) in self._position_set

    def take_hit(self, row: int, col: int) -> bool:
        """Damage the ship at ``(row, col)``.

        Returns True if this square just became damaged, False if the square is
        not part of the ship or was already hit.
        """
        if (row, col) not in self._position_set:
            return False
        if (row, col) in self._hits:
            return False
        self._hits.add((row, col))
        return True

    def is_sunk(self) -> bool:
        """True when every square of the ship has been hit."""
        return len(self._hits) >= self.length

    def status(self) -> str:
        """Short text for the display, e.g. ``'Cruiser 1/3'``."""
        return "%s %d/%d" % (self.name, self.health, self.length)

    def __repr__(self) -> str:
        return "<Ship %s %d/%d at %s>" % (
            self.name,
            self.health,
            self.length,
            self._positions,
        )


# ----------------------------------------------------------------- ship types
def create_ship(name: str, ship_id: int = 0) -> Ship:
    """Create an unplaced ship of one of the standard types.

    >>> create_ship("Cruiser").length
    3
    """
    if name not in SHIP_TYPES:
        raise PlacementError(
            "Unknown ship type %r. Choose one of: %s."
            % (name, ", ".join(SHIP_TYPES))
        )
    return Ship(name, SHIP_TYPES[name], ship_id=ship_id)


# ---------------------------------------------------------------- coordinates
def in_bounds(row: int, col: int, size: int = BOARD_SIZE) -> bool:
    """True if ``(row, col)`` is a real square of a ``size`` x ``size`` board."""
    return (
        isinstance(row, int)
        and isinstance(col, int)
        and 0 <= row < size
        and 0 <= col < size
    )


def parse_coordinate(text: str, size: int = BOARD_SIZE) -> Tuple[int, int]:
    """Convert player text such as ``"C4"`` / ``"j10"`` into ``(row, col)``.

    Raises ValueError with a player-friendly message on bad input.
    """
    if not isinstance(text, str):
        raise ValueError("Enter a square such as C4.")
    cleaned = text.strip().upper().replace(" ", "")
    if len(cleaned) < 2:
        raise ValueError("Enter a square such as C4.")
    letter, digits = cleaned[0], cleaned[1:]
    last_letter = chr(ord("A") + size - 1)
    if not ("A" <= letter <= last_letter):
        raise ValueError("The column must be a letter from A to %s." % last_letter)
    if not digits.isdigit():
        raise ValueError("The row must be a number from 1 to %d." % size)
    number = int(digits)
    if not 1 <= number <= size:
        raise ValueError("The row must be a number from 1 to %d." % size)
    return number - 1, ord(letter) - ord("A")


def format_coordinate(row: int, col: int) -> str:
    """Convert ``(row, col)`` back to display text, e.g. ``(3, 2)`` -> ``'C4'``."""
    return "%s%d" % (chr(ord("A") + col), row + 1)


# ------------------------------------------------------------------ placement
def normalise_orientation(orientation: str) -> str:
    """Return ``'H'`` or ``'V'``; accept h/v and the full words."""
    if not isinstance(orientation, str):
        raise PlacementError("Direction must be H (horizontal) or V (vertical).")
    key = orientation.strip().upper()
    if key in ("H", "HORIZONTAL", "ROW"):
        return HORIZONTAL
    if key in ("V", "VERTICAL", "COLUMN", "COL"):
        return VERTICAL
    raise PlacementError("Direction must be H (horizontal) or V (vertical).")


def ship_cells(
    row: int,
    col: int,
    length: int,
    orientation: str,
    size: int = BOARD_SIZE,
) -> List[Tuple[int, int]]:
    """List the squares a ship would cover, or raise PlacementError."""
    if not isinstance(length, int) or length < 1:
        raise PlacementError("A ship must be at least 1 square long.")
    direction = normalise_orientation(orientation)
    step_row, step_col = _STEPS[direction]
    cells = [(row + i * step_row, col + i * step_col) for i in range(length)]
    for cell_row, cell_col in cells:
        if not in_bounds(cell_row, cell_col, size):
            raise PlacementError("That placement runs off the board.")
    return cells


def can_place_ship(
    ships: Sequence[Ship],
    row: int,
    col: int,
    length: int,
    orientation: str,
    size: int = BOARD_SIZE,
) -> bool:
    """True if the ship fits on the board and does not overlap another ship.

    Never raises: computer.py can retry random placements with this.
    Ships ARE allowed to touch each other.
    """
    try:
        cells = ship_cells(row, col, length, orientation, size)
    except PlacementError:
        return False
    occupied = set()
    for ship in ships:
        occupied.update(ship.positions)
    return not any(cell in occupied for cell in cells)


def place_ship(
    ships: List[Ship],
    name: str,
    length: int,
    row: int,
    col: int,
    orientation: str = HORIZONTAL,
    ship_id: Optional[int] = None,
    size: int = BOARD_SIZE,
) -> Ship:
    """Place one ship, append it to ``ships`` and return it.

    Raises PlacementError if the ship is off the board, overlaps another ship
    or the direction is invalid.  ``ship_id`` defaults to ``len(ships) + 1``;
    ``board.py`` may use it as the value written into its grid.
    """
    cells = ship_cells(row, col, length, orientation, size)
    for ship in ships:
        for cell_row, cell_col in cells:
            if ship.occupies(cell_row, cell_col):
                raise PlacementError(
                    "%s is already occupied by the %s."
                    % (format_coordinate(cell_row, cell_col), ship.name)
                )
    if ship_id is None:
        ship_id = len(ships) + 1
    new_ship = Ship(name, length, ship_id=ship_id, positions=cells)
    ships.append(new_ship)
    return new_ship


def stamp_on_board(board: List[List], ship: Ship, marker=None) -> None:
    """Optional helper: write ``ship`` into a 10x10 grid owned by board.py.

    ``board`` must be ``board[row][col]``.  ``marker`` defaults to
    ``ship.ship_id``; pass ``"S"`` if your board uses ``"~"`` / ``"S"``.
    """
    value = ship.ship_id if marker is None else marker
    for row, col in ship.positions:
        board[row][col] = value


def all_sunk(ships: Sequence[Ship]) -> bool:
    """True when every ship in the fleet has been sunk.

    Note: an empty fleet also returns True, so fill both fleets before you use
    this for the win condition.
    """
    return all(ship.is_sunk() for ship in ships)


def ships_afloat(ships: Sequence[Ship]) -> List[Ship]:
    """The ships that are still in the game."""
    return [ship for ship in ships if not ship.is_sunk()]


# --------------------------------------------------------- interactive helper
def place_fleet(
    ships: List[Ship],
    fleet: Sequence[Tuple[str, int]] = FLEET,
    size: int = BOARD_SIZE,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    show_fn: Optional[Callable[[Sequence[Ship]], None]] = None,
) -> List[Ship]:
    """Let the player place the whole fleet from the keyboard.

    Input format: ``"C4 H"`` (square + direction).  ``H`` is the default.
    Commands: ``reset`` / ``r`` clears the fleet and starts again,
    ``quit`` / ``q`` raises PlacementError.

    ``show_fn(ships)`` is called before every prompt, so display.py can draw
    the placement screen.  The function is kept separate from the game loop on
    purpose: main.py decides when placement happens.
    """
    ships.clear()
    index = 0
    total = len(fleet)
    while index < total:
        name, length = fleet[index]
        if show_fn is not None:
            show_fn(ships)
        try:
            raw = input_fn(
                "Place %s (%d squares) - square + direction, e.g. C4 H: "
                % (name, length)
            )
        except EOFError:
            raise PlacementError("Placement cancelled (no more input).")
        command = "" if raw is None else str(raw).strip()
        lowered = command.lower()
        if lowered in ("q", "quit"):
            raise PlacementError("Placement cancelled by the player.")
        if lowered in ("r", "reset"):
            ships.clear()
            index = 0
            output_fn("Fleet cleared - starting the placement again.")
            continue
        parts = command.split()
        if not parts:
            output_fn("  ! Enter a square such as C4, optionally followed by H or V.")
            continue
        # Allow "C4H" as well as "C4 H".
        if len(parts) == 1 and len(parts[0]) > 2 and parts[0][-1].upper() in ("H", "V"):
            parts = [parts[0][:-1], parts[0][-1]]
        orientation = parts[1] if len(parts) > 1 else HORIZONTAL
        try:
            row, col = parse_coordinate(parts[0], size)
            ship = place_ship(
                ships,
                name,
                length,
                row,
                col,
                orientation,
                ship_id=index + 1,
                size=size,
            )
        except (ValueError, PlacementError) as error:
            output_fn("  ! %s" % error)
            continue
        cells = ship.positions
        output_fn(
            "  %s placed on %s-%s."
            % (
                name,
                format_coordinate(*cells[0]),
                format_coordinate(*cells[-1]),
            )
        )
        index += 1
    return ships
