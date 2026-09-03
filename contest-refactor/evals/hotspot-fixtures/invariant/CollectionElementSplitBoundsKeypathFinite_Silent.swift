import Foundation

// Post-fix PlaybackSpec.init shape: finite check through a keypath closure,
// a `$0.`-prefixed right operand, and each field's two bounds split across
// separate allSatisfy guards. Every field ends up two-sided and finite, so
// the invariant queue must stay silent.
struct Dropout {
    let startSeconds: Double
    let endSeconds: Double
    let fadeInSeconds: Double
    let fadeOutSeconds: Double

    var durationSeconds: Double { endSeconds - startSeconds }
}

struct PlaybackSpec {
    let dropouts: [Dropout]

    init(dropouts: [Dropout]) throws {
        let isFinite = { (dropout: Dropout) in
            [dropout.startSeconds, dropout.endSeconds, dropout.fadeInSeconds, dropout.fadeOutSeconds]
                .allSatisfy(\.isFinite)
        }
        guard dropouts.allSatisfy(isFinite) else {
            throw SpecError.nonFinite
        }
        guard dropouts.allSatisfy({ $0.endSeconds >= $0.startSeconds }) else {
            throw SpecError.inverted
        }
        guard dropouts.allSatisfy({ $0.startSeconds >= 0 }) else {
            throw SpecError.negativeStart
        }
        guard dropouts.allSatisfy({ $0.fadeInSeconds >= 0 && $0.fadeOutSeconds >= 0 }) else {
            throw SpecError.negativeFade
        }
        guard
            dropouts.allSatisfy({ dropout in
                let halfRegion = dropout.durationSeconds / 2
                return dropout.fadeInSeconds <= halfRegion && dropout.fadeOutSeconds <= halfRegion
            })
        else {
            throw SpecError.fadeTooLong
        }
        self.dropouts = dropouts
    }
}

enum SpecError: Error {
    case nonFinite
    case inverted
    case negativeStart
    case negativeFade
    case fadeTooLong
}
