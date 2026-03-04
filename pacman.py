#!/usr/bin/env python3
"""Terminal Pacman game using curses and text characters."""

import curses
import random
import time

# Maze layout: # = wall, . = dot, o = power pellet, P = pacman start, G = ghost start, ' ' = empty
MAZE_TEMPLATE = [
    "###########################",
    "#............#............#",
    "#.####.#####.#.#####.####.#",
    "#o####.#####.#.#####.####o#",
    "#.####.#####.#.#####.####.#",
    "#.........................#",
    "#.####.##.#######.##.####.#",
    "#.####.##.#######.##.####.#",
    "#......##....#....##......#",
    "######.##### # #####.######",
    "     #.##### # #####.#     ",
    "     #.##    G    ##.#     ",
    "     #.## ####### ##.#     ",
    "######.## #     # ##.######",
    "      .   #G G G#   .      ",
    "######.## #     # ##.######",
    "     #.## ####### ##.#     ",
    "     #.##         ##.#     ",
    "     #.## ####### ##.#     ",
    "######.## ####### ##.######",
    "#............#............#",
    "#.####.#####.#.#####.####.#",
    "#.####.#####.#.#####.####.#",
    "#o..##.......P.......##..o#",
    "###.##.##.#######.##.##.###",
    "###.##.##.#######.##.##.###",
    "#......##....#....##......#",
    "#.##########.#.##########.#",
    "#.##########.#.##########.#",
    "#.........................#",
    "###########################",
]

# Direction constants
UP = 0
DOWN = 1
LEFT = 2
RIGHT = 3
NONE = -1

DIR_DELTA = {
    UP: (-1, 0),
    DOWN: (1, 0),
    LEFT: (0, -1),
    RIGHT: (0, 1),
    NONE: (0, 0),
}

GHOST_CHARS = ["♠", "♣", "♦", "♥"]
GHOST_NAMES = ["Blinky", "Pinky", "Inky", "Clyde"]


class Ghost:
    def __init__(self, row, col, idx):
        self.row = row
        self.col = col
        self.start_row = row
        self.start_col = col
        self.idx = idx
        self.char = GHOST_CHARS[idx % len(GHOST_CHARS)]
        self.direction = random.choice([UP, DOWN, LEFT, RIGHT])
        self.frightened = False
        self.frightened_timer = 0
        self.eaten = False

    def reset(self):
        self.row = self.start_row
        self.col = self.start_col
        self.direction = random.choice([UP, DOWN, LEFT, RIGHT])
        self.frightened = False
        self.frightened_timer = 0
        self.eaten = False


