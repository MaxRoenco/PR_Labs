# Lab 3: Memory Scramble - Multiplayer Card Game

**Author:** Maxim Roenco  
**Group:** FAF-231  
**Course:** Network Programming  
**Date:** November 2025

---

## Overview

This project implements a concurrent multiplayer memory card game based on the MIT 6.102 Memory Scramble assignment. The game allows multiple players to simultaneously flip cards and find matching pairs, with proper concurrency control to prevent race conditions and deadlocks.

**Live Server:** Start with `npm start 8080 boards/perfect.txt` and navigate to http://localhost:8080

---

## Quick Start

### Prerequisites
- Node.js 22.12.x
- npm or Docker

### Installation & Running

**Local Development:**
```bash
npm install          # Install dependencies
npm run compile      # Compile TypeScript
npm start 8080 boards/perfect.txt   # Start server
```

**With Docker:**
```bash
docker compose up    # Build and run
```

**Testing:**
```bash
npm test            # Run test suite (47 tests)
npm run coverage    # Generate coverage report
npm run simulation  # Run 4-player simulation
```

---

## Project Structure

```
lab3/
├── src/
│   ├── board.ts       # Board ADT with game logic (875 lines)
│   ├── commands.ts    # API command handlers
│   ├── server.ts      # HTTP server setup
│   └── simulation.ts  # Multi-player simulation
├── test/
│   └── board.test.ts  # Comprehensive test suite (47 tests)
├── boards/            # Game configurations
│   ├── perfect.txt    # 3x3 emoji board
│   ├── ab.txt         # 5x5 letter board
│   └── zoom.txt       # Custom board
├── public/
│   └── index.html     # Web game interface
├── docker-compose.yml
├── Dockerfile
└── package.json
```

---

## Architecture & Design

### Board ADT

The core `Board` class is a thread-safe mutable data type that manages game state:

**Key Fields:**
```typescript
private readonly grid: Space[][]              // 2D card grid
private readonly players: Map<string, PlayerState>  // Player states
private readonly waitQueue: Map<string, Array<() => void>>  // Waiting players
private readonly changeListeners: Array<() => void>  // Watch callbacks
```

**Abstraction Function:**  
Represents a Memory Scramble game board where `grid[r][c]` is the space at row r, column c. Each space contains a card (or is empty), with state tracking whether it's face up/down and who controls it. Players map stores each player's current move state, waitQueue handles concurrent access conflicts, and changeListeners enable real-time board updates.

**Representation Invariant:**
- Grid dimensions match declared rows × cols
- Empty spaces are always face down and uncontrolled
- Controlled cards are always face up
- No two players control the same card
- Matched cards remain controlled until removed
- Non-matching second cards are uncontrolled (Rule 2-E)

**Safety from Rep Exposure:**
- All fields are private
- Grid never returned directly (only formatted strings)
- No mutable objects exposed through public methods
- Constructor copies input arrays

### Commands Module

Thin wrapper providing clean API interface:

```typescript
export async function look(board: Board, playerId: string): Promise<string>
export async function flip(board: Board, playerId: string, row: number, column: number): Promise<string>
export async function map(board: Board, playerId: string, f: (card: string) => Promise<string>): Promise<string>
export async function watch(board: Board, playerId: string): Promise<string>
```

Each function is 1-3 lines, delegating to Board methods. This keeps the API layer simple and testable.

### HTTP Server

Express-based server exposing RESTful endpoints:
- `GET /look/:playerId` - View board state
- `GET /flip/:playerId/:row,:column` - Flip a card
- `GET /replace/:playerId/:fromCard/:toCard` - Transform cards
- `GET /watch/:playerId` - Wait for changes
- `GET /` - Serve web UI

---

## Game Rules Implementation

### First Card Rules (Rules 1-A through 1-D)

**Rule 1-A: No Card Present**
```typescript
if (space.card === null) {
    throw new Error(`no card at (${row},${col})`);
}
```

**Rule 1-B: Face Down Card**
```typescript
space.faceUp = true;
space.controlledBy = playerId;
```

**Rule 1-C: Face Up Uncontrolled Card**
```typescript
if (space.faceUp && space.controlledBy === null) {
    space.controlledBy = playerId;  // Take control
}
```

**Rule 1-D: Card Controlled by Another Player**
```typescript
while (space.controlledBy !== null && space.controlledBy !== playerId) {
    await this.waitForCard(row, col);  // Wait for release
}
```

### Second Card Rules (Rules 2-A through 2-E)

**Rule 2-A: Empty Space** - Relinquish first card and throw error

**Rule 2-B: Controlled Card** - Relinquish first card immediately (no wait) to prevent deadlock

