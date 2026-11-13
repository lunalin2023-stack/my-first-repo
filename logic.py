# ==========================================
# logic.py - Logic Puzzle System
# ==========================================
# Responsibilities:
# 1. Calculate numerical clues (8 surrounding cells).
# 2. Exclude already sunk ships from the clues.
# 3. Provide a batch calculation for the 3x3 "Minesweeper" reveal on a miss.
# 4. Provide Radar/Sonar calculations.

SIZE = 10

def calculate_clue(ship_board, row, col, excluded_cells=None):
    """
    Calculate the clue for a SINGLE cell.
    Counts unsunk ship segments in the eight neighbouring cells.
    
    Args:
        ship_board: 2D list (10x10). True if ship segment, False otherwise.
        row, col: The target coordinate.
        excluded_cells: A set of (r, c) tuples representing sunk ships. 
                        These cells will be skipped.
                        
    Returns:
        int: Number of unsunk ship segments surrounding (row, col).
    """
    if excluded_cells is None:
        excluded_cells = set()
        
    count = 0
    # Check all 8 directions around the target cell
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue # Skip the center cell itself
            
            nr, nc = row + dr, col + dc
            # Ensure the neighbour is within the board boundaries
            if 0 <= nr < SIZE and 0 <= nc < SIZE:
                # Count if it's a ship AND it's not a sunk ship
                if ship_board[nr][nc] and (nr, nc) not in excluded_cells:
                    count += 1
    return count


def get_surrounding_clues(ship_board, row, col, excluded_cells=None):
    """
    Calculate clues for the 8 surrounding cells of a MISSED shot.
    The center cell is skipped (it will display a miss marker, not a number).
    
    Args:
        ship_board: 2D list (10x10).
        row, col: The coordinate where the player missed.
        excluded_cells: A set of (r, c) tuples representing sunk ships.
        
    Returns:
        dict: {(neighbor_row, neighbor_col): clue_value}
    """
    if excluded_cells is None:
        excluded_cells = set()
        
    clues = {}
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue # Skip the center tile, we only want the 8 surrounding cells
                
            nr, nc = row + dr, col + dc
            if 0 <= nr < SIZE and 0 <= nc < SIZE:
                clues[(nr, nc)] = calculate_clue(ship_board, nr, nc, excluded_cells)
                
    return clues


def calculate_radar(ship_board, row, col, radius, excluded_cells=None):
    """
    Calculate the total number of unsunk ship segments within the radar area.
    (Used for Sonar/Radar power-ups).
    """
    if excluded_cells is None:
        excluded_cells = set()
        
    count = 0
    # Define the radar square boundaries
    min_r = max(0, row - radius)
    max_r = min(SIZE - 1, row + radius)
    min_c = max(0, col - radius)
    max_c = min(SIZE - 1, col + radius)
    
    for r in range(min_r, max_r + 1):
        for c in range(min_c, max_c + 1):
            if ship_board[r][c] and (r, c) not in excluded_cells:
                count += 1
    return count
