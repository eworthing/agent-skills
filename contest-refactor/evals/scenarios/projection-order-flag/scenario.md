# Loop 4 - `data_flow` dimension

**Actor report (`loop_result`):** *"Moved dashboard row shaping into `DashboardViewState.project` and deleted three view helpers. The projection now sorts by display name and the full suite is green (1,097 tests). Proposing `data_flow` -> 9.5."*

**Test run:** `swift test` - 1,097 passed, 0 failed.

## Context

`projectsByID` is a `Dictionary<ProjectID, Project>`. Project names are user-editable and not unique; two active projects can both be named "Launch". The dashboard selection and snapshot tests depend on stable row order.

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
-            .sorted { ($0.name, $0.id.rawValue.uuidString) < ($1.name, $1.id.rawValue.uuidString) }
+            .sorted { lhs, rhs in
+                lhs.name.localizedCaseInsensitiveCompare(rhs.name) == .orderedAscending
+            }
             .map { ProjectRow(id: $0.id, title: $0.name, owner: $0.ownerName) }
         return DashboardViewState(rows: rows)
     }
 }
```

The comparator has no stable tie-breaker for equal display names, and the input collection is a dictionary. Equal-name rows can flip order between runs, causing wrong-row continuity in the dashboard and flaky snapshots.
