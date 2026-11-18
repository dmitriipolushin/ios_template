---
description: "iOS QA testing. Builds, runs tests, audits code for crashes/security/concurrency/memory/SwiftUI bugs/hit testing/dark mode/flow logic/navigation/keyboard/accessibility/performance/render loops/App Store rejection/spec compliance/dead code. Three tiers: quick, standard, exhaustive. Use when: 'qa', 'test the app', 'find bugs', 'run QA'."
---

# iOS QA

Systematically QA test an iOS application. Combines build verification, test execution,
static analysis (crash/security/concurrency/memory/SwiftUI/hit testing/dark mode/flow logic/
navigation/keyboard/accessibility/performance/render loops patterns),
spec compliance checking, dead code detection, App Store rejection risk audit, and dependency audit.

## Arguments

$ARGUMENTS — optional: tier (quick|standard|exhaustive), specific feature/screen to test.
Default tier: standard.

---

## Phase 1: Environment & Context

### 1.1 Detect toolchain

```bash
xcodebuild -version 2>/dev/null || echo "NO_XCODE"
xcrun simctl list devices available | grep -E "iPhone|iPad" | head -10
which swiftlint 2>/dev/null || echo "NO_SWIFTLINT"
```

### 1.2 Detect project type

```bash
ls project.yml 2>/dev/null && echo "XCODEGEN"
ls *.xcworkspace 2>/dev/null
ls *.xcodeproj 2>/dev/null
ls Package.swift 2>/dev/null
```

If `project.yml` exists → `xcodegen generate` first.

### 1.3 Detect scheme

```bash
xcodebuild -list 2>/dev/null
```

### 1.4 Load spec context (if available)

Check for speckit artifacts to enable spec compliance checking:

```bash
ls .specify/features/*/spec.md 2>/dev/null
ls .specify/features/*/tasks.md 2>/dev/null
ls .specify/features/*/plan.md 2>/dev/null
ls specs/*/spec.md 2>/dev/null
ls specs/*/tasks.md 2>/dev/null
ls specs/*/plan.md 2>/dev/null
```

If spec exists → load requirements for Phase 7 compliance check.

Also check for CLAUDE.md project rules:
```bash
ls CLAUDE.md 2>/dev/null && head -100 CLAUDE.md
```

---

## Phase 2: Build Verification

```bash
xcodebuild build \
  -scheme "<SCHEME>" \
  -destination "platform=iOS Simulator,name=iPhone 16" \
  -quiet \
  2>&1 | tail -30
```

If build **fails**:
1. Read the full error output
2. Report as CRITICAL finding with exact compiler message
3. **STOP** — all other phases require a successful build
4. Attempt fix if straightforward (missing import, typo), rebuild, continue
5. If 2 fix attempts fail → STOP and report per CLAUDE.md escalation rules

If build **succeeds** with warnings:
```bash
xcodebuild build \
  -scheme "<SCHEME>" \
  -destination "platform=iOS Simulator,name=iPhone 16" \
  2>&1 | grep -E "warning:" | sort | uniq -c | sort -rn | head -20
```
Report each unique warning as LOW finding.

---

## Phase 3: Run Tests

### 3.1 Unit tests

```bash
xcodebuild test \
  -scheme "<SCHEME>" \
  -destination "platform=iOS Simulator,name=iPhone 16" \
  -only-testing:"<TARGET>Tests" \
  -quiet \
  2>&1 | tail -50
```

Parse: passed / failed / skipped. Each failure → finding with test name, assertion, file:line.

### 3.2 UI tests (if exist)

```bash
xcodebuild test \
  -scheme "<SCHEME>" \
  -destination "platform=iOS Simulator,name=iPhone 16" \
  -only-testing:"<TARGET>UITests" \
  -quiet \
  2>&1 | tail -50
```

### 3.3 SwiftLint (if available)

```bash
swiftlint lint --reporter json 2>/dev/null | head -200
```

Parse violations by severity. Each error-level → HIGH finding, warning-level → LOW.

---

## Phase 4: Static Analysis — Crash Risks

**Scan all `.swift` files excluding tests, mocks, generated code, and third-party.**

Use Grep tool for all pattern searches below. Never scan files matching:
`*Test*`, `*Mock*`, `*Stub*`, `*Generated*`, `Pods/*`, `.build/*`, `DerivedData/*`

### 4.1 CRITICAL — Runtime Crashes

| ID | Pattern | Grep | Risk |
|---|---|---|---|
| C01 | Force unwrap | `!\.' and '!,` and `![^=]` after optionals | Crash on nil |
| C02 | Force cast | `as!` | Crash on type mismatch |
| C03 | Force try | `try!` | Crash on throw |
| C04 | Array index access | `\[\w+\]` without bounds check | Index out of range |
| C05 | Unowned reference | `\[unowned` | Crash if deallocated |
| C06 | Implicitly unwrapped optional | `var \w+:\s*\w+!` (not IBOutlet) | Crash on access |
| C07 | Missing @unknown default | `switch` on system enum without it | Crash on future case |
| C08 | Main thread deadlock | `DispatchQueue\.main\.sync` | Deadlock from main |
| C09 | Division by zero | `/\s*\w+` where divisor could be 0 | Arithmetic crash |

**Grep commands for C01-C03:**
```
Pattern: as!
Pattern: try!
Pattern: !\. (excluding !=, !==, and comments)
```

For each match: read surrounding context (5 lines before/after) to verify it's a real risk, not a URL literal or test assertion.

### 4.2 HIGH — Security & Data Loss

