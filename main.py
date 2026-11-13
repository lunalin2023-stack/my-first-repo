
# ==========================================
# Tactical Command Edition
# main.py - Main Game Controller
# ==========================================


from board import create_board, update_cell

from display import (
    EndOfInput,
    clear_screen,
    display_board,
    display_both_boards,
    display_game_status,
    display_message,
    display_shop,
    display_radar,
    display_title_screen,
    display_victory,
    display_defeat,
    get_player_input,
    pause
)

from combat import (
    process_player_attack,
    process_computer_attack,
    award_cash,
    check_victory
)

from computer import ComputerAI

from ship import (
    PlacementError,
    Ship,
    FLEET,
    place_fleet,
    parse_coordinate,
    stamp_on_board
)

from logic import calculate_clue, get_surrounding_clues

from shop import (
    new_player_wallet,
    get_shop_items,
    find_item,
    purchase_item,
    apply_power_up,
    use_extra_shot,
    use_radar_charge,
    radar_area
)



# ==========================================
# 1. GAME INITIALIZATION
# ==========================================

def initialize_game():
    """Initialize boards, fleets, player information and game state."""

    # Create the four boards
    player_board = create_board(10, 10)
    computer_board = create_board(10, 10)

    player_attack_board = create_board(10, 10)
    computer_attack_board = create_board(10, 10)

    
    # Initialize player information
    player = new_player_wallet()
    player["ships_remaining"] = 5

    computer = {
        "ships_remaining": 5
    }

    # Initialize the game state
    game_state = {
        "player_board": player_board,
        "computer_board": computer_board,

        "player_attack_board": player_attack_board,
        "computer_attack_board": computer_attack_board,

        "player": player,
        "computer": computer,

        "player_ships": [],
        "computer_ships": [],

        "player_shots": set(),
        "computer_shots": set(),

        "computer_ai": ComputerAI(level=3),

        # Shop power-ups
        "extra_shots": 0,
        "radar_charges": 0,

        # Cells that currently show a revealed number clue.
        # They are recalculated after every shot so the numbers never go stale.
        "clue_cells": set(),          # numbers on the player's attack board
        "computer_clue_cells": set(),  # numbers on the computer's attack board

        "turn": 1,
        "game_over": False,
        "winner": None,
        "quit": False
    }


    return game_state


# ==========================================
# 2. SHIP PLACEMENT
# ==========================================

def place_all_fleets(game_state):
    """Let the player place their fleet and randomly place the computer fleet."""

    player_ships = game_state["player_ships"]
    computer_ships = game_state["computer_ships"]

    player_board = game_state["player_board"]
    computer_board = game_state["computer_board"]

    # --------------------------------------
    # Player ship placement
    # --------------------------------------

    display_message("PLACE YOUR FLEET")

    def show_player_fleet(ships):
        """Display the player's fleet during placement."""

        temporary_board = create_board(10, 10)

        for ship in ships:
            stamp_on_board(temporary_board, ship, marker="S")

        empty_attack_board = create_board(10, 10)

        display_board(
            temporary_board,
            empty_attack_board
        )

    try:
        place_fleet(
            player_ships,
            show_fn=show_player_fleet
        )
    except PlacementError as error:
        # Closed input (Ctrl-D) or "quit" during placement: end gracefully.
        display_message(str(error))
        return False

    # Record the player's ships on their board
    for ship in player_ships:
        stamp_on_board(player_board, ship, marker="S")

    display_message("Your fleet has been placed successfully!")

    # --------------------------------------
    # Computer ship placement
    # --------------------------------------

    display_message("Computer is deploying its fleet...")

    computer_ai = game_state["computer_ai"]

    _, fleet_positions = computer_ai.generate_ship_positions()

    for ship_id, ((name, length), positions) in enumerate(
        zip(FLEET, fleet_positions),
        start=1
    ):
        # Convert generated coordinates into actual Ship objects
        ship = Ship(
            name,
            length,
            ship_id=ship_id,
            positions=positions
        )

        computer_ships.append(ship)

        # Record the ship on the computer's board
        stamp_on_board(computer_board, ship, marker="S")

    display_message("Computer fleet deployed successfully!")

    return True


