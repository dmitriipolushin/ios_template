---
description: "iOS-specific implementation from speckit tasks. Extends /speckit.implement with XcodeGen, SPM, simulator builds, SwiftUI patterns, and iOS validation. Use when: 'implement', 'build feature', 'start coding', 'implement spec'."
---

# iOS Implementation from Spec

Execute the speckit task plan with iOS-specific toolchain awareness.
This command wraps the speckit workflow with Xcode/SwiftUI/iOS knowledge.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Phase 0: iOS Environment Check

Before touching any task, verify the iOS toolchain:

```bash
# Xcode
xcodebuild -version 2>/dev/null || echo "NO_XCODE"

# XcodeGen (required for this template)
which xcodegen 2>/dev/null || echo "NO_XCODEGEN"

# SwiftLint (optional)
which swiftlint 2>/dev/null || echo "NO_SWIFTLINT"

# Simulators available
xcrun simctl list devices available | grep "iPhone" | head -5

# Current project.yml
cat project.yml 2>/dev/null | head -5
```

If `xcodegen` is missing:
```
⚠️ XcodeGen not installed. Install with: brew install xcodegen
This project uses project.yml instead of .xcodeproj — XcodeGen is required.
```
STOP and ask user to install.

## Phase 1: Load Speckit Context

Run the standard speckit prerequisite check:
```bash
.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
```

Parse FEATURE_DIR and AVAILABLE_DOCS. Read all available artifacts:
- **REQUIRED**: `tasks.md`, `plan.md`
- **IF EXISTS**: `data-model.md`, `contracts/`, `research.md`, `quickstart.md`
- **IF EXISTS**: `checklists/` — check completion status, ask user if incomplete

Also read the project's iOS-specific files:
- `project.yml` — current XcodeGen config (packages, targets, settings)
- `App/Services/` directory — existing template services (AdaptyManager, OpenAIClient, KeychainHelper)
- `CLAUDE.md` — project rules and constraints

## Phase 2: Plan iOS Structure

Before executing tasks, map the speckit plan to iOS file structure:

```
App/
├── App/                    # @main entry point, AppDelegate
├── Features/
│   └── <FeatureName>/
│       ├── <Feature>View.swift
│       ├── <Feature>ViewModel.swift
│       └── Components/     # Feature-specific subviews
├── Models/                 # SwiftData models, domain entities
├── Services/               # Business logic, API services
├── Shared/
│   ├── Components/         # Reusable SwiftUI components
│   ├── Extensions/         # Swift extensions
│   └── Utilities/          # Helpers
└── Resources/
    ├── Assets.xcassets/
    └── Localizable.xcstrings
```

**Naming conventions:**
- Views: `FeatureNameView.swift`
- ViewModels: `FeatureNameViewModel.swift`
- Models: `EntityName.swift` (singular)
- Services: `EntityNameService.swift` or `FeatureNameService.swift`

## Phase 3: Execute Tasks

Process tasks from `tasks.md` phase by phase. For each task, apply iOS-specific patterns.

### For Model/Entity tasks:

Use SwiftData with `@Model`:
```swift
import SwiftData

@Model
final class EntityName {
    var property: Type
    var relationship: [RelatedEntity]
    var createdAt: Date

    init(property: Type) {
        self.property = property
        self.createdAt = .now
    }
}
```

Cross-reference with `data-model.md` for fields, relationships, validation rules.

### For ViewModel tasks:

Always use `@Observable` + `@MainActor`:
```swift
import SwiftUI

@MainActor
@Observable
final class FeatureViewModel {
    // MARK: - State
    var items: [Item] = []
    var isLoading = false
    var error: String?

    // MARK: - Dependencies
    private let service: ServiceProtocol

    init(service: ServiceProtocol) {
        self.service = service
    }

    // MARK: - Actions
    func load() async {
        isLoading = true
        defer { isLoading = false }

        do {
            items = try await service.fetchItems()
        } catch {
            self.error = error.localizedDescription
        }
    }
}
```

### For View tasks:

SwiftUI views with proper state management:
```swift
struct FeatureView: View {
    @State private var viewModel: FeatureViewModel

    init(service: ServiceProtocol) {
        _viewModel = State(initialValue: FeatureViewModel(service: service))
    }

    var body: some View {
        content
            .task { await viewModel.load() }
    }

    @ViewBuilder
    private var content: some View {
        if viewModel.isLoading {
            ProgressView()
        } else if let error = viewModel.error {
            ContentUnavailableView("Error", systemImage: "exclamationmark.triangle", description: Text(error))
        } else if viewModel.items.isEmpty {
            ContentUnavailableView("No Items", systemImage: "tray", description: Text("Nothing here yet"))
        } else {
            itemsList
        }
    }
}
```

**Mandatory view patterns:**
- `.task { }` for async loading (NOT `onAppear` + `Task { }`)
- Three states: loading (`ProgressView`), empty (`ContentUnavailableView`), error (`ContentUnavailableView`)
- `@ViewBuilder` for conditional content
- Extract subviews when body > 40 lines

### For Service tasks:

Protocol + Implementation pattern:
```swift
protocol FeatureServiceProtocol: Sendable {
    func fetchItems() async throws -> [Item]
}

final class FeatureService: FeatureServiceProtocol {
    private let client: OpenAIClient  // or URLSession, SwiftData context, etc.

    init(client: OpenAIClient) {
        self.client = client
    }

    func fetchItems() async throws -> [Item] {
        // Implementation
    }
}
```

### For Navigation tasks:

Use `NavigationStack` + Router pattern:
```swift
@MainActor
@Observable
final class Router {
    var path = NavigationPath()

    enum Destination: Hashable {
        case featureDetail(id: String)
        case settings
    }

    func navigate(to destination: Destination) {
        path.append(destination)
    }

    func popToRoot() {
        path = NavigationPath()
    }
}
```

### For Subscription/Paywall tasks:

Use the template's `AdaptyManager` from `Base/Subscription/`:
```swift
// Check premium status
if adaptyManager.isPremium {
    // Premium feature
} else {
    // Show paywall
    adaptyManager.showPaywall = true
}
```

### For AI/OpenAI tasks:

Use the template's `OpenAIClient` from `Base/OpenAI/`:
```swift
let client = OpenAIClient()
let response = try await client.complete(
    system: "System prompt here",
    user: userInput,
    temperature: 0.7,
    maxTokens: 1000,
    jsonMode: true
)
let parsed = response.decodeJSON(as: MyResponse.self)
```

## Phase 4: Build Validation (after each phase)

After completing each task phase, validate:

### 1. Update project.yml if new files/packages added

If a task creates new Swift files, verify they're in a directory that `project.yml` sources include.
If a task adds a new SPM dependency:

```yaml
# Add to packages: section
packages:
  NewPackage:
    url: https://github.com/owner/repo
    from: "X.Y.Z"

# Add to target dependencies:
dependencies:
  - package: NewPackage
    product: ProductName
```

### 2. Regenerate Xcode project

```bash
xcodegen generate 2>&1
```

If this fails, fix `project.yml` before continuing.

### 3. Build check

```bash
xcodebuild build \
  -scheme "$(xcodebuild -list -json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['project']['schemes'][0])" 2>/dev/null || echo 'AppName')" \
  -destination "platform=iOS Simulator,name=iPhone 16" \
  -quiet \
  2>&1 | tail -30
```

If build fails:
1. Read the compiler errors
2. Fix the issue in the source file
3. Rebuild
4. If stuck after 3 attempts, report the error and move to next task

### 4. Mark task complete

Update `tasks.md`: change `- [ ]` to `- [x]` for the completed task.

## Phase 5: iOS-Specific Validation (after all tasks)

### SwiftData schema check
If models were created/modified:
```bash
# Verify all @Model classes have proper init
grep -rn "@Model" App/ --include="*.swift" -A5
```

### Accessibility check
```bash
# Verify images have accessibility
grep -rn 'Image(' App/ --include="*.swift" | grep -v 'accessibilityLabel\|accessibilityHidden\|systemName'
```

### Dark mode check
```bash
# Flag hard-coded colors
grep -rn 'Color\.black\|Color\.white\|Color(red:' App/ --include="*.swift"
```

### Dynamic Type check
```bash
# Flag fixed font sizes
grep -rn '\.font(\.system(size:' App/ --include="*.swift"
```

Report any violations as warnings (don't auto-fix unless task explicitly requires it).

## Phase 6: Final Report

```
## Implementation Complete

**Feature:** [feature name from spec]
**Branch:** [current branch]
**Tasks:** X/Y completed

### Files Created/Modified
- App/Features/Feature/FeatureView.swift (new)
- App/Models/Entity.swift (new)
- project.yml (modified: added dependency)
- ...

### Build Status
- ✅ XcodeGen: project generated successfully
- ✅ Build: compiles without errors
- ⚠️ Warnings: N compiler warnings

### iOS Validation
- Accessibility: X images without labels
- Dark Mode: X hard-coded colors
- Dynamic Type: X fixed font sizes

### Next Steps
- [ ] Run /ios-qa to test the implementation
- [ ] Run /ios-design-review to audit HIG compliance
- [ ] Run /ios-review before merging
```

## Rules

### Code patterns (MANDATORY)
- `@Observable` + `@MainActor` on all ViewModels
- Protocol-based DI for all services
- `.task { }` modifier, never `onAppear` + `Task { }`
- `[weak self]` in stored closures
- Three view states: loading, empty, error
- SwiftData `@Model` for persistence
- `async/await` — no Combine unless explicitly in spec
- No force unwraps (`!`) except `URL(string: "literal")!`

### File organization
- One type per file (exceptions: small helper types in same file)
- Feature folders: `Features/FeatureName/`
- Shared components: `Shared/Components/`
- Use `// MARK: -` sections in files > 50 lines

### Dependencies
- Always add via `project.yml` packages section, never manually
- Run `xcodegen generate` after any `project.yml` change
- Verify build after adding dependencies

### What NOT to do
- Don't create .xcodeproj manually — XcodeGen handles this
- Don't add files to Xcode groups — XcodeGen auto-discovers from source directories
- Don't use storyboards or XIBs — SwiftUI only
- Don't use UIKit unless wrapping a system component not available in SwiftUI
- Don't commit DerivedData, .build, or .xcodeproj
