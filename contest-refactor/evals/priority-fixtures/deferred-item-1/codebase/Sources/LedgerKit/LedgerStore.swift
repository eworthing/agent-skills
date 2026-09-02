import Foundation

public final class LedgerStore {
    private var ledger = Ledger()
    private let fileURL: URL
    private let formatter: DateFormatter

    public init(fileURL: URL) {
        self.fileURL = fileURL
        self.formatter = DateFormatter()
        self.formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ssZ"
        self.formatter.locale = Locale(identifier: "en_US_POSIX")
    }

    public func load() throws {
        guard let text = try? String(contentsOf: fileURL, encoding: .utf8) else { return }
        for line in text.split(separator: "\n") {
            let parts = line.split(separator: ",", omittingEmptySubsequences: false)
            guard parts.count == 4 else { continue }
            guard let date = formatter.date(from: String(parts[1])) else { continue }
            guard let cents = Int(parts[2]) else { continue }
            guard !parts[0].isEmpty else { continue }
            guard parts[3].count <= 140 else { continue }
            ledger.append(Entry(id: String(parts[0]),
                                recordedAt: date,
                                amountCents: cents,
                                memo: String(parts[3])))
        }
    }

    public func save() throws {
        var out = ""
        for entry in ledger.entries {
            out += entry.id + ","
            out += formatter.string(from: entry.recordedAt) + ","
            out += String(entry.amountCents) + ","
            out += entry.memo + "\n"
        }
        try out.write(to: fileURL, atomically: true, encoding: .utf8)
    }

    public func add(id: String, at date: Date, cents: Int, memo: String) throws {
        guard !id.isEmpty else { throw LedgerError.invalidIdentifier }
        guard memo.count <= 140 else { throw LedgerError.memoTooLong }
        ledger.append(Entry(id: id, recordedAt: date, amountCents: cents, memo: memo))
        try save()
    }

    public func displayRows() -> [String] {
        ledger.entries.map { entry in
            let sign = entry.amountCents < 0 ? "-" : ""
            let whole = abs(entry.amountCents) / 100
            let frac = abs(entry.amountCents) % 100
            return "\(formatter.string(from: entry.recordedAt))  \(sign)\(whole).\(String(format: "%02d", frac))  \(entry.memo)"
        }
    }

    public func balance() -> Int { ledger.runningBalance() }
}

public enum LedgerError: Error {
    case invalidIdentifier
    case memoTooLong
}