def sunk_cells(ships):
    """Every square belonging to a ship that has already sunk."""

    cells = set()

    for ship in ships:
        if ship.is_sunk():
            cells.update(ship.positions)

    return cells


def reveal_clues_around(ship_board, attack_board, ships, row, col, clue_cells):
    """Write the eight clue numbers around a missed shot.

    The number belongs to the square, not to what sits on it, so a square that
    happens to hold a ship gets a number as well.  Skipping those squares would
    give the fleet away: the only square without a number would be a ship.
    """

    excluded_cells = sunk_cells(ships)

    clues = get_surrounding_clues(
        ship_board,
        row,
        col,
        excluded_cells
    )

    for (r, c), clue in clues.items():

        # Never overwrite something already known about that square
        if attack_board[r][c] is not None:
            continue

        update_cell(attack_board, r, c, clue)

        # Remember this square so the number can be refreshed later
        clue_cells.add((r, c))


def refresh_clues(ship_board, attack_board, ships, clue_cells):
    """Recalculate every revealed clue number on one board.

    Clues leave out ships that have already sunk.  Without a refresh, a number
    revealed early still counts a ship that has sunk since, so the board would
    contradict itself.  A board is only 10x10, so redrawing is cheap.
    """

    excluded_cells = sunk_cells(ships)

    for (r, c) in list(clue_cells):

        value = attack_board[r][c]

        # Fired at since then: the square shows a shot, not a number
        if value is None or isinstance(value, str):
            clue_cells.discard((r, c))
            continue

        update_cell(
            attack_board,
            r,
            c,
            calculate_clue(ship_board, r, c, excluded_cells)
        )


def refresh_all_clues(game_state):
    """Refresh the clue numbers on both boards (player and computer)."""

    refresh_clues(
        game_state["computer_board"],
        game_state["player_attack_board"],
        game_state["computer_ships"],
        game_state["clue_cells"]
    )

    refresh_clues(
        game_state["player_board"],
        game_state["computer_attack_board"],
        game_state["player_ships"],
        game_state["computer_clue_cells"]
    )



def open_shop(game_state):
    """Allow the player to purchase power-ups."""

    player = game_state["player"]

    while True:
        print("\n")
        display_message(f"Your available cash: ${player['cash']}")

        display_shop(get_shop_items())

        try:
            choice = get_player_input(
                "Enter item number/name, or press Enter to leave: "
            )
        except EndOfInput:
            display_message("Leaving the shop.")
            return

        # Leave the shop
        if choice == "":
            display_message("Leaving the shop.")
            return

        # Find the selected item
        item = find_item(choice)

        if item is None:
            display_message("Invalid shop selection.")
            continue

        # Process the purchase
        success, message = purchase_item(player, item)

        display_message(message)

        if success:
            # Apply the purchased power-up
            power_message = apply_power_up(item, game_state)
            display_message(power_message)

def use_radar(game_state):
    """Use one radar charge to scan a 3x3 area."""

    if game_state["radar_charges"] <= 0:
        display_message("You do not have any radar charges.")
        return

    try:
        coordinate = get_player_input(
            "Enter the centre coordinate for radar (e.g. B5): "
        )
    except EndOfInput:
        return

    try:
        row, col = parse_coordinate(coordinate)

    except ValueError as error:
        display_message(str(error))
        return

    # Identify cells belonging to sunk ships
    excluded_cells = set()

    for ship in game_state["computer_ships"]:
        if ship.is_sunk():
            excluded_cells.update(ship.positions)

    # Get the 3x3 radar area
    squares = radar_area(row, col)

    # Calculate the clue for every square
    results = []

    computer_board = game_state["computer_board"]

    for r, c in squares:

        clue = calculate_clue(
            computer_board,
            r,
            c,
            excluded_cells
        )

        results.append(((r, c), clue))

    # Spend one radar charge
    use_radar_charge(game_state)

    # Display the radar results
    display_radar(row, col, results)

# ==========================================
# 3. PLAYER TURN
# ==========================================


