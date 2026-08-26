// workspace's own bundled test suite (this variant).
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

let root = Workspace<EditorPanel>(state: EditorState(title: "Untitled", inspector: InspectorState(zoom: 1)))
check(root.state.title == "Untitled", "title should read back")

let inspector = root.child(InspectorPanel.self, at: \EditorState.inspector)
check(inspector.state.zoom == 1, "scoped zoom should match parent")

inspector.state.zoom = 4
check(root.state.inspector.zoom == 4, "writing through the scoped child should reach the parent")

print("OK: main.swift")
