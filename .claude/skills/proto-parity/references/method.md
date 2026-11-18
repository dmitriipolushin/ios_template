# Measuring an app against an HTML prototype

The rules below come from a real parity pass (an iOS 26 SwiftUI app against a 402x874 HTML
prototype). Each one exists because the opposite produced a wrong conclusion that cost a fix
and then a revert.

## 1. One grid for both

Shoot the prototype at the simulator's point size with `deviceScaleFactor` equal to its
scale (iPhone 17 Pro: 402x874 @3x -> 1206x2622). The app's Maestro screenshots come out the
same size, so 1 pt = 3 px in both and every number can be compared directly. A different
device needs a different viewport, not a resize of the images.

## 2. The prototype's DOM is the reference, not its pixels

`getBoundingClientRect` gives the prototype's exact geometry (heading box, first card, row
heights). Pixel measurements of glyphs differ by a pixel between Chromium and Core Text
because they rasterise type differently. When pixels and DOM disagree, believe the DOM.
A handy check: if every page of a family has the same DOM geometry (same heading box, same
first-card top), any page-to-page spread in your pixel numbers is measurement noise, and a
page that stands out has a real cause.

## 3. Align by the screen's own CSS, not one global number

The prototype runs without a status bar; the app sits under a safe area (62 pt on iPhone 17
Pro, 34 pt home indicator). How a screen absorbs that depends on its CSS:

| CSS of the top edge | on the device | offset to apply |
|---|---|---|
| `padding-top: max(14px, env(safe-area-inset-top))` | 14 px replaced by 62 | +48 pt |
| `padding-top: calc(26px + env(safe-area-inset-top))` | 26 + 62 | +62 pt |
| absolute, full-screen layer (camera, scanner chrome) | unchanged | 0 |
| `bottom: calc(20px + env(safe-area-inset-bottom))` | +34 from the bottom | -34 pt for that block |

Read the CSS of the screen (or its container) before choosing. A bottom-anchored block and a
top-anchored one on the same screen need separate offsets. The app should reproduce what the
prototype would do on the device, which is what this table encodes.

## 4. Measure shapes, at the right place

- A card's top or bottom edge: sample at the card's centre column. Near the corners the edge
  curves, and CSS draws a circular radius where iOS draws a continuous (squircle) corner, so a
  column 10 pt from the edge reads 2-3 pt off even when the card is exactly in place.
- Use a shape as the reference for vertical gaps (the round back button's bottom edge, a
  separator line, a button's fill) rather than the top of a glyph.
- Separators are thin (0.5 pt); find them as "neither page nor card colour" rows (`px.py edges`).
- Buttons: the first run of the fill colour at the centre column (`px.py button-gap`).

## 5. Text: compare widths, not weight

- Chromium on macOS renders white text on a dark fill visibly heavier than iOS. Compare the
  ink width of the same string (`px.py ink-x`): equal widths mean the same font, size and
  tracking, whatever the strokes look like.
- If the widths match but a line wraps differently, check the room the line has: Chromium may
  keep a line whose ink is a fraction of a point wider than the box; Core Text breaks it. One
  point of extra room (a gap, a margin) is the fix, not a smaller font.
- iOS will not leave a single word alone on a last line: it carries the previous word down.
  A paragraph wrapping one word earlier than the prototype for that reason is platform
  typography, not a width problem.
- CSS `letter-spacing` maps to SwiftUI `.tracking` one to one. A missing tracking shows up as
  a string several points wider than the prototype's.

## 6. Line heights

CSS centres the half-leading of each line box above and below the glyphs; SwiftUI puts no
leading around a single line. Where the prototype sets `line-height` on a heading and a margin
under it, the visible distance between the heading's glyphs and the next line's glyphs is a few
points larger in the prototype. Measure glyph top to glyph top in both and compensate the
spacing by the measured difference (explain it in a comment), instead of guessing from the CSS.

## 7. SwiftUI List spacing (iOS 26)

Two neighbouring sections sit as far apart as the SMALLER of their `listSectionSpacing`
values, plus the next section's header height. Consequences:
- a section that wants less room around it sets its own value, and that value applies on both
  of its sides (a small value on one section also shrinks the gap above it);
- a header-less first group after a title section loses the 1 pt a floating header would add;
  pass that difference explicitly;
- a row inside an inset-grouped section is clipped to the group's rounded corners, so a card
  with its own radius and shadow belongs in a section header, not in a row.

## 8. Reading a difference image

`diff.py` thresholds |proto - app| and reports horizontal bands of differing pixels. Use the
bands to find WHERE to look, then measure that place with `px.py`. Typical bands:
- a band at every text line, a few hundred px each: antialiasing, ignore;
- a thick band from some y downwards: everything below that y is shifted; find the first
  element whose position differs;
- a short band of thousands of px: a block that is drawn differently (icon size, a missing
  shadow, a different placeholder colour).
Mask what cannot match before diffing: the status bar remnant at the top, the floating tab
bar, live data (codes, dates, prices), simulator-only notices.

## 9. Verdicts

- exact: 0 px.
- rounding: 1-2 px, the same on every page of the family. Two pixel grids round fractional
  positions in different directions; chasing it makes other devices worse.
- platform: a documented platform difference (references/known-differences.md).
- decision: the ticket or spec says something else than the prototype; the owner decides.
- mismatch: everything else, with the measured number and the suspected file:line.
