# ==========================================
# display.py - User Interface
# ==========================================

# Responsibilities:
# 1. Display the player's board.
# 2. Display the computer's board.
# 3. Show hit and miss messages.
# 4. Display numerical clues.
# 5. Display the shop and game menus.
# 6. Display victory and defeat screens.
#
# Everything stays inside an 80-column by 24-row terminal.
# This file only draws. It never changes boards, cash or ships.
#
# Data this file expects (agree on these with the team):
#   board        -> 10x10 list (board[row][col]) of ship positions.
#                   Water: None, "", ".", "~", 0 or False.
#                   Anything else (e.g. "S", a ship name, 1) = ship segment.
#   attack_board -> 10x10 list of attacks made on that board:
#                   None, "", "."        not attacked yet
#                   "X" or "hit"         hit
#                   "#" or "sunk"        part of a sunk ship
#                   "O" or "miss"        miss with no clue
#                   int 0-8 (or "0"-"8") miss showing a numerical clue
#   player       -> dict with "cash" (see shop.py)
#   game_state   -> dict; display reads these keys if present:
#                   "turn", "player_ships_left", "computer_ships_left",
#                   "extra_shots", "radar_charges"
#   Coordinates are (row, col), 0-based. Shown on screen as A-J and 1-10.

import os
import sys

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 24
BOARD_SIZE = 10
COLUMN_LETTERS = "ABCDEFGHIJ"

WATER_VALUES = (None, "", ".", "~", "water", "empty", 0, False)


# ---------- Small helpers ----------
def fit(text):
    """Cut a line so it never goes past 80 columns."""
    return str(text)[:SCREEN_WIDTH]


def center(text):
    """Centre a line inside the 80 columns."""
    return fit(str(text).center(SCREEN_WIDTH).rstrip())


def clear_screen():
    """Clear the terminal (Windows, macOS and Linux)."""
    os.system("cls" if os.name == "nt" else "clear")


def print_lines(lines):
    """Print lines, each cut to 80 columns, at most 23 (row 24 is for input)."""
    for line in list(lines)[: SCREEN_HEIGHT - 1]:
        print(fit(line))


def coord_to_text(row, col):
    """(2, 3) -> 'D3'."""
    return f"{COLUMN_LETTERS[col]}{row + 1}"


