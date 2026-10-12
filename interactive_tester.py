#!/usr/bin/env python3
"""
Interactive Arena Rush Bot Tester - Test custom scenarios in real-time.

Usage:
    python interactive_tester.py

Then follow the menu to create and test custom game states.
"""

import json
import subprocess
import sys
from typing import Dict, List, Any, Optional


class GameBuilder:
    """Build Arena Rush game states interactively."""

    def __init__(self):
        self.state = self.default_state()

    @staticmethod
    def default_state() -> Dict[str, Any]:
        """Get default 15×15 empty arena."""
        return {
            "grid_size": 15,
            "walls": [],
            "visible_orbs": [],
            "energy_orbs": [],
            "my_bots": [{"id": 0, "position": [7, 7], "energy": 5, "hp": 10}],
            "enemy_bots": []
        }

    def print_state(self):
        """Pretty-print current game state."""
        print("\n" + "="*80)
        print("CURRENT GAME STATE")
        print("="*80)
        print(json.dumps(self.state, indent=2))
        print("="*80 + "\n")

    def print_grid(self):
        """ASCII visualization of grid."""
        grid = [['.' for _ in range(15)] for _ in range(15)]

        # Place walls
        for x, y in self.state.get("walls", []):
            if 0 <= x < 15 and 0 <= y < 15:
                grid[y][x] = 'W'

        # Place energy orbs
        for x, y in self.state.get("energy_orbs", []):
            if 0 <= x < 15 and 0 <= y < 15:
                grid[y][x] = 'O'

        # Place visible orbs
        for x, y in self.state.get("visible_orbs", []):
            if 0 <= x < 15 and 0 <= y < 15 and grid[y][x] == '.':
                grid[y][x] = 'o'

        # Place enemy bots
        for bot in self.state.get("enemy_bots", []):
            pos = bot.get("position")
            if pos and 0 <= pos[0] < 15 and 0 <= pos[1] < 15:
                grid[pos[1]][pos[0]] = 'E'

        # Place my bots (last, highest priority)
        for i, bot in enumerate(self.state.get("my_bots", [])):
            pos = bot.get("position")
            if pos and 0 <= pos[0] < 15 and 0 <= pos[1] < 15:
                grid[pos[1]][pos[0]] = str(i)

        # Print grid
        print("\n" + "="*80)
        print("GRID VISUALIZATION (15×15)")
        print("="*80)
        print("  ", end="")
        for x in range(15):
            print(f"{x:2}", end="")
        print()

        for y in range(15):
            print(f"{y:2}", end="")
            for x in range(15):
                print(f" {grid[y][x]}", end="")
            print()

        print("\nLegend:")
        print("  [0-9] = Your bot (number = bot_id)")
        print("  [E]   = Enemy bot")
        print("  [O]   = Energy orb (recharges bot)")
        print("  [o]   = Visible orb (regular)")
        print("  [W]   = Wall (obstacle)")
        print("  [.]   = Empty walkable space")
        print("="*80 + "\n")

    def add_wall(self):
        """Add a wall to the grid."""
        try:
            x = int(input("Wall X (0-14): "))
            y = int(input("Wall Y (0-14): "))
            if 0 <= x < 15 and 0 <= y < 15:
                if [x, y] not in self.state["walls"]:
                    self.state["walls"].append([x, y])
                    print(f"✅ Wall added at ({x}, {y})")
                else:
                    print("❌ Wall already exists at this position")
            else:
                print("❌ Position out of bounds")
        except ValueError:
            print("❌ Invalid input")

    def add_energy_orb(self):
        """Add an energy orb."""
        try:
            x = int(input("Orb X (0-14): "))
            y = int(input("Orb Y (0-14): "))
            if 0 <= x < 15 and 0 <= y < 15:
                if [x, y] not in self.state["energy_orbs"]:
                    self.state["energy_orbs"].append([x, y])
                    print(f"✅ Energy orb added at ({x}, {y})")
                else:
                    print("❌ Orb already exists at this position")
            else:
                print("❌ Position out of bounds")
        except ValueError:
            print("❌ Invalid input")

    def add_enemy_bot(self):
        """Add an enemy bot."""
        try:
            bot_id = len(self.state["enemy_bots"]) + 1
            x = int(input("Enemy X (0-14): "))
            y = int(input("Enemy Y (0-14): "))
            hp = int(input("Enemy HP (default 3): ") or "3")

            if 0 <= x < 15 and 0 <= y < 15 and hp > 0:
                enemy = {"id": bot_id, "position": [x, y], "hp": hp}
                self.state["enemy_bots"].append(enemy)
                print(f"✅ Enemy bot {bot_id} added at ({x}, {y}) with HP={hp}")
            else:
                print("❌ Invalid position or HP")
        except ValueError:
            print("❌ Invalid input")

    def edit_my_bot(self):
        """Edit your bot's stats."""
        try:
            bot_id = int(input("Bot ID (default 0): ") or "0")
            if bot_id < len(self.state["my_bots"]):
                x = int(input(f"New X position (current {self.state['my_bots'][bot_id]['position'][0]}): ") or str(self.state["my_bots"][bot_id]['position'][0]))
                y = int(input(f"New Y position (current {self.state['my_bots'][bot_id]['position'][1]}): ") or str(self.state["my_bots"][bot_id]['position'][1]))
                energy = int(input(f"Energy (current {self.state['my_bots'][bot_id]['energy']}): ") or str(self.state["my_bots"][bot_id]['energy']))
                hp = int(input(f"HP (current {self.state['my_bots'][bot_id]['hp']}): ") or str(self.state["my_bots"][bot_id]['hp']))

                if 0 <= x < 15 and 0 <= y < 15 and energy >= 0 and hp > 0:
                    self.state["my_bots"][bot_id] = {
                        "id": bot_id,
                        "position": [x, y],
                        "energy": energy,
                        "hp": hp
                    }
                    print(f"✅ Bot {bot_id} updated")
                else:
                    print("❌ Invalid values")
            else:
                print("❌ Bot ID out of range")
        except ValueError:
            print("❌ Invalid input")

    def reset_state(self):
        """Reset to default state."""
        self.state = self.default_state()
        print("✅ Game state reset to default")

    def clear_all(self):
        """Clear walls, orbs, enemies."""
        self.state["walls"] = []
        self.state["energy_orbs"] = []
        self.state["visible_orbs"] = []
        self.state["enemy_bots"] = []
        print("✅ Cleared all obstacles, orbs, and enemies")


