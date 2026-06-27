import Foundation
#if os(iOS)
import UIKit

/// Presents the system share sheet for arbitrary content (iOS only).
///
/// tvOS sharing routes through TVShareView; ShareSheetPresenter has no tvOS
/// callsites — confirmed by callsite audit in loop_result.
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
