# ==========================================
# shop.py - Economy and Shop System
# ==========================================

# Responsibilities:
# 1. Track the player's cash.
# 2. Define power-ups and their prices.
# 3. Check whether the player can afford items.
# 4. Process purchases.
# 5. Apply purchased upgrades.
#
# Shared data this file expects (agree on these with the team):
#   player      -> dict with at least {"cash": int}
#                  (create one with new_player_wallet())
#   game_state  -> dict; this file only reads/writes these keys:
#                  "extra_shots"   : int, extra shots left this turn
#                  "radar_charges" : int, radar scans waiting to be used
#
# This file never draws to the screen. It returns short messages
# (under 80 characters) that display.py can print.

# ---------- Economy settings ----------
# Only the starting balance lives here.  Rewards are owned by combat.py
# (HIT_REWARD / SINK_BONUS) so the game has exactly one reward table.
STARTING_CASH = 50     # cash the player starts the game with

# ---------- Power-up catalogue ----------
# key: name typed by the player -> price and a short description
SHOP_ITEMS = {
    "radar": {
        "price": 40,
        "description": "Radar scan: reveals number clues in a 3x3 area",
    },
    "extra strike": {
        "price": 50,
        "description": "Extra strike: take one more shot next turn",
    },
}


# ---------- Cash tracking ----------
def new_player_wallet(starting_cash=STARTING_CASH):
    """Create the player's cash record at the start of the game."""
    return {"cash": starting_cash}


def get_cash(player):
    """Return how much cash the player has."""
    return player.get("cash", 0)


def add_cash(player, amount):
    """Add cash to the player (amount must not be negative)."""
    if amount < 0:
        raise ValueError("amount must not be negative")
    player["cash"] = get_cash(player) + amount
    return player["cash"]


def reward_for_attack(player, hit, sunk):
    """Give cash after an attack, using combat.py's reward table.

    Kept as a thin wrapper so callers that only know "hit"/"sunk" can still
    award cash; the amounts themselves come from combat.py.
    Returns (amount_earned, message).
    """
    from combat import HIT_REWARD, SINK_BONUS

    earned = 0
    if hit:
        earned += HIT_REWARD
    if sunk:
        earned += SINK_BONUS
    if earned > 0:
        add_cash(player, earned)
        return earned, f"You earned ${earned}. Cash: ${get_cash(player)}"
    return 0, ""


# ---------- Shop items ----------
def get_shop_items():
    """Return available power-ups and their prices."""
    return {name: info["price"] for name, info in SHOP_ITEMS.items()}


def get_shop_menu_lines():
    """Return the shop menu as a list of short lines for display.py."""
    lines = []
    for number, (name, info) in enumerate(SHOP_ITEMS.items(), start=1):
        line = f"{number}. {name.title():<14} ${info['price']:<4} {info['description']}"
        lines.append(line[:80])  # stay inside the 80-column limit
    return lines


def find_item(choice):
    """Turn the player's input (a name or a menu number) into an item name.

    Returns the item name, or None if the input does not match an item.
    """
    choice = str(choice).strip().lower()
    names = list(SHOP_ITEMS.keys())
    if choice.isdigit():
        index = int(choice) - 1
        if 0 <= index < len(names):
            return names[index]
        return None
    if choice in SHOP_ITEMS:
        return choice
    return None


# ---------- Buying ----------
def can_afford(player, item_name):
    """Return True if the player has enough cash for the item."""
    if item_name not in SHOP_ITEMS:
        return False
    return get_cash(player) >= SHOP_ITEMS[item_name]["price"]


def purchase_item(player, item_name):
    """Process a purchase and update the player's cash.

    Returns (success, message). Cash only changes when success is True.
    """
    item = find_item(item_name)
    if item is None:
        return False, f"'{item_name}' is not sold here."

    price = SHOP_ITEMS[item]["price"]
    if not can_afford(player, item):
        short = price - get_cash(player)
        return False, f"Not enough cash for {item}. You need ${short} more."

    player["cash"] = get_cash(player) - price
    return True, f"Bought {item} for ${price}. Cash left: ${get_cash(player)}"


# ---------- Using power-ups ----------
def apply_power_up(item_name, game_state):
    """Apply the purchased power-up to the game.

    This only records the power-up in game_state; main.py / combat.py
    act on it:
      - "extra strike": game_state["extra_shots"] goes up by 1, so the
        player may fire again (the normal rule is one shot per turn,
        even after a hit).
      - "radar": game_state["radar_charges"] goes up by 1. main.py asks
        for a centre coordinate and logic.py works out the clues.
        Radar shows numbers only, never ship positions.
    Returns a short message.
    """
    item = find_item(item_name)
    if item == "extra strike":
        game_state["extra_shots"] = game_state.get("extra_shots", 0) + 1
        return "Extra strike ready: you get one more shot."
    if item == "radar":
        game_state["radar_charges"] = game_state.get("radar_charges", 0) + 1
        return "Radar ready: choose a centre square to scan."
    return f"Unknown power-up: {item_name}"


def use_extra_shot(game_state):
    """Spend one extra shot. Returns True if one was available."""
    if game_state.get("extra_shots", 0) > 0:
        game_state["extra_shots"] -= 1
        return True
    return False


def use_radar_charge(game_state):
    """Spend one radar charge. Returns True if one was available."""
    if game_state.get("radar_charges", 0) > 0:
        game_state["radar_charges"] -= 1
        return True
    return False


def radar_area(row, col, size=10):
    """Return the squares a radar scan centred on (row, col) covers.

    Gives the 3x3 block around the centre, clipped to the board edge.
    logic.py can calculate the number clue for each of these squares.
    """
    squares = []
    for r in range(row - 1, row + 2):
        for c in range(col - 1, col + 2):
            if 0 <= r < size and 0 <= c < size:
                squares.append((r, c))
    return squares


# ---------- Quick self-test (runs only when this file is run directly) ----------
if __name__ == "__main__":
    player = new_player_wallet()
    state = {}
    print("Shop items:", get_shop_items())
    for line in get_shop_menu_lines():
        print(line)

    print(purchase_item(player, "radar"))          # $50 -> $10 left
    print(purchase_item(player, "extra strike"))   # not enough cash now
    print(reward_for_attack(player, hit=True, sunk=True))  # +$40 -> $50
    ok, msg = purchase_item(player, "2")            # buy by menu number
    print(ok, msg)
    if ok:
        print(apply_power_up("extra strike", state))
    print("Use extra shot:", use_extra_shot(state), state)
    print("Radar at corner A1:", radar_area(0, 0))
    print(purchase_item(player, "laser"))