| ID | Pattern | Grep | Risk |
|---|---|---|---|
| S01 | Hardcoded API keys | `sk-\|api_key\|bearer\|secret.*=.*"` | Key in binary |
| S02 | HTTP (not HTTPS) | `http://` (not localhost) | Insecure transport |
| S03 | Hardcoded IP address | `\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}` | IPv6 fail + hardcoded endpoint |
| S04 | UserDefaults for secrets | `UserDefaults.*token\|password\|secret\|apiKey` | Plain-text storage |
| S05 | NSAllowsArbitraryLoads | `NSAllowsArbitraryLoads.*true\|YES` | ATS disabled |
| S06 | Missing save after mutation | `context.insert` without `context.save()` nearby | Data loss on crash |
| S07 | Silent error swallowing | `catch\s*\{\s*\}` (empty catch) | Hidden failures |
| S08 | Print in production | `print\(` (not in #if DEBUG) | Data leak to console |

---

## Phase 5: Static Analysis — Concurrency & Memory

### 5.1 MEDIUM — Concurrency Issues

| ID | Pattern | Grep | Issue |
|---|---|---|---|
| T01 | ViewModel without @MainActor | `@Observable.*class.*ViewModel` without `@MainActor` | UI updates off main thread |
| T02 | Task in onAppear | `.onAppear` followed by `Task {` within 3 lines | No auto-cancellation |
| T03 | Non-final non-Sendable class | `^class ` without `final\|@MainActor\|Sendable` | Data race in Swift 6 |
| T04 | Static mutable state | `static var` (not `static let`) | Global data race |
| T05 | Task.detached | `Task\.detached` | Loses actor context |
| T06 | @Published without @MainActor | `@Published` in class without `@MainActor` | Background publish crash |
| T07 | Unstructured Task in View | `Task\s*\{` inside View body or onAppear | Outlives view lifecycle |

**Grep for T01 (ViewModel pattern):**
Read each file matching `*ViewModel.swift`. Check that class declaration has both `@MainActor` and `@Observable`. Report any that don't.

### 5.2 MEDIUM — Memory Leaks

| ID | Pattern | Grep | Issue |
|---|---|---|---|
| M01 | Strong delegate | `var delegate:` without `weak` | Retain cycle |
| M02 | Timer without weak self | `Timer.scheduledTimer` → check next 3 lines for `[weak self]` | Timer retains target |
| M03 | Combine sink without weak self | `.sink\s*\{` without `[weak self]` | Subscriber retains |
| M04 | NotificationCenter without removal | `addObserver(forName` without matching `removeObserver` | Observer leak |
| M05 | Closure property on class | `var \w+:\s*\(.*\) ->` in class | Potential retain cycle |
| M06 | Strong self in Task | `Task {` with `self.` without `[weak self]` | Extends object lifetime |

**For M01 — verify delegate pattern:**
```
Search: var delegate:
Exclude: weak var delegate
Each non-weak delegate → MEDIUM finding
```

---

## Phase 6: Static Analysis — SwiftUI Patterns

### 6.1 MEDIUM — SwiftUI Bugs

| ID | Pattern | Grep | Issue |
|---|---|---|---|
| U01 | @StateObject with @Observable | `@StateObject` (in iOS 17+ project) | Wrong property wrapper |
| U02 | Multiple sheets same view | File has >1 `.sheet(` modifier | Only last works (pre-16.4) |
| U03 | ForEach with \.self | `ForEach.*\.self` on non-Identifiable types | Unstable identity → full re-render |
| U04 | .task without error handling | `.task {` without `try` or `catch` within 10 lines | Cancellation not handled |
| U05 | NavigationView (deprecated) | `NavigationView` | Should use NavigationStack |
| U06 | ObservableObject in iOS 17+ | `ObservableObject` + `@Published` | Should use @Observable |

### 6.2 LOW — UX States

For each screen/feature view, verify presence of all three states:

| ID | Check | How | Issue |
|---|---|---|---|
| X01 | Loading state | `ProgressView` exists in file | User sees blank on load |
| X02 | Empty state | `ContentUnavailableView` or `\.isEmpty` check | Confusing blank screen |
| X03 | Error state | `error` or `Error` display after catch | Silent failure |
| X04 | Keyboard dismiss | `.scrollDismissesKeyboard` or `focused` or `.toolbar.*keyboard` | Keyboard stuck |
| X05 | Pull to refresh | `.refreshable` if view has async data load | No way to refresh |

**How to check:** For each `*View.swift` that contains `.task {` or `onAppear`:
1. Check for ProgressView → if missing, report X01
2. Check for empty state handling → if missing, report X02
3. Check for error display → if missing, report X03

### 6.3 HIGH — Hit Testing & Interaction Bugs

**Why:** `.clipped()` and `.clipShape()` only clip visuals, NOT hit-test area. This causes invisible tap zones that block buttons, navigation, and gestures. [Reference: oleb.net/2022/clipped-hit-testing](https://oleb.net/2022/clipped-hit-testing/)

| ID | Pattern | Grep | Issue |
|---|---|---|---|
| H01 | `.scaledToFill()` + `.clipped()` without `.contentShape()` | Search `scaledToFill` → read ±5 lines → verify `contentShape(Rectangle())` exists | Tap area extends beyond visible frame, blocks buttons behind/above |
| H02 | Decorative `.overlay(` without `.allowsHitTesting(false)` | Search `.overlay(` containing `LinearGradient`, `Color.`, or `Blur` → check for `.allowsHitTesting(false)` | Overlay intercepts taps meant for views underneath |
| H03 | `.highPriorityGesture` on `ScrollView`/`List` | Search `highPriorityGesture` near `ScrollView` or `List` | Scrolling stops working |
| H04 | `.simultaneousGesture` with `DragGesture` in `ScrollView` | Search `simultaneousGesture` + `Drag` in same context | Gesture conflict breaks scroll |

**How to check H01:**
1. Grep for `scaledToFill`
2. For each match, read surrounding 10 lines
3. If `.clipped()` or `.clipShape()` is present but NO `.contentShape(Rectangle())` → report HIGH
4. Especially dangerous when the image is near interactive elements (buttons, navigation bars)

**How to check H02:**
1. Grep for `.overlay(`
2. For each match, check if overlay content is decorative (gradient, color, blur)
3. If decorative overlay has NO `.allowsHitTesting(false)` → report HIGH
4. Verify by checking if interactive elements exist underneath the overlay

### 6.4 MEDIUM — Dark Mode & Color Contrast

**Why:** `.preferredColorScheme()` does NOT propagate to all system components (DatePicker, confirmationDialog). [Reference: HWS forums](https://www.hackingwithswift.com/forums/swiftui/preferredcolorscheme-not-affecting-datepicker-and-confirmationdialog/11796)

| ID | Pattern | Grep | Issue |
|---|---|---|---|
| V01 | `DatePicker` `.wheel` on dark background without explicit colorScheme | Search `datePickerStyle(.wheel)` → check if `.colorScheme(.dark)` or `.environment(\.colorScheme` exists within 5 lines | Wheel text invisible on dark background |
| V02 | `.foregroundStyle(.gray)` on `Color.black` background | Search `.foregroundStyle(.gray)` in files that contain `Color.black` as background | Insufficient contrast ratio |
| V03 | System components (Picker, DatePicker, Toggle) in forced color scheme without explicit override | Search `Picker\|DatePicker\|Toggle` in views with `.preferredColorScheme(.dark)` but no per-component `.colorScheme` | Component uses system theme, ignoring parent override |

### 6.5 HIGH — Flow Logic & State Machine

**Why:** Enum-based flows (onboarding, wizards) often have mismatched initial state, skipped analytics, or broken back-navigation. These bugs are invisible to grep-only analysis — requires reading the flow logic.

| ID | Pattern | How to check | Issue |
|---|---|---|---|
| F01 | Enum `CaseIterable` with `@State` NOT initialized to first case | Find enums conforming to `CaseIterable` → find `@State` variable of that type → compare initial value with `.allCases.first` | Steps/screens skipped in the flow |
| F02 | Analytics tracked in `onChange` but NOT in `onAppear` | Search for `onChange.*track\|onChange.*Analytics\|onChange.*Amplitude` → verify matching `onAppear` tracking exists | First screen/state never tracked |
| F03 | Auto-advance on selection without re-selectable back state | Read quiz/option views where `onSelect` immediately calls `onNext()` → check if going back allows re-selection | User can't change answer after going back |
| F04 | Flow navigation without bounds check | Read `goNext()`/`goBack()` functions → verify they check array bounds | Crash on first/last step |

**How to check F01-F02 (mandatory for flows):**
1. Find all enums with `CaseIterable` in onboarding/wizard/flow files
2. Find the `@State` property that uses this enum
3. If initial value ≠ first enum case → report HIGH (skipped steps)
4. Find all analytics tracking calls in `onChange(of:)` → verify matching `onAppear` call exists
5. If `onAppear` tracking is missing → report HIGH (first event lost)

### 6.6 MEDIUM — Navigation & Modal Bugs

**Why:** Known SwiftUI platform bugs that cause crashes, memory leaks, or broken animations in specific modifier combinations.

| ID | Pattern | Grep | Issue |
|---|---|---|---|
| N01 | Navigation push immediately after `.sheet`/`.fullScreenCover` dismiss | Search for `dismiss()` followed by navigation within 10 lines | Animation loss on iOS 16 |
| N02 | `.searchable` + `.refreshable` on same view | Search for files containing both `searchable` and `refreshable` | Memory leak — retain cycle (Apple FB10640905) |
| N03 | `ForEach` with `Binding` + animated deletion of last element | Search `ForEach.*\$` with `.onDelete` modifier | Crash when last element deleted with animation |
| N04 | Multiple `.fullScreenCover` on same view | File has >1 `.fullScreenCover(` modifier | Only last one works, others silently ignored |

### 6.7 MEDIUM — Keyboard & Safe Area

| ID | Pattern | Grep | Issue |
|---|---|---|---|
| K01 | `TextField` in `VStack`/`ZStack` (not `ScrollView`) without keyboard handling | Search `TextField` → check parent is NOT ScrollView/List/Form AND no `.ignoresSafeArea(.keyboard)` or `.scrollDismissesKeyboard` | Keyboard covers input field |
| K02 | `.ignoresSafeArea(.keyboard)` on view containing `TextField` | Search `.ignoresSafeArea(.keyboard)` in file with `TextField` | View won't move up when keyboard appears — field hidden |
| K03 | `TextEditor` without `.scrollDismissesKeyboard` | Search `TextEditor` → check for keyboard dismiss mechanism nearby | No way to dismiss keyboard |

### 6.8 HIGH — Data Persistence & Migration

**Why:** Adding/removing/renaming a Codable property silently crashes decoding of existing UserDefaults data after app update. Users lose data with no error visible.

| ID | Pattern | How to check | Issue |
|---|---|---|---|
| D10 | Codable struct saved to UserDefaults without migration strategy | Find Codable structs used with `JSONEncoder`/`JSONDecoder` + `UserDefaults` → check if `init(from decoder:)` handles missing keys with defaults | App update crash — old data can't decode new struct |
| D11 | `@AppStorage` with Codable via `RawRepresentable` | Search `@AppStorage` with custom types using `RawRepresentable` + `Codable` | Infinite recursion crash from encode/rawValue cycle |
| D12 | UserDefaults key collision | Collect all UserDefaults keys → check for duplicates or ambiguous keys | Silent data overwrite between unrelated features |
| D13 | Missing `CodingKeys` when struct has `let id = UUID()` | Search for `let id = UUID()` in Codable structs | Decoder can't overwrite `let` with initial value — always generates new ID |

**How to check D10 (critical for app updates):**
1. Find all Codable structs stored via UserDefaults/JSONEncoder
2. Check git history — if properties were added/removed since last release
3. If no custom `init(from decoder:)` with fallback defaults → report HIGH
4. Especially dangerous: non-optional properties added without default

### 6.9 MEDIUM — View Lifecycle & Resource Cleanup

**Why:** SwiftUI views don't have `deinit`. Timers, observers, and Combine subscriptions started in `onAppear` must be cleaned up in `onDisappear`, but `onDisappear` is NOT always called (e.g., TabView keeps all tabs alive). [Reference: oleb.net/2022/swiftui-view-lifecycle](https://oleb.net/2022/swiftui-view-lifecycle/)

| ID | Pattern | Grep | Issue |
|---|---|---|---|
| LC01 | `Timer.scheduledTimer` without `invalidate()` in `onDisappear` | Search `Timer.scheduledTimer` or `Timer.publish` → check for matching cleanup in `onDisappear` | Timer continues running after view is gone — CPU waste + potential crash |
| LC02 | `NotificationCenter.addObserver` without `removeObserver` in `onDisappear` | Search `addObserver(forName` → check matching `removeObserver` in `onDisappear` | Observer leak, duplicate handlers |
| LC03 | `.onAppear` doing work without checking if already done | Search `.onAppear` with network/data fetch → check for guard against duplicate calls | `onAppear` fires multiple times in TabView — duplicate requests |
| LC04 | Combine `.sink` stored in `@State` var without cancellation in `onDisappear` | Search `AnyCancellable` or `.sink` stored in `@State` → check `onDisappear` cleanup | Subscription outlives view |

### 6.10 HIGH — Presentation Race Conditions

**Why:** Presenting alert/sheet/confirmationDialog simultaneously with dismissing another causes silent failure or crash. [Reference: openradar FB12078831](https://openradar.appspot.com/FB12078831)

| ID | Pattern | Grep | Issue |
|---|---|---|---|
| PR01 | `.alert` + `.sheet` + `.confirmationDialog` sharing same Bool binding | Search files with multiple presentation modifiers → check they use distinct state bindings | Only one presentation works, others silently fail |
| PR02 | Programmatic dismiss + immediate present | Search `dismiss()` followed by state change triggering `.sheet`/`.alert` within 5 lines | New presentation fails — dismissed before shown |
| PR03 | `.alert` on view inside `.sheet` | Search `.alert(` inside a view that is presented via `.sheet(` | Alert may not appear on some iOS versions |

### 6.11 MEDIUM — Resource Integrity

**Why:** Missing images and localization keys don't crash but show broken UI — raw keys visible to users, blank image areas.

| ID | Pattern | How to check | Issue |
|---|---|---|---|
| RI01 | `Image("name")` referencing non-existent asset | Collect all `Image("` string literals → cross-reference with Asset catalog contents | Blank/invisible image in UI |
| RI02 | `.localized` or `NSLocalizedString` key not in .strings/.xcstrings file | Collect all `"key".localized` patterns → cross-reference with Localizable.strings | Raw key shown to user instead of translation |
| RI03 | Missing localization for secondary language | Compare keys in all .lproj folders → flag keys present in one but missing in another | Untranslated strings for some users |
| RI04 | Asset name conflicts with system symbols | Check Asset catalog names against SF Symbol names (e.g., "checkmark", "star") | Xcode warning, potential wrong image displayed |

### 6.12 LOW — Device Compatibility

| ID | Pattern | Grep | Issue |
|---|---|---|---|
| DC01 | Hardcoded screen dimensions | Search `UIScreen.main.bounds` or hardcoded `375\|390\|414\|428` pixel widths | Breaks on different device sizes |
| DC02 | No `horizontalSizeClass` / `verticalSizeClass` usage with iPad support | If deployment target includes iPad → search for `sizeClass` or `UserInterfaceSizeClass` | Layout broken in iPad split view / multitasking |
| DC03 | `.ignoresSafeArea()` without specifying edges | Search `.ignoresSafeArea()` with no parameters | Content hidden behind Dynamic Island / home indicator on all edges |
| DC04 | Fixed `NavigationSplitView` columns without iPad adaptation | Search `NavigationSplitView` → check for `.navigationSplitViewColumnWidth` or size class handling | Broken layout in iPad portrait |

### 6.13 HIGH — Double Tap & Rapid Action Prevention

**Why:** Users spam buttons during loading. Without protection: duplicate purchases, duplicate API calls, duplicate data entries, race conditions. [Reference: Swift by Sundell — async buttons](https://www.swiftbysundell.com/articles/building-an-async-swiftui-button/)

| ID | Pattern | How to check | Issue |
|---|---|---|---|
| DT01 | Purchase/subscribe button without `.disabled` during async | Read paywall/purchase views → check if buy button is disabled while `isLoading`/`isProcessing` | Double purchase, double charge |
| DT02 | "Save"/"Submit" button without loading guard | Read form submission buttons → check for `@State var isLoading` + `.disabled(isLoading)` | Duplicate data creation |
| DT03 | Navigation action without guard against rapid taps | Search `NavigationLink` or programmatic navigation in `Button` → check for debounce/guard | Multiple screens pushed simultaneously |
| DT04 | `Task {}` in button action without cancellation of previous task | Read async button actions → check if previous Task is cancelled before starting new one | Multiple concurrent operations for same action |
| DT05 | Delete/destructive action without confirmation alert | Search `.onDelete` or destructive buttons → verify `.alert` confirmation before execution | Accidental data loss |

**How to check DT01 (critical for IAP):**
1. Find all purchase/subscribe buttons in paywall views
2. Verify button has `.disabled(isLoading)` or `.disabled(adapty.isLoading)` or equivalent
3. Verify ProgressView is shown during purchase
4. If no protection → report HIGH

### 6.14 HIGH — Permission Request Patterns

**Why:** iOS system permission dialogs can only be shown ONCE. If denied, the user must go to Settings manually. Asking at the wrong time = permanent denial. [Reference: NN/g](https://www.nngroup.com/articles/permission-requests/)

| ID | Pattern | How to check | Issue |
|---|---|---|---|
| PM01 | System permission requested on first launch without context | Search `requestAuthorization\|requestTrackingAuthorization\|PHPhotoLibrary.requestAuthorization` → check if it's called in `onAppear` of first screen or app init | User denies — permanent loss of permission |
| PM02 | No pre-permission dialog before system prompt | Search for system permission request → check if custom UI explanation is shown BEFORE system dialog | Lower opt-in rate, no second chance |
| PM03 | Permission denied state not handled in UI | Search `UNAuthorizationStatus\|authorizationStatus\|ATTrackingManager.AuthorizationStatus` → check for `.denied` case handling with "Go to Settings" guidance | User stuck — feature broken with no explanation |
| PM04 | ATT prompt shown before value demonstrated | Search `requestTrackingAuthorization` → check timing relative to onboarding flow | Low ATT opt-in rate — asked too early |
| PM05 | No fallback when permission denied | Search features requiring camera/photos/location → check if app works (with degraded UX) when permission is denied | App crashes or shows blank screen |

### 6.15 MEDIUM — Network & Offline Edge Cases

| ID | Pattern | How to check | Issue |
|---|---|---|---|
| NW01 | Async data fetch without error handling visible to user | Search `.task {` or `onAppear` with `await` → check for `catch` with user-visible error | Silent failure — blank screen |
| NW02 | No offline/no-internet state detection | Search for `NWPathMonitor\|NetworkMonitor\|isConnected` — if absent in app with network calls | App hangs or shows cryptic error offline |
| NW03 | No retry mechanism for failed network requests | Search error handling in network calls → check for retry button or automatic retry | User must restart app to retry |
| NW04 | Loading indicator without timeout | Search `ProgressView` in loading states → check if there's a timeout or cancel mechanism | Infinite spinner if network request hangs |

### 6.16 MEDIUM — Dynamic Type & Text Layout

**Why:** ~30% of iOS users change default text size. At accessibility sizes (AX1-AX5), most hardcoded layouts break — text truncated, overlapping, or invisible. [Reference: nilcoalescing.com](https://nilcoalescing.com/blog/AvoidingTextTruncationInSwiftUI/)

| ID | Pattern | Grep | Issue |
|---|---|---|---|
| DY01 | `.lineLimit(1)` on user-facing text without `.minimumScaleFactor` | Search `.lineLimit(1)` → check for `.minimumScaleFactor` or `ViewThatFits` | Text truncated at large Dynamic Type |
| DY02 | Fixed `.frame(height:)` on text containers | Search `.frame(height:` near `Text(` or `VStack` with text | Container clips text at accessibility sizes |
| DY03 | Horizontal layout that should stack vertically at large sizes | Search `HStack` containing multiple `Text` → check for `@Environment(\.dynamicTypeSize)` or `ViewThatFits` | Text overlaps or overflows horizontally |
| DY04 | `.font(.system(size:))` without `.dynamicTypeSize` range limit | Search `.font(.system(size:` → check if `.dynamicTypeSize(...:)` range modifier exists | Font doesn't scale OR scales too much |

### 6.17 MEDIUM — Modal & Popup Lifecycle

**Why:** Sheets/fullScreenCovers have complex lifecycle — they can be dismissed by swipe, by scenePhase changes, or by parent view updates. State must stay consistent across all dismiss paths.

| ID | Pattern | How to check | Issue |
|---|---|---|---|
| ML01 | `.sheet` content using `@State` from parent without `@Binding` | Read `.sheet { }` closures → check if they capture `@State` by value instead of `@Binding` | Sheet shows stale data, edits lost on dismiss |
| ML02 | No `.interactiveDismissDisabled()` on form sheets with unsaved changes | Search `.sheet(` for forms/editors → check if `.interactiveDismissDisabled` is used when data is dirty | User loses work by accidental swipe-to-dismiss |
| ML03 | `.fullScreenCover` dismissed by child sheet dismiss | Search `.fullScreenCover` containing `.sheet` → verify dismiss paths | Parent fullScreenCover dismissed when child sheet dismisses |
| ML04 | Modal presenting new modal without dismissing first | Search for chained `.sheet` or `.fullScreenCover` presentations → check timing | Undefined behavior — sometimes works, sometimes crashes |

---

## Phase 7: Spec Compliance (if spec exists)

If speckit artifacts were found in Phase 1.4, verify implementation matches spec.

### 7.1 Requirements coverage

Read `spec.md`. For each functional requirement (FR-xxx or bullet point):
1. Identify what Swift code should implement it
2. Grep for relevant patterns (view names, function names, keywords)
3. If no matching code found → report as MEDIUM finding: "Spec requirement not implemented"

### 7.2 Architecture conformance

Read `plan.md` or `CLAUDE.md`. Verify:
- Each planned file exists
- ViewModels follow the declared pattern (`@MainActor @Observable`)
- DI uses protocols (not direct class references in Views)
- Navigation goes through Router (if Router pattern is specified)

```bash
# Views importing data layer directly (architecture violation)
```
Grep for: `import.*Repository|import.*DataSource` in `*View.swift` files.

```bash
# Services without protocol
```
Grep for: `class \w+Service` without matching `protocol \w+ServiceProtocol` in same or imported file.

### 7.3 Task completion

Read `tasks.md`. For each task:
- Check if task deliverables exist (files created, patterns present)
- Mark as ✅ implemented or ❌ missing
- Report missing tasks as MEDIUM findings

---

## Phase 8: Accessibility Audit (standard + exhaustive)

### 8.1 Dynamic Type

| ID | Pattern | Grep | Issue |
|---|---|---|---|
| A01 | Fixed font size | `.font(.system(size:` | No Dynamic Type scaling |
| A02 | Fixed frame heights on text | `.frame(height:` near `Text(` | Clips scaled text |

### 8.2 VoiceOver

| ID | Pattern | Grep | Issue |
|---|---|---|---|
| A03 | Image without label | `Image(` without `.accessibilityLabel` or `.accessibilityHidden(true)` within 3 lines | VoiceOver can't describe |
| A04 | Icon-only button | `Button.*Image(` without `.accessibilityLabel` | VoiceOver reads nothing useful |
| A05 | Decorative image not hidden | `Image(decorative:` or SF Symbol used decoratively | Should be `.accessibilityHidden(true)` |

### 8.3 Touch Targets

| ID | Pattern | Issue |
|---|---|---|
| A06 | Small tap target | `.frame(` with width or height < 44 points on interactive element | Below Apple minimum 44x44 |

### 8.4 Color & Contrast

| ID | Pattern | Grep | Issue |
|---|---|---|---|
| A07 | Hardcoded Color.black/white | `Color.black\|Color.white\|UIColor.black\|UIColor.white` | No dark mode adaptation |
| A08 | Color-only indicator | `.foregroundColor(.red)\|.foregroundColor(.green)` | Color-blind users can't distinguish |
| A09 | Hardcoded UIColor RGB | `UIColor(red:` | Should use named colors from asset catalog |

---

## Phase 9: Performance Analysis (exhaustive only)

### 9.1 Main Thread Blocking

| ID | Pattern | Grep | Issue |
|---|---|---|---|
| P01 | Synchronous file read | `Data(contentsOf:\|String(contentsOfFile:` | Blocks main thread |
| P02 | DateFormatter in body/computed | `DateFormatter()` in View body or computed property | Expensive allocation per render |
| P03 | Thread.sleep | `Thread.sleep\|sleep(` | Blocks thread entirely |
| P04 | Heavy sync computation in body | Complex logic inside `var body:` | UI freeze |

### 9.2 Excessive Re-renders

| ID | Pattern | Grep | Issue |
|---|---|---|---|
| P05 | GeometryReader | `GeometryReader` | Extra layout pass, use sparingly |
| P06 | Body > 50 lines | View body longer than 50 lines | Hard to optimize, extract subviews |
| P07 | @Observable with many properties | Class with >10 published properties | Any change re-renders all observers |

### 9.3 Memory

| ID | Pattern | Grep | Issue |
|---|---|---|---|
| P08 | Full-res image load | `UIImage(contentsOfFile:\|UIImage(data:` without downsampling | OOM risk with large images |
| P09 | Large array without pagination | Data load without `limit\|page\|offset\|cursor` | Unbounded memory growth |

### 9.4 Render Loops & Infinite Updates

**Why:** SwiftUI silently breaks infinite loops by capping re-renders, but this causes stale UI and "onChange tried to update multiple times per frame" warnings. [Reference: fatbobman.com/en/posts/onchange](https://fatbobman.com/en/posts/onchange/)

| ID | Pattern | Grep | Issue |
|---|---|---|---|
| P10 | `@State` mutation inside `var body` | Search for `@State` property assignments inside `var body:` (not in closures like `onTapGesture`) | Infinite render loop — body triggers state change triggers body |
| P11 | `onChange` modifying its observed value | Search `onChange(of:` → check if closure mutates the same property being observed | Infinite loop, capped by SwiftUI at ~6 iterations |
| P12 | `VStack`/`HStack` (not Lazy) with `ForEach` inside `ScrollView` | Search `ScrollView` containing `VStack {` or `HStack {` with `ForEach` (NOT `LazyVStack`/`LazyHStack`) | All views loaded eagerly — freezes on large datasets |
| P13 | `GeometryReader` modifying `@State` via `DispatchQueue.main.async` | Search `GeometryReader` → check for `DispatchQueue.main.async` with state mutation | Potential infinite layout loop |

---

## Phase 10: Dead Code & Hygiene (exhaustive only)

### 10.1 Leftover markers

| ID | Pattern | Grep | Issue |
|---|---|---|---|
| D01 | TODO/FIXME left | `TODO\|FIXME\|HACK\|XXX\|TEMP` | Unfinished work |
| D02 | Placeholder text | `Lorem\|placeholder\|test123\|example\.com` | Not production-ready |
| D03 | Disabled code | `#if false\|// DISABLED\|/* REMOVED` | Dead code block |
| D04 | Debug prints | `print(` not inside `#if DEBUG` | Console noise in production |
| D05 | Commented-out code | Large blocks of `//` commented Swift code (>5 lines) | Clutters codebase |

### 10.2 Unused code

| Pattern | How to check |
|---|---|
| Unused imports | `import Foundation` when `import SwiftUI` is present (SwiftUI re-exports Foundation) |
| Unused private functions | `private func` not called elsewhere in same file |
| Empty files | Files with only import and empty struct/class |

### 10.3 Redundant patterns

| Pattern | Grep | Better |
|---|---|---|
| `Combine` in new code | `import Combine` | async/await |
| `.count == 0` | `.count == 0\|.count > 0` | `.isEmpty` / `!.isEmpty` |
| Optional collection | `var \w+: \[\w+\]\?` | Use empty array instead |
| Redundant nil init | `var \w+: \w+\? = nil` | `var x: Type?` (nil is default) |

---

## Phase 11: Dependency & Permissions Audit (exhaustive only)

### 11.1 Dependencies

```bash
cat Package.resolved 2>/dev/null | head -50
```

Check:
- Any dependency with known vulnerabilities
- Major version behind on critical deps (Adapty, Firebase, etc.)
- Unused dependencies (imported in project but not used in code)

### 11.2 Permissions

Scan for API usage and verify matching Info.plist descriptions:

| API Usage | Required Key |
|---|---|
| `AVCaptureSession\|UIImagePickerController.*camera` | `NSCameraUsageDescription` |
| `PHPhotoLibrary\|UIImagePickerController` | `NSPhotoLibraryUsageDescription` |
| `CLLocationManager` | `NSLocationWhenInUseUsageDescription` |
| `ATTrackingManager` | `NSUserTrackingUsageDescription` |
| `SFSpeechRecognizer` | `NSSpeechRecognitionUsageDescription` |
| `HKHealthStore` | `NSHealthShareUsageDescription` |

Flag:
- API used but no matching permission description → App Store rejection
- Permission requested but API never used → unnecessary permission prompt

### 11.3 App Store Rejection Risks

**Why:** ~40% of iOS submissions face delays or rejection due to preventable errors. [Reference: theapplaunchpad.com](https://theapplaunchpad.com/blog/app-store-review-guidelines)

| ID | Pattern | How to check | Issue |
|---|---|---|---|
| R01 | Missing Privacy Manifest | Check for `PrivacyInfo.xcprivacy` in project | Rejection since May 2024 — required for all apps |
| R02 | SDK without privacy manifest | Check `Package.resolved` deps → verify each has `PrivacyInfo.xcprivacy` | Rejection since Feb 2025 for privacy-impacting SDKs |
| R03 | Required Reason API without declaration | Search for `UserDefaults`, `NSFileSystemFreeSize`, `systemUptime`, `activePrewarms` → verify declared in `PrivacyInfo.xcprivacy` | Apple requires reason for specific API usage |
| R04 | Placeholder content in UI | Grep for `Lorem\|placeholder\|TODO\|Coming soon\|test123\|example\.com` in user-facing strings | Rejection for incomplete/placeholder content |
| R05 | Missing minimum iOS version support | Check deployment target — must support at least iOS 17 for new apps in 2026 | Built with outdated SDK |

### 11.4 StoreKit & In-App Purchase Audit

**Why:** ~25% of StoreKit purchases fail silently in production. Edge cases around restore, sandbox, and concurrent purchases cause data loss and revenue loss.

| ID | Pattern | How to check | Issue |
|---|---|---|---|
| IAP01 | No restore purchases button | Search for `restorePurchases\|restore` in paywall views → verify button exists | App Store rejection — restore is mandatory |
| IAP02 | Purchase result not handling `.userCancelled` | Read purchase flow → verify `userCancelled` case is handled separately from errors | User cancel treated as error — confusing UX |
| IAP03 | No error handling for `Product.products(for:)` | Search `Product.products` → check for `catch` with user-visible error | Empty paywall with no explanation |
| IAP04 | Missing `Transaction.currentEntitlements` check on launch | Search for `currentEntitlements\|Transaction.updates` in app init | Premium state lost after app restart |
| IAP05 | Hardcoded product IDs not matching App Store Connect | Search for product ID strings → flag if not centralized in one place | Wrong product purchased or empty paywall |

### 11.5 Notification & Permission Audit

| ID | Pattern | How to check | Issue |
|---|---|---|---|
| NP01 | No handling of notification permission `.denied` state | Search `requestAuthorization` → check if `.denied` result is handled (e.g., guide to Settings) | User stuck — can't enable notifications after initial deny |
| NP02 | `UNUserNotificationCenter.add()` without completion handler error check | Search `.add(request)` without trailing closure or `try await` | Silent notification scheduling failure |
| NP03 | Missing `UNUserNotificationCenter.delegate` assignment | Search for `UNUserNotificationCenter.current().delegate` → verify set in AppDelegate or App init | Foreground notifications don't appear |
| NP04 | Badge count not reset on app launch | Search for `applicationIconBadgeNumber = 0` or `setBadgeCount(0)` in `scenePhase .active` or `applicationDidBecomeActive` | Stale badge confuses users |

### 11.6 Deep Link & URL Handling Audit

| ID | Pattern | How to check | Issue |
|---|---|---|---|
| DL01 | `.onOpenURL` without checking app initialization state | Search `.onOpenURL` → verify it doesn't navigate before root view is ready | Crash or blank screen on cold-start deep link |
| DL02 | URL scheme defined in Info.plist but no `.onOpenURL` handler | Check URL Types in Info.plist → verify matching `.onOpenURL` in code | Deep links silently ignored |
| DL03 | Universal Links: missing `apple-app-site-association` reference | If `applinks:` entitlement exists → verify AASA file handling | Universal links don't work |

---

## Report Format

```
# iOS QA Report

**Project:** <name>
**Tier:** quick | standard | exhaustive
**Date:** YYYY-MM-DD
**Spec:** <spec name or "no spec">

---

## Build & Tests

| Check | Status |
|-------|--------|
| Build | ✅ Pass / ❌ Fail |
| Unit tests | X passed, Y failed, Z skipped |
| UI tests | X passed, Y failed, Z skipped / none |
| SwiftLint | X errors, Y warnings / not installed |

---

## Findings Summary

| Severity | Count | Categories |
|----------|-------|------------|
| 🔴 Critical | X | Crashes |
| 🟠 High | X | Security, Data Loss, Hit Testing, Flow Logic |
| 🟡 Medium | X | Concurrency, Memory, SwiftUI, Dark Mode, Navigation, Keyboard, Spec |
| 🔵 Low | X | UX, Accessibility, Hygiene |
| ⚪ Cosmetic | X | Deprecated, Style |

---

## Health Score: XX/100

Starting from 100, deductions:
- 🔴 Critical: **-25** each
- 🟠 High: **-15** each
- 🟡 Medium: **-8** each
- 🔵 Low: **-3** each
- ⚪ Cosmetic: **-1** each

Minimum score: 0.

---

## Findings

### 🔴 Critical

#### C01: Force unwrap in ProductService.swift
**File:** `App/Services/ProductService.swift:42`
**Category:** Crash
```swift
// Current
let url = URL(string: endpoint)!

// Fix
guard let url = URL(string: endpoint) else {
    throw APIError.invalidURL
}
```

### 🟠 High
...

### 🟡 Medium
...

### 🔵 Low
...

### ⚪ Cosmetic
...

---

## Spec Compliance (if spec loaded)

| Requirement | Status | Notes |
|-------------|--------|-------|
| FR-001: User login | ✅ | LoginView + LoginViewModel |
| FR-002: Data sync | ❌ | Not implemented |
| FR-003: Offline mode | ⚠️ | Partial — no queue |

**Coverage:** X/Y requirements implemented (Z%)

---

## Ship Readiness

🟢 **READY** — score ≥ 85, zero critical, zero high
🟡 **CONDITIONAL** — score 60-84, zero critical, ≤ 2 high
🔴 **NOT READY** — score < 60, or any critical

**Verdict:** 🟡 CONDITIONAL (score: 72/100)
**Blockers:** 1 high security issue (S01)
**Recommendation:** Fix S01, re-run /ios-qa quick

---

## Next Steps

1. Fix critical/high findings first
2. Run `/ios-qa quick` to verify fixes
3. Address medium findings before release
4. Low/cosmetic — at your discretion
```

---

## Fix Loop (if user approves)

After presenting the report, ask:
> Исправить найденные проблемы? (all / critical+high only / specific IDs)

For each approved fix, by severity (critical first):
1. Read the file and surrounding context
2. Apply fix using Edit tool
3. If fix touches multiple files — fix all related files
4. After each fix, report what was changed

After all fixes:
1. Re-build to verify no regressions
2. Re-run the relevant checks (not full QA)
3. Report updated score and delta: `72/100 → 89/100 (+17)`

---

## Tier Definitions

### Quick (~2 min)
- Phase 2: Build
- Phase 3: Tests
- Phase 4: Crash risks (C01-C09)
- Phase 4: Security (S01-S05)

### Standard (~10 min) — default
- Everything in Quick, plus:
- Phase 5: Concurrency + Memory (T01-T07, M01-M06)
- Phase 6: SwiftUI patterns + UX states (U01-U06, X01-X05)
- Phase 6.3: Hit Testing & Interaction (H01-H04)
- Phase 6.4: Dark Mode & Contrast (V01-V03)
- Phase 6.5: Flow Logic & State Machine (F01-F04)
- Phase 6.6: Navigation & Modal Bugs (N01-N04)
- Phase 6.7: Keyboard & Safe Area (K01-K03)
- Phase 6.8: Data Persistence & Migration (D10-D13)
- Phase 6.9: View Lifecycle & Cleanup (LC01-LC04)
- Phase 6.10: Presentation Race Conditions (PR01-PR03)
- Phase 6.11: Resource Integrity (RI01-RI04)
- Phase 6.12: Device Compatibility (DC01-DC04)
- Phase 6.13: Double Tap & Rapid Action Prevention (DT01-DT05)
- Phase 6.14: Permission Request Patterns (PM01-PM05)
- Phase 6.15: Network & Offline Edge Cases (NW01-NW04)
- Phase 6.16: Dynamic Type & Text Layout (DY01-DY04)
- Phase 6.17: Modal & Popup Lifecycle (ML01-ML04)
- Phase 7: Spec compliance (if spec exists)
- Phase 8: Accessibility audit (A01-A09)

### Exhaustive (~15 min)
- Everything in Standard, plus:
- Phase 9: Performance (P01-P13, including render loops)
- Phase 10: Dead code + Hygiene (D01-D05)
- Phase 11: Dependency + Permissions + App Store rejection risks (R01-R05)
- Phase 11.4: StoreKit & IAP audit (IAP01-IAP05)
- Phase 11.5: Notification & Permission audit (NP01-NP04)
- Phase 11.6: Deep Link & URL handling audit (DL01-DL03)
- SwiftLint full report

---

## Rules

1. **Build first.** If it fails, that's the only finding — stop.
2. **Never modify tests to make them pass.** Fix source code.
3. **Each finding is independent.** Don't combine multiple issues.
4. **Include line numbers and fix code** for every finding.
5. **Skip third-party code**: Pods, .build, DerivedData, generated files.
6. **Verify before reporting**: read context around grep match — false positives waste trust.
7. **For Xcode errors**: include the exact compiler message, not a paraphrase.
8. **Spec compliance**: only check if spec artifacts exist. Don't invent requirements.
9. **Don't over-report**: 3 instances of same pattern = 1 finding + "and N more occurrences".
