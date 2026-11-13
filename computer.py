# ==========================================
# computer.py - Computer AI (Opponent)
# ==========================================
# Responsibilities:
# 1. Randomly place computer ships.
# 2. Select attack coordinates without cheating.
# 3. Remember which cells have been shot.
# 4. Three levels of play:
#      level 1 - random shooting;
#      level 2 - hunt/target: after a hit, try its neighbours;
#      level 3 - clue deduction: reason from the numbers on its own board,
#                exactly like the player does (see analyse_board()).
#
# Level 3 never looks at the player's fleet.  It only reads the board it is
# shooting at, which holds nothing but shots and the numbers a miss reveals.

import random

SIZE = 10
FLEET = (5, 4, 3, 3, 2)  # Carrier, Battleship, Cruiser, Submarine, Destroyer

# What a square of the attack board can hold
HIT_WORDS = ("hit", "x")
SUNK_WORDS = ("sunk", "#")


# --------------------------------------------------------------- board reading
def neighbours(row, col):
    """The (up to) eight squares around (row, col), inside the board."""
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            r, c = row + dr, col + dc
            if 0 <= r < SIZE and 0 <= c < SIZE:
                yield r, c


def is_clue(value):
    """True if a board square holds a clue number (0-8)."""
    return isinstance(value, int) and not isinstance(value, bool)


def read_board(board):
    """Split one attack board into what each square tells us.

    Returns (clues, ships, sunk, shots):
      clues  -> {(r, c): number}   squares showing a number
      ships  -> {(r, c)}          hit squares of ships still afloat
      sunk   -> {(r, c)}          squares of ships that have sunk
      shots  -> {(r, c)}          every square already fired at
    """
    clues = {}
    ships = set()
    sunk = set()
    shots = set()

    for r in range(SIZE):
        for c in range(SIZE):
            value = board[r][c]
            if value is None:
                continue
            if is_clue(value):
                clues[(r, c)] = value
                continue

            text = str(value).strip().lower()
            if text in HIT_WORDS:
                ships.add((r, c))
                shots.add((r, c))
            elif text in SUNK_WORDS:
                sunk.add((r, c))
                shots.add((r, c))
            else:
                shots.add((r, c))       # a miss

    return clues, ships, sunk, shots


def analyse_board(board):
    """Work out what the visible numbers prove, without guessing.

    Every clue counts the *unsunk* ship squares in its eight neighbours, so:

      * if a clue already equals the number of known ship squares around it,
        every remaining neighbour is water                       -> "safe";
      * if every unknown neighbour would have to be a ship to reach the clue,
        all of them are ships                                    -> "certain".

    Returns (safe, certain), both sets of (row, col).
    """
    clues, ships, sunk, shots = read_board(board)

    safe = set()
    certain = set()

    for (row, col), total in clues.items():
        known_ships = 0
        unknown = []

        for cell in neighbours(row, col):
            if cell in ships:
                known_ships += 1
            elif cell in sunk:
                continue                # sunk ships are not counted by clues
            elif cell in shots:
                continue                # already fired at
            else:
                unknown.append(cell)

        if not unknown:
            continue

        if known_ships == total:
            safe.update(unknown)
        elif known_ships + len(unknown) == total:
            certain.update(unknown)

    # A cell can never be both, and never a square already fired at
    certain -= shots
    safe -= shots
    safe -= certain

    return safe, certain


class ComputerAI:
    def __init__(self, level=3):
        # Level 1: random
        # Level 2: targets the neighbours of an unresolved hit
        # Level 3: level 2 + deduction from the numbers on its board
        self.level = level

        # --- AI's memory (it never sees the player's ship board) ---
        self.shot = [[False] * SIZE for _ in range(SIZE)]
        self.pending_hits = []      # hits that have not sunk a ship yet
        self.sunk_cells = set()     # squares of ships that are fully sunk

    # ------------------------------------------------------------ placement
    def generate_ship_positions(self):
        """Generate valid random positions for the computer fleet."""
        board = [[False] * SIZE for _ in range(SIZE)]
        fleet_positions = []

        for length in FLEET:
            while True:
                # Randomly choose orientation: 0 = Horizontal, 1 = Vertical
                orientation = random.randint(0, 1)

                if orientation == 0:
                    r = random.randint(0, SIZE - 1)
                    c = random.randint(0, SIZE - length)
                    cells = [(r, c + i) for i in range(length)]
                else:
                    r = random.randint(0, SIZE - length)
                    c = random.randint(0, SIZE - 1)
                    cells = [(r + i, c) for i in range(length)]

                # Check if the ship overlaps with existing ships
                if not any(board[r][c] for r, c in cells):
                    for r, c in cells:
                        board[r][c] = True
                    fleet_positions.append(cells)
                    break

        return board, fleet_positions

    # ------------------------------------------------------------- memory
    def report_result(self, r, c, result, sunk_ship_cells=None, clue_data=None):
        """Update the AI's memory after it fires at (r, c).

        result can be: 'MISS', 'HIT' or 'SUNK'.
        """
        self.shot[r][c] = True

        if result in ("HIT", "SUNK"):
            if (r, c) not in self.pending_hits:
                self.pending_hits.append((r, c))

        if result == "SUNK" and sunk_ship_cells:
            self.sunk_cells.update(sunk_ship_cells)
            self.pending_hits = [
                hit for hit in self.pending_hits if hit not in sunk_ship_cells
            ]

    def was_shot(self, cell):
        return self.shot[cell[0]][cell[1]]

    # ------------------------------------------------------------- shooting
    def generate_computer_attack(self, board=None):
        """Choose a square to fire at.

        ``board`` is the AI's own attack board (the one displayed to the
        player).  Passing it lets level 3 read the clue numbers; without it the
        AI falls back to levels 1-2 only.
        """
        safe = set()

        if self.level >= 3 and board is not None:
            safe, certain = analyse_board(board)

            fresh = [cell for cell in certain if not self.was_shot(cell)]
            if fresh:
                # Proven ships: take one straight away
                return random.choice(fresh)

        if self.level == 1:
            return self._attack_basic(safe)

        return self._attack_intermediate(safe)

    def _unshot(self, exclude=frozenset()):
        available = []
        for r in range(SIZE):
            for c in range(SIZE):
                if not self.shot[r][c] and (r, c) not in exclude:
                    available.append((r, c))
        return available

    def _attack_basic(self, exclude=frozenset()):
        """Level 1: pick a random square that is not known to be water."""
        available = self._unshot(exclude)

        if available:
            return random.choice(available)

        # Every remaining square is "known safe": that means the numbers are
        # telling us nothing useful is left, so shoot anywhere still untried.
        fallback = self._unshot()
        if fallback:
            return random.choice(fallback)
        return (0, 0)

    def _attack_intermediate(self, exclude=frozenset()):
        """Level 2: prefer the neighbours of hits that have not sunk anything."""
        targets = set()

        for r, c in self.pending_hits:
            for nr, nc in neighbours(r, c):
                if not self.shot[nr][nc] and (nr, nc) not in exclude:
                    targets.add((nr, nc))

        if targets:
            return random.choice(list(targets))

        return self._attack_basic(exclude)