**Rule 2-C: Turn Face Up** - Card becomes visible

**Rule 2-D: Check Match**
```typescript
if (firstCard === secondCard) {
    // Match! Keep control of both cards
    space.controlledBy = playerId;
    playerState.matched = true;
} else {
    // No match - relinquish control of both (Rule 2-E)
    firstSpace.controlledBy = null;
    playerState.matched = false;
}
```

### Cleanup Rules (Rules 3-A and 3-B)

Before flipping a new first card, finish previous play:

**Rule 3-A: Remove Matched Cards**
```typescript
if (playerState.matched) {
    this.removeCard(firstCard.row, firstCard.col, playerId);
    this.removeCard(secondCard.row, secondCard.col, playerId);
}
```

**Rule 3-B: Turn Down Non-Matching Cards**
```typescript
if (!playerState.matched && space.controlledBy === null) {
    space.faceUp = false;
}
```

---

## Concurrency Implementation

### Waiting Mechanism

Uses `Promise.withResolvers()` for clean async coordination:

```typescript
private async waitForCard(row: number, col: number): Promise<void> {
    const key = this.posKey(row, col);
    const { promise, resolve } = Promise.withResolvers<void>();
    
    if (!this.waitQueue.has(key)) {
        this.waitQueue.set(key, []);
    }
    this.waitQueue.get(key).push(resolve);
    
    await promise;  // Wait until notified
}

private notifyWaiters(row: number, col: number): void {
    const waiters = this.waitQueue.get(this.posKey(row, col));
    if (waiters) {
        waiters.forEach(resolve => resolve());  // Wake all waiting players
        this.waitQueue.delete(this.posKey(row, col));
    }
}
```

### Deadlock Prevention

**Rule 2-B** prevents deadlock by rejecting second card flips on controlled cards instead of waiting:

```typescript
// Second card - don't wait for controlled cards
if (space.controlledBy !== null) {
    firstSpace.controlledBy = null;  // Release first card
    this.notifyWaiters(first.row, first.col);
    throw new Error(`card controlled by another player`);
}
```

This ensures no circular wait conditions can occur.

---

## Advanced Features

### Map Function (Pairwise Consistency)

Transforms all cards while maintaining matching pairs:

```typescript
public async map(f: (card: string) => Promise<string>): Promise<void> {
    // Group cards by value
    const cardPositions = new Map<string, Array<{row, col}>>();
    
    for (const [oldCard, positions] of cardPositions) {
        const newCard = await f(oldCard);  // Transform once per unique value
        
        // Update all instances atomically
        for (const {row, col} of positions) {
            if (this.grid[row][col].card === oldCard) {
                this.grid[row][col].card = newCard;
            }
        }
    }
}
```

**Key Property:** All instances of a card value transform together, so matching pairs remain matching throughout the operation.

### Watch Function (Real-Time Updates)

Notifies clients when board changes:

```typescript
public watchForChange(): Promise<void> {
    const { promise, resolve } = Promise.withResolvers<void>();
    this.changeListeners.push(resolve);
    return promise;
}

private notifyChangeListeners(): void {
    const listeners = [...this.changeListeners];
    this.changeListeners.length = 0;
    
    listeners.forEach(listener => listener());
}
```

**Triggered by:** Cards flipping up/down, cards removed, card values changing  
**Not triggered by:** Control changes without face state changes

---

## Testing Strategy

### Test Suite Breakdown (47 Tests)

**Parsing Tests (6 tests)**
- Valid files: 1x1, 3x3, 5x5 boards
- Invalid files: wrong card count, bad dimensions, malformed format

**Look Tests (4 tests)**
- All cards face down initially
- Controlled cards shown as "my CARD"
- Other players' cards shown as "up CARD"
- Empty spaces shown as "none"

**First Card Flip Tests (4 tests)**
- Flip face-down card → gain control
- Take control of uncontrolled face-up card
- Error on empty space
- Wait for controlled card

**Second Card Flip Tests (4 tests)**
- Match → keep control of both
- No match → relinquish both
- Empty space → error + relinquish first
- Controlled card → error + relinquish first

**Cleanup Tests (4 tests)**
- Matched cards removed on next move
- Non-matching cards turned face down
- Cards controlled by others stay face up
- Complex scenario with control changes

**Concurrency Tests (10 tests)**
- Multiple players flip different cards
- Multiple waiters for same card
- Player moves while another waits
- 5 concurrent players
- Waiting chains (A controls, B waits, C waits)
- Matches while others wait
- No deadlock scenarios
- Rapid concurrent flips
- Interleaving look() and flip()
- Finishing moves with pending operations

**Map Tests (6 tests)**
- Transform all cards
- Pairwise consistency during transformation
- Face state preserved
- Control state preserved
- Interleaving with flip operations
- Empty spaces handled correctly

