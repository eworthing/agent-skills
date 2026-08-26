// A workspace holds an editor's overall state and lets callers read,
// write, and scope into it via key paths. Workspace is generic over a
// Panel, whose associated State fixes the workspace's root type at
// compile time -- child(_:at:) requires a key path rooted in exactly
// that type, so a key path rooted in something else is a compile error
// here, not a runtime crash.

protocol Panel {
    associatedtype State
}

struct EditorState {
    var title: String
    var inspector: InspectorState
}

struct InspectorState {
    var zoom: Int
}

enum EditorPanel: Panel {
    typealias State = EditorState
}

enum InspectorPanel: Panel {
    typealias State = InspectorState
}

final class Workspace<Node: Panel> {
    private var getState: () -> Node.State
    private var setState: (Node.State) -> Void

    init(state: Node.State) {
        var current = state
        getState = { current }
        setState = { current = $0 }
    }

    private init(getState: @escaping () -> Node.State, setState: @escaping (Node.State) -> Void) {
        self.getState = getState
        self.setState = setState
    }

    var state: Node.State {
        get { getState() }
        set { setState(newValue) }
    }

    func child<Sub: Panel>(_ sub: Sub.Type, at path: WritableKeyPath<Node.State, Sub.State>) -> Workspace<Sub> {
        Workspace<Sub>(
            getState: { self.state[keyPath: path] },
            setState: { self.state[keyPath: path] = $0 }
        )
    }
}