def run_bot_test(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Send state to bot and get response."""
    try:
        proc = subprocess.Popen(
            [sys.executable, "arena_rush_bot.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd="."
        )

        input_json = json.dumps(state)
        stdout, stderr = proc.communicate(input=input_json, timeout=5)

        if not stdout.strip():
            print("❌ Bot produced no output")
            return None

        response = json.loads(stdout.strip())
        return response

    except subprocess.TimeoutExpired:
        print("❌ Bot timeout (possible infinite loop)")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Bot output is not valid JSON: {e}")
        return None
    except Exception as e:
        print(f"❌ Error running bot: {e}")
        return None


def print_menu():
    """Print interactive menu."""
    print("\n" + "="*80)
    print("ARENA RUSH BOT - INTERACTIVE TESTER")
    print("="*80)
    print("[1] View current game state (JSON)")
    print("[2] View grid visualization")
    print("[3] Add wall")
    print("[4] Add energy orb")
    print("[5] Add enemy bot")
    print("[6] Edit your bot (position, energy, hp)")
    print("[7] Clear all obstacles/orbs/enemies")
    print("[8] Reset to default state")
    print("[9] TEST: Run bot on current state")
    print("[0] EXIT")
    print("="*80)
    print()


def main():
    """Main interactive loop."""
    builder = GameBuilder()

    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*15 + "ARENA RUSH BOT - INTERACTIVE TESTER" + " "*29 + "║")
    print("╚" + "="*78 + "╝")
    print("\nBuild custom game scenarios and test the bot in real-time!")
    print("The bot will read your scenario via stdin and output its action.\n")

    while True:
        print_menu()

        try:
            choice = input("Enter choice (0-9): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n✅ Exiting. Goodbye!")
            break

        if choice == "1":
            builder.print_state()

        elif choice == "2":
            builder.print_grid()

        elif choice == "3":
            builder.add_wall()

        elif choice == "4":
            builder.add_energy_orb()

        elif choice == "5":
            builder.add_enemy_bot()

        elif choice == "6":
            builder.edit_my_bot()

        elif choice == "7":
            builder.clear_all()

        elif choice == "8":
            builder.reset_state()

        elif choice == "9":
            print("\n" + "="*80)
            print("TESTING BOT...")
            print("="*80)

            response = run_bot_test(builder.state)

            if response:
                print("\n✅ Bot responded successfully:\n")
                print(json.dumps(response, indent=2))

                # Analyze response
                if "action" in response:
                    action = response["action"]
                    print(f"\n📋 Decision: {action.get('type').upper()}")
                    if action.get("type") == "shoot":
                        print(f"   → Shooting at {action.get('target')} (target ID: {action.get('target_id')})")
                    elif action.get("type") == "move":
                        print(f"   → Moving to {action.get('position')}")
                    elif action.get("type") == "wait":
                        print(f"   → Waiting")

                elif "actions" in response:
                    print(f"\n📋 Decisions for {len(response['actions'])} bots:")
                    for act in response["actions"]:
                        bot_id = act.get("bot_id")
                        action_type = act.get("type")
                        if action_type == "shoot":
                            print(f"   Bot {bot_id}: Shoot at {act.get('target')}")
                        elif action_type == "move":
                            print(f"   Bot {bot_id}: Move to {act.get('position')}")
                        else:
                            print(f"   Bot {bot_id}: Wait")

                if "error" in response:
                    print(f"\n⚠️  Error: {response['error']}")

                print("\n" + "="*80 + "\n")
            else:
                print("\n❌ Bot test failed (see error above)\n")
                print("="*80 + "\n")

        elif choice == "0":
            print("\n✅ Exiting. Goodbye!")
            break

        else:
            print("❌ Invalid choice. Try again.")


if __name__ == "__main__":
    main()
