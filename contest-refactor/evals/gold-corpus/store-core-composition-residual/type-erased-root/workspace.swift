// A workspace holds an editor's overall state and lets callers read,
// write, and scope into it via key paths. The workspace boxes its state
// as Any, so read/write/child all take their "root" type as a free
// generic parameter, inferred fresh from whatever key path a caller
// happens to pass -- nothing here checks that the key path is actually
// rooted in the type this particular workspace boxes.

struct EditorState {
    var title: String
    var inspector: InspectorState
}

struct InspectorState {
    var zoom: Int
}

final class Workspace {
    private var getState: () -> Any
    private var setState: (Any) -> Void

    init<S>(state: S) {
        var current: Any = state
        getState = { current }
        setState = { current = $0 }
    }

    private init(getState: @escaping () -> Any, setState: @escaping (Any) -> Void) {
        self.getState = getState
        self.setState = setState
    }

    func read<Root, Value>(_ path: WritableKeyPath<Root, Value>) -> Value {
        (getState() as! Root)[keyPath: path]
    }

    func write<Root, Value>(_ newValue: Value, at path: WritableKeyPath<Root, Value>) {
        var root = getState() as! Root
        root[keyPath: path] = newValue
        setState(root)
    }

    /// Scopes down to a child workspace via a key path. `Root` is
    /// inferred purely from `path`, independent of whatever type this
    /// workspace actually boxes -- a key path rooted in an unrelated
    /// type still compiles here.
    func child<Root, Value>(at path: WritableKeyPath<Root, Value>) -> Workspace {
        Workspace(
            getState: { self.read(path) },
            setState: { self.write($0 as! Value, at: path) }
        )
    }
}
