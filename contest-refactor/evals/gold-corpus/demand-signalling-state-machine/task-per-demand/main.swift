// signal_relay's own bundled test suite (this variant).
//
// Run: swiftc signal_relay.swift main.swift -o /tmp/<name> && /tmp/<name>
// Exits 0 on success, 1 on failure.

import Foundation

func check(_ condition: Bool, _ message: String) {
    if !condition {
        print("FAIL: \(message)")
        exit(1)
    }
}

let relay = Relay(sourceCount: 1)

let onDemand = relay.step(.demandArrived(request: 1))
check(onDemand == [.startSourceWork(source: .first)], "the first demand should start the one known source")

let onValue = relay.step(.valueProduced(source: .first, value: 42))
check(
    onValue == [.resumeWithValue(request: 1, value: 42)],
    "a produced value should resume the request waiting for it"
)

let onFinish = relay.step(.sourceFinished(source: .first))
check(onFinish.isEmpty, "a source finishing with no request outstanding should not resume anything")

let onLateDemand = relay.step(.demandArrived(request: 2))
check(
    onLateDemand == [.resumeWithFinish(request: 2)],
    "a demand arriving after every source has finished should resume immediately, not hang"
)

let idleCancel = Relay(sourceCount: 1)
check(idleCancel.step(.cancelled).isEmpty, "cancelling with nothing outstanding should not resume anything")

let cancelling = Relay(sourceCount: 1)
_ = cancelling.step(.demandArrived(request: 9))
let onCancel = cancelling.step(.cancelled)
check(
    onCancel == [.resumeWithFinish(request: 9)],
    "cancelling while one request is outstanding should resume it"
)

let bufferingThenCancel = Relay(sourceCount: 2)
_ = bufferingThenCancel.step(.demandArrived(request: 5))
_ = bufferingThenCancel.step(.valueProduced(source: .second, value: 7))
_ = bufferingThenCancel.step(.valueProduced(source: .first, value: 3))
let onBufferedCancel = bufferingThenCancel.step(.cancelled)
check(
    onBufferedCancel.isEmpty,
    "cancelling while a value is buffered but no request is outstanding should not resume anything"
)

print("OK: main.swift")
