import SwiftUI

@main
struct AppNameApp: App {
    @State private var adapty = AdaptyManager.shared

    init() {
        // Use the singleton directly: @State isn't installed yet inside App.init()
        Task { await AdaptyManager.shared.activate() }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(adapty)
        }
    }
}
