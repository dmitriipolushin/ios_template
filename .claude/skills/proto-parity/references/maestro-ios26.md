# Capturing the app with Maestro: traps that look like app bugs

Maestro 2.x on iOS 26 simulators. Each of these first looked like a defect in the app and was
not. Check a failed capture against this list before reporting a bug.

## Taking the screenshots

- Name every capture after the prototype state: `takeScreenshot: <prefix><state>` (for example
  `fsc264_35_support`), so `report.py` can pair them. One flow per screen family is enough;
  scroll positions get `_p1`, `_p2` like the prototype's scrolled shots.
- Run one batch per simulator, addressed by UDID, never `booted` (another session may own the
  booted one). `scripts/maestro/runflows.sh` does that and retries a run that died during
  driver start-up.
- Keep the Mac awake for long batches (`caffeinate -i -t 3600 &`): a sleeping Mac breaks the
  driver connection and the runs hang with a stack trace in run.log, no FAILED line.
- Flows that depend on state left by another flow (onboarding done, an item saved) say so in
  their header; run them in that order.
- A build configuration with another bundle id (Debug vs a production-like scheme) may also
  claim the app's URL scheme; uninstall it from test simulators before deep-link captures.

## Traps

- `hideKeyboard` does nothing on a List with `.scrollDismissesKeyboard(.interactively)`: its
  small swipes are not an interactive drag. `scrollUntilVisible` then calls a button under the
  keyboard "visible" and the tap hits the keyboard. Drag the content up instead
  (`swipe: {start: "50%, 45%", end: "50%, 12%"}`).
- `scrollUntilVisible` stops as soon as the element enters the screen, which can be under the
  floating tab bar; the tap at its centre lands on the tab bar (often the Scan button).
  Use `centerElement: true`, or for the last element of a page one more swipe up before the tap.
  `centerElement` cannot centre the very last element of a list and then times out.
- Scroll direction depends on where the list was left: coming back to a long list keeps its
  position, so an element above it needs `direction: UP`.
- The iOS 26 share sheet may open as a compact card with no Close button: dismiss it with a
  tap outside (`point: "50%,15%"`) under `runFlow: when: notVisible: <next element>`. While it
  is up the app's elements behind it are not in the hierarchy.
- A tap waits for the screen to settle. A toast followed by a sheet can keep it busy longer
  than the toast lives (5-9 s on a loaded Mac, `waitToSettleTimeoutMs` does not help enough):
  make the toast check `optional` and assert the sheet.
- System alerts: assert what follows after tapping OK, not under the alert.
- Accessibility sizes (`xcrun simctl ui <udid> content_size accessibility-extra-extra-extra-large`)
  make pages much longer; give scrolls long timeouts and set the size back to `large` after.
- Regex in text selectors: write `.` for characters you cannot type reliably (em dash, non-
  breaking hyphen, middle dot) instead of the character itself.
