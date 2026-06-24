# Loop 4 — `domain_modeling` dimension

**Actor report (`loop_result`):** *"Refactored roster management so the One-League Rule invariant lives exclusively inside `LeagueRoster.addPlayer(checking:)`. Both `RosterView` and `ImportService` call through the domain method rather than performing their own guards. Full suite green (2,041 tests). Proposing `domain_modeling` → 9.5."*

**Test run:** `swift test` — 2,041 passed, 0 failed.

## Context

The application manages sports league rosters. A hard domain invariant governs membership: **a player may not be active on two rosters in the same league simultaneously** (`CONTEXT.md` §3: "One-League Rule"). This loop installs a single authoritative enforcement point inside the domain owner.

## Diff

```diff
--- a/Sources/Domain/LeagueRoster.swift
+++ b/Sources/Domain/LeagueRoster.swift
@@
 struct LeagueRoster {
     let leagueID: League.ID
     private(set) var activePlayers: [Player] = []

+    /// Adds `player` to this roster, enforcing the One-League Rule across `allRosters`.
+    /// - Throws: `RosterError.playerAlreadyInLeague` if `player` is already active
+    ///   in any roster with the same `leagueID`.
+    mutating func addPlayer(
+        _ player: Player,
+        checking allRosters: [LeagueRoster]
+    ) throws {
+        let conflict = allRosters.first {
+            $0.leagueID == leagueID && $0.activePlayers.contains(player)
+        }
+        if let conflict {
+            throw RosterError.playerAlreadyInLeague(player, roster: conflict)
+        }
+        activePlayers.append(player)
+    }
 }

--- a/Sources/Presentation/RosterView.swift
+++ b/Sources/Presentation/RosterView.swift
@@
 struct RosterView: View {
     @StateObject private var store: RosterStore
 
     private func handleAdd(_ player: Player) {
-        store.addPlayer(player)
+        do {
+            try store.addPlayerToCurrentRoster(player)
+        } catch RosterError.playerAlreadyInLeague(let p, _) {
+            store.presentError(.playerAlreadyInLeague(p))
+        }
     }
 }

--- a/Sources/Infrastructure/ImportService.swift
+++ b/Sources/Infrastructure/ImportService.swift
@@
 actor ImportService {
     private let store: RosterStore
 
     func importRoster(from rows: [CSVRow]) async throws {
         for row in rows {
             let player = try Player(csvRow: row)
-            await store.addPlayer(player)
+            try await store.addPlayer(player, toLeague: row.leagueID)
         }
     }
 }
```

`RosterStore.addPlayerToCurrentRoster` and `RosterStore.addPlayer(toLeague:)` both delegate to `LeagueRoster.addPlayer(_:checking:)`. The invariant check executes once, in the domain type, regardless of which path adds the player. The two callers carry no guard logic of their own.
