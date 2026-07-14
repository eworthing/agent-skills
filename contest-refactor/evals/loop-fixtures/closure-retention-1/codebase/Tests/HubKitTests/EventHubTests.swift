import XCTest

@testable import HubKit

final class EventHubTests: XCTestCase {
    func testPublishDeliversPayloadToSubscriber() {
        let hub = EventHub()
        let pipeline = ImagePipeline(stageName: "resize", frameBuffer: [1, 2, 3], hub: hub)
        hub.publish("flush", payload: "cycle-1")
        XCTAssertEqual(pipeline.log, ["resize flushed: cycle-1"])
    }

    func testPublishReachesEverySubscriber() {
        let hub = EventHub()
        let first = ImagePipeline(stageName: "resize", frameBuffer: [1], hub: hub)
        let second = ImagePipeline(stageName: "encode", frameBuffer: [2], hub: hub)
        hub.publish("flush", payload: "cycle-2")
        XCTAssertEqual(first.log, ["resize flushed: cycle-2"])
        XCTAssertEqual(second.log, ["encode flushed: cycle-2"])
    }

    func testRepeatedPublishesAppendToLogInOrder() {
        let hub = EventHub()
        let pipeline = ImagePipeline(stageName: "resize", frameBuffer: [1], hub: hub)
        hub.publish("flush", payload: "cycle-1")
        hub.publish("flush", payload: "cycle-2")
        XCTAssertEqual(pipeline.log, ["resize flushed: cycle-1", "resize flushed: cycle-2"])
    }

    func testPublishUnknownEventIsNoOp() {
        let hub = EventHub()
        let pipeline = ImagePipeline(stageName: "resize", frameBuffer: [1], hub: hub)
        hub.publish("shutdown", payload: "cycle-3")
        XCTAssertEqual(pipeline.log, [])
    }

    func testCropFramesRunsCompletionOnce() {
        let hub = EventHub()
        let pipeline = ImagePipeline(stageName: "resize", frameBuffer: [1, 2, 3, 4, 5], hub: hub)
        var reportedCounts: [Int] = []
        pipeline.cropFrames(to: 2) { count in
            reportedCounts.append(count)
        }
        XCTAssertEqual(reportedCounts, [2])
        XCTAssertEqual(pipeline.frameBuffer, [1, 2])
    }
}