class PacmanGame:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.score = 0
        self.lives = 3
        self.level = 1
        self.game_over = False
        self.won = False
        self.total_dots = 0
        self.dots_eaten = 0
        self.pac_row = 0
        self.pac_col = 0
        self.pac_dir = NONE
        self.next_dir = NONE
        self.pac_mouth_open = True
        self.mouth_timer = 0
        self.ghosts = []
        self.maze = []
        self.flash_timer = 0
        self.message = ""
        self.message_timer = 0
        self.paused = False

        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.timeout(100)

        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_YELLOW, -1)   # Pacman
            curses.init_pair(2, curses.COLOR_RED, -1)      # Blinky / walls
            curses.init_pair(3, curses.COLOR_MAGENTA, -1)  # Pinky
            curses.init_pair(4, curses.COLOR_CYAN, -1)     # Inky / dots
            curses.init_pair(5, curses.COLOR_GREEN, -1)    # Clyde
            curses.init_pair(6, curses.COLOR_BLUE, -1)     # Frightened ghost
            curses.init_pair(7, curses.COLOR_WHITE, -1)    # Text / power pellet
            curses.init_pair(8, curses.COLOR_BLUE, -1)     # Walls

        self.init_maze()

    def init_maze(self):
        self.maze = []
        self.ghosts = []
        self.total_dots = 0
        self.dots_eaten = 0
        ghost_idx = 0

        for r, row in enumerate(MAZE_TEMPLATE):
            maze_row = list(row)
            for c, ch in enumerate(row):
                if ch == "P":
                    self.pac_row = r
                    self.pac_col = c
                    self.pac_dir = NONE
                    self.next_dir = NONE
                    maze_row[c] = " "
                elif ch == "G":
                    ghost = Ghost(r, c, ghost_idx)
                    self.ghosts.append(ghost)
                    ghost_idx += 1
                    maze_row[c] = " "
                elif ch == "." or ch == "o":
                    self.total_dots += 1
            self.maze.append(maze_row)

    def reset_positions(self):
        """Reset pacman and ghosts to starting positions."""
        for r, row in enumerate(MAZE_TEMPLATE):
            for c, ch in enumerate(row):
                if ch == "P":
                    self.pac_row = r
                    self.pac_col = c
                    self.pac_dir = NONE
                    self.next_dir = NONE
        for ghost in self.ghosts:
            ghost.reset()

    def is_wall(self, row, col):
        if row < 0 or row >= len(self.maze) or col < 0 or col >= len(self.maze[0]):
            return True
        return self.maze[row][col] == "#"

    def can_move(self, row, col, direction):
        dr, dc = DIR_DELTA[direction]
        new_r, new_c = row + dr, col + dc
        # Tunnel wrap
        if new_c < 0:
            new_c = len(self.maze[0]) - 1
        elif new_c >= len(self.maze[0]):
            new_c = 0
        return not self.is_wall(new_r, new_c)

    def wrap_col(self, col):
        if col < 0:
            return len(self.maze[0]) - 1
        elif col >= len(self.maze[0]):
            return 0
        return col

    def move_pacman(self):
        # Try next direction first
        if self.next_dir != NONE and self.can_move(self.pac_row, self.pac_col, self.next_dir):
            self.pac_dir = self.next_dir
            self.next_dir = NONE

        if self.pac_dir == NONE:
            return

        if self.can_move(self.pac_row, self.pac_col, self.pac_dir):
            dr, dc = DIR_DELTA[self.pac_dir]
            self.pac_row += dr
            self.pac_col = self.wrap_col(self.pac_col + dc)

            # Eat dot
            cell = self.maze[self.pac_row][self.pac_col]
            if cell == ".":
                self.maze[self.pac_row][self.pac_col] = " "
                self.score += 10
                self.dots_eaten += 1
            elif cell == "o":
                self.maze[self.pac_row][self.pac_col] = " "
                self.score += 50
                self.dots_eaten += 1
                # Frighten ghosts
                for ghost in self.ghosts:
                    if not ghost.eaten:
                        ghost.frightened = True
                        ghost.frightened_timer = 50  # ~5 seconds

            # Check win
            if self.dots_eaten >= self.total_dots:
                self.won = True

        # Animate mouth
        self.mouth_timer += 1
        if self.mouth_timer >= 2:
            self.pac_mouth_open = not self.pac_mouth_open
            self.mouth_timer = 0

    def get_pac_char(self):
        if not self.pac_mouth_open:
            return "●"
        if self.pac_dir == UP:
            return "∨"
        elif self.pac_dir == DOWN:
            return "∧"
        elif self.pac_dir == LEFT:
            return ">"
        elif self.pac_dir == RIGHT:
            return "<"
        return "◉"

    def move_ghosts(self):
        for ghost in self.ghosts:
            if ghost.eaten:
                # Move back to start
                if ghost.row == ghost.start_row and ghost.col == ghost.start_col:
                    ghost.eaten = False
                    ghost.frightened = False
                    continue
                # Simple pathfinding back to start
                dr = 0
                dc = 0
                if ghost.row < ghost.start_row:
                    dr = 1
                elif ghost.row > ghost.start_row:
                    dr = -1
                if ghost.col < ghost.start_col:
                    dc = 1
                elif ghost.col > ghost.start_col:
                    dc = -1
                if dr != 0 and not self.is_wall(ghost.row + dr, ghost.col):
                    ghost.row += dr
                elif dc != 0 and not self.is_wall(ghost.row, ghost.col + dc):
                    ghost.col += dc
                continue

            # Update frightened timer
            if ghost.frightened:
                ghost.frightened_timer -= 1
                if ghost.frightened_timer <= 0:
                    ghost.frightened = False

            # Ghost AI: try to chase pacman (or run away if frightened)
            possible_dirs = []
            for d in [UP, DOWN, LEFT, RIGHT]:
                if self.can_move(ghost.row, ghost.col, d):
                    # Don't reverse direction unless no other choice
                    reverse = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}
                    if d != reverse.get(ghost.direction, NONE):
                        possible_dirs.append(d)

            if not possible_dirs:
                # Allow reverse if stuck
                for d in [UP, DOWN, LEFT, RIGHT]:
                    if self.can_move(ghost.row, ghost.col, d):
                        possible_dirs.append(d)

            if not possible_dirs:
                continue

            if ghost.frightened:
                # Run away: pick direction that maximizes distance from pacman
                ghost.direction = max(
                    possible_dirs,
                    key=lambda d: (
                        (ghost.row + DIR_DELTA[d][0] - self.pac_row) ** 2
                        + (ghost.col + DIR_DELTA[d][1] - self.pac_col) ** 2
                    ),
                )
            else:
                # Chase: mix of targeting pacman and randomness
                if random.random() < 0.7:
                    ghost.direction = min(
                        possible_dirs,
                        key=lambda d: (
                            (ghost.row + DIR_DELTA[d][0] - self.pac_row) ** 2
                            + (ghost.col + DIR_DELTA[d][1] - self.pac_col) ** 2
                        ),
                    )
                else:
                    ghost.direction = random.choice(possible_dirs)

            dr, dc = DIR_DELTA[ghost.direction]
            new_r = ghost.row + dr
            new_c = self.wrap_col(ghost.col + dc)
            if not self.is_wall(new_r, new_c):
                ghost.row = new_r
                ghost.col = new_c

    def check_collisions(self):
        for ghost in self.ghosts:
            if ghost.row == self.pac_row and ghost.col == self.pac_col:
                if ghost.frightened and not ghost.eaten:
                    ghost.eaten = True
                    self.score += 200
                    self.message = "YUM! +200"
                    self.message_timer = 15
                elif not ghost.eaten:
                    self.lives -= 1
                    if self.lives <= 0:
                        self.game_over = True
                    else:
                        self.message = f"OUCH! Lives: {self.lives}"
                        self.message_timer = 20
                        self.reset_positions()
                    return

    def draw(self):
        self.stdscr.erase()
        max_h, max_w = self.stdscr.getmaxyx()

        # Calculate offset to center the maze
        maze_h = len(self.maze)
        maze_w = len(self.maze[0]) if self.maze else 0
        offset_r = max(0, (max_h - maze_h - 4) // 2)
        offset_c = max(0, (max_w - maze_w) // 2)

        # Draw header
        header = f" PACMAN  Score: {self.score}  Lives: {'◉ ' * self.lives}  Level: {self.level} "
        if offset_r > 0 and max_w > len(header):
            try:
                self.stdscr.addstr(
                    offset_r - 1,
                    max(0, (max_w - len(header)) // 2),
                    header,
                    curses.color_pair(1) | curses.A_BOLD,
                )
            except curses.error:
                pass

        # Draw maze
        for r, row in enumerate(self.maze):
            for c, ch in enumerate(row):
                sr = r + offset_r
                sc = c + offset_c
                if sr >= max_h - 1 or sc >= max_w - 1 or sr < 0 or sc < 0:
                    continue
                try:
                    if ch == "#":
                        self.stdscr.addstr(sr, sc, "█", curses.color_pair(8))
                    elif ch == ".":
                        self.stdscr.addstr(sr, sc, "·", curses.color_pair(4))
                    elif ch == "o":
                        self.flash_timer += 1
                        if (self.flash_timer // 5) % 2 == 0:
                            self.stdscr.addstr(sr, sc, "●", curses.color_pair(7) | curses.A_BOLD)
                        else:
                            self.stdscr.addstr(sr, sc, "●", curses.color_pair(4))
                    else:
                        self.stdscr.addstr(sr, sc, " ")
                except curses.error:
                    pass

        # Draw ghosts
        ghost_colors = [2, 3, 4, 5]
        for ghost in self.ghosts:
            sr = ghost.row + offset_r
            sc = ghost.col + offset_c
            if sr >= max_h - 1 or sc >= max_w - 1 or sr < 0 or sc < 0:
                continue
            try:
                if ghost.eaten:
                    self.stdscr.addstr(sr, sc, "\"", curses.color_pair(7))
                elif ghost.frightened:
                    if ghost.frightened_timer < 15 and (ghost.frightened_timer // 2) % 2:
                        self.stdscr.addstr(sr, sc, "≈", curses.color_pair(7) | curses.A_BOLD)
                    else:
                        self.stdscr.addstr(sr, sc, "≈", curses.color_pair(6) | curses.A_BOLD)
                else:
                    color = ghost_colors[ghost.idx % len(ghost_colors)]
                    self.stdscr.addstr(sr, sc, ghost.char, curses.color_pair(color) | curses.A_BOLD)
            except curses.error:
                pass

        # Draw pacman
        sr = self.pac_row + offset_r
        sc = self.pac_col + offset_c
        if 0 <= sr < max_h - 1 and 0 <= sc < max_w - 1:
            try:
                self.stdscr.addstr(sr, sc, self.get_pac_char(), curses.color_pair(1) | curses.A_BOLD)
            except curses.error:
                pass

        # Draw message
        if self.message_timer > 0:
            self.message_timer -= 1
            msg_r = offset_r + maze_h + 1
            if msg_r < max_h - 1:
                try:
                    self.stdscr.addstr(
                        msg_r,
                        max(0, (max_w - len(self.message)) // 2),
                        self.message,
                        curses.color_pair(1) | curses.A_BOLD,
                    )
                except curses.error:
                    pass

        # Draw controls hint
        hint = "Arrow keys: Move | P: Pause | Q: Quit"
        hint_r = offset_r + maze_h + 2
        if hint_r < max_h - 1 and max_w > len(hint):
            try:
                self.stdscr.addstr(
                    hint_r,
                    max(0, (max_w - len(hint)) // 2),
                    hint,
                    curses.color_pair(7),
                )
            except curses.error:
                pass

        self.stdscr.refresh()

    def draw_game_over(self):
        self.stdscr.erase()
        max_h, max_w = self.stdscr.getmaxyx()
        mid_r = max_h // 2
        mid_c = max_w // 2

        if self.won:
            lines = [
                "╔═══════════════════════╗",
                "║    YOU WIN! ◉ ◉ ◉     ║",
                f"║    Score: {self.score:<12}║",
                "║                       ║",
                "║  Press R to Restart   ║",
                "║  Press Q to Quit      ║",
                "╚═══════════════════════╝",
            ]
            color = curses.color_pair(1) | curses.A_BOLD
        else:
            lines = [
                "╔═══════════════════════╗",
                "║      GAME OVER        ║",
                f"║    Score: {self.score:<12}║",
                "║                       ║",
                "║  Press R to Restart   ║",
                "║  Press Q to Quit      ║",
                "╚═══════════════════════╝",
            ]
            color = curses.color_pair(2) | curses.A_BOLD

        for i, line in enumerate(lines):
            r = mid_r - len(lines) // 2 + i
            c = mid_c - len(line) // 2
            if 0 <= r < max_h and c + len(line) < max_w:
                try:
                    self.stdscr.addstr(r, c, line, color)
                except curses.error:
                    pass

        self.stdscr.refresh()

    def draw_title(self):
        self.stdscr.erase()
        max_h, max_w = self.stdscr.getmaxyx()
        mid_r = max_h // 2
        mid_c = max_w // 2

        title_art = [
            "  ____   _    ____  __  __    _    _   _ ",
            " |  _ \\ / \\  / ___||  \\/  |  / \\  | \\ | |",
            " | |_) / _ \\| |    | |\\/| | / _ \\ |  \\| |",
            " |  __/ ___ \\ |___ | |  | |/ ___ \\| |\\  |",
            " |_| /_/   \\_\\____||_|  |_/_/   \\_\\_| \\_|",
        ]

        info = [
            "",
            "◉ < · · · ♠ ♣ ♦ ♥",
            "",
            "Arrow keys to move",
            "Eat all dots to win!",
            "Watch out for ghosts!",
            "Eat power pellets ● to chomp ghosts!",
            "",
            "Press any key to start...",
        ]

        all_lines = title_art + info
        for i, line in enumerate(all_lines):
            r = mid_r - len(all_lines) // 2 + i
            c = mid_c - len(line) // 2
            if 0 <= r < max_h and 0 <= c and c + len(line) < max_w:
                try:
                    if i < len(title_art):
                        self.stdscr.addstr(r, c, line, curses.color_pair(1) | curses.A_BOLD)
                    elif "♠" in line or "◉" in line:
                        self.stdscr.addstr(r, c, line, curses.color_pair(4) | curses.A_BOLD)
                    else:
                        self.stdscr.addstr(r, c, line, curses.color_pair(7))
                except curses.error:
                    pass

        self.stdscr.refresh()

    def handle_input(self, key):
        if key == curses.KEY_UP or key == ord("w") or key == ord("W"):
            self.next_dir = UP
        elif key == curses.KEY_DOWN or key == ord("s") or key == ord("S"):
            self.next_dir = DOWN
        elif key == curses.KEY_LEFT or key == ord("a") or key == ord("A"):
            self.next_dir = LEFT
        elif key == curses.KEY_RIGHT or key == ord("d") or key == ord("D"):
            self.next_dir = RIGHT
        elif key == ord("p") or key == ord("P"):
            self.paused = not self.paused

    def run(self):
        # Title screen
        self.draw_title()
        self.stdscr.nodelay(False)
        self.stdscr.getch()
        self.stdscr.nodelay(True)
        self.stdscr.timeout(100)

        tick = 0

        while True:
            key = self.stdscr.getch()

            if key == ord("q") or key == ord("Q"):
                break

            if self.game_over or self.won:
                self.draw_game_over()
                if key == ord("r") or key == ord("R"):
                    self.__init__(self.stdscr)
                    self.draw_title()
                    self.stdscr.nodelay(False)
                    self.stdscr.getch()
                    self.stdscr.nodelay(True)
                    self.stdscr.timeout(100)
                    tick = 0
                continue

            self.handle_input(key)

            if self.paused:
                max_h, max_w = self.stdscr.getmaxyx()
                pause_msg = "PAUSED - Press P to resume"
                try:
                    self.stdscr.addstr(
                        max_h // 2,
                        max(0, (max_w - len(pause_msg)) // 2),
                        pause_msg,
                        curses.color_pair(1) | curses.A_BOLD,
                    )
                except curses.error:
                    pass
                self.stdscr.refresh()
                continue

            # Update game state
            self.move_pacman()

            # Ghosts move slightly slower than pacman
            if tick % 2 == 0:
                self.move_ghosts()

            self.check_collisions()
            self.draw()

            tick += 1


def main(stdscr):
    game = PacmanGame(stdscr)
    game.run()


if __name__ == "__main__":
    curses.wrapper(main)
