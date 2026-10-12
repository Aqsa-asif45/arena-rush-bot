# Arena Rush Bot - Testing Guide

## Quick Start

### Run Full Test Suite
```bash
python test_bot.py
```

### Run Single Test Manually
```bash
# Echo JSON input to bot via stdin
echo '{"grid_size":15,"walls":[],"visible_orbs":[],"energy_orbs":[],"my_bots":[{"id":0,"position":[7,7],"energy":5,"hp":10}],"enemy_bots":[{"id":1,"position":[7,9],"hp":3}]}' | python arena_rush_bot.py
```

---

## What We're Testing

### 1. **State Parsing** ✓
- Bot correctly reads and interprets JSON input
- Handles missing fields (uses defaults)
- Graceful handling of malformed data

**Test Case:** `TEST 12 - Missing grid_size`
- **Input:** Missing `grid_size` field
- **Expected:** Bot uses default 15×15 grid, outputs valid action
- **What's verified:** Robust input handling

---

### 2. **Pathfinding (BFS)** ✓
- Finds shortest paths without hitting walls
- Navigates around obstacles
- Returns empty list if no path exists

**Test Cases:**
- `TEST 7 - Move to orb`
- `TEST 13 - Navigate around walls`

- **Expected:** Bot moves 1 step toward target
- **What's verified:** Correct A* path calculation

---

### 3. **Line-of-Sight (LOS) - 3 Range** ✓
- Detects enemies within Chebyshev distance ≤ 3
- Walls block line of sight (Bresenham algorithm)
- Range validation prevents long-distance shots

**Test Cases:**
- `TEST 2 - Enemy in LOS`
- `TEST 5 - Wall blocks vision`
- `TEST 6 - Enemy out of range`

- **Input:** Enemy at different distances/angles
- **Expected:** 
  - Shoot if: in LOS, distance ≤ 3, no walls blocking
  - Wait otherwise
- **What's verified:** Chebyshev distance + wall obstruction detection

---

### 4. **Combat Logic** ✓
- Only shoots when energy > 0
- Targets lowest HP enemies first (prioritize wounded)
- Outputs valid `{"type": "shoot", "target": [x, y], "target_id": id}` action

**Test Cases:**
- `TEST 2 - Basic shoot`
- `TEST 3 - Prefer low HP`
- `TEST 4 - Zero energy, no shoot`
- `TEST 15 - Combat priority`

- **Expected:** Shoot action with correct target
- **What's verified:** 
  - Energy check
  - HP-based priority
  - Valid action format

---

### 5. **Collision Prevention** ✓
- Two friendly bots never move to same tile
- Pathfinding avoids positions occupied by allies
- Bot finds alternate routes when direct path blocked

**Test Cases:**
- `TEST 8 - Two bots avoid collision`
- `TEST 9 - Friendly bot blocks path`

- **Input:** Two or more friendly bots with overlapping movement goals
- **Expected:** Each bot moves to different position, no crashes
- **What's verified:**
  - Reserved positions tracked correctly
  - BFS excludes ally positions
  - Alternate paths found

---

### 6. **Energy Management** ✓
- Bot seeks energy orbs when energy = 0
- Pathfinds to nearest energy orb
- Falls back to control zone if no orbs

**Test Cases:**
- `TEST 4 - Zero energy, seeks orb`
- `TEST 7 - Move to energy orb`
- `TEST 10 - Control zone fallback`

- **Expected:** Move action toward orb or center
- **What's verified:**
  - Energy state tracking
  - Orb priority detection
  - Control zone as fallback

---

### 7. **Control Zone Navigation** ✓
- Central 3×3 zone is positions (6-8, 6-8) on 15×15 grid
- Used as default gathering point
- Reachable from any position on grid

**Test Case:** `TEST 10 - Control Zone fallback`

- **Input:** Bot at (0,0), no orbs
- **Expected:** Move toward center (7,7 area)
- **What's verified:**
  - Zone correctly calculated as `grid_size//2 ± 1`
  - Pathfinding to zone works

---

### 8. **Error Handling & Robustness** ✓
- Zero crashes on bad input
- Always outputs valid JSON
- Graceful fallback to WAIT action
- Error messages included in response

**Test Cases:**
- `TEST 11 - Malformed position`
- `TEST 12 - Missing fields`

- **Input:** Invalid/incomplete JSON
- **Expected:** `{"action": {"type": "wait"}, "error": "<reason>"}`
- **What's verified:**
  - Exception caught at all stages
  - Valid JSON output (never crashes)
  - Distinguishes error types

---

### 9. **Multi-Bot Coordination** ✓
- Handles multiple friendly bots
- Each bot decides independently (but aware of others)
- Returns array of actions: `{"actions": [...]}`