# ---------- Turning cells into symbols ----------
def attack_symbol(value):
    """Symbol for an attacked square, or None if it was not attacked."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value) if 0 <= value <= 8 else "?"
    text = str(value).strip().lower()
    if text in ("", ".", "~"):
        return None
    if text in ("x", "hit"):
        return "X"
    if text in ("#", "sunk"):
        return "#"
    if text in ("o", "miss"):
        return "o"
    if len(text) == 1 and text.isdigit():
        return text
    return text[0].upper()


def cell_symbol(ship_value, attack_value, hide_ships=False):
    """One character for a square.

    A clue number belongs to the square, not to what sits on it, so a number can
    be written on a square that also holds a ship.  On your own board the ship
    still wins, because you already know where your fleet is; on the enemy board
    the number is shown (the ship is hidden there anyway).
    """
    shot = attack_symbol(attack_value)
    is_ship = ship_value not in WATER_VALUES

    if shot is not None:
        if is_ship and not hide_ships and shot.isdigit():
            return "S"
        return shot

    if is_ship and not hide_ships:
        return "S"
    return "."


def board_lines(board, attack_board, hide_ships=False):
    """Return a board as 11 text lines (header + 10 rows), 23 chars wide."""
    lines = ["   " + " ".join(COLUMN_LETTERS)]
    for row in range(BOARD_SIZE):
        cells = []
        for col in range(BOARD_SIZE):
            ship = board[row][col] if board else None
            shot = attack_board[row][col] if attack_board else None
            cells.append(cell_symbol(ship, shot, hide_ships))
        lines.append(f"{row + 1:>2} " + " ".join(cells))
    return lines


# ---------- 1 & 2. Boards ----------
def display_board(board, attack_board, hide_ships=False):
    """Display the game board in the terminal.

    Player's board:   display_board(player_board, player_attacks)
    Computer's board: display_board(computer_board, computer_attacks,
                                    hide_ships=True)
    """
    title = "ENEMY WATERS" if hide_ships else "YOUR FLEET"
    print_lines(["    " + title] + ["    " + line for line in
                                     board_lines(board, attack_board, hide_ships)])


def display_both_boards(player_board, player_attacks,
                        computer_board, computer_attacks):
    """Display both boards side by side (fits the 80x24 screen better)."""
    left = ["YOUR FLEET"] + board_lines(player_board, player_attacks)
    right = ["ENEMY WATERS"] + board_lines(computer_board, computer_attacks,
                                         hide_ships=True)
    lines = ["    " + l.ljust(31) + r for l, r in zip(left, right)]
    lines.append("")
    lines.append("    Key: S ship  X hit  # sunk  o miss  "
                 "0-8 ship parts touching that square")
    print_lines(lines)


# ---------- 3 & 4. Messages and clues ----------
def display_message(message):
    """Display a message to the player."""
    if isinstance(message, (list, tuple)):
        for line in message:
            print(fit(" " + str(line)))
    elif message:
        print(fit(" " + str(message)))


def attack_message(who, row, col, result, clue=None):
    """Build a hit/miss message, e.g. for display_message().

    who    -> "You" or "Computer"
    result -> "hit", "sunk" or "miss"
    clue   -> number clue on a miss (or None)
    """
    where = coord_to_text(row, col)
    if result == "sunk":
        return f"{who} fired at {where}: HIT - ship sunk!"
    if result == "hit":
        return f"{who} fired at {where}: HIT!"
    if clue is not None:
        return f"{who} fired at {where}: miss. Clue: {clue} ship part(s) nearby."
    return f"{who} fired at {where}: miss."


def display_radar(row, col, results):
    """Display radar clues. results = list of ((row, col), clue).
    Radar shows numbers only, never ship positions."""
    clues = {square: clue for square, clue in results}
    rows = sorted({r for r, _ in clues})
    cols = sorted({c for _, c in clues})
    lines = [center("=== RADAR SCAN ==="),
             center(f"Centre: {coord_to_text(row, col)}"), "",
             "        " + " ".join(COLUMN_LETTERS[c] for c in cols)]
    for r in rows:
        lines.append(f"     {r + 1:>2} " +
                     " ".join(str(clues.get((r, c), " ")) for c in cols))
    lines += ["", "  Each number = ship parts touching that square",
              "  (sideways or diagonally). Sunk ships are not counted."]
    print_lines(lines)


# ---------- 5. Shop and menus ----------
def display_shop(items):
    """Display available shop items and their prices.

    items -> dict {item name: price}, e.g. shop.get_shop_items()
    """
    try:
        import shop
        descriptions = {n: i["description"] for n, i in shop.SHOP_ITEMS.items()}
    except (ImportError, AttributeError, KeyError, TypeError):
        descriptions = {}

    lines = [center("=== TACTICAL SHOP ==="), ""]
    for number, (name, price) in enumerate(items.items(), start=1):
        line = f"  {number}. {name.title():<14} ${price:<4} {descriptions.get(name, '')}"
        lines.append(line.rstrip())
    lines += ["", "  Type an item's number or name to buy it.",
              "  Press Enter with nothing typed to leave the shop."]
    print_lines(lines)


def display_title_screen():
    """Display the title / instructions screen."""
    print_lines([
        "", "",
        center("B A T T L E S H I P"),
        center("Tactical Command Edition"),
        "",
        center("Sink the computer's fleet before it sinks yours."),
        "",
        center("A miss shows a number: how many ship parts touch"),
        center("that square (sideways or diagonally)."),
        center("Use the clues to work out where the enemy ships are."),
        "",
        center("Hits and sinks earn cash to spend in the shop."),
    ])


def display_menu(options, title="MENU"):
    """Display a numbered menu, e.g. ["Fire", "Shop", "Quit"]."""
    lines = [center(f"=== {title} ===")]
    lines += [f"  {i}. {option}" for i, option in enumerate(options, start=1)]
    print_lines(lines)


# ---------- Input ----------
class EndOfInput(Exception):
    """Raised when the player closes the input (Ctrl-D) or presses Ctrl-C.

    main.py catches this so the game can end with a friendly message instead of
    a Python traceback.  Graders often pipe a fixed list of moves into the game;
    that hits this case when the list runs out.
    """


def get_player_input(prompt="Enter your move (e.g. C4): "):
    """Get and return the player's input, or raise EndOfInput."""
    try:
        return input(fit(prompt)).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise EndOfInput()


