---
description: "iOS design audit against Apple HIG. Reviews SwiftUI code for typography, colors, spacing, accessibility, dark mode, Dynamic Type, touch targets, navigation, and component usage. Use when: 'design review', 'visual audit', 'check HIG compliance', 'design polish'."
---

# iOS Design Review

Audit SwiftUI code against Apple Human Interface Guidelines.
This is a static analysis of source code — no simulator required.

## Arguments

$ARGUMENTS — optional: specific views/features to audit. If empty, audit all SwiftUI views.

## Phase 1: Discovery

Find all SwiftUI view files:
```bash
find . -name "*.swift" -not -path "*/.*" -not -path "*/Tests/*" | head -200
```

Use Grep to identify SwiftUI views (files containing `struct.*View.*body`).
Read each view file completely.

Also read:
- Asset catalog colors: `find . -name "*.colorset" -not -path "*/.*"`
- Asset catalog images: `find . -name "*.imageset" -not -path "*/.*"`
- Info.plist or project settings for supported orientations, appearances

## Phase 2: Audit Categories

Rate each category 0-10. For each finding, note the file, line, issue, and fix.

### 1. Typography (Weight: 15%)

**Rules:**
- Use semantic text styles (`.font(.body)`, `.font(.title)`) — they scale with Dynamic Type
- `.font(.system(size: N))` is a **violation** — it doesn't scale
- `.font(.custom("Name", fixedSize: N))` is a **violation** — use `relativeTo:` parameter
- Custom fonts must use `.font(.custom("Name", size: N, relativeTo: .body))` for scaling
- Minimum readable size: 11pt (`.caption2`)

**Search patterns:**
```
.font(.system(size:       → VIOLATION: fixed size, won't scale
.font(.custom(.*fixedSize → VIOLATION: fixed size custom font
.font(.system(            → Check: is it using .design/.weight only? OK. Has size:? BAD.
```

**Scoring:** -2 per fixed-size font, -1 per missing text style

### 2. Colors (Weight: 15%)

**Rules:**
- Use semantic colors: `Color(.label)`, `Color(.systemBackground)`, `Color(.secondaryLabel)`
- Use Asset Catalog colors with dark mode variants for brand colors
- `Color.black` / `Color.white` — **red flag** unless truly decorative (shadows, overlays)
- Hard-coded `Color(red:green:blue:)` or hex — **violation** unless in Asset Catalog
- `Color("name")` is OK if Asset Catalog has dark variant

**Search patterns:**
```
Color.black               → WARNING: doesn't adapt to dark mode
Color.white               → WARNING: doesn't adapt to dark mode
Color(red:                 → VIOLATION: hard-coded, no dark mode
Color(hex:                 → VIOLATION: hard-coded, no dark mode
Color(#                    → VIOLATION: hard-coded hex
UIColor(red:               → VIOLATION: hard-coded
.foregroundColor(.black)   → WARNING: use Color(.label) instead
.background(Color.white)   → WARNING: use Color(.systemBackground)
```

**Scoring:** -3 per hard-coded color in UI, -1 per Color.black/white

### 3. Spacing & Layout (Weight: 10%)

**Rules:**
- Standard horizontal margin: 16pt (compact) / 20pt (regular width)
- Default `.padding()` is ~16pt — preferred over hard-coded values
- `@ScaledMetric` for spacing that should scale with Dynamic Type
- `.ignoresSafeArea()` only for backgrounds/images, never for interactive content
- Content must respect safe area (notch, Dynamic Island, home indicator)

**Search patterns:**
```
.ignoresSafeArea()         → CHECK: is this for a background only?
.edgesIgnoringSafeArea(    → CHECK: same rule
.padding(.all, N)          → INFO: consider @ScaledMetric if N is non-standard
frame(width:.*height:      → CHECK: are these flexible or rigid?
```

**Scoring:** -2 per unsafe area violation, -1 per rigid frame on text content

