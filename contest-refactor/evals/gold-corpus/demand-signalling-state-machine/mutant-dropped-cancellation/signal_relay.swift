// A relay that lets one consumer pull values produced by several
// independent sources, coordinated by an explicit phase per
// combination of "is a consumer waiting" and "is a value already
// available" -- rather than a single flag standing in for both.
//
// Source work is started exactly once, the first time any demand
// arrives -- never restarted by a later demand -- and nothing here
// runs on more than one unit of work at a time, so there is no
// broader safety marker to satisfy either.
//
// One deliberate ordering choice this design makes: a pending
// consumer request is never resumed from inside this relay's own
// bookkeeping update. `step` only ever returns *which* requests to
// resume, as data, and leaves actually resuming them to the caller,
// once this call has returned and any lock guarding this relay's own
// state has been released. Resuming a request while still holding
// that lock risks the resumed side re-entering this same relay before
// the lock is free -- keeping "decide what happened" and "resume
// whoever was waiting" as two separate, non-overlapping steps is what
// avoids that.

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

private struct SourceBookkeeping {
    var started: Set<SourceID> = []
    var finished: Set<SourceID> = []
    let total: Int
    var allFinished: Bool { finished.count >= total }
}

final class Relay {
    private enum Phase {
        /// No demand has ever arrived; no source's work has started yet.
        case awaitingFirstDemand(sources: SourceBookkeeping)
        /// A value is already available; no consumer request is
        /// currently outstanding for it.
        case holding(buffered: [Int], sources: SourceBookkeeping)
        /// One or more consumer requests are outstanding; no value is
        /// buffered to satisfy any of them yet.
        case awaitingRequest(requests: [Int], sources: SourceBookkeeping)
        /// Neither a buffered value nor an outstanding request exists,
        /// but at least one source is still live.
        case quiescent(sources: SourceBookkeeping)
        /// Every source has finished and nothing is outstanding.
        case finished
        case cancelled
    }

    private var phase: Phase

    init(sourceCount: Int) {
        phase = .awaitingFirstDemand(sources: SourceBookkeeping(total: sourceCount))
    }

    func step(_ event: RelayEvent) -> [RelayAction] {
        switch (phase, event) {
        case (.awaitingFirstDemand(let sources), .demandArrived(let request)):
            var updated = sources
            let toStart = allSources(sources.total).subtracting(sources.started)
            updated.started.formUnion(toStart)
            phase = .awaitingRequest(requests: [request], sources: updated)
            return toStart.sorted { $0.rawValue < $1.rawValue }.map { .startSourceWork(source: $0) }

        case (.awaitingFirstDemand, .cancelled):
            phase = .cancelled
            return []

        case (.holding(var buffered, let sources), .demandArrived(let request)):
            let value = buffered.removeFirst()
            phase = buffered.isEmpty ? .quiescent(sources: sources) : .holding(buffered: buffered, sources: sources)
            return [.resumeWithValue(request: request, value: value)]

        case (.holding(let buffered, var sources), .sourceFinished(let source)):
            sources.finished.insert(source)
            phase = .holding(buffered: buffered, sources: sources)
            return []

        case (.holding(var buffered, let sources), .valueProduced(_, let value)):
            buffered.append(value)
            phase = .holding(buffered: buffered, sources: sources)
            return []

        case (.holding, .cancelled):
            phase = .cancelled
            return []

        case (.awaitingRequest(var requests, let sources), .demandArrived(let request)):
            requests.append(request)
            phase = .awaitingRequest(requests: requests, sources: sources)
            return []

        case (.awaitingRequest(var requests, let sources), .valueProduced(_, let value)):
            let request = requests.removeFirst()
            phase =
                requests.isEmpty
                ? .quiescent(sources: sources) : .awaitingRequest(requests: requests, sources: sources)
            return [.resumeWithValue(request: request, value: value)]

        case (.awaitingRequest(let requests, var sources), .sourceFinished(let source)):
            sources.finished.insert(source)
            if sources.allFinished {
                phase = .finished
                return requests.map { .resumeWithFinish(request: $0) }
            }
            phase = .awaitingRequest(requests: requests, sources: sources)
            return []

        case (.awaitingRequest, .cancelled):
            phase = .cancelled
            return []

        case (.quiescent(let sources), .demandArrived(let request)):
            phase = .awaitingRequest(requests: [request], sources: sources)
            return []

        case (.quiescent(let sources), .valueProduced(_, let value)):
            phase = .holding(buffered: [value], sources: sources)
            return []

        case (.quiescent(var sources), .sourceFinished(let source)):
            sources.finished.insert(source)
            phase = sources.allFinished ? .finished : .quiescent(sources: sources)
            return []

        case (.quiescent, .cancelled):
            phase = .cancelled
            return []

        case (.finished, .demandArrived(let request)), (.cancelled, .demandArrived(let request)):
            return [.resumeWithFinish(request: request)]

        default:
            return []
        }
    }
}
