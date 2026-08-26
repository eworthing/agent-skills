// A relay that lets one consumer pull values produced by several
// independent sources. Each time the consumer signals demand, this
// relay spins up a fresh unit of work per source still in play to
// satisfy it, rather than reusing work already started by an earlier
// demand.
//
// Because that per-demand work reaches into the relay's own buffered
// state, the relay itself has to be safe to share across those
// independently-scheduled units of work.

/// Marks a type as safe to share across independently-scheduled units
/// of work that may run concurrently with one another.
protocol ConcurrencySafe {}

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

final class Relay: ConcurrencySafe {
    private enum Phase {
        case running(buffered: [Int], requests: [Int], finishedSources: Set<SourceID>)
        case finished
        case cancelled
    }

    private var phase: Phase
    private let total: Int

    init(sourceCount: Int) {
        total = sourceCount
        phase = .running(buffered: [], requests: [], finishedSources: [])
    }

    func step(_ event: RelayEvent) -> [RelayAction] {
        if case .demandArrived(let request) = event, isTerminal {
            return [.resumeWithFinish(request: request)]
        }

        switch phase {
        case .finished, .cancelled:
            return []

        case .running(var buffered, var requests, var finishedSources):
            switch event {
            case .demandArrived(let request):
                let live = allSources(total).subtracting(finishedSources)
                let restart = live.sorted { $0.rawValue < $1.rawValue }.map {
                    RelayAction.startSourceWork(source: $0)
                }
                if !buffered.isEmpty {
                    let value = buffered.removeFirst()
                    phase = .running(buffered: buffered, requests: requests, finishedSources: finishedSources)
                    return [.resumeWithValue(request: request, value: value)] + restart
                }
                requests.append(request)
                phase = .running(buffered: buffered, requests: requests, finishedSources: finishedSources)
                return restart

            case .valueProduced(_, let value):
                if !requests.isEmpty {
                    let request = requests.removeFirst()
                    phase = .running(buffered: buffered, requests: requests, finishedSources: finishedSources)
                    return [.resumeWithValue(request: request, value: value)]
                }
                buffered.append(value)
                phase = .running(buffered: buffered, requests: requests, finishedSources: finishedSources)
                return []

            case .sourceFinished(let source):
                finishedSources.insert(source)
                if finishedSources.count >= total && buffered.isEmpty {
                    let toResume = requests
                    phase = .finished
                    return toResume.map { .resumeWithFinish(request: $0) }
                }
                phase = .running(buffered: buffered, requests: requests, finishedSources: finishedSources)
                return []

            case .cancelled:
                phase = .cancelled
                return requests.map { .resumeWithFinish(request: $0) }
            }
        }
    }

    private var isTerminal: Bool {
        if case .running = phase { return false }
        return true
    }
}
