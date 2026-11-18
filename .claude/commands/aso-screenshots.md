---
description: "Generate App Store screenshots. Creates marketing slides with device frames, backgrounds, and text — exported as pixel-perfect PNGs in all required Apple sizes. Use when: 'aso screenshots', 'app store screenshots', 'marketing screenshots', 'store listing'."
---

# ASO Screenshot Generator

Generate pixel-perfect App Store screenshots from real app screenshots + marketing text.

## Arguments

$ARGUMENTS — what to generate. Can include:
- App name and taglines for each slide
- Paths to real app screenshots (from simulator or device)
- Color scheme / brand colors
- Style preference (minimal, gradient, bold, dark)
- Number of slides (1-10, default 5)
- Locales if multilingual

## Phase 1: Gather Inputs

### 1.1 Check environment

```bash
# Node.js (required for Puppeteer rendering)
node --version 2>/dev/null || echo "NO_NODE"

# Puppeteer
npm list -g puppeteer 2>/dev/null || npm list puppeteer 2>/dev/null || echo "NO_PUPPETEER"

# Image optimization tools
which pngquant 2>/dev/null || echo "NO_PNGQUANT"
which optipng 2>/dev/null || echo "NO_OPTIPNG"
```

If Node.js is missing → STOP:
```
⛔ Node.js required for screenshot rendering.
Install: brew install node
```

If Puppeteer is missing, install it locally:
```bash
npm install puppeteer
```

### 1.2 Collect screenshot inputs

Ask the user for (if not provided in $ARGUMENTS):

1. **App screenshots** — paths to PNG/JPEG files captured from simulator or device
   - Best source: Simulator → File → Save Screen (⌘S)
   - Or: `xcrun simctl io booted screenshot ~/Desktop/screen1.png`

2. **Slide content** — for each slide:
   - Headline (5-7 words max, must be readable on thumbnail)
   - Subheadline (optional, 1 short sentence)
   - Which app screenshot to use

3. **Brand config**:
   - Primary color (hex, e.g. `#6C5CE7`)
   - Secondary color (hex, for gradient)
   - Font preference: `sf-pro` (default), `sf-pro-rounded`, or custom
   - Style: `gradient` (default), `solid`, `dark`, `light`

4. **Device frame**: `iphone-15-pro` (default), `iphone-15`, `none`

5. **Target sizes** (default: both):
   - iPhone 6.9" → 1320 x 2868 px (recommended, covers all iPhones)
   - iPad 13" → 2064 x 2752 px (if iPad supported)

### 1.3 Validate inputs

- Check all screenshot paths exist and are valid images
- Warn if screenshots are not retina resolution (width < 1000px)
- Confirm slide count (1-10)

## Phase 2: Plan & Confirm

Show the user a slide plan before generating:

```
📱 ASO Screenshot Plan

Slide 1: "Track Your Habits Daily"
  └ Screenshot: ~/Desktop/home-screen.png
  └ Background: gradient #6C5CE7 → #A29BFE

Slide 2: "Beautiful Analytics"
  └ Screenshot: ~/Desktop/analytics.png
  └ Background: gradient #6C5CE7 → #A29BFE

...

Export sizes: iPhone 6.9" (1320x2868)
Device frame: iPhone 15 Pro
Style: gradient

Proceed? (y/n)
```

Wait for confirmation.

## Phase 3: Generate Background (optional — kie.ai)

If the user wants AI-generated backgrounds instead of CSS gradients:

```bash
curl -s -X POST "https://api.kie.ai/api/v1/jobs/createTask" \
  -H "Authorization: Bearer $KIE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nano-banana-2",
    "input": {
      "prompt": "Abstract flowing gradient waves in soft purple and pink tones, smooth organic shapes, dreamy atmospheric depth, digital art, minimal and elegant, no text, no objects",
      "image_input": [],
      "aspect_ratio": "9:16",
      "resolution": "1K",
      "output_format": "png"
    }
  }'
```

Poll for results, download to `/tmp/aso-bg-{n}.png`.

Skip this phase if user chose CSS gradient backgrounds (default).

## Phase 4: Build HTML Templates

Create a temporary directory and generate one HTML file per slide.

```bash
mkdir -p /tmp/aso-screenshots/html
mkdir -p /tmp/aso-screenshots/output
```

### HTML Template Structure

Each slide is an HTML file rendered at exact pixel dimensions. Write the HTML file using the Write tool.