def show_status(game_state):
    """Draw the status bar: turn, cash, ships left and power-ups."""

    player = game_state["player"]

    display_game_status(
        player,
        {
            "turn": game_state.get("turn"),
            "player_ships_left": player.get("ships_remaining"),
            "computer_ships_left": game_state["computer"].get("ships_remaining"),
            "extra_shots": game_state.get("extra_shots"),
            "radar_charges": game_state.get("radar_charges"),
        }
    )


def draw_frame(game_state, heading, message=""):
    """Clear the screen and draw one complete frame.

    Used before every prompt so the boards always show what has just happened.
    """

    clear_screen()

    display_message(heading)

    show_status(game_state)

    # Both waters: your fleet on the left (and where the computer hit it),
    # the enemy waters you are shelling on the right.
    display_both_boards(
        game_state["player_board"],
        game_state["computer_attack_board"],
        game_state["computer_board"],
        game_state["player_attack_board"]
    )

    if message:
        display_message(message)


def player_turn(game_state):
    """Handle one complete player turn."""

    computer_board = game_state["computer_board"]
    player_attack_board = game_state["player_attack_board"]

    # Consume an extra-shot charge purchased on a previous turn.
    # A charge gives one additional attack this turn.
    extra_shot_available = use_extra_shot(game_state)

    shots_remaining = 1 + int(extra_shot_available)

    # Continue until all attacks for this turn have been used
    result = None
    message = ""

    while shots_remaining > 0:

        # Redraw the whole frame before every prompt.  Without this the board
        # still shows the state from the start of the turn, so a square you have
        # just fired at looks untouched -- and typing it again says
        # "already fired at" while nothing appears on the screen.
        draw_frame(game_state, "YOUR TURN", message)

        display_message(
            f"Attacks remaining this turn: {shots_remaining}"
        )

        try:
            coordinate = get_player_input(
                "\nEnter coordinate, SHOP, RADAR or Q to quit: "
            ).strip().upper()
        except EndOfInput:
            game_state["quit"] = True
            game_state["game_over"] = True
            game_state["winner"] = "quit"
            display_message("Input closed - ending the game.")
            return None

        # Quit the game
        if coordinate == "Q":
            game_state["quit"] = True
            game_state["game_over"] = True
            game_state["winner"] = "quit"

            display_message("You have quit the game.")
            return None

        # Open the shop
        if coordinate == "SHOP":
            open_shop(game_state)
            message = ""
            continue

        # Use radar
        if coordinate == "RADAR":
            use_radar(game_state)
            message = ""
            continue

        # Validate attack coordinate
        try:
            row, col = parse_coordinate(coordinate)

        except ValueError as error:
            message = str(error)
            continue

        # Process the attack
        result = process_player_attack(
            game_state["computer_ships"],
            row,
            col,
            game_state["player_shots"]
        )

        # Repeated or invalid attacks do not consume an attack
        if not result.consumes_turn:
            message = result.message
            continue

        shots_remaining -= 1

        # Write the outcome onto the board in one place, whatever it was.  One
        # branch instead of three means a square can never end up recorded in
        # player_shots while still looking untouched on the screen.
        update_cell(player_attack_board, row, col, result.outcome)

        if result.outcome == "sunk":
            game_state["computer"]["ships_remaining"] -= 1

        elif result.outcome == "miss":
            # Reveal the eight numbers around the missed square
            reveal_clues_around(
                game_state["computer_board"],
                player_attack_board,
                game_state["computer_ships"],
                row,
                col,
                game_state["clue_cells"]
            )

        # Keep every revealed number consistent with the ships still afloat
        refresh_all_clues(game_state)

        # Update cash
        player = game_state["player"]

        player["cash"] = award_cash(
            player["cash"],
            result
        )

        message = "%s  Remaining cash: $%d" % (result.message, player["cash"])

        # Check whether the player has won
        if check_game_over(game_state):
            draw_frame(game_state, "YOUR TURN", message)
            return result

    # Show the last shot of the turn before the computer moves
    draw_frame(game_state, "YOUR TURN", message)

    return result



# ==========================================
# 4. COMPUTER TURN
# ==========================================

