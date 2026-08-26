// Grader-only adapter. Not shown to a candidate (listed in
// provenance.json's grader_only_files, NOT candidate_visible_files).
//
// Gives oracles.py the same two uniform probe entry points across all
// five variants, reconciling this variant's own real API -- Workspace's
// generic read/write/child, whose Root is unconstrained relative to any
// container type -- into one call shape.

func probeInitialChildZoomMatchesParent(initialTitle: String, initialZoom: Int) -> Int {
    let root = Workspace(state: EditorState(title: initialTitle, inspector: InspectorState(zoom: initialZoom)))
    let child = root.child(at: \EditorState.inspector)
    return child.read(\InspectorState.zoom)
}

func probeChildWriteBackReachesParent(initialTitle: String, initialZoom: Int, newZoom: Int) -> Int {
    let root = Workspace(state: EditorState(title: initialTitle, inspector: InspectorState(zoom: initialZoom)))
    let child = root.child(at: \EditorState.inspector)
    child.write(newZoom, at: \InspectorState.zoom)
    return root.read(\EditorState.inspector).zoom
}
