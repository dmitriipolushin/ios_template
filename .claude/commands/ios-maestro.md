---
description: "Maestro E2E testing for iOS. Generates YAML flows from specs/user stories, runs tests on simulator, reports results. Use when: 'e2e test', 'maestro', 'test on device', 'run the app and test'."
---

# iOS Maestro — E2E Testing

Generate and run Maestro YAML test flows for iOS apps. Complements `/ios-qa` (static analysis)
with dynamic runtime testing on simulator.

## Arguments

$ARGUMENTS — optional: action (generate|run|both), specific feature/flow to test.
Default action: both (generate missing flows + run all).

---

## Phase 1: Environment Check

### 1.1 Check Maestro installed

```bash
maestro --version 2>/dev/null || echo "NOT_INSTALLED"
```

If NOT_INSTALLED:
```
Maestro CLI не установлен. Установить?
  curl -fsSL "https://get.maestro.mobile.dev" | bash
Требует: Java 17+ (проверь java -version)
```

**Version:** parallel runs need **Maestro ≥ 2.6** (checked on 2.11.0). On older versions every
iOS driver listens on the fixed port `127.0.0.1:7001`: if another project's session is running
tests, your flows read *its* simulator's screen and fail with "Element not found".
```bash
maestro --version 2>/dev/null | tail -1   # < 2.6 → offer the upgrade
curl -fsSL "https://get.maestro.mobile.dev" | bash   # upgrades in place (~300 MB)
```
The install in `~/.maestro` is shared by every project on the machine: upgrading it breaks the
run of any session that is running tests at that moment. Ask the user before upgrading.

### 1.2 Pick this project's simulator

Use one dedicated simulator per project (e.g. "<App> QA") and pin its UDID. Other projects'
simulators may be booted too: never run against them, never shut them down.

```bash
xcrun simctl list devices | grep -E "iPhone|iPad"
SIM_UDID=<UDID of this project's simulator>
xcrun simctl boot "$SIM_UDID" 2>/dev/null   # no-op if already booted
```

No dedicated simulator yet → create one:
```bash
xcrun simctl create "<App> QA" "iPhone 17 Pro"
```

### 1.3 Check app installed on simulator

```bash
xcrun simctl listapps "$SIM_UDID" 2>/dev/null | grep -i "CFBundleIdentifier" | head -10
```

If app not installed → build and install:
```bash
xcodebuild build -scheme "<SCHEME>" -destination "id=$SIM_UDID" -quiet
APP_PATH=$(find ~/Library/Developer/Xcode/DerivedData -name "*.app" -path "*Debug-iphonesimulator*" | head -1)
xcrun simctl install "$SIM_UDID" "$APP_PATH"
```

### 1.4 Load spec context

```bash
ls specs/*/spec.md 2>/dev/null
ls .specify/features/*/spec.md 2>/dev/null
```

If spec exists → read user stories for flow generation.

---

## Phase 2: Generate Flows from Spec

For each **User Story** in spec.md, generate a Maestro YAML flow.

### 2.1 Naming convention

```
.maestro/
  {feature}/
    {feature}_{scenario}.yaml
```

Examples:
- `.maestro/onboarding/onboarding_happy_path.yaml`
- `.maestro/onboarding/onboarding_skip_notifications.yaml`
- `.maestro/routine/routine_create_from_pack.yaml`
- `.maestro/routine/routine_execution_complete.yaml`
- `.maestro/paywall/paywall_close_without_purchase.yaml`

### 2.2 Flow template

```yaml
# {User Story Title}
# {Description of what this flow verifies}
#
# Prerequisites: {state needed}
# Expected: {expected outcome}

appId: ${APP_ID}
name: {Human-readable name}
tags:
  - {priority: smoke|regression|edge-case}
  - {feature: onboarding|routine|paywall|settings}
---
- launchApp:
    clearState: true  # for flows that need fresh state

# Step 1: {description}
- assertVisible:
    id: "{screen_identifier}"
- tapOn:
    id: "{button_identifier}"

# Step 2: {description}
- assertVisible: "{expected text}"

- takeScreenshot: {flow_name}_result
```

### 2.3 accessibilityIdentifier convention

When generating flows, use this naming:

| Element | Pattern | Example |
|---------|---------|---------|
| Screen container | `{feature}_{screen}_screen` | `onboarding_welcome_screen` |
| Primary button | `{feature}_{action}_button` | `onboarding_continue_button` |
| Back button | `{feature}_back_button` | `onboarding_back_button` |
| Text input | `{feature}_{field}_input` | `onboarding_name_input` |
| Tab bar item | `tab_{name}` | `tab_routines` |
| Close/dismiss | `{feature}_close_button` | `paywall_close_button` |
| List item | `{feature}_item_{index}` | `routine_item_0` |

**IMPORTANT:** After generating flows, list all required `accessibilityIdentifier` values
that need to be added to Swift code. Format:

```
## Required accessibilityIdentifiers

### OnboardingWelcomeView.swift
- `onboarding_welcome_screen` → root VStack
- `onboarding_continue_button` → primary Button

### RoutinesTabView.swift
- `routines_screen` → root view
- `add_routine_button` → toolbar add button
```

### 2.4 Flow categories to generate

For each spec, generate flows covering:

| Category | Priority | What to test |
|----------|----------|-------------|
| Happy path | P0 (smoke) | Main user journey end-to-end |
| Back navigation | P1 (regression) | Back button on every screen |
| Permission denied | P1 | App works when permissions denied |
| Edge cases | P2 | Empty states, max limits, special characters |
| Double tap | P2 | Rapid taps don't break UI |
| Offline | P3 (edge-case) | App handles no network gracefully |

