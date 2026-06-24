# Loop 4 — `domain_modeling` dimension

**Actor report (`loop_result`):** *"Refactored roster management so `RosterView` validates the single-league invariant before adding a player, and `ImportService` now also guards the invariant on bulk imports. Full suite green (2,041 tests). Proposing `domain_modeling` → 9.5."*

**Test run:** `swift test` — 2,041 passed, 0 failed.

## Context

The application manages sports league rosters. A hard domain invariant governs membership: **a player may not be active on two rosters in the same league simultaneously** (`CONTEXT.md` §3: "One-League Rule"). This invariant must hold whether a player is added through the UI or via a bulk CSV import.

Before this loop, `LeagueRoster` (the domain owner) had no method that checked the invariant; all callers performed ad-hoc guard logic. This loop extracts those guards — but instead of placing the check inside the domain type, it duplicates a local copy in `RosterView` (presentation layer) and another in `ImportService` (background infrastructure layer). `LeagueRoster.addPlayer` remains a plain mutation that trusts its caller.

## Diff

```diff
--- a/Sources/Domain/LeagueRoster.swift
+++ b/Sources/Domain/LeagueRoster.swift
@@
 struct LeagueRoster {
     let leagueID: League.ID
     private(set) var activePlayers: [Player] = []
 
-    mutating func addPlayer(_ player: Player) {
+    /// Adds a player. Callers are expected to pre-validate the One-League Rule.
+    mutating func addPlayer(_ player: Player) {
         activePlayers.append(player)
     }
 }

--- a/Sources/Presentation/RosterView.swift
+++ b/Sources/Presentation/RosterView.swift
@@
 struct RosterView: View {
     @StateObject private var store: RosterStore
 
     private func handleAdd(_ player: Player) {
-        store.addPlayer(player)
+        // Enforce One-League Rule before mutating roster
+        let alreadyActive = store.allRosters
+            .filter { $0.leagueID == store.currentRoster.leagueID && $0.activePlayers.contains(player) }
+        guard alreadyActive.isEmpty else {
+            store.presentError(.playerAlreadyInLeague(player))
+            return
+        }
+        store.addPlayer(player)
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
+            // Enforce One-League Rule for each imported player
+            let activeRosters = await store.allRosters
+                .filter { $0.leagueID == row.leagueID && $0.activePlayers.contains(player) }
+            guard activeRosters.isEmpty else {
+                throw ImportError.playerAlreadyInLeague(player)
+            }
+            await store.addPlayer(player)
         }
     }
 }
```

The two guard blocks are structurally similar but not shared: `RosterView` reads `store.currentRoster.leagueID` while `ImportService` reads `row.leagueID`. In a future change where `row.leagueID` resolves differently from `store.currentRoster.leagueID`, the two paths silently diverge, and a carefully-timed import can add a player who is already active in that league without triggering either guard.
