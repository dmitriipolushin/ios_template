# CLAUDE.md — Project Rules

## Stack

- iOS 17+, SwiftUI, async/await, XcodeGen (project.yml)
- No UIKit (except wrapping system components unavailable in SwiftUI)
- Code in English, communication in Russian

## Autonomy (RACI)

### R — Does on own, no approval needed
- Create and edit Swift files
- Read any project files for context
- Run grep/search/glob to explore codebase

### A — Must ask before doing
- Add/remove SPM dependencies (changes to project.yml packages)
- Run xcodegen, xcodebuild, or any build commands
- Delete files or significant code blocks
- Git operations (commit, push, branch, merge) — only on explicit request

### C — Show options, user decides
- Architecture changes (new patterns, module restructuring)
- Navigation structure changes
- Data persistence approach (SwiftData, UserDefaults, Keychain scope)

### I — Never do, only inform
- Force push, reset --hard, destructive git operations
- Modify .claude/ settings or permissions
- Change deployment target or Swift version

## Development Process

### New Features
Always go through speckit workflow:
1. `/speckit.specify` — create feature specification
2. `/speckit.plan` — technical planning
3. `/speckit.tasks` — break into tasks
4. `/ios-implement` — implement with iOS patterns

Do NOT skip to writing code without a spec.
Use `/ios-implement`, not `/speckit.implement` (the generic version without iOS patterns).

### Features with a Design
If there is a design (`.fig`, `.pen` or an HTML prototype), run the design skills before and after implementation, never in parallel with it:
1. Before `/speckit.plan`: `/fig-pixel-parity` steps 1–2 — spec (sizes, colors, fonts) and assets into `Assets.xcassets`
2. `/ios-implement` — build the screens with those assets
3. After implementation: pixel check — `/fig-pixel-parity` step 4 (`.fig`/`.pen`) or `/proto-parity` (HTML prototype); fix differences and check again

### Before Writing Code
Always show a plan first — what files will be created/modified and why.
Wait for approval before proceeding.

### Tests
Do NOT write unit tests unless explicitly asked.

### E2E Tests (Maestro)
Maestro YAML flows live in `.maestro/`. Use `/ios-maestro` to generate and run.
- Every interactive SwiftUI element needs `.accessibilityIdentifier("snake_case_id")`
- Convention: `{feature}_{element}_button`, `{feature}_{screen}_screen`, `tab_{name}`
- Run: `maestro test -e APP_ID=com.yourcompany.app .maestro/`

## Code Patterns

### ViewModel
```swift
@MainActor
@Observable
final class FeatureViewModel {
    private let service: ServiceProtocol
    init(service: ServiceProtocol) { self.service = service }
}
```

### View
- `.task { }` for async work (never `onAppear` + `Task { }`)
- Three states: loading (`ProgressView`), empty (`ContentUnavailableView`), error
- `@ViewBuilder` for conditional content
- Extract subviews when body > 40 lines

### Dependencies
- Protocol-based injection for all services
- Resolve via init parameters, not singletons (AdaptyManager.shared is the only exception)

### Navigation
- `NavigationStack` + `Router` (see `App/App/Router.swift`)
- `.sheet()` for lightweight modals, `.fullScreenCover()` for immersive flows

## Communication Style

- Language: code in English, conversation in Russian
- Be detailed — explain what you're doing and why
- After completing a task: summary of what was done + recommendation for next steps
- When stuck or unsure: stop immediately and ask, do not guess

## Escalation

If you encounter any of these, STOP and ask:
- Build fails after 2 fix attempts
- Unclear which architecture approach to use
- Task requires deleting or restructuring existing code
- Spec is ambiguous or contradictory
- Need to add a dependency not already in project.yml

Format when stopping:
```
⛔ Stuck: [what happened]
Options:
  A) [option]
  B) [option]
Recommendation: [which and why]
```

## Available Skills

| Skill | Purpose |
|-------|---------|
| `/speckit.specify` | Create feature spec from description |
| `/speckit.plan` | Technical planning and research |
| `/speckit.tasks` | Break plan into actionable tasks |
| `/ios-implement` | Implement tasks with iOS patterns |
| `/ios-qa` | QA testing (build + static analysis, 144 checks, 3 tiers) |
| `/ios-maestro` | E2E testing with Maestro (generate flows + run on simulator) |
| `/ios-review` | Code review (crashes, security, concurrency) |
| `/ios-design-review` | HIG compliance audit (12 categories, A-F grade) |
| `/proto-parity` | Pixel and copy parity with an HTML prototype: Playwright shots + DOM geometry, Maestro shots, montages, masked diff images, shape-based measurements, copy and translation-table check (`.claude/skills/proto-parity`, once: `npm install` in its `scripts/`) |
| `/fig-pixel-parity` | Design from a local `.fig` (or `.pen` via Pencil MCP) into the app pixel for pixel: spec, vector icons, colors and images into `Assets.xcassets`, reference renders and captioned pixel diffs against the simulator |
| `/store-subscriptions` | Subscriptions end to end: keys and where they go (`KEYS.md`), App Store Connect via the `asc` CLI, Adapty via the `adapty` CLI (products, paywalls, placements), server notifications, purchase checks |
| `/figma` | Fetch a frame from a Figma link via REST API (needs `FIGMA_TOKEN`) |
| `/aso-screenshots` | App Store marketing screenshots in all required sizes |
| `/imagine` | Generate images via kie.ai |
| `/youtrack` | Query YouTrack issues (needs `YOUTRACK_URL`, `YOUTRACK_TOKEN`, `YOUTRACK_PROJECT`) |
| `/speckit.clarify` | Resolve ambiguities in spec |
| `/speckit.analyze` | Cross-artifact consistency check |
| `/speckit.checklist` | Quality checklist for the current feature's requirements |
| `/speckit.constitution` | Create or update project principles |
| `/speckit.taskstoissues` | Turn tasks into GitHub issues |