**Watch Tests (7 tests)**
- Wait and notify on card flip
- Notify on removal
- Notify on face down
- Notify on map transformation
- Multiple concurrent watchers
- No notification on pure control changes
- Interleaving look() with watch()

### Coverage Results

```
File         | Statements | Branches | Functions | Lines
-------------|------------|----------|-----------|-------
board.ts     | 96.12%    | 95.91%  | 94.73%   | 96.12%
commands.ts  | 100%      | 100%    | 100%     | 100%
server.ts    | 82.35%    | 50%     | 81.81%   | 82.35%
simulation.ts| 95.83%    | 90.90%  | 100%     | 95.83%
-------------|------------|----------|-----------|-------
All files    | 94.21%    | 88.63%  | 93.33%   | 94.21%
```

---

## Simulation Results

### Configuration
- **Players:** 4 (player0, player1, player2, player3)
- **Attempts:** 100 per player
- **Delays:** Random 0.1-2ms between moves
- **Board:** 5x5 from boards/ab.txt
- **No shuffling** (as required)

### Sample Run Statistics
```
Total flips attempted: 107
Successful matches: 12
Failed flips: 378 (empty spaces, controlled cards)
Times waited for card: 2
Final state: Nearly empty board (24 cards removed)
```

### Special Test Scenarios

**Scenario 1: Multiple Players Waiting**
- Alice controls (0,0)
- Bob and Charlie both try to flip it → both wait
- Alice releases → one gets it immediately

**Scenario 2: Matched Cards Cleanup**
- Alice matches two cards at (0,0) and (0,2)
- Bob waits for (0,0)
- Alice makes next move → cards removed
- Bob's wait fails with "no card at (0,0)" ✓

**Result:** ✅ No crashes, no deadlocks, proper concurrency handling

---

## Docker Setup

### Dockerfile
```dockerfile
FROM node:22.12
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run compile
EXPOSE 8080
CMD ["node", "--require", "source-map-support/register", 
     "dist/src/server.js", "8080", "boards/perfect.txt"]
```

### docker-compose.yml
```yaml
services:
  game-server:
    build: .
    ports:
      - "8080:8080"
    command: ["node", "--require", "source-map-support/register",
              "dist/src/server.js", "8080", "boards/perfect.txt"]
```

---

## API Documentation

### GET /look/:playerId
Returns board state from player's perspective.

**Response Format:**
```
ROWSxCOLS
SPOT
SPOT
...
```

Where SPOT is one of:
- `none` - Empty space
- `down` - Face-down card
- `up CARD` - Face-up card (not controlled by you)
- `my CARD` - Face-up card you control

**Example:**
```
3x3
my 🦄
down
up 🌈
none
down
my 🌈
```

### GET /flip/:playerId/:row,:column
Flip a card at the specified position.

**Returns:** Board state after flip (on success)  
**Error (409):** "cannot flip this card: [reason]"

### GET /replace/:playerId/:fromCard/:toCard
Replace all instances of fromCard with toCard.

**Returns:** Board state after replacement

### GET /watch/:playerId
Wait until board changes, then return new state.

**Returns:** Board state after next change  
**Blocks until:** Any card flips, is removed, or changes value

---

## Key Learning Outcomes

### Concurrency Patterns
- Promise-based async coordination
- Wait queues and notification mechanisms
- Deadlock prevention strategies
- Race condition handling

### Software Engineering Practices
- Abstraction functions and rep invariants
- Comprehensive test coverage (>94%)
- Clean separation of concerns (ADT → Commands → HTTP)
- Safety from rep exposure

### TypeScript Features
- Strong typing for safety
- Async/await patterns
- Promise.withResolvers() for coordination
- Strict null checking

---

## Known Limitations

1. **No persistence** - Board state lost on server restart
2. **No authentication** - Player IDs are self-declared
3. **Memory usage** - Wait queues grow with concurrent players
4. **No game reset** - Must restart server for new game

---

## Future Enhancements

- [ ] Persistent game state (database)
- [ ] WebSocket support for real-time updates
- [ ] Player authentication and sessions
- [ ] Game rooms (multiple concurrent games)
- [ ] Leaderboard and statistics
- [ ] Replay functionality
- [ ] Performance metrics dashboard

---

## References

1. MIT 6.102/6.031 Course Materials (2025) - Problem Set 4: Memory Scramble
2. TypeScript Documentation - Promise.withResolvers()
3. Herlihy & Shavit - *The Art of Multiprocessor Programming*
4. Express.js Documentation
5. Mocha Testing Framework

---

## License

Educational project for TUM Network Programming course.

---

**End of Report**

