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


def initialize_game():
    player_board = create_board(10, 10)
    computer_board = create_board(10, 10)
    player_attack_board = create_board(10, 10)
    computer_attack_board = create_board(10, 10)

    player = new_player_wallet()
    player["ships_remaining"] = 5

    computer = {"ships_remaining": 5}

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
        "extra_shots": 0,
        "radar_charges": 0,
        "clue_cells": set(),
        "computer_clue_cells": set(),
        "turn": 1,
        "game_over": False,
        "winner": None,
        "quit": False
    }
    return game_state


def place_all_fleets(game_state):
    player_ships = game_state["player_ships"]
    computer_ships = game_state["computer_ships"]
    player_board = game_state["player_board"]
    computer_board = game_state["computer_board"]

    def show_player_fleet(ships, message=""):
        clear_screen()
        display_message("=== PLACE YOUR FLEET ===")
        if message:
            display_message(message)
            print()
        temporary_board = create_board(10, 10)
        for ship in ships:
            stamp_on_board(temporary_board, ship, marker="S")
        empty_attack_board = create_board(10, 10)
        display_board(temporary_board, empty_attack_board)

    try:
        place_fleet(player_ships, show_fn=show_player_fleet)
    except PlacementError as error:
        display_message(str(error))
        return False

    for ship in player_ships:
        stamp_on_board(player_board, ship, marker="S")

    display_message("Your fleet has been placed successfully!")
    display_message("Computer is deploying its fleet...")

    computer_ai = game_state["computer_ai"]
    _, fleet_positions = computer_ai.generate_ship_positions()

    for ship_id, ((name, length), positions) in enumerate(zip(FLEET, fleet_positions), start=1):
        ship = Ship(name, length, ship_id=ship_id, positions=positions)
        computer_ships.append(ship)
        stamp_on_board(computer_board, ship, marker="S")

    display_message("Computer fleet deployed successfully!")
    return True


def sunk_cells(ships):
    cells = set()
    for ship in ships:
        if ship.is_sunk():
            cells.update(ship.positions)
    return cells


def reveal_clues_around(ship_board, attack_board, ships, row, col, clue_cells):
    excluded_cells = sunk_cells(ships)
    clues = get_surrounding_clues(ship_board, row, col, excluded_cells)
    for (r, c), clue in clues.items():
        if attack_board[r][c] is not None:
            continue
        update_cell(attack_board, r, c, clue)
        clue_cells.add((r, c))


def refresh_clues(ship_board, attack_board, ships, clue_cells):
    excluded_cells = sunk_cells(ships)
    for (r, c) in list(clue_cells):
        value = attack_board[r][c]
        if value is None or isinstance(value, str):
            clue_cells.discard((r, c))
            continue
        update_cell(attack_board, r, c, calculate_clue(ship_board, r, c, excluded_cells))


def refresh_all_clues(game_state):
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
    """Allow the player to purchase power-ups, while keeping the board visible."""
    player = game_state["player"]
    message = ""

    while True:
        clear_screen()
        display_message("TACTICAL SHOP")
        show_status(game_state)
        # ⭐ 删除了之前多余的 print("-" * 80)
        
        display_both_boards(
            game_state["player_board"],
            game_state["computer_attack_board"],
            game_state["computer_board"],
            game_state["player_attack_board"]
        )
        if message:
            display_message(message)
            message = ""
            
        display_shop(get_shop_items())
        
        try:
            choice = get_player_input("Enter item no./name, or press Enter to leave: ")
        except EndOfInput:
            return

        if choice == "":
            return

        item = find_item(choice)
        if item is None:
            message = "Invalid shop selection. Please try again."
            continue

        success, msg = purchase_item(player, item)
        if success:
            msg += " " + apply_power_up(item, game_state)
        message = msg


def use_radar(game_state):
    if game_state["radar_charges"] <= 0:
        display_message("You do not have any radar charges.")
        pause("Press Enter to continue...")
        return

    try:
        coordinate = get_player_input("Enter the centre coordinate for radar (e.g. B5): ")
    except EndOfInput:
        return

    try:
        row, col = parse_coordinate(coordinate)
    except ValueError as error:
        display_message(str(error))
        pause("Press Enter to continue...")
        return

    excluded_cells = sunk_cells(game_state["computer_ships"])
    squares = radar_area(row, col)
    results = []
    computer_board = game_state["computer_board"]

    for r, c in squares:
        clue = calculate_clue(computer_board, r, c, excluded_cells)
        results.append(((r, c), clue))
        if game_state["player_attack_board"][r][c] is None:
            update_cell(game_state["player_attack_board"], r, c, clue)
            game_state["clue_cells"].add((r, c))

    use_radar_charge(game_state)
    refresh_all_clues(game_state)

    # 雷达结果直接合并到棋盘（不单独显示雷达界面）
    draw_frame(game_state, "YOUR TURN", "Radar scan complete.")
    pause()


def show_status(game_state):
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
    clear_screen()
    display_message(heading)
    show_status(game_state)
    display_both_boards(
        game_state["player_board"],
        game_state["computer_attack_board"],
        game_state["computer_board"],
        game_state["player_attack_board"]
    )
    if message:
        display_message(message)


