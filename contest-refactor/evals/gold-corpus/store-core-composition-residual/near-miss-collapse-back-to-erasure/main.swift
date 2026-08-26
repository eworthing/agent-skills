// workspace's own bundled test suite.
//
// Run: swiftc workspace.swift main.swift -o /tmp/<name> && /tmp/<name>
// Exits 0 on success, 1 on failure.

import Foundation

func check(_ condition: Bool, _ message: String) {
    if !condition {
        print("FAIL: \(message)")
        exit(1)
    }
}

let root = Workspace(state: EditorState(title: "Untitled", inspector: InspectorState(zoom: 1)))
check(root.read(\EditorState.title) == "Untitled", "title should read back")

let inspector = root.child(at: \EditorState.inspector)
check(inspector.read(\InspectorState.zoom) == 1, "scoped zoom should match parent")

inspector.write(4, at: \InspectorState.zoom)
check(root.read(\EditorState.inspector).zoom == 4, "writing through the scoped child should reach the parent")

print("OK: main.swift")
