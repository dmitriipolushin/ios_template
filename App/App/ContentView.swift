import SwiftUI

struct ContentView: View {
    @State private var router = Router()

    var body: some View {
        NavigationStack(path: $router.path) {
            Text("Hello, World!")
                .font(.largeTitle)
                .navigationTitle("AppName")
                .navigationDestination(for: Router.Destination.self) { destination in
                    switch destination {
                    case .placeholder: EmptyView()
                    }
                }
        }
        .sheet(item: $router.sheet) { sheet in
            switch sheet {
            case .placeholder: EmptyView()
            }
        }
        .fullScreenCover(item: $router.fullScreenCover) { cover in
            switch cover {
            case .placeholder: EmptyView()
            }
        }
        .environment(router)
    }
}

#Preview {
    ContentView()
}