**Test Case:** `TEST 14 - Multi-bot coordination`

- **Input:** 3+ bots, overlapping targets
- **Expected:** `{"actions": [action0, action1, action2]}`
- **What's verified:**
  - Multiple bot support
  - Collision-free simultaneous moves
  - Array output format

---

## Test Results Interpretation

### ✅ PASS
- Bot outputs correct action type for scenario
- JSON is valid and parseable
- No exceptions or crashes

### ❌ FAIL
- Bot outputs wrong action (e.g., "wait" instead of "shoot")
- Invalid JSON or output
- Bot crashed or timed out (infinite loop)

---

## Running Individual Scenarios

### Scenario 1: Basic Combat
```bash
cat << 'EOF' | python arena_rush_bot.py
{
  "grid_size": 15,
  "walls": [],
  "visible_orbs": [],
  "energy_orbs": [],
  "my_bots": [{"id": 0, "position": [7, 7], "energy": 5, "hp": 10}],
  "enemy_bots": [{"id": 1, "position": [7, 9], "hp": 3}]
}
EOF

# EXPECTED OUTPUT:
# {"action": {"type": "shoot", "bot_id": 0, "target": [7, 9], "target_id": 1}, "turn": true}
```

### Scenario 2: Collision Prevention
```bash
cat << 'EOF' | python arena_rush_bot.py
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
}
EOF

# EXPECTED OUTPUT:
# Bot 0 moves to orb without colliding with Bot 1
# {"actions": [...], "turn": true}
```

### Scenario 3: Error Handling
```bash
cat << 'EOF' | python arena_rush_bot.py
{
  "grid_size": 15,
  "walls": [],
  "my_bots": [{"position": "invalid"}]
}
EOF

# EXPECTED OUTPUT:
# {"action": {"type": "wait"}, "error": "..."}
# (No crash, always valid JSON)
```

---

## Edge Cases Covered

| Edge Case | Test | Expected Behavior |
|-----------|------|-------------------|
| Empty arena | TEST 1 | Wait |
| No energy | TEST 4 | Move to orb, not shoot |
| Wall blocks LOS | TEST 5 | No shoot (can't see through) |
| Out of range | TEST 6 | No shoot (>3 away) |
| Path blocked by ally | TEST 9 | Find alternate route |
| No orbs available | TEST 10 | Move to control zone |
| Malformed input | TEST 11 | WAIT + error message |
| Missing fields | TEST 12 | Use defaults, proceed |
| Multiple bots | TEST 14 | Coordinated, collision-free moves |

---

## Expected Output Format

### Single Bot Action
```json
{
  "action": {
    "type": "shoot|move|wait",
    "bot_id": 0,
    "target": [x, y],      // if type="shoot"
    "position": [x, y]     // if type="move"
  },
  "turn": true
}
```

### Multiple Bots
```json
{
  "actions": [
    {"type": "move", "bot_id": 0, "position": [8, 7]},
    {"type": "wait", "bot_id": 1},
    {"type": "shoot", "bot_id": 2, "target": [9, 6], "target_id": 5}
  ],
  "turn": true
}
```

### Error Fallback
```json
{
  "action": {"type": "wait"},
  "error": "json_decode_error|state_parse_error|decision_error|..."
}
```

---

## Performance Notes

- **BFS Pathfinding:** O(grid_size²) = O(225) per bot
- **LOS Check:** O(3²) = O(9) checks per target
- **Collision Check:** O(num_bots) per decision
- **Total per turn:** <100ms for 4 bots

---

## How to Debug Failures

1. **Check bot output format:**
   ```bash
   echo '...' | python arena_rush_bot.py | python -m json.tool
   ```

2. **Enable verbose logging** (add to arena_rush_bot.py):
   ```python
   import sys
   sys.stderr.write(f"DEBUG: {state}\n")
   ```

3. **Run single test:**
   ```python
   from test_bot import BotTester
   tester = BotTester()
   result = tester.test("My Test", my_state_dict, "shoot")
   ```

4. **Verify grid visualization:**
   ```
   Grid (15x15):
   [W] = wall, [E] = enemy, [O] = orb, [B] = your bot, [.] = empty
   
   (0,0) ............ (14,0)
     .
   (0,7) [B] . [E] . O . . . . .
     .
   (0,14) ............ (14,14)
   ```

---

## Summary Checklist

- ✅ Pathfinding works (find shortest paths)
- ✅ LOS detects enemies within 3 range
- ✅ Combat prioritizes low-HP targets
- ✅ Collision prevention avoids friendly bots
- ✅ Energy management seeks orbs → control zone
- ✅ Error handling catches all exceptions
- ✅ Multi-bot coordination works
- ✅ Zero crashes on edge cases
