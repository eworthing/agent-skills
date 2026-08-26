// Grader-only adapter. Not shown to a candidate (listed in
// provenance.json's grader_only_files, NOT candidate_visible_files).
//
// Gives oracles.py the same two uniform probe entry points across all
// five variants, reconciling this variant's own real construction path
// -- Workspace<Node>, pinned to Node.State -- into one call shape.

func probeInitialChildZoomMatchesParent(initialTitle: String, initialZoom: Int) -> Int {
    let root = Workspace<EditorPanel>(state: EditorState(title: initialTitle, inspector: InspectorState(zoom: initialZoom)))
    let child = root.child(InspectorPanel.self, at: \EditorState.inspector)
    return child.state.zoom
}

func probeChildWriteBackReachesParent(initialTitle: String, initialZoom: Int, newZoom: Int) -> Int {
    let root = Workspace<EditorPanel>(state: EditorState(title: initialTitle, inspector: InspectorState(zoom: initialZoom)))
    let child = root.child(InspectorPanel.self, at: \EditorState.inspector)
    child.state.zoom = newZoom
    return root.state.inspector.zoom
}
