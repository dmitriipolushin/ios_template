---
description: "iOS/Swift code review. Analyzes diff against base branch for crashes, security, concurrency, memory, architecture, and performance issues. Use when: 'review code', 'code review', 'check my diff', 'pre-landing review'."
---

# iOS Code Review

Perform a thorough code review of the current branch's diff against the base branch.
Focus on iOS/Swift-specific issues that static analysis misses.

## Arguments

$ARGUMENTS — optional: specific files or areas to focus on. If empty, review entire diff.

## Phase 1: Setup

```bash
# Detect base branch
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
CURRENT=$(git branch --show-current)
echo "Reviewing: $CURRENT against $BASE"
echo "---"
git diff "$BASE"...HEAD --stat
```

Collect the full diff:
```bash
git diff "$BASE"...HEAD
```

Read all changed Swift files in full (not just the diff) to understand context.

## Phase 2: Analysis

Review every changed file against this checklist, **in priority order**:

### P0 — Crashes & Data Loss
- [ ] Force unwraps (`!`) outside tests/IBOutlets — each one is a potential crash
- [ ] Force casts (`as!`) and force tries (`try!`)
- [ ] Unhandled optionals that could be nil at runtime
- [ ] Array index access without bounds checking
- [ ] Unowned references (`[unowned self]`) — prefer `[weak self]`
- [ ] Missing `@unknown default` in switch over system enums

### P1 — Security
- [ ] Hardcoded API keys, tokens, secrets (strings matching `sk-`, `api_key`, `secret`, `Bearer`, `token`)
- [ ] `UserDefaults` storing sensitive data (tokens, passwords, credentials) — must use Keychain
- [ ] `NSAllowsArbitraryLoads = true` in Info.plist without per-domain exceptions
- [ ] Sensitive data in `print()`, `NSLog()`, `os_log` without `.private` privacy
- [ ] Missing input validation at system boundaries (user input, API responses)

### P2 — Concurrency Safety
- [ ] Mutable state accessed from multiple actors/threads without isolation
- [ ] Missing `@MainActor` on ViewModels that update UI state
- [ ] `@unchecked Sendable` without documented thread-safety justification
- [ ] `Task { }` inside `onAppear` instead of `.task { }` modifier (no auto-cancellation)
- [ ] Missing `Task.isCancelled` / `checkCancellation()` in long-running loops
- [ ] Global/static mutable `var` (must be actor-isolated or `let`)
- [ ] Closures crossing actor boundaries capturing non-Sendable types

### P3 — Memory
- [ ] Missing `[weak self]` in stored closures, completion handlers, NotificationCenter observers
- [ ] Strong reference cycles between objects (delegate should be `weak`)
- [ ] `Task` stored as property without cancellation in `deinit` / disappear
- [ ] Closure-based APIs where the closure captures `self` strongly and object may outlive closure

### P4 — Architecture
- [ ] Business logic in SwiftUI Views (calculations, filtering, formatting in `body`)
- [ ] View directly importing networking/database frameworks
- [ ] ViewModel importing SwiftUI (except `@MainActor`)
- [ ] Concrete dependencies instead of protocol-based DI
- [ ] God objects (single class doing everything) — >300 lines is a red flag
- [ ] Singleton (`shared`) for mutable state — prefer actor or DI

### P5 — Performance
- [ ] Heavy computation inside `body` (sorting, filtering large arrays)
- [ ] `AnyView` type erasure — use `@ViewBuilder` instead
- [ ] `VStack`/`HStack` with large datasets — use `LazyVStack`/`LazyHStack`
- [ ] Missing pagination (loading all items at once)
- [ ] Large images without `.resizable()` or caching
- [ ] Synchronous I/O on main thread (file reads, JSON parsing of large data)
- [ ] ForEach without stable `Identifiable` id (index-based causes full re-renders)

### P6 — Modern Patterns (iOS 17+)
- [ ] `ObservableObject` + `@Published` in new code targeting iOS 17+ — use `@Observable`
- [ ] `@StateObject` — use `@State` with `@Observable`
- [ ] `@ObservedObject` — use plain property with `@Observable`
- [ ] `@EnvironmentObject` — use `@Environment` with `@Observable`
- [ ] `NavigationView` — use `NavigationStack`
- [ ] `Combine` (sink, AnyCancellable, Subject) where `async/await` suffices
- [ ] `onChange(of:perform:)` (deprecated) — use `onChange(of:) { oldValue, newValue in }`

### P7 — Code Quality
- [ ] Functions > 50 lines
- [ ] Files > 500 lines
- [ ] Cyclomatic complexity > 10 (deeply nested if/switch/guard)
- [ ] Dead code (unused functions, unreachable branches)
- [ ] String literals used as identifiers instead of enums/constants
- [ ] Duplicate code blocks (>10 lines identical)

## Phase 3: Report

For each finding, output in this format:

```
### [SEVERITY] Title
**File:** `path/to/file.swift:LINE`
**Category:** P0-Crash | P1-Security | P2-Concurrency | P3-Memory | P4-Architecture | P5-Performance | P6-ModernPatterns | P7-Quality

**What:** Description of the issue
**Why:** Why this is a problem (crash scenario, security risk, performance impact)
**Fix:**
```swift
// Before
problematic code

// After
fixed code
```
```

### Severity Levels

- **CRITICAL** — Must fix before merge. Crashes, security vulnerabilities, data races, data loss.
- **WARNING** — Should fix. Memory leaks, architectural violations, deprecated APIs, performance issues.
- **INFO** — Consider fixing. Style, modern patterns, minor improvements. Don't block merge for these.

## Phase 4: Summary

End with a summary:

```
## Review Summary

**Branch:** feature/xxx → main
**Files reviewed:** N
**Findings:** X critical, Y warnings, Z info

### Verdict: ✅ APPROVE | ⚠️ APPROVE WITH CONCERNS | ❌ REQUEST CHANGES

[One-line rationale]
```

**Verdict rules:**
- Any CRITICAL finding → ❌ REQUEST CHANGES
- 3+ WARNINGs → ⚠️ APPROVE WITH CONCERNS
- Only INFO → ✅ APPROVE

## Rules

- Review ONLY changed lines and their immediate context. Don't audit the entire codebase.
- Don't flag style preferences (trailing commas, brace style) — that's SwiftLint's job.
- Don't suggest adding documentation/comments unless logic is genuinely unclear.
- Don't flag test code for force unwraps or force tries — that's acceptable in tests.
- If a pattern looks intentional (e.g., force unwrap with a comment explaining why), note it as INFO, not CRITICAL.
- Be specific: always include file path, line number, and concrete fix code.
- Don't review generated files, Pods, or Package.resolved.
