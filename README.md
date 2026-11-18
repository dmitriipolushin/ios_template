# iOS Template

Template for building iOS apps with SwiftUI + Claude Code. Includes ready-to-use services, AI-powered development workflow, and quality automation skills.

## Quick Start

```bash
git clone <this-repo> MyNewApp
cd MyNewApp
./setup.sh
```

The setup script will:
1. Ask for app name and bundle ID
2. Rename all `AppName` references throughout the project
3. Copy `Secrets.plist.example` → `App/Resources/Secrets.plist`
4. Install XcodeGen (if missing) and generate `.xcodeproj`

After setup, open the `.xcodeproj` in Xcode, set your team, and run.

---

## How It Works

This template is built around two ideas:
1. **Spec-driven development** — every feature starts with a specification, not code
2. **AI-assisted quality** — automated code review, design audit, and QA testing

### Development Workflow

```
/speckit.specify → /speckit.plan → /speckit.tasks → /ios-implement
                                                          ↓
                                                   /ios-qa → /ios-review → /ios-design-review
```

### Phase 1: Specification

| Command | What it does |
|---------|-------------|
| `/speckit.specify` | Takes a natural language feature description ("add user profile with avatar and settings") and creates a formal spec: user stories, requirements, success criteria. No code — only WHAT and WHY. |
| `/speckit.clarify` | Reviews the spec for ambiguities, asks up to 5 clarification questions, and updates the spec with your answers. |

**Output:** `specs/001-feature-name/spec.md`

### Phase 2: Planning

| Command | What it does |
|---------|-------------|
| `/speckit.plan` | Reads the spec and creates a technical plan: data models, API contracts, architecture decisions, file structure. |

**Output:** `specs/001-feature-name/plan.md`, `data-model.md`, `contracts/`, `research.md`

### Phase 3: Tasks

| Command | What it does |
|---------|-------------|
| `/speckit.tasks` | Breaks the plan into ordered, actionable tasks. Each task has an ID, description, and file path. Marks parallelizable tasks with `[P]`. |
| `/speckit.analyze` | Read-only audit — checks consistency between spec, plan, and tasks. Finds gaps, contradictions, missing requirements. |

**Output:** `specs/001-feature-name/tasks.md`

### Phase 4: Implementation

| Command | What it does |
|---------|-------------|
| `/ios-implement` | Executes tasks phase by phase with iOS-specific patterns: `@Observable` ViewModels, SwiftUI views with 3 states (loading/empty/error), protocol-based DI, `NavigationStack` routing. Validates build after each phase via XcodeGen + xcodebuild. |

**Output:** Swift files in `App/`, updated `project.yml`, tasks marked complete in `tasks.md`

### Phase 5: Quality

| Command | What it does |
|---------|-------------|
| `/ios-qa` | Builds the app, runs tests, scans code for crashes/security/memory issues. Three tiers: quick, standard, exhaustive. Outputs health score 0-100 and ship readiness. |
| `/ios-review` | Code review against base branch. Checks 7 priority levels: crashes → security → concurrency → memory → architecture → performance → modern patterns. Outputs verdict: approve / request changes. |
| `/ios-design-review` | Audits SwiftUI code against Apple HIG. 12 categories (typography, colors, dark mode, accessibility, touch targets...). Outputs grade A-F with weighted score. |

### Other Skills

| Command | What it does |
|---------|-------------|
| `/imagine` | Generate images via kie.ai (Nano Banana 2). Text-to-image, image-to-image, background removal, PNG optimization. |
| `/speckit.constitution` | Define project principles and governance rules. |
| `/speckit.checklist` | Generate quality checklists for requirements. |

---

## Project Structure

```
├── .claude/
│   ├── commands/              ← All skill definitions (14 commands)
│   └── settings.json          ← Claude Code permissions
├── .specify/
│   ├── templates/             ← Spec, plan, task templates
│   ├── scripts/bash/          ← Automation scripts
│   └── memory/                ← Project constitution
├── App/
│   ├── App/
│   │   ├── AppNameApp.swift   ← @main entry point
│   │   ├── ContentView.swift  ← Root view with NavigationStack
│   │   └── Router.swift       ← Navigation state management
│   ├── Features/              ← Feature modules (View + ViewModel per feature)
│   ├── Models/                ← Data models (SwiftData or plain)
│   ├── Services/
│   │   ├── OpenAI/            ← OpenAI client + Keychain helper
│   │   └── Subscription/      ← Adapty in-app purchases
│   ├── Shared/
│   │   ├── Components/        ← Reusable SwiftUI components
│   │   └── Extensions/        ← Swift extensions
│   └── Resources/
│       └── Assets.xcassets/   ← App icon, colors, images
├── CLAUDE.md                  ← Agent rules (auto-read by Claude Code)
├── project.yml                ← XcodeGen config (generates .xcodeproj)
├── .swiftlint.yml             ← Code style rules
├── .gitignore
├── Secrets.plist.example      ← API key template (copy to App/Resources/)
└── setup.sh                   ← One-time project setup
```

## Built-in Services

### OpenAI (`App/Services/OpenAI/`)

```swift
let client = OpenAIClient()

// Simple call
let response = try await client.complete(
    system: "You are a helpful assistant.",
    user: "Hello",
    jsonMode: true
)

// Streaming
for try await chunk in client.completeStreaming(messages: [.system("..."), .user("...")]) {
    text += chunk
}

// Parse JSON response
let result = response.decodeJSON(as: MyResponse.self)
```

API key resolution: Keychain → Secrets.plist → Environment variable.

### Subscriptions (`App/Services/Subscription/`)

```swift
// Check premium status
if adaptyManager.isPremium { /* premium feature */ }

// Purchase
let success = await adaptyManager.purchase(product)

// Restore
let restored = await adaptyManager.restore()
```

Configured via `AdaptyConfig` — set your API key and placement ID.

### Navigation (`App/App/Router.swift`)

```swift
// Push
router.navigate(to: .profile(userId: "123"))

// Sheet
router.present(.compose)

// Full screen cover
router.presentFullScreen(.onboarding)

// Back
router.pop()
router.popToRoot()
```

Add destinations in `Router.Destination`, sheets in `Router.Sheet`, covers in `Router.FullScreenCover`.

---

## Configuration

### API Keys

Copy `Secrets.plist.example` → `App/Resources/Secrets.plist` and fill in:

| Key | Where to get |
|-----|-------------|
| `OPENAI_API_KEY` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `ADAPTY_API_KEY` | Adapty Dashboard → App settings → General |
| `KIE_API_KEY` | [kie.ai](https://kie.ai) (for `/imagine` skill) |

### project.yml

XcodeGen configuration. Uncomment dependencies as needed:
- **Firebase**: analytics, auth, crash reporting
- **Supabase**: backend, auth, database

After editing `project.yml`, run `xcodegen generate` to regenerate `.xcodeproj`.

### CLAUDE.md

Agent behavior rules. Defines:
- What the agent does autonomously vs. asks permission for
- Development process (speckit workflow)
- Code patterns and technical constraints
- Communication style
- Escalation rules

---

## Requirements

- Xcode 16+
- iOS 17.0+ deployment target
- [XcodeGen](https://github.com/yonaskolb/XcodeGen): `brew install xcodegen`
- [SwiftLint](https://github.com/realm/SwiftLint) (optional): `brew install swiftlint`
- [Claude Code](https://claude.ai/claude-code) for AI-powered workflow
