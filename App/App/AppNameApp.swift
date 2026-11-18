import SwiftUI

@main
struct AppNameApp: App {
    @State private var adapty = AdaptyManager.shared

    init() {
        Task { await adapty.activate() }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(adapty)
        }
    }
}
