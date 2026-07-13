import HubKit

let hub = EventHub()
let pipeline = ImagePipeline(stageName: "resize", frameBuffer: [1, 2, 3, 4], hub: hub)
hub.publish("flush", payload: "cycle-start")
pipeline.cropFrames(to: 2) { count in
    print("cropped to \(count) frames")
}
for entry in pipeline.log {
    print(entry)
}