def computer_turn(game_state):
    """Handle one complete computer turn."""

    # Get the necessary game information
    computer_ai = game_state["computer_ai"]

    player_ships = game_state["player_ships"]

    computer_attack_board = game_state["computer_attack_board"]

    computer_shots = game_state["computer_shots"]

    # Generate an attack coordinate.  The AI reads the same board the player
    # sees, so it can reason from the clue numbers exactly like the player.
    row, col = computer_ai.generate_computer_attack(computer_attack_board)

    # Process the attack against the player's fleet
    result = process_computer_attack(
        player_ships,
        row,
        col,
        computer_shots
    )

    # Check whether the attack is valid
    if not result.consumes_turn:
        draw_frame(game_state, "COMPUTER'S TURN", result.message)
        return result

    # Write the outcome onto the board in one place, whatever it was
    update_cell(computer_attack_board, row, col, result.outcome)

    if result.outcome == "sunk":
        game_state["player"]["ships_remaining"] -= 1

    elif result.outcome == "miss":
        # The computer plays by exactly the same rule: its miss reveals the
        # eight numbers around that square on the board it is shooting at.
        reveal_clues_around(
            game_state["player_board"],
            computer_attack_board,
            game_state["player_ships"],
            row,
            col,
            game_state["computer_clue_cells"]
        )

    # Keep both boards' numbers consistent with the ships still afloat
    refresh_all_clues(game_state)

    # Update the computer AI's memory
    sunk_ship_cells = None

    if result.is_sunk and result.ship is not None:
        sunk_ship_cells = result.ship.positions

    computer_ai.report_result(
        row,
        col,
        result.outcome.upper(),
        sunk_ship_cells=sunk_ship_cells,
        clue_data=result.clue
    )

    # Draw the whole frame once, with the mark and the numbers already on it
    draw_frame(
        game_state,
        "COMPUTER'S TURN",
        "Computer attacked %s: %s" % (result.coordinate, result.message)
    )

    # Let the player look at where the shot landed before the screen is cleared
    pause()

    # Check whether the game has ended
    check_game_over(game_state)

    return result


# ==========================================
# 5. GAME OVER CHECK
# ==========================================


def check_game_over(game_state):
    """Check whether the game has ended."""

    # Do not overwrite a quit result with a victory/defeat result
    if game_state["quit"]:
        return True

    winner = check_victory(
        game_state["player_ships"],
        game_state["computer_ships"]
    )

    if winner is not None:
        game_state["game_over"] = True
        game_state["winner"] = winner

    return game_state["game_over"]



# ==========================================
# 6. MAIN GAME LOOP
# ==========================================


def main():
    """Control the overall game flow."""

    clear_screen()

    # Title screen also explains the rules of the game
    display_title_screen()

    try:
        get_player_input("\nPress Enter to start (or Q to quit): ")
    except EndOfInput:
        return

    clear_screen()

    print("=" * 40)
    print("       TACTICAL COMMAND EDITION")
    print("=" * 40)

    print("\nGAME STARTS!\n")

    # Initialize the game
    game_state = initialize_game()

    # Place both fleets (False = the player cancelled or closed the input)
    if not place_all_fleets(game_state):
        display_message("No fleets placed - the game has ended.")
        return

    display_message("\nBATTLE BEGINS!")

    turn = 1

    # Main game loop
    while not check_game_over(game_state):

        game_state["turn"] = turn

        # player_turn() clears the screen and draws the status bar itself,
        # so nothing is printed here that would be wiped straight away.
        player_turn(game_state)

        # Stop if the player quit or won
        if check_game_over(game_state):
            break

        # Computer's turn
        computer_turn(game_state)

        turn += 1

    # Display final result
    print("\n" + "=" * 40)

    if game_state["winner"] == "player":
        display_victory(turn)

    elif game_state["winner"] == "computer":
        display_defeat(turn)

    elif game_state["winner"] == "quit":
        display_message("GAME ENDED: You chose to quit.")

    print("=" * 40)


if __name__ == "__main__":
    main()
# __name__ of (python name.py) = __name__
# main() is tiggered (game starts) iff main.py is run, not in the case of [main is imported to another file and that file is run]