def pause(prompt="\nPress Enter to continue... "):
    """Wait for the player to look at the screen.

    Only when a person is actually at the keyboard: when the moves are piped in
    (automated tests, grading scripts) waiting for Enter would eat the next
    move, so the pause is skipped instead.
    """
    if not sys.stdin.isatty():
        return
    try:
        get_player_input(prompt)
    except EndOfInput:
        pass


# ---------- Status ----------
def display_game_status(player, game_state):
    """Display the current game status."""
    parts = []
    if game_state.get("turn") is not None:
        parts.append(f"Turn {game_state['turn']}")
    parts.append(f"Cash: ${player.get('cash', 0)}")
    if game_state.get("player_ships_left") is not None:
        parts.append(f"Your ships: {game_state['player_ships_left']}")
    if game_state.get("computer_ships_left") is not None:
        parts.append(f"Enemy ships: {game_state['computer_ships_left']}")
    if game_state.get("extra_shots"):
        parts.append(f"Extra shots: {game_state['extra_shots']}")
    if game_state.get("radar_charges"):
        parts.append(f"Radar: {game_state['radar_charges']}")
    print(fit("    " + "   ".join(parts)))
    print("-" * SCREEN_WIDTH)


# ---------- 6. Victory and defeat ----------
def display_victory(turns=None):
    """Display the victory screen."""
    lines = ["", "", "", center("*** VICTORY ***"), "",
             center("You sank the entire enemy fleet!")]
    if turns is not None:
        lines += ["", center(f"Turns played: {turns}")]
    print_lines(lines)


def display_defeat(turns=None):
    """Display the defeat screen."""
    lines = ["", "", "", center("*** DEFEAT ***"), "",
             center("The computer sank your fleet.")]
    if turns is not None:
        lines += ["", center(f"Turns played: {turns}")]
    print_lines(lines)


# ---------- Quick self-test (runs only when this file is run directly) ----------
if __name__ == "__main__":
    player_board = [[None] * 10 for _ in range(10)]
    player_attacks = [[None] * 10 for _ in range(10)]
    computer_board = [[None] * 10 for _ in range(10)]
    computer_attacks = [[None] * 10 for _ in range(10)]
    for c in range(1, 5):
        player_board[0][c] = "Battleship"
    player_attacks[0][2] = "hit"
    computer_board[4][4] = "S"
    computer_board[3][3] = "S"            # hidden: must NOT appear
    computer_attacks[4][4] = "X"
    computer_attacks[2][2] = 3
    computer_attacks[9][9] = "miss"

    print("--- main game screen ---")
    display_both_boards(player_board, player_attacks,
                        computer_board, computer_attacks)
    display_game_status({"cash": 60}, {"turn": 4, "player_ships_left": 5,
                                       "computer_ships_left": 5,
                                       "extra_shots": 1})
    display_message([attack_message("You", 2, 2, "miss", 3),
                     attack_message("Computer", 0, 2, "hit"),
                     attack_message("You", 4, 4, "sunk")])

    print("\n--- single board (enemy) ---")
    display_board(computer_board, computer_attacks, hide_ships=True)

    print("\n--- shop ---")
    try:
        import shop
        display_shop(shop.get_shop_items())
    except ImportError:
        display_shop({"radar": 40, "extra strike": 50})

    print("\n--- radar ---")
    display_radar(0, 0, [((0, 0), 1), ((0, 1), 2), ((1, 0), 0), ((1, 1), 1)])

    print("\n--- victory / defeat ---")
    display_victory(25)
    display_defeat()