def player_turn(game_state):
    computer_board = game_state["computer_board"]
    player_attack_board = game_state["player_attack_board"]

    extra_shot_available = use_extra_shot(game_state)
    shots_remaining = 1 + int(extra_shot_available)
    result = None
    message = ""

    while shots_remaining > 0:
        draw_frame(game_state, "YOUR TURN", message)
        display_message(f"Attacks remaining this turn: {shots_remaining}")

        try:
            coordinate = get_player_input("\nEnter coordinate, SHOP, RADAR or Q to quit: ").strip().upper()
        except EndOfInput:
            game_state["quit"] = True
            game_state["game_over"] = True
            game_state["winner"] = "quit"
            return None

        if coordinate == "Q":
            game_state["quit"] = True
            game_state["game_over"] = True
            game_state["winner"] = "quit"
            return None

        if coordinate == "SHOP":
            open_shop(game_state)
            message = ""
            continue

        if coordinate == "RADAR":
            use_radar(game_state)
            message = ""
            continue

        try:
            row, col = parse_coordinate(coordinate)
        except ValueError as error:
            draw_frame(game_state, "YOUR TURN", f"Error: {error}")
            pause("Press Enter to try again...")
            message = ""
            continue

        result = process_player_attack(
            game_state["computer_ships"],
            row,
            col,
            game_state["player_shots"]
        )

        if not result.consumes_turn:
            message = result.message
            continue

        shots_remaining -= 1
        update_cell(player_attack_board, row, col, result.outcome)

        if result.outcome == "sunk":
            game_state["computer"]["ships_remaining"] -= 1
        elif result.outcome == "miss":
            reveal_clues_around(
                game_state["computer_board"],
                player_attack_board,
                game_state["computer_ships"],
                row,
                col,
                game_state["clue_cells"]
            )

        refresh_all_clues(game_state)
        player = game_state["player"]
        player["cash"] = award_cash(player["cash"], result)
        message = "%s  Remaining cash: $%d" % (result.message, player["cash"])

        if check_game_over(game_state):
            draw_frame(game_state, "YOUR TURN", message)
            return result

    draw_frame(game_state, "YOUR TURN", message)
    return result


def computer_turn(game_state):
    computer_ai = game_state["computer_ai"]
    player_ships = game_state["player_ships"]
    computer_attack_board = game_state["computer_attack_board"]
    computer_shots = game_state["computer_shots"]

    row, col = computer_ai.generate_computer_attack(computer_attack_board)
    result = process_computer_attack(player_ships, row, col, computer_shots)

    if not result.consumes_turn:
        draw_frame(game_state, "COMPUTER'S TURN", result.message)
        return result

    update_cell(computer_attack_board, row, col, result.outcome)

    if result.outcome == "sunk":
        game_state["player"]["ships_remaining"] -= 1
    elif result.outcome == "miss":
        reveal_clues_around(
            game_state["player_board"],
            computer_attack_board,
            game_state["player_ships"],
            row,
            col,
            game_state["computer_clue_cells"]
        )

    refresh_all_clues(game_state)
    sunk_ship_cells = result.ship.positions if result.is_sunk and result.ship is not None else None

    computer_ai.report_result(
        row, col, result.outcome.upper(),
        sunk_ship_cells=sunk_ship_cells, clue_data=result.clue
    )

    draw_frame(game_state, "COMPUTER'S TURN", "Computer attacked %s: %s" % (result.coordinate, result.message))
    pause()
    check_game_over(game_state)
    return result


def check_game_over(game_state):
    if game_state["quit"]:
        return True
    winner = check_victory(game_state["player_ships"], game_state["computer_ships"])
    if winner is not None:
        game_state["game_over"] = True
        game_state["winner"] = winner
    return game_state["game_over"]


def main():
    while True:
        clear_screen()
        display_title_screen()

        try:
            choice = get_player_input("\nPress Enter to start (or Q to quit): ").strip().upper()
            if choice == "Q":
                print("You have quitted the game.")
                break
        except EndOfInput:
            print("You have quitted the game.")
            break

        clear_screen()
        print("=" * 40)
        print("       TACTICAL COMMAND EDITION")
        print("=" * 40)
        print("\nGAME STARTS!\n")

        game_state = initialize_game()

        if not place_all_fleets(game_state):
            display_message("No fleets placed - returning to main menu.")
            pause("Press Enter to continue...")
            continue

        display_message("\nBATTLE BEGINS!")
        turn = 1

        while not check_game_over(game_state):
            game_state["turn"] = turn
            player_turn(game_state)
            if check_game_over(game_state):
                break
            computer_turn(game_state)
            turn += 1

        clear_screen()
        print("=" * 40)
        if game_state["winner"] == "player":
            display_victory(turn)
        elif game_state["winner"] == "computer":
            display_defeat(turn)
        elif game_state["winner"] == "quit":
            display_message("GAME ENDED: You chose to quit.")
        print("=" * 40)

        try:
            choice = get_player_input("\nPress Enter to return to main menu (or Q to quit): ").strip().upper()
            if choice == "Q":
                print("You have quitted the game.")
                break
        except EndOfInput:
            print("You have quitted the game.")
            break


if __name__ == "__main__":
    main()
