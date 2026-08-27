// A relay that lets one consumer pull values produced by several
// independent sources. Demand and delivery are tracked with a single
// suspended flag plus one held slot for whatever is currently
// pending.

enum SourceID: Int, Hashable {
    case first = 0
    case second = 1
}

func allSources(_ count: Int) -> Set<SourceID> {
    Set((0..<count).compactMap { SourceID(rawValue: $0) })
}

enum RelayEvent {
    case demandArrived(request: Int)
    case valueProduced(source: SourceID, value: Int)
    case sourceFinished(source: SourceID)
    case cancelled
}

enum RelayAction: Equatable {
    case resumeWithValue(request: Int, value: Int)
    case resumeWithFinish(request: Int)
    case startSourceWork(source: SourceID)
}

final class Relay {
    private var isSuspended = false
    private var pendingRequest: Int?
    private var pendingValue: Int?
    private var startedSources: Set<SourceID> = []
    private var finishedSources: Set<SourceID> = []
    private let total: Int
    private var isFinished = false
    private var isCancelled = false

    init(sourceCount: Int) {
        // SourceID enumerates every source this relay can represent. A caller
        // asking for more than that would leave the finished-count target
        // permanently out of reach, because the surplus sources can never
        // report finishing, so count what is actually representable.
        total = allSources(sourceCount).count
    }

    func step(_ event: RelayEvent) -> [RelayAction] {
        if case .demandArrived(let request) = event, isFinished || isCancelled {
            return [.resumeWithFinish(request: request)]
        }
        if isFinished || isCancelled {
            return []
        }

        switch event {
        case .demandArrived(let request):
            if let value = pendingValue {
                pendingValue = nil
                return [.resumeWithValue(request: request, value: value)]
            }
            let needsStart = startedSources.isEmpty
            isSuspended = true
            pendingRequest = request
            guard needsStart else { return [] }
            let toStart = allSources(total)
            startedSources = toStart
            return toStart.sorted { $0.rawValue < $1.rawValue }.map { .startSourceWork(source: $0) }

        case .valueProduced(_, let value):
            if isSuspended, let request = pendingRequest {
                isSuspended = false
                pendingRequest = nil
                return [.resumeWithValue(request: request, value: value)]
            }
            pendingValue = value
            return []

        case .sourceFinished(let source):
            finishedSources.insert(source)
            guard finishedSources.count >= total else { return [] }
            isFinished = true
            if isSuspended, let request = pendingRequest {
                isSuspended = false
                pendingRequest = nil
                return [.resumeWithFinish(request: request)]
            }
            return []

        case .cancelled:
            isCancelled = true
            if isSuspended, let request = pendingRequest {
                isSuspended = false
                pendingRequest = nil
                return [.resumeWithFinish(request: request)]
            }
            return []
        }
    }
}