Template structure for each slide (`/tmp/aso-screenshots/html/slide-{n}.html`):

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    width: {{WIDTH}}px;
    height: {{HEIGHT}}px;
    overflow: hidden;
    font-family: -apple-system, 'SF Pro Display', 'Helvetica Neue', sans-serif;
  }

  .slide {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    padding: {{PADDING_TOP}}px {{PADDING_SIDE}}px 0;
    background: {{BACKGROUND}};
    /* If using AI background image instead of gradient: */
    /* background: url('file:///tmp/aso-bg-1.png') center/cover; */
  }

  .headline {
    font-size: {{HEADLINE_FONT_SIZE}}px;
    font-weight: 800;
    color: white;
    text-align: center;
    line-height: 1.15;
    margin-bottom: {{HEADLINE_MARGIN}}px;
    max-width: 90%;
    /* text-shadow for readability over complex backgrounds */
    text-shadow: 0 2px 20px rgba(0,0,0,0.15);
  }

  .subheadline {
    font-size: {{SUBHEADLINE_FONT_SIZE}}px;
    font-weight: 400;
    color: rgba(255,255,255,0.85);
    text-align: center;
    margin-bottom: {{SUB_MARGIN}}px;
    max-width: 80%;
  }

  .device-container {
    flex: 1;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    width: 100%;
    overflow: hidden;
  }

  .device-frame {
    position: relative;
    width: {{DEVICE_WIDTH}}px;
    /* Device frame with rounded corners and shadow */
    border-radius: {{DEVICE_RADIUS}}px;
    overflow: hidden;
    box-shadow: 0 20px 80px rgba(0,0,0,0.3), 0 0 0 {{BEZEL}}px #1a1a1a;
    /* Push device down so bottom is cropped — creates depth effect */
    transform: translateY({{DEVICE_OFFSET}}px);
  }

  .device-frame img {
    width: 100%;
    display: block;
  }

  /* Optional notch/dynamic island */
  .dynamic-island {
    position: absolute;
    top: {{DI_TOP}}px;
    left: 50%;
    transform: translateX(-50%);
    width: {{DI_WIDTH}}px;
    height: {{DI_HEIGHT}}px;
    background: #000;
    border-radius: {{DI_RADIUS}}px;
    z-index: 10;
  }
</style>
</head>
<body>
<div class="slide">
  <h1 class="headline">{{HEADLINE}}</h1>
  <p class="subheadline">{{SUBHEADLINE}}</p>
  <div class="device-container">
    <div class="device-frame">
      <div class="dynamic-island"></div>
      <img src="file://{{SCREENSHOT_PATH}}" />
    </div>
  </div>
