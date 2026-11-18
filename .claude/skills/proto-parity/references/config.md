# Project files for a parity pass

Keep both files in the project (for example under `.maestro/parity/`) so the next pass reuses
them. The skill itself holds no project paths.

## states.json: how to reach each prototype state

```json
[
  { "name": "35_support", "js": ["nav('you')", "openSupport()"], "scroll": true },
  { "name": "37_ask", "js": ["nav('you')", "openReportScreen('other')"] },
  { "name": "m02_member_downloading",
    "js": ["PLUS.member=true; PLUS.offline.on=true; PLUS.offline.ready=false;", "openPlus()"],
    "wait": 300, "geometry": ["#offBar"] }
]
```

- `name`: the state; the app screenshot is `<appPrefix><name>.png`.
- `js`: steps evaluated in the page in order (state setup, then navigation). Find the
  prototype's own functions (`openView`, `render*`, `nav`) by searching its script; prefer
  them to clicking.
- `wait`, `stepWait`: ms; animations in the prototype need them.
- `scroll`: also shoot the scrolled screen page by page.
- `geometry`: extra selectors for `<name>.geo.json`.

## parity.json: how to compare

```json
{
  "prototype": "../../docs/prototype_v534.html",
  "states": "states.json",
  "protoShots": "../../build/parity/proto",
  "appShotDirs": ["../../build/maestro/final"],
  "appPrefixes": ["fsc264_", "s2_"],
  "defaultOffsetPt": 48,
  "offsets": { "29_redeem_guest_signin": 62, "a07_scanner_barcode": 0 },
  "maskTopPt": 14,
  "maskBottomPt": 110,
  "masks": { "*": [], "33_invite_signed": [[200, 140, 182, 40]] },
  "gapRef": "button",
  "fuzz": 8,
  "translations": { "var": "T", "source": "en", "catalog": "../../App/Resources/Localizable.xcstrings" },
  "copy": { "swift": ["../../App"], "catalog": "../../App/Resources/Localizable.xcstrings" }
}
```

- Paths are relative to parity.json.
- `offsets`: per-state alignment in points (method.md section 3); `defaultOffsetPt` for the rest.
- `maskTopPt`: what is left of the app's status bar after alignment (62 - 48 = 14 for top-bar
  pages). `maskBottomPt`: the floating tab bar. `masks`: rectangles in points after alignment,
  `"*"` for every state; mask live data (codes, dates, prices).
- `gapRef`: `button` (the round back button, a shape) or `title` (glyphs, 1 px noisier).
- `fuzz`: per-pixel tolerance in percent for the difference image.
