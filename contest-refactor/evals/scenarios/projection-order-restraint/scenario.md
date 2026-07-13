# Loop 4 - `data_flow` dimension

**Actor report (`loop_result`):** *"Moved dashboard row shaping into `DashboardViewState.project`, made the display order explicit, and deleted three view helpers. Full suite green (1,097 tests). Proposing `data_flow` -> 9.5."*

**Test run:** `swift test` - 1,097 passed, 0 failed.

## Context

`projectsByID` is a `Dictionary<ProjectID, Project>`. Project names are user-editable and not unique, so the projection owns a deterministic tie-breaker.

## Diff

```diff
--- a/Sources/Dashboard/DashboardViewState.swift
+++ b/Sources/Dashboard/DashboardViewState.swift
@@
 struct DashboardViewState {
     let rows: [ProjectRow]

     static func project(from state: DashboardState) -> DashboardViewState {
         let rows = state.projectsByID.values
             .filter { $0.isActive }
+            .sorted { lhs, rhs in
+                let left = (lhs.name.localizedLowercase, lhs.id.rawValue.uuidString)
+                let right = (rhs.name.localizedLowercase, rhs.id.rawValue.uuidString)
+                return left < right
+            }
             .map { ProjectRow(id: $0.id, title: $0.name, owner: $0.ownerName) }
         return DashboardViewState(rows: rows)
     }
 }
```

`DashboardViewStateTests.testEqualNamesSortByID` builds two active projects with the same display name and asserts the observable row order.
