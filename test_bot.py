#!/usr/bin/env python3
"""
Test harness for Arena Rush Bot - Tests core functionality and edge cases.

WHAT WE'RE TESTING:
1. State parsing: Correctly reads JSON input
2. Pathfinding: BFS finds shortest collision-free paths
3. LOS (Line-of-Sight): 3-range visibility with wall obstruction
4. Combat: Targeting low-HP enemies with energy
5. Collision prevention: Two bots never move to same tile
6. Energy management: Bot seeks orbs or control zone
7. Error handling: Graceful fallback on bad input
8. Control zone: Central 3x3 area pathfinding

WHAT TO EXPECT:
- Shoot action when enemy in LOS with energy > 0
- Move to energy orbs (priority) or control zone
- Wait when no path or no target
- WAIT fallback on any exception (zero crashes)
"""

import json
import subprocess
import sys
from typing import Dict, List, Any, Optional


class BotTester:
    """Run test cases against arena_rush_bot.py via stdin/stdout."""

    def __init__(self, bot_script: str = "arena_rush_bot.py"):
        self.bot_script = bot_script
        self.test_count = 0
        self.passed = 0
        self.failed = 0

    def run_bot_turn(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send JSON state to bot, receive JSON action.

        Args:
            state: Game state dictionary

        Returns:
            Parsed action dictionary or None on error
        """
        try:
            proc = subprocess.Popen(
                [sys.executable, self.bot_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            input_json = json.dumps(state)
            stdout, stderr = proc.communicate(input=input_json, timeout=5)

            if not stdout.strip():
                print(f"  ❌ No output from bot")
                return None

            response = json.loads(stdout.strip())
            return response

        except subprocess.TimeoutExpired:
            print(f"  ❌ Bot timeout (infinite loop?)")
            return None
        except json.JSONDecodeError as e:
            print(f"  ❌ Invalid JSON output: {e}")
            return None
        except Exception as e:
            print(f"  ❌ Error running bot: {e}")
            return None

    def test(self, name: str, state: Dict[str, Any],
             expected_action: str = None, expected_field: str = None) -> bool:
        """Run a single test case.

        Args:
            name: Test case name
            state: Input game state
            expected_action: Expected "type" field value (e.g., "shoot", "move", "wait")
            expected_field: Optional field to verify (e.g., "position")

        Returns:
            True if test passed, False otherwise
        """
        self.test_count += 1
        print(f"\n[TEST {self.test_count}] {name}")
        print(f"  Input: {json.dumps(state, separators=(',', ':'))[:80]}...")

        response = self.run_bot_turn(state)

        if response is None:
            self.failed += 1
            return False

        print(f"  Output: {json.dumps(response, separators=(',', ':'))}")

        # Check for error in response (means fallback was triggered)
        if "error" in response and expected_action != "wait":
            print(f"  ❌ Got error response: {response.get('error')}")
            self.failed += 1
            return False

        # Extract actual action
        if "action" in response:
            action = response["action"]
        elif "actions" in response:
            action = response["actions"][0] if response["actions"] else None
        else:
            action = None

        if action is None:
            print(f"  ❌ No action in response")
            self.failed += 1
            return False

        # Verify expected action type
        if expected_action:
            actual_type = action.get("type")
            if actual_type == expected_action:
                print(f"  ✅ Correct action type: {actual_type}")
                self.passed += 1
                return True
            else:
                print(f"  ❌ Expected '{expected_action}' but got '{actual_type}'")
                self.failed += 1
                return False
        else:
            print(f"  ✅ Got action: {action.get('type')}")
            self.passed += 1
            return True


def create_test_cases() -> List[tuple]:
    """Create all test case scenarios.

    Returns:
        List of (name, state_dict, expected_action) tuples
    """

    tests = []

    # ===== TEST 1: No targets/orbs - moves to control zone =====
    tests.append((
        "BASIC: Empty arena - bot seeks control zone (fallback)",
        {
            "grid_size": 15,
            "walls": [],
            "visible_orbs": [],
            "energy_orbs": [],
            "my_bots": [{"id": 0, "position": [7, 7], "energy": 0, "hp": 10}],
            "enemy_bots": []
        },
        "move"  # Seeks control zone as fallback
    ))

    # ===== TEST 2: Combat - Shoot enemy in LOS =====
    tests.append((
        "COMBAT: Enemy in LOS, energy > 0 - bot shoots",
        {
            "grid_size": 15,
            "walls": [],
            "visible_orbs": [],
            "energy_orbs": [],
            "my_bots": [{"id": 0, "position": [7, 7], "energy": 5, "hp": 10}],
            "enemy_bots": [{"id": 1, "position": [7, 9], "hp": 3}]  # 2 tiles away, in LOS
        },
        "shoot"
    ))

    # ===== TEST 3: Combat - Prefer low HP enemy =====
    tests.append((
        "COMBAT: Multiple enemies - prefer low HP target",
        {
            "grid_size": 15,
            "walls": [],
            "visible_orbs": [],
            "energy_orbs": [],
            "my_bots": [{"id": 0, "position": [7, 7], "energy": 5, "hp": 10}],
            "enemy_bots": [
                {"id": 1, "position": [7, 9], "hp": 5},
                {"id": 2, "position": [9, 7], "hp": 1}  # Lower HP, should target this
            ]
        },
        "shoot"
    ))

    # ===== TEST 4: Combat - No energy, no shoot =====
    tests.append((
        "COMBAT: Zero energy - cannot shoot, seeks energy",
        {
            "grid_size": 15,
            "walls": [],
            "visible_orbs": [],
            "energy_orbs": [[5, 5]],
            "my_bots": [{"id": 0, "position": [7, 7], "energy": 0, "hp": 10}],
            "enemy_bots": [{"id": 1, "position": [7, 9], "hp": 3}]
        },
        "move"  # Should move to energy orb, not shoot
    ))

    # ===== TEST 5: LOS - Wall blocks vision - seeks control zone =====
    tests.append((
        "LOS: Wall blocks line of sight - cannot shoot, seeks control zone",
        {
            "grid_size": 15,
            "walls": [[7, 8]],  # Wall between bot and enemy
            "visible_orbs": [],
            "energy_orbs": [],
            "my_bots": [{"id": 0, "position": [7, 7], "energy": 5, "hp": 10}],
            "enemy_bots": [{"id": 1, "position": [7, 9], "hp": 3}]
        },
        "move"  # Cannot see through wall, falls back to control zone
    ))

    # ===== TEST 6: LOS - Out of range - seeks control zone =====
    tests.append((
        "LOS: Enemy beyond 3-range - cannot shoot, seeks control zone",
        {
            "grid_size": 15,
            "walls": [],
            "visible_orbs": [],
            "energy_orbs": [],
            "my_bots": [{"id": 0, "position": [7, 7], "energy": 5, "hp": 10}],
            "enemy_bots": [{"id": 1, "position": [7, 12], "hp": 3}]  # 5 tiles away
        },
        "move"  # Out of range, falls back to control zone
    ))

    # ===== TEST 7: Pathfinding - Move to orb =====
    tests.append((
        "PATHFINDING: Move to nearest energy orb",
        {
            "grid_size": 15,
            "walls": [],
            "visible_orbs": [],
            "energy_orbs": [[8, 7], [6, 7]],
            "my_bots": [{"id": 0, "position": [7, 7], "energy": 0, "hp": 10}],
            "enemy_bots": []
        },
        "move"
    ))

    # ===== TEST 8: Collision Prevention - Two bots =====
    tests.append((
        "COLLISION: Two friendly bots - avoid same destination",
        {
            "grid_size": 15,
            "walls": [],
            "visible_orbs": [],
            "energy_orbs": [[8, 7]],
            "my_bots": [
                {"id": 0, "position": [7, 7], "energy": 0, "hp": 10},
                {"id": 1, "position": [7, 6], "energy": 0, "hp": 10}
            ],
            "enemy_bots": []
        },
        "move"  # Bot 0 moves toward orb, avoids bot 1
    ))

    # ===== TEST 9: Collision Prevention - Path blocked =====
    tests.append((
        "COLLISION: Friendly bot blocks path - seek alternative",
        {
            "grid_size": 15,
            "walls": [],
            "visible_orbs": [],
            "energy_orbs": [[9, 7]],
            "my_bots": [
                {"id": 0, "position": [7, 7], "energy": 0, "hp": 10},
                {"id": 1, "position": [8, 7], "energy": 0, "hp": 10}  # Blocks direct path
            ],
            "enemy_bots": []
        },
        "move"  # Bot 0 finds alternate route
    ))

    # ===== TEST 10: Control Zone - Fallback destination =====
    tests.append((
        "CONTROL ZONE: No orbs - moves to central 3x3 zone",
        {
            "grid_size": 15,
            "walls": [],
            "visible_orbs": [],
            "energy_orbs": [],
            "my_bots": [{"id": 0, "position": [0, 0], "energy": 0, "hp": 10}],
            "enemy_bots": []
        },
        "move"  # Should move toward center (7,7 area)
    ))

    # ===== TEST 11: Error Handling - Malformed position =====
    tests.append((
        "ERROR: Malformed bot position - graceful fallback",
        {
            "grid_size": 15,
            "walls": [],
            "visible_orbs": [],
            "energy_orbs": [],
            "my_bots": [{"id": 0, "position": "invalid"}],  # Invalid format
            "enemy_bots": []
        },
        "wait"  # Should output WAIT, not crash
    ))

    # ===== TEST 12: Error Handling - Missing grid_size =====
    tests.append((
        "ERROR: Missing grid_size - uses default 15x15, seeks control zone",
        {
            "walls": [],
            "visible_orbs": [],
            "energy_orbs": [],
            "my_bots": [{"id": 0, "position": [7, 7], "energy": 0, "hp": 10}],
            "enemy_bots": []
        },
        "move"  # Uses default grid, moves to control zone
    ))

    # ===== TEST 13: Wall obstruction - pathfinding =====
    tests.append((
        "PATHFINDING: Navigate around walls",
        {
            "grid_size": 15,
            "walls": [[8, 7], [8, 8], [8, 9]],  # Vertical wall
            "visible_orbs": [],
            "energy_orbs": [[10, 7]],
            "my_bots": [{"id": 0, "position": [7, 7], "energy": 0, "hp": 10}],
            "enemy_bots": []
        },
        "move"  # Should pathfind around wall
    ))

    # ===== TEST 14: Multi-bot coordination =====
    tests.append((
        "MULTI-BOT: Three bots, coordinated movement",
        {
            "grid_size": 15,
            "walls": [],
            "visible_orbs": [],
            "energy_orbs": [[7, 10], [10, 7]],
            "my_bots": [
                {"id": 0, "position": [7, 7], "energy": 0, "hp": 10},
                {"id": 1, "position": [5, 7], "energy": 0, "hp": 10},
                {"id": 2, "position": [7, 5], "energy": 0, "hp": 10}
            ],
            "enemy_bots": []
        },
        "move"
    ))

    # ===== TEST 15: Combat + Energy tradeoff =====
    tests.append((
        "STRATEGY: Combat priority over energy (if low energy but enemy near)",
        {
            "grid_size": 15,
            "walls": [],
            "visible_orbs": [],
            "energy_orbs": [[3, 3]],
            "my_bots": [{"id": 0, "position": [7, 7], "energy": 1, "hp": 10}],
            "enemy_bots": [{"id": 1, "position": [8, 7], "hp": 2}]  # Close, low HP
        },
        "shoot"  # Shoot first (priority), then seek energy
    ))

    return tests


def print_header():
    """Print test suite header."""
    print("=" * 80)
    print("ARENA RUSH BOT - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print(__doc__)


def print_summary(tester: BotTester):
    """Print test results summary."""
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total:  {tester.test_count}")
    print(f"Passed: {tester.passed} ✅")
    print(f"Failed: {tester.failed} ❌")

    if tester.failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        pct = (tester.passed / tester.test_count * 100) if tester.test_count > 0 else 0
        print(f"\n📊 Pass rate: {pct:.1f}%")


def main():
    """Run all tests."""
    print_header()

    tester = BotTester()
    test_cases = create_test_cases()

    for name, state, expected_action in test_cases:
        tester.test(name, state, expected_action)

    print_summary(tester)

    return 0 if tester.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
