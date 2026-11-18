# Differences that are not defects

Report these as "platform" or "decision", with the reason, instead of fixing them. Fixing them
usually means replacing system behaviour with a hand-made imitation, which the owner of this
setup asked not to do ("do it the proper system way").

## Platform

| what | prototype | app | why it stays |
|---|---|---|---|
| group corners | CSS circular radius | iOS continuous corner | system List look; < 1 pt at the edge |
| switches | custom CSS toggle / On-Off pills | system `Toggle` | system control, same visual role |
| last line of a paragraph | may end on one word | iOS carries a word down | Core Text line breaking |
| white text on dark | looks bolder | lighter strokes | Chromium font smoothing; compare widths |
| text field placeholder without explicit CSS colour | Chromium default #757575 | system placeholder colour | the prototype did not choose; where it sets a colour (e.g. #8E8E93), match it |
| keyboard, share sheet, alerts, status bar | simulated or absent | system | system UI |
| 1-2 px everywhere on a family of pages | | | pixel-grid rounding, see method.md section 9 |

## Typical decisions (ask, do not decide)

- Copy the server supplies on purpose (legal consent wording, remote titles): the spec wins
  over the prototype's text; say so in the report.
- A navigation difference (a sheet with Done vs a pushed page with a back chevron): changing
  navigation needs the owner's approval in most projects.
- A hidden feature row (language picker hidden for an English-only launch).
- Strings the prototype shows in English inside a translated mode because its own translation
  table does not cover them: the app showing them in English matches the prototype; whether to
  translate them is a product decision.

## Environment, not app

- Prices, renewal dates, subscription rows missing on a simulator without an App Store
  product: compare with a real sandbox purchase or leave out of the verdict.
- Camera-unavailable notices and debug-only controls on simulator screenshots: mask them.
- A flow that needs a local test server (offline packs, mocks) cannot verify that path while
  the server is down; say which flows and why, do not mark them failed.