</div>
</body>
</html>
```

### Size Presets

**iPhone 6.9" (1320 x 2868)**:
- `WIDTH`: 1320, `HEIGHT`: 2868
- `PADDING_TOP`: 180, `PADDING_SIDE`: 60
- `HEADLINE_FONT_SIZE`: 96
- `SUBHEADLINE_FONT_SIZE`: 48
- `HEADLINE_MARGIN`: 20, `SUB_MARGIN`: 60
- `DEVICE_WIDTH`: 900
- `DEVICE_RADIUS`: 60, `BEZEL`: 12
- `DEVICE_OFFSET`: 120 (how much to crop bottom)
- Dynamic Island: `DI_TOP`: 18, `DI_WIDTH`: 180, `DI_HEIGHT`: 50, `DI_RADIUS`: 25

**iPad 13" (2064 x 2752)**:
- `WIDTH`: 2064, `HEIGHT`: 2752
- `PADDING_TOP`: 160, `PADDING_SIDE`: 100
- `HEADLINE_FONT_SIZE`: 108
- `SUBHEADLINE_FONT_SIZE`: 54
- `HEADLINE_MARGIN`: 24, `SUB_MARGIN`: 60
- `DEVICE_WIDTH`: 1500
- `DEVICE_RADIUS`: 30, `BEZEL`: 10
- `DEVICE_OFFSET`: 100
- No Dynamic Island

### Background Styles

Based on user's style choice, set `{{BACKGROUND}}`:

- **gradient** (default): `linear-gradient(160deg, {{PRIMARY}} 0%, {{SECONDARY}} 100%)`
- **solid**: `{{PRIMARY}}`
- **dark**: `linear-gradient(160deg, #1a1a2e 0%, #16213e 50%, {{PRIMARY}}44 100%)`
- **light**: `linear-gradient(160deg, #f8f9fa 0%, #e9ecef 50%, {{PRIMARY}}22 100%)`
  - Also change headline color to `#1a1a1a` and subheadline to `rgba(0,0,0,0.6)`

### Multiple Slide Variations

For variety across slides, rotate the gradient angle:
- Slide 1: `160deg`, Slide 2: `200deg`, Slide 3: `140deg`, Slide 4: `180deg`, Slide 5: `220deg`

Or alternate between primary→secondary and secondary→primary gradients.

## Phase 5: Render with Puppeteer

Create a Node.js render script:

```bash
cat > /tmp/aso-screenshots/render.mjs << 'SCRIPT'
import puppeteer from 'puppeteer';
import { readdir } from 'fs/promises';
import { join } from 'path';

const htmlDir = '/tmp/aso-screenshots/html';
const outDir = '/tmp/aso-screenshots/output';

const browser = await puppeteer.launch({
  headless: true,
  args: ['--no-sandbox', '--disable-setuid-sandbox']
});

const files = (await readdir(htmlDir)).filter(f => f.endsWith('.html')).sort();

for (const file of files) {
  const page = await browser.newPage();
  const htmlPath = join(htmlDir, file);

  // Read dimensions from filename: slide-1-1320x2868.html
  const match = file.match(/(\d+)x(\d+)/);
  const width = match ? parseInt(match[1]) : 1320;
  const height = match ? parseInt(match[2]) : 2868;

  await page.setViewport({ width, height, deviceScaleFactor: 1 });
  await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0' });

  const outName = file.replace('.html', '.png');
  await page.screenshot({
    path: join(outDir, outName),
    type: 'png',
    clip: { x: 0, y: 0, width, height }
  });

  console.log(`✅ ${outName} (${width}x${height})`);
  await page.close();
}

await browser.close();
console.log(`\nDone! ${files.length} screenshots saved to ${outDir}`);
SCRIPT

node /tmp/aso-screenshots/render.mjs
```

## Phase 6: Optimize

Optimize each PNG for App Store upload (smaller file, no visible quality loss):

```bash
for f in /tmp/aso-screenshots/output/*.png; do
  original_size=$(stat -f%z "$f")

  # Lossy compression (visually lossless)
  pngquant --quality=85-98 --force --output "$f.tmp" "$f" && mv "$f.tmp" "$f"

  # Lossless optimization on top
  optipng -o2 -quiet "$f"

  new_size=$(stat -f%z "$f")
  reduction=$(( (original_size - new_size) * 100 / original_size ))
  echo "$(basename $f): ${original_size}B → ${new_size}B (-${reduction}%)"
done
```

If `pngquant` or `optipng` not available, skip optimization and note it:
```
⚠️ Install for smaller files: brew install pngquant optipng
```

## Phase 7: Copy to Project & Show Results

```bash
# Create output directory in project
mkdir -p screenshots/aso

# Copy with clean names
cp /tmp/aso-screenshots/output/slide-*-iphone-*.png screenshots/aso/
cp /tmp/aso-screenshots/output/slide-*-ipad-*.png screenshots/aso/ 2>/dev/null
```

Show each screenshot to the user using the **Read** tool (it can display images).

## Phase 8: Summary & Iterate

Present results:

```
📱 ASO Screenshots Generated

✅ Slide 1: "Track Your Habits" — screenshots/aso/slide-1-iphone-1320x2868.png
✅ Slide 2: "Beautiful Analytics" — screenshots/aso/slide-2-iphone-1320x2868.png
✅ Slide 3: "Smart Reminders"    — screenshots/aso/slide-3-iphone-1320x2868.png

Sizes generated:
  iPhone 6.9": 1320 x 2868 px ✓

Total: 3 slides, ~2.1 MB

Next steps:
  1. Review each slide — ask me to adjust text, colors, or layout
  2. Generate iPad versions: /aso-screenshots ipad
  3. Upload to App Store Connect → App Information → Screenshots
```

Ask if adjustments are needed:
- **Text changes** → regenerate specific slide
- **Color/style changes** → regenerate all slides with new theme
- **Different screenshot** → swap the app screenshot for a specific slide
- **Add locale** → duplicate slides with translated text
- **AI background** → use /imagine to generate background, then re-render

## Appendix A: Device Frame Reference

### iPhone 15 Pro / 16 Pro frame

The CSS `.device-frame` creates a device-like appearance using:
- Rounded corners matching the real device radius
- Dark bezel (box-shadow with solid color)
- Dynamic Island overlay
- Bottom cropping via translateY (creates depth, hides home indicator)

For a **more realistic frame**, use a device mockup PNG:
1. Download from Apple Design Resources or mockuphone.com
2. Save to `screenshots/frames/iphone-15-pro.png`
3. Use as overlay via absolute positioning in the HTML template

### No frame option

Set `DEVICE_RADIUS: 0`, `BEZEL: 0`, `DEVICE_OFFSET: 80` — shows just the screenshot floating with a shadow.

## Appendix B: ASO Best Practices Checklist

Before finalizing, verify:

- [ ] **First 3 slides sell the app** — 90% of users don't scroll further
- [ ] **Each slide = one message** — single headline, 5-7 words
- [ ] **Text readable on thumbnail** — zoom out to verify
- [ ] **Consistent visual style** — same colors, fonts, device frame across all slides
- [ ] **Headline describes VALUE, not feature** — "Sleep Better Tonight" > "Sleep Tracking"
- [ ] **No placeholder/demo data** — use realistic content in screenshots
- [ ] **Color contrast** — WCAG AA for text over backgrounds
- [ ] **Order: Value → Usage → Trust** — what you get → how it works → why it's good

## Appendix C: Quick Reference — Apple Screenshot Sizes

| Device | Dimensions | Aspect | Required? |
|--------|-----------|--------|-----------|
| iPhone 6.9" | 1320 x 2868 | ~1:2.17 | Yes (covers all iPhones) |
| iPhone 6.5" | 1284 x 2778 | ~1:2.16 | Alternative to 6.9" |
| iPad 13" | 2064 x 2752 | ~3:4 | If iPad supported |
| iPad 12.9" | 2048 x 2732 | ~3:4 | Alternative to 13" |