---

## Phase 3: Run Tests

### 3.1 Run all flows

```bash
APP_ID=$(grep -m1 "PRODUCT_BUNDLE_IDENTIFIER" project.yml 2>/dev/null | awk '{print $2}')
APP_ID=${APP_ID:-com.example.app}
maestro --udid "$SIM_UDID" test -e APP_ID="$APP_ID" .maestro/ 2>&1
```

### 3.2 Run by tag

```bash
# Smoke tests only (P0)
maestro --udid "$SIM_UDID" test -e APP_ID="$APP_ID" --include-tags=smoke .maestro/

# Specific feature
maestro --udid "$SIM_UDID" test -e APP_ID="$APP_ID" --include-tags=onboarding .maestro/
```

### 3.3 Run single flow

```bash
maestro --udid "$SIM_UDID" test -e APP_ID="$APP_ID" .maestro/onboarding/onboarding_happy_path.yaml
```

### 3.4 Continuous mode (for debugging)

```bash
maestro --udid "$SIM_UDID" test -c -e APP_ID="$APP_ID" .maestro/onboarding/onboarding_happy_path.yaml
```

### 3.5 Parallel sessions & pitfalls (Maestro ≥ 2.6)

Several Claude sessions (different projects) can run Maestro at the same time, one simulator each:

- **Always pin the device:** `maestro --udid "$SIM_UDID" test ...`. Without it Maestro takes the
  first booted simulator, which may be another project's.
- **Ports are per device** since 2.6: each iOS driver gets its own random port (e.g. 60015). There
  is **no** `--driver-host-port` flag in 2.11 (despite blog posts) and none is needed.
- **Never shut down or erase another project's simulator**, even if it is booted and in the way.
- **Diagnose "Element not found" on a screen you can see**: `lsof -nP -iTCP -sTCP:LISTEN | grep
  maestro-d`, then `ps -o command= -p <pid>`. The `Devices/<UDID>` in the path says which
  simulator the driver belongs to. On Maestro < 2.6 this is the port-7001 collision: upgrade.
- **Safari "choose search engine" dialog:** a flow that opens a link (terms, privacy, paywall)
  launches Safari, and iOS may raise a system dialog that covers every later flow. Maestro cannot
  see it. Clear it with `xcrun simctl terminate "$SIM_UDID" com.apple.mobilesafari`, and run
  link-opening flows last.
- **Screenshots land in the cwd** (`takeScreenshot`, `testOutputDir`): run from the repo root.

---

## Phase 4: Report Results

```
# Maestro E2E Report

**Project:** <name>
**Date:** YYYY-MM-DD
**Device:** <simulator name + iOS version>
**Flows run:** X total

---

## Results

| Flow | Status | Duration | Notes |
|------|--------|----------|-------|
| onboarding_happy_path | ✅ Pass | 12s | |
| onboarding_back_nav | ❌ Fail | 8s | Back button blocked on screen 13 |
| tab_navigation | ✅ Pass | 5s | |
| double_tap_prevention | ⚠️ Flaky | 6s | Passed 2/3 runs |

---

## Failed Flows Detail

### onboarding_back_nav
**Failed at step:** tapOn: id "onboarding_back_button"
**Error:** Element not found / not interactable
**Screenshot:** build/maestro-results/back_nav_fail.png
**Root cause:** .scaledToFill() image blocking hit area (H01)

---

## Coverage

| User Story | Flows | Status |
|------------|-------|--------|
| US1: Onboarding | 3 flows | 2 pass, 1 fail |
| US2: Routine execution | 2 flows | 2 pass |
| US3: Routine management | 1 flow | 1 pass |

---

## Recommendations

1. Fix failing flows before release
2. Add missing accessibilityIdentifiers (list below)
3. Run `maestro test --include-tags=smoke` in CI
```

---

## Phase 5: Add accessibilityIdentifiers to Code

After generating flows, if identifiers are missing from Swift code:

1. Read the view file
2. Add `.accessibilityIdentifier("id")` to the relevant elements
3. **Never change existing identifiers** — only add missing ones
4. Prefer adding to the outermost container of each screen

Example:
```swift
// Before
VStack {
    Text("Welcome")
    Button("Continue") { onNext() }
}

// After
VStack {
    Text("Welcome")
    Button("Continue") { onNext() }
        .accessibilityIdentifier("onboarding_continue_button")
}
.accessibilityIdentifier("onboarding_welcome_screen")
```

---

## Rules

1. **Always use `id:` selectors** (accessibilityIdentifier) — never rely on text for interactive elements in localized apps
2. **Use `optional: true`** for elements that may not appear on every run (permission dialogs, paywall)
3. **Always `takeScreenshot`** at the end of each flow — evidence for pass/fail
4. **Tag every flow** — smoke for P0, regression for P1, edge-case for P2+
5. **One assertion per step** — if a step fails, you know exactly what broke
6. **Subflows for reuse** — put common sequences (skip onboarding, login) in `subflows/`
7. **`clearState: true`** for onboarding flows, omit for flows testing returning users
8. **`${APP_ID}` variable** — never hardcode bundle ID, pass via `-e APP_ID=...`
9. **Always `--udid "$SIM_UDID"`** — this project's simulator only; other sessions may be running Maestro in parallel
