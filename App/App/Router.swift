import SwiftUI

@MainActor
@Observable
final class Router {

    // MARK: - Navigation State

    var path = NavigationPath()
    var sheet: Sheet?
    var fullScreenCover: FullScreenCover?

    // MARK: - Destinations (push navigation)

    /// Add your screens here. Example:
    ///   case profile(userId: String)
    ///   case settings
    ///   case detail(item: Item)
    enum Destination: Hashable {
        // case example
    }

    // MARK: - Sheets (modal)

    /// Add your sheets here. Example:
    ///   case compose
    ///   case picker(PickerType)
    enum Sheet: String, Identifiable {
        case placeholder // remove when adding real cases
        var id: String { rawValue }
    }

    // MARK: - Full Screen Covers

    /// Add your full-screen covers here. Example:
    ///   case onboarding
    ///   case paywall
    ///   case camera
    enum FullScreenCover: String, Identifiable {
        case placeholder // remove when adding real cases
        var id: String { rawValue }
    }

    // MARK: - Actions

    func navigate(to destination: Destination) {
        path.append(destination)
    }

    func pop() {
        guard !path.isEmpty else { return }
        path.removeLast()
    }

    func popToRoot() {
        path = NavigationPath()
    }

    func present(_ sheet: Sheet) {
        self.sheet = sheet
    }

    func presentFullScreen(_ cover: FullScreenCover) {
        self.fullScreenCover = cover
    }

    func dismiss() {
        sheet = nil
        fullScreenCover = nil
    }
}
