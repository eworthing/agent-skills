import Foundation
import Testing
@testable import LedgerKit

@Test func runningBalanceSumsAmounts() {
    var ledger = Ledger()
    ledger.append(Entry(id: "a", recordedAt: Date(timeIntervalSince1970: 10), amountCents: 250, memo: "one"))
    ledger.append(Entry(id: "b", recordedAt: Date(timeIntervalSince1970: 20), amountCents: -100, memo: "two"))
    #expect(ledger.runningBalance() == 150)
}

@Test func appendKeepsEveryEntry() {
    var ledger = Ledger()
    ledger.append(Entry(id: "b", recordedAt: Date(timeIntervalSince1970: 20), amountCents: 1, memo: "x"))
    ledger.append(Entry(id: "a", recordedAt: Date(timeIntervalSince1970: 10), amountCents: 2, memo: "y"))
    #expect(ledger.entries.count == 2)
}

@Test func negativeAmountsFormatWithSign() {
    let url = FileManager.default.temporaryDirectory.appendingPathComponent("l1.csv")
    let store = LedgerStore(fileURL: url)
    try? store.add(id: "a", at: Date(timeIntervalSince1970: 0), cents: -1250, memo: "refund")
    #expect(store.displayRows().first?.contains("-12.50") == true)
}

@Test func emptyIdentifierIsRejected() {
    let url = FileManager.default.temporaryDirectory.appendingPathComponent("l2.csv")
    let store = LedgerStore(fileURL: url)
    #expect(throws: LedgerError.self) {
        try store.add(id: "", at: Date(), cents: 1, memo: "x")
    }
}

@Test func overlongMemoIsRejected() {
    let url = FileManager.default.temporaryDirectory.appendingPathComponent("l3.csv")
    let store = LedgerStore(fileURL: url)
    #expect(throws: LedgerError.self) {
        try store.add(id: "a", at: Date(), cents: 1, memo: String(repeating: "z", count: 141))
    }
}
