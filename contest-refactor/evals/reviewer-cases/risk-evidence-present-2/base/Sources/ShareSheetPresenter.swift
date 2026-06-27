import Foundation
#if os(iOS) || os(tvOS)
import UIKit

/// Presents the system share sheet for arbitrary content.
///
/// Guarded by os(iOS) || os(tvOS) — but UIActivityViewController is iOS-only;
/// the tvOS branch is a latent compile error.  The targeted finding.
final class ShareSheetPresenter {
    private weak var hostViewController: UIViewController?

    init(hostViewController: UIViewController) {
        self.hostViewController = hostViewController
    }

    /// Shows a UIActivityViewController for the provided items.
    /// - Parameters:
    ///   - items: Objects to share (URLs, strings, images, etc.).
    ///   - anchor: Optional bar button item for iPad popover anchoring.
    func present(items: [Any], anchor: UIBarButtonItem? = nil) {
        let sheet = UIActivityViewController(activityItems: items,
                                             applicationActivities: nil)
        if let anchor, let popover = sheet.popoverPresentationController {
            popover.barButtonItem = anchor
        }
        hostViewController?.present(sheet, animated: true)
    }
}
#endif