### 4. Touch Targets (Weight: 10%)

**Rules:**
- Minimum touch target: **44×44 points** — Apple's firm guideline
- Buttons, links, toggles, interactive elements must meet this
- Small icons used as buttons need `.frame(minWidth: 44, minHeight: 44)` or adequate padding
- `.contentShape(Rectangle())` may be needed for tap areas on custom layouts

**Search patterns:**
```
Image(systemName:.*onTapGesture   → CHECK: does it have 44pt frame?
.frame(width: N, height: N)       → FLAG if N < 44 on interactive element
Button.*Image(systemName:         → CHECK: SF Symbol button, adequate size?
```

**Scoring:** -3 per interactive element below 44pt

### 5. Dark Mode (Weight: 10%)

**Rules:**
- App must look correct in both light and dark mode
- All custom colors need dark variants in Asset Catalog
- Elevated surfaces should be lighter in dark mode
- Images with transparency need dark mode variants if they contain assumed-light backgrounds
- No `.preferredColorScheme(.light)` forcing light mode globally

**Search patterns:**
```
.preferredColorScheme(.light)     → VIOLATION: forces light mode
.preferredColorScheme(.dark)      → VIOLATION: forces dark mode
.colorScheme                      → OK: conditional adaptation
```

**Also check:** Asset Catalog `.colorset` directories — do they have "Any, Dark" appearances?

**Scoring:** -3 per forced color scheme, -2 per custom color without dark variant

### 6. Dynamic Type (Weight: 10%)

**Rules:**
- All text must scale with Dynamic Type (semantic `.font()` styles)
- Layouts should adapt at accessibility sizes (stack vertically instead of horizontally)
- Use `@Environment(\.dynamicTypeSize)` to adapt layouts at large sizes
- Use `@ScaledMetric` for non-text dimensions that should scale (icons, spacing)
- Test: would this layout work at `.accessibilityExtraExtraExtraLarge`?

**Search patterns:**
```
.dynamicTypeSize(              → OK: limiting range, but check if too restrictive
.sizeCategory                  → OK: reading current size (legacy API)
@ScaledMetric                  → GOOD: scaling non-text values
HStack.*Text.*Text             → CHECK: will these overlap at AX sizes? Need VStack fallback?
```

**Scoring:** -2 per fixed-size text, -1 per HStack with text that could overflow

### 7. Accessibility (Weight: 10%)

**Rules:**
- All images need `.accessibilityLabel()` or `.accessibilityHidden(true)` if decorative
- Interactive elements need descriptive labels (not "button 1")
- Use `.accessibilityElement(children: .combine)` for grouped content
- Color must not be the only way to convey information (add icons/text)
- `.accessibilityHint()` for non-obvious actions
- Correct `.accessibilityTraits` (`.isButton`, `.isHeader`, `.isSelected`)

**Search patterns:**
```
Image(.*name:(?!.*accessib)       → WARNING: image without accessibility
.accessibilityHidden(true)        → OK: decorative
.accessibilityLabel(              → GOOD
```

**Scoring:** -2 per meaningful image without label, -1 per missing hint on complex interaction

### 8. Navigation (Weight: 5%)

**Rules:**
- Use `NavigationStack` (not deprecated `NavigationView`)
- `TabView` for top-level sections (3-5 tabs max)
- Tab items must not trigger sheets/actions — only switch sections
- `.sheet()` for lightweight tasks, `.fullScreenCover()` for immersive experiences
- Standard back button behavior preserved (swipe-to-go-back works)
- No hamburger menus — use TabView or NavigationStack

**Search patterns:**
```
NavigationView       → VIOLATION: deprecated, use NavigationStack
TabView.*tabItem.*>5 → WARNING: too many tabs
```

**Scoring:** -3 per NavigationView, -2 per non-standard navigation

### 9. Components (Weight: 5%)

**Rules:**
- Use system components when available (`Toggle`, `Picker`, `Stepper`, `DatePicker`)
- Only one `.buttonStyle(.borderedProminent)` per context (primary action)
- `List` for settings/forms, `LazyVStack` in `ScrollView` for custom layouts
- `ContentUnavailableView` for empty states (iOS 17+)
- `ProgressView` for loading states
- Alerts: title short, destructive action uses `.destructive` role, cancel always present

**Scoring:** -1 per missing system component replacement, -2 per missing empty/loading/error state

### 10. SF Symbols & Icons (Weight: 5%)

**Rules:**
- Use `.font()` to size SF Symbols (matches adjacent text), not `.resizable().frame()`
- Symbol weight should match adjacent text weight (`.fontWeight()`)
- Use appropriate rendering mode (monochrome, hierarchical, palette, multicolor)
- Prefer SF Symbols over custom icons when a matching symbol exists
- Never use text emoji as icons — use SF Symbols

**Scoring:** -1 per incorrectly sized symbol, -1 per custom icon where SF Symbol exists

### 11. Haptic Feedback (Weight: 2.5%)

**Rules:**
- `.sensoryFeedback()` (iOS 17+) or `UIImpactFeedbackGenerator` for meaningful interactions
- `.success` for completed actions, `.error` for failures, `.selection` for picker changes
- Don't overuse — haptics should be meaningful and sparse
- Must respect system "Reduce Motion" / haptic settings

### 12. Motion & Animation (Weight: 2.5%)

**Rules:**
- Prefer spring animations over linear/easeInOut: `.spring(response: 0.3, dampingFraction: 0.7)`
- Standard duration: 0.25-0.35s
- Check `@Environment(\.accessibilityReduceMotion)` — offer crossfade alternative
- `.animation()` should be scoped to specific values, not blanket `.animation(.default)`

**Search patterns:**
```
.animation(.default)          → WARNING: blanket animation, scope it
.animation(.*value:           → OK: scoped animation
withAnimation                 → OK
accessibilityReduceMotion     → GOOD: respecting preference
```

## Phase 3: Report

```
## iOS Design Review

### Scores by Category

| Category | Score | Weight | Weighted |
|----------|-------|--------|----------|
| Typography | X/10 | 15% | X.X |
| Colors | X/10 | 15% | X.X |
| Spacing & Layout | X/10 | 10% | X.X |
| Touch Targets | X/10 | 10% | X.X |
| Dark Mode | X/10 | 10% | X.X |
| Dynamic Type | X/10 | 10% | X.X |
| Accessibility | X/10 | 10% | X.X |
| Navigation | X/10 | 5% | X.X |
| Components | X/10 | 5% | X.X |
| SF Symbols | X/10 | 5% | X.X |
| Haptics | X/10 | 2.5% | X.X |
| Animation | X/10 | 2.5% | X.X |
| **TOTAL** | | | **X.X/10** |

### Grade: A/B/C/D/F

- A (9-10): Exemplary HIG compliance
- B (7-8.9): Good, minor issues
- C (5-6.9): Needs work, multiple violations
- D (3-4.9): Significant HIG violations
- F (0-2.9): Major redesign needed

### Findings

[List each finding with file, line, issue, fix code]
```

## Phase 4: Fix Loop (if user approves)

For each finding by severity:
1. Apply the fix (Edit tool)
2. Commit atomically: `style(design): DES-NNN - description`
3. Move to next finding

After all fixes, re-run the audit and report the score delta.

## Rules

- This is a **code audit**, not a visual audit. You're reading SwiftUI source code.
- Don't suggest design changes beyond HIG compliance (no aesthetic opinions).
- Don't flag patterns that are intentionally non-standard with clear comments.
- Focus on violations that affect real users: accessibility, usability, dark mode.
- Asset Catalog analysis: just check if dark variants exist, don't evaluate color choices.
