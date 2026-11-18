---
name: proto-parity
description: Pixel-level parity check of a mobile app (iOS/SwiftUI, Maestro screenshots) against an HTML/web prototype. Shoots every prototype state with Playwright at the device size, captures the app's same states, aligns them by the prototype's own safe-area CSS, measures geometry from shapes (card edges, separators, buttons) in physical pixels, makes side-by-side montages and masked difference images, and diffs the visible copy and the translation table. Use it whenever the app has to match a prototype, mockup HTML or a new prototype version ("full match with the prototype", "полное совпадение с прототипом", "сверь с прототипом", "pixel perfect", "сравни с макетом", "новый прототип vNNN"), when someone asks why a screen looks different from the prototype, or when a layout fix needs before/after evidence, even for a single screen. Not for Figma or local .fig files (use the figma or fig-pixel-parity skill) or for a HIG audit (ios-design-review).
---

# Prototype parity

Make an app screen match its HTML prototype and prove it with numbers: positions in physical
pixels, a difference image, and a copy and translation check. The method in
`references/method.md` is the core of this skill; the scripts only make it repeatable.

Two modes. Default to **report** unless the user asked for fixes ("поправь", "fix it", "make
it match"):
- **report**: capture, compare, explain every difference with a measured number and a verdict.
- **report + fix**: the same, then fix the mismatches, rebuild, re-capture only the affected
  states and re-measure until each state is exact, rounding, platform or decision.

## Setup (once per machine)

```bash
cd <skill>/scripts && npm install          # playwright-core only; no browser download
```
Needs: Node, a Chromium in the Playwright cache (or `PARITY_CHROMIUM=<path>`), ffmpeg/ffprobe,
Python 3, ImageMagick 7 (`magick`) for the difference image (ffmpeg fallback without it),
Maestro and a simulator for the app side. All script paths below are relative to this skill.

## Workflow

### 1. Inventory the prototype

Read the prototype's script for the functions that open screens and set state (`nav`,
`openView`, `render*`), and the CSS of each screen's top and bottom edge (safe-area formula).
Write the project's `states.json` and `parity.json` (formats and an example in
`references/config.md`; keep them in the project, for example `.maestro/parity/`). One state per
screen and per meaningful variant (guest, signed in, member, empty, typed, error, scrolled).

### 2. Shoot the prototype

```bash
node scripts/proto/shoot.mjs <prototype.html> <states.json> <proto_out> --width 402 --height 874 --scale 3
node scripts/proto/strings.mjs <prototype.html> <proto_out>/strings.txt
```
Per state: `<name>.png`, `<name>.txt` (visible text), `<name>.geo.json` (DOM boxes, font,
line-height, letter-spacing, colours). The DOM numbers are the reference (method.md section 2).

### 3. Capture the app

Each state needs a Maestro `takeScreenshot: <prefix><name>`. Reuse the project's flows; write
the missing ones (the ios-maestro skill helps). Run batches per simulator with
`scripts/maestro/runflows.sh` (`APP_ID=... runflows.sh <udid> <out> flows...`). Before reporting
a failed capture as an app bug, read `references/maestro-ios26.md`.

### 4. Compare

```bash
python3 scripts/compare/report.py --config <parity.json> --out <report_dir>
```
For every state with both shots: `pairs/<name>.png` (prototype | app), `diff/<name>_diff.png`
(differences in red), `_blend.png`, `_abs.png`, `_stats.json` (differing pixels and the bands
they gather in), and the first card's position against a shape reference. `report.md` sums it
up with a first-pass verdict.

Then look at every pair yourself (open the PNGs): icon sizes, colours, wrapping, missing
shadows do not always show as geometry. Drill into anything suspicious:
```bash
python3 scripts/compare/px.py edges <png> <x_px> <y0_px> <y1_px>    # card edges, separators
python3 scripts/compare/px.py ink-x <png> <y0> <y1> <x0> <x1>       # a text line's width
python3 scripts/compare/px.py button-gap <png>                      # card -> button gap
python3 scripts/compare/px.py color <png> <x> <y>                   # placeholder, disabled fill
python3 scripts/compare/gap.py --proto-dir ... --app-dir ... --prefix ... --names ...
python3 scripts/compare/diff.py <proto.png> <app.png> <prefix> --offset-pt 48 --mask-top 14 --mask-bottom 110
```
Compare a measurement with the same measurement in the prototype, never with a number from
memory, and measure where method.md says (card centre, shapes, ink width).

### 5. Copy and translations

```bash
python3 scripts/copy/copy_inventory.py --states <proto_out> --catalog <Localizable.xcstrings> \
    --swift <App dir> --out <report_dir>/copy.md [--ignore <ignore.txt>]
python3 scripts/copy/translations.py --proto <prototype.html> --catalog <Localizable.xcstrings> \
    --var T --source en --out <report_dir>/translations.md        # --apply writes the prototype's wording
```
`--states` checks the visible text of the shot states, per state (start there; `--rendered` and
`--scripts` widen it to the whole prototype, demo data included). Live values do not count as
differences ("34 of 80 MB" matches "%@ of %@ MB"). `typography` (quotes, dashes, ellipsis,
non-breaking characters) and `near` are copy differences to look at; `missing` needs judgement:
not built, server-supplied copy, or a prototype-only group (demo/testing rows: put those lines in
the ignore file once). Translations matter even when a language picker is hidden if the app
follows the phone's language.

### 6. Verdict per state

Use the categories in method.md section 9: exact, rounding, platform (see
`references/known-differences.md`), decision, mismatch. A uniform 1-2 px on every page of a
family is rounding; a page that differs from its siblings has a cause worth finding. Before
calling something a mismatch, rule out the measurement (wrong offset formula, a corner sample,
a glyph reference, environment data).

### 7. Fix mode

For each mismatch: find the code that draws it, change the value that the measurement points
to (explain the prototype rule in a short code comment, for example `.pill{margin:28px 0 0}`),
rebuild, re-capture only the affected states, re-run `report.py --names ...`. Prefer the
system's own mechanisms; do not imitate system UI to win a pixel. When the ticket or spec
contradicts the prototype, or the change touches navigation, stop and ask.

## Report to the user

Write it in the user's language. Structure:

1. One line: how many states compared, how many exact / rounding / platform / decision /
   mismatch (and fixed, in fix mode), and what was not compared and why.
2. Mismatches (or fixes): state, what differs, measured prototype vs app, the cause, file:line.
3. Platform differences and decisions for the owner, each with its reason.
4. Copy and translations: typography and wording differences, missing strings worth a look.
5. Where the evidence is: report_dir with pairs and diff images.

Do not claim "exact" for anything you did not measure, and do not count a capture that could
not run (missing test server, environment data) as a pass or a fail; list it separately.
