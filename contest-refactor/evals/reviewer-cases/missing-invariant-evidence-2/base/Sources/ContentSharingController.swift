import Foundation
#if os(iOS) || os(tvOS)
import UIKit

/// Presents the system share sheet for arbitrary content.
///
/// Guarded by os(iOS) || os(tvOS), but UIActivityViewController is iOS-only;
/// the tvOS branch is a latent compile error — UIActivity is unavailable on tvOS.
final class ContentSharingController {
    private weak var hostViewController: UIViewController?

    init(hostViewController: UIViewController) {
        self.hostViewController = hostViewController
    }

    /// Shows a UIActivityViewController for the provided items.
    /// - Parameters:
    ///   - items: Objects to share (URLs, strings, images, etc.).
    ///   - from: Optional bar button item for iPad popover anchoring.
    func present(items: [Any], from barButtonItem: UIBarButtonItem? = nil) {
        let activityVC = UIActivityViewController(activityItems: items,
                                                  applicationActivities: nil)
        if let barButton = barButtonItem,
           let popover = activityVC.popoverPresentationController {
            popover.barButtonItem = barButton
        }
        hostViewController?.present(activityVC, animated: true)
    }
}
#endif
