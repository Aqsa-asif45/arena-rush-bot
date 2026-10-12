import json
import sys
from collections import deque
from typing import List, Tuple, Dict, Set, Optional, Any


class ArenaRushBot:
    """Complete skeleton for Arena Rush bot AI with combat and energy logic."""

    GRID_SIZE = 15
    LOS_MAX_RANGE = 3
    DIRECTIONS = [(0, -1), (1, 0), (0, 1), (-1, 0)]  # Up, Right, Down, Left
    CONTROL_ZONE_RADIUS = 1  # 3x3 zone around center (center ± 1)

    def __init__(self):
        """Initialize bot state containers."""
        self.grid_size: int = self.GRID_SIZE
        self.walls: Set[Tuple[int, int]] = set()
        self.visible_orbs: List[Tuple[int, int]] = []
        self.energy_orbs: List[Tuple[int, int]] = []
        self.my_bots: List[Dict[str, Any]] = []
        self.enemy_bots: List[Dict[str, Any]] = []
        self.my_energy: int = 0
        self.my_hp: int = 10

    # ========== STATE MANAGEMENT ==========

    def parse_input_state(self, raw_json: Dict[str, Any]) -> None:
        """Parse JSON input and update internal state.

        Expected format:
        {
            "grid_size": 15,
            "walls": [[x, y], ...],
            "visible_orbs": [[x, y], ...],
            "energy_orbs": [[x, y], ...],
            "my_bots": [{"id": 0, "position": [x, y], "energy": 5, "hp": 10}, ...],
            "enemy_bots": [{"id": 0, "position": [x, y], "hp": 5}, ...]
        }
        """
        self.grid_size = raw_json.get('grid_size', self.GRID_SIZE)
        self.walls = set(tuple(w) for w in raw_json.get('walls', []))
        self.visible_orbs = [tuple(o) for o in raw_json.get('visible_orbs', [])]
        self.energy_orbs = [tuple(o) for o in raw_json.get('energy_orbs', [])]
        self.my_bots = raw_json.get('my_bots', [])
        self.enemy_bots = raw_json.get('enemy_bots', [])

        if self.my_bots:
            self.my_energy = self.my_bots[0].get('energy', 0)
            self.my_hp = self.my_bots[0].get('hp', 10)

    # ========== GRID VALIDATION ==========

    def is_walkable(self, x: int, y: int) -> bool:
        """Check if position is in bounds and not a wall."""
        if not (0 <= x < self.grid_size and 0 <= y < self.grid_size):
            return False
        return (x, y) not in self.walls

    def get_bot_position(self, bot: Dict[str, Any]) -> Optional[Tuple[int, int]]:
        """Extract position from bot dict. Returns None if invalid."""
        pos_data = bot.get('position')
        if isinstance(pos_data, (list, tuple)) and len(pos_data) >= 2:
            x, y = pos_data[0], pos_data[1]
            if isinstance(x, int) and isinstance(y, int):
                return (x, y)
        return None

    def is_bot_at_position(self, x: int, y: int) -> bool:
        """Check if any bot occupies this position."""
        for bot in self.my_bots + self.enemy_bots:
            pos = self.get_bot_position(bot)
            if pos == (x, y):
                return True
        return False

    # ========== LINE OF SIGHT (LOS) ==========

    def has_line_of_sight(self, from_pos: Tuple[int, int],
                          to_pos: Tuple[int, int]) -> bool:
        """Check if to_pos is visible from from_pos within LOS_MAX_RANGE.

        Uses Chebyshev distance for range check and Bresenham's algorithm
        for wall obstruction.
        """
        x0, y0 = from_pos
        x1, y1 = to_pos

        # Chebyshev distance (max of absolute differences)
        chebyshev_dist = max(abs(x1 - x0), abs(y1 - y0))
        if chebyshev_dist > self.LOS_MAX_RANGE:
            return False

        return self._bresenham_clear_line(x0, y0, x1, y1)

    def _bresenham_clear_line(self, x0: int, y0: int, x1: int, y1: int) -> bool:
        """Bresenham's line algorithm to detect wall obstruction.

        Returns True if there's a clear line from (x0,y0) to (x1,y1).
        """
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x1 > x0 else -1
        sy = 1 if y1 > y0 else -1
        err = dx - dy

        x, y = x0, y0

        while True:
            # Wall check (exclude start position)
            if (x, y) != (x0, y0) and (x, y) in self.walls:
                return False

            if x == x1 and y == y1:
                return True

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def get_visible_positions(self, from_pos: Tuple[int, int]) -> Set[Tuple[int, int]]:
        """Get all walkable positions visible from a position within LOS range."""
        visible = set()
        x0, y0 = from_pos

        for x in range(max(0, x0 - self.LOS_MAX_RANGE),
                      min(self.grid_size, x0 + self.LOS_MAX_RANGE + 1)):
            for y in range(max(0, y0 - self.LOS_MAX_RANGE),
                          min(self.grid_size, y0 + self.LOS_MAX_RANGE + 1)):
                if self.has_line_of_sight(from_pos, (x, y)):
                    visible.add((x, y))

        return visible

    # ========== PATHFINDING (BFS) ==========

    def bfs_pathfind(self, start: Tuple[int, int],
                     goal: Tuple[int, int],
                     avoid_enemy_bots: bool = True) -> List[Tuple[int, int]]:
        """Find shortest path from start to goal using BFS.

        Returns list of positions [start, ..., goal] or empty list if no path.
        Can avoid positions occupied by enemy bots.
        """
        if not self.is_walkable(start[0], start[1]):
            return []
        if not self.is_walkable(goal[0], goal[1]):
            return []
        if start == goal:
            return [start]

        queue: deque = deque([(start, [start])])
        visited: Set[Tuple[int, int]] = {start}

        while queue:
            (x, y), path = queue.popleft()

            for dx, dy in self.DIRECTIONS:
                nx, ny = x + dx, y + dy
                next_pos = (nx, ny)

                if next_pos in visited:
                    continue
                if not self.is_walkable(nx, ny):
                    continue
                if avoid_enemy_bots and self.is_bot_at_position(nx, ny):
                    continue

                if next_pos == goal:
                    return path + [next_pos]

                visited.add(next_pos)
                queue.append((next_pos, path + [next_pos]))

        return []

    def bfs_pathfind_to_nearest(self, start: Tuple[int, int],
                                goals: Set[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Find shortest path to nearest goal from a set of goals."""
        if not goals:
            return []

        valid_goals = {g for g in goals if self.is_walkable(g[0], g[1])}
        if not valid_goals:
            return []
        if start in valid_goals:
            return [start]

        queue: deque = deque([(start, [start])])
        visited: Set[Tuple[int, int]] = {start}

        while queue:
            (x, y), path = queue.popleft()

            for dx, dy in self.DIRECTIONS:
                nx, ny = x + dx, y + dy
                next_pos = (nx, ny)

                if next_pos in visited:
                    continue
                if not self.is_walkable(nx, ny):
                    continue

                if next_pos in valid_goals:
                    return path + [next_pos]

                visited.add(next_pos)
                queue.append((next_pos, path + [next_pos]))

        return []

    # ========== COMBAT & TARGETING ==========

    def get_control_zone_positions(self) -> Set[Tuple[int, int]]:
        """Get all positions in the central 3x3 Control Zone.

        For a 15x15 grid, center is at (7, 7), so control zone is (6-8, 6-8).
        """
        center_x = self.grid_size // 2
        center_y = self.grid_size // 2
        zone = set()

        for dx in range(-self.CONTROL_ZONE_RADIUS, self.CONTROL_ZONE_RADIUS + 1):
            for dy in range(-self.CONTROL_ZONE_RADIUS, self.CONTROL_ZONE_RADIUS + 1):
                x, y = center_x + dx, center_y + dy
                if self.is_walkable(x, y):
                    zone.add((x, y))

        return zone

    def select_target(self, from_pos: Tuple[int, int]) -> Optional[Dict[str, Any]]:
        """Select best enemy target in LOS with energy > 0.

        Priority: enemies with lowest HP (prefer wounded enemies).
        Returns enemy bot dict or None if no valid target.
        """
        if self.my_energy <= 0:
            return None

        targets = []
        for enemy in self.enemy_bots:
            enemy_pos = self.get_bot_position(enemy)
            if enemy_pos is None:
                continue

            if self.has_line_of_sight(from_pos, enemy_pos):
                targets.append(enemy)

        if not targets:
            return None

        return min(targets, key=lambda e: e.get('hp', 5))

    def get_energy_goal(self, from_pos: Tuple[int, int],
                        bot_index: int = 0) -> Optional[Tuple[int, int]]:
        """Determine energy gathering target: orb or control zone.

        Priority: nearest visible energy orb, then control zone center.
        Considers collision-free pathfinding.
        """
        if self.energy_orbs:
            orb_set = set(self.energy_orbs)
            for orb in orb_set:
                path = self.find_collision_free_path(from_pos, orb, bot_index)
                if path and len(path) > 1:
                    return path[1]

        control_zone = self.get_control_zone_positions()
        for zone_pos in control_zone:
            path = self.find_collision_free_path(from_pos, zone_pos, bot_index)
            if path and len(path) > 1:
                return path[1]

        return None

    # ========== COLLISION PREVENTION ==========

    def get_reserved_positions(self, exclude_bot_index: int = -1) -> Set[Tuple[int, int]]:
        """Get set of positions that friendly bots currently occupy.

        Can exclude one bot (when deciding its move to avoid reserving its current pos).
        """
        reserved = set()
        for i, bot in enumerate(self.my_bots):
            if i == exclude_bot_index:
                continue
            pos = self.get_bot_position(bot)
            if pos:
                reserved.add(pos)
        return reserved

    def is_collision_free_path(self, path: List[Tuple[int, int]],
                               exclude_index: int = -1) -> bool:
        """Check if path doesn't collide with other friendly bots.

        Allows path to start at current bot position but next moves must be clear.
        exclude_index: bot index to exclude from collision checking.
        """
        if len(path) < 2:
            return True

        reserved = self.get_reserved_positions(exclude_index)

        for i, pos in enumerate(path[1:], 1):
            if pos in reserved:
                return False

        return True

    def find_collision_free_path(self, start: Tuple[int, int],
                                 goal: Tuple[int, int],
                                 bot_index: int = 0) -> List[Tuple[int, int]]:
        """Find path avoiding both walls and friendly bots.

        Returns shortest collision-free path or empty list if none exists.
        """
        if not self.is_walkable(start[0], start[1]):
            return []
        if not self.is_walkable(goal[0], goal[1]):
            return []
        if start == goal:
            return [start]

        reserved = self.get_reserved_positions(bot_index)
        queue: deque = deque([(start, [start])])
        visited: Set[Tuple[int, int]] = {start}

        while queue:
            (x, y), path = queue.popleft()

            for dx, dy in self.DIRECTIONS:
                nx, ny = x + dx, y + dy
                next_pos = (nx, ny)

                if next_pos in visited:
                    continue
                if not self.is_walkable(nx, ny):
                    continue
                if next_pos in reserved:
                    continue

                if next_pos == goal:
                    return path + [next_pos]

                visited.add(next_pos)
                queue.append((next_pos, path + [next_pos]))

        return []

    # ========== DECISION LOGIC ==========

    def decide_action_for_bot(self, bot_index: int) -> Dict[str, Any]:
        """Decide action for a specific bot, considering collisions with other bots.

        Returns: shoot, move (collision-free), or wait action.
        """
        if bot_index >= len(self.my_bots):
            return {"type": "wait"}

        bot = self.my_bots[bot_index]
        bot_id = bot.get('id', bot_index)
        bot_pos = self.get_bot_position(bot)

        if bot_pos is None:
            return {"type": "wait"}

        # PRIORITY 1: Combat - shoot if target in LOS and energy available
        target = self.select_target(bot_pos)
        if target:
            target_pos = self.get_bot_position(target)
            return {
                "type": "shoot",
                "bot_id": bot_id,
                "target": list(target_pos),
                "target_id": target.get('id', -1)
            }

        # PRIORITY 2: Energy gathering - collision-free pathfinding
        energy_move = self.get_energy_goal(bot_pos, bot_index)
        if energy_move:
            return {
                "type": "move",
                "bot_id": bot_id,
                "position": list(energy_move)
            }

        # FALLBACK: Wait
        return {"type": "wait"}

    def decide_action(self) -> Dict[str, Any]:
        """Wrapper for primary bot action (backwards compatibility)."""
        return self.decide_action_for_bot(0)

    def decide_all_actions(self) -> List[Dict[str, Any]]:
        """Decide actions for all friendly bots with collision prevention."""
        actions = []
        for i in range(len(self.my_bots)):
            action = self.decide_action_for_bot(i)
            actions.append(action)
        return actions

    # ========== OUTPUT GENERATION ==========

    def generate_response(self, use_all_bots: bool = True) -> Dict[str, Any]:
        """Generate JSON response with bot actions.

        If use_all_bots=True, returns actions for all friendly bots.
        Otherwise, returns single action for primary bot.
        """
        if use_all_bots and len(self.my_bots) > 1:
            actions = self.decide_all_actions()
            return {
                "actions": actions,
                "turn": len(self.my_bots) > 0
            }
        else:
            action = self.decide_action()
            return {
                "action": action,
                "turn": len(self.my_bots) > 0
            }

    def generate_fallback_response(self, error_msg: str = "unknown") -> Dict[str, Any]:
        """Generate safe fallback response with WAIT action(s)."""
        if len(self.my_bots) > 1:
            actions = [{"type": "wait"} for _ in self.my_bots]
            return {
                "actions": actions,
                "error": error_msg
            }
        else:
            return {
                "action": {"type": "wait"},
                "error": error_msg
            }

    # ========== MAIN GAME LOOP ==========

    def run(self) -> None:
        """Main loop with fail-safe error handling: read JSON, process, output JSON.

        Zero-crash guarantee: any exception triggers WAIT action output.
        Never exits except on EOF or fatal stdin error.
        """
        while True:
            response = None

            try:
                # ===== INPUT STAGE =====
                try:
                    line = sys.stdin.readline()
                    if not line:
                        break
                except (IOError, OSError):
                    response = self.generate_fallback_response("stdin_read_error")
                    raise

                # ===== PARSING STAGE =====
                try:
                    state_json = json.loads(line.strip())
                except json.JSONDecodeError:
                    response = self.generate_fallback_response("json_decode_error")
                    raise
                except (ValueError, TypeError):
                    response = self.generate_fallback_response("json_type_error")
                    raise

                # ===== STATE UPDATE STAGE =====
                try:
                    self.parse_input_state(state_json)
                except (KeyError, IndexError, AttributeError):
                    response = self.generate_fallback_response("state_parse_error")
                    raise
                except Exception:
                    response = self.generate_fallback_response("state_update_error")
                    raise

                # ===== DECISION STAGE =====
                try:
                    response = self.generate_response(use_all_bots=True)
                except (RecursionError, MemoryError):
                    response = self.generate_fallback_response("resource_exhausted")
                    raise
                except Exception:
                    response = self.generate_fallback_response("decision_error")
                    raise

            except Exception:
                # Final fallback: if response not yet generated, create it now
                if response is None:
                    response = self.generate_fallback_response("unknown_error")

            # ===== OUTPUT STAGE =====
            try:
                output = json.dumps(response)
                print(output)
                sys.stdout.flush()
            except (IOError, OSError):
                # Unable to write output, but we tried
                pass
            except Exception:
                # Last resort: try raw output
                try:
                    sys.stdout.write('{"action":{"type":"wait"},"error":"output_error"}\n')
                    sys.stdout.flush()
                except:
                    pass


def main() -> None:
    """Entry point with initialization fail-safe."""
    try:
        bot = ArenaRushBot()
        bot.run()
    except KeyboardInterrupt:
        pass
    except Exception:
        try:
            sys.stderr.write('{"action":{"type":"wait"},"error":"init_error"}\n')
            sys.stderr.flush()
        except:
            pass


if __name__ == "__main__":
    main()