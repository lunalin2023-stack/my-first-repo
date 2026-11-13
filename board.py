

# ==========================================
# board.py - Board Management
# ==========================================

# Responsibilities:
# 1. Create the game boards.
# 2. Store ship positions.
# 3. Record hit and miss locations.
# 4. Check whether coordinates are valid.


def create_board(rows=10, cols=10):
    """Create and return an empty board with specified dimensions."""

    if rows <= 0 or cols <= 0:
        raise ValueError("Board dimensions must be positive.")

    board = [[None for col in range(cols)] for row in range(rows)]

    return board


def is_valid_coordinate(row, col, rows=10, cols=10):
    """Check whether a coordinate is within the specified dimensions."""

    return (
        isinstance(row, int) #isinstance(obj,type)= obj is type
        and isinstance(col, int)
        and 0 <= row < rows
        and 0 <= col < cols
    )


def get_cell(board, row, col):
    """Return the content of a specific cell."""

    if not board or not board[0]: # bool([])=False
        raise ValueError("Board cannot be empty.")

    rows = len(board)
    cols = len(board[0])

    if not is_valid_coordinate(row, col, rows, cols):
        raise IndexError("Coordinate is outside the board.")

    return board[row][col]


def update_cell(board, row, col, value):
    """Update the content of a specific cell."""

    if not board or not board[0]:
        raise ValueError("Board cannot be empty.")

    rows = len(board)
    cols = len(board[0])

    if not is_valid_coordinate(row, col, rows, cols):
        raise IndexError("Coordinate is outside the board.")

    board[row][col] = value


def record_attack(attack_board, row, col, result):
    """
    Record an attack as a hit ('H') or miss ('M').

    Return True if the attack is recorded.
    Return False if the cell has already been attacked.
    """

    if result not in ("H", "M"):
        raise ValueError("Attack result must be 'H' or 'M'.")

    if get_cell(attack_board, row, col) is not None:
        return False

    update_cell(attack_board, row, col, result)

    return True


def has_been_attacked(attack_board, row, col):
    """Check whether a particular cell has already been attacked."""

    return get_cell(attack_board, row, col) is not None
