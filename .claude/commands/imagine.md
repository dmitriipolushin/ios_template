# Image Generation with Nano Banana 2 (kie.ai)

Generate images using the Nano Banana 2 model via kie.ai API.

## Arguments

$ARGUMENTS — The user's request. Can include:
- Text description of the desired image
- Path(s) to local reference images or URLs
- Style / mood / aesthetic instructions
- Aspect ratio (1:1)
- Resolution (1K)

## Environment

Requires `KIE_API_KEY` environment variable. If not set, ask the user to provide it.

Rate limit: 20 requests per 10 seconds. Generated files expire after 14 days on kie.ai servers — always download locally.

## Workflow

### Step 1: Determine mode

- Only text description → **text2img**
- Reference image(s) provided (file paths or URLs) → **img2img**

### Step 2: Craft the prompt

Write the prompt following the "Prompt Writing" section below. Show the planned prompt to the user and ask for confirmation unless they said to go ahead.

If you have project context (specs, screen descriptions, design system), use it to craft a more relevant and visually consistent prompt.

### Step 3: Handle reference images (img2img only)

- Local file paths → upload or convert to publicly accessible URL
- URLs → use directly in `image_input`

### Step 4: Generate

```bash
curl -s -X POST "https://api.kie.ai/api/v1/jobs/createTask" \
  -H "Authorization: Bearer $KIE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nano-banana-2",
    "input": {
      "prompt": "<PROMPT>",
      "image_input": [],
      "aspect_ratio": "1:1",
      "resolution": "1K",
      "output_format": "png"
    }
  }'
```

Parse `taskId` from response.

### Step 5: Poll for results

Poll every 10 seconds:

```bash
curl -s -X GET "https://api.kie.ai/api/v1/jobs/recordInfo?taskId=<TASK_ID>" \
  -H "Authorization: Bearer $KIE_API_KEY"
```

- `data.state` = `waiting` | `queuing` | `generating` → keep polling
- `data.state` = `success` → extract image URL from `data.resultJson`
- `data.state` = `fail` → report `data.failMsg`

### Step 6: Remove background (if needed)

Use when the image is a character, icon, mascot, or UI element that needs transparency. Skip for scenes, landscapes, backgrounds.

**Do NOT prompt for transparent backgrounds** — generate normally, then remove in post-processing:

```bash
curl -s -X POST "https://api.kie.ai/api/v1/jobs/createTask" \
  -H "Authorization: Bearer $KIE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "recraft/remove-background",
    "input": {
      "image": "<IMAGE_URL_FROM_STEP_5>"
    }
  }'
```

Poll with the same endpoint. Output is **WebP** — convert to PNG:
```bash
dwebp <DOWNLOADED.webp> -o <OUTPUT.png>
```

### Step 7: Download, optimize, save

1. Download image via curl to `/tmp/`
2. Optimize PNG (~70% size reduction, no visible quality loss):
```bash
pngquant --quality=80-95 --force --output <OUTPUT_PATH> <TEMP_PATH>
optipng -o2 <OUTPUT_PATH>
```
3. Save to project (ask user for path, or suggest `Assets.xcassets/` for iOS projects)
4. Report size reduction (original vs optimized)
5. Show the image to the user using the Read tool

### Step 8: Iterate

Ask if adjustments needed:
- Minor changes → update prompt, re-generate (text2img)
- Style/composition changes → use previous result as reference (img2img)

---

## Prompt Writing

### Structure

Always write prompts in **English**. Use this order — the model weighs earlier words more heavily:

```
[Subject] [Action/Pose] [Setting/Background] [Style] [Lighting] [Technical details]
```

### Rules

1. **Be specific, not vague**
   - Bad: "a beautiful girl"
   - Good: "a young woman with short black hair wearing a white linen shirt, looking at camera, soft studio lighting, neutral beige background"

2. **Describe what you WANT, not what you DON'T want**
   - Bad: "no blurry, no ugly, no watermark"
   - Good: "sharp focus, clean composition, high detail"

3. **Front-load the most important elements** — subject and style come first

4. **Always specify style explicitly**:
   - Photorealistic: "photorealistic, DSLR photograph, 85mm lens, f/1.8, natural lighting"
   - Illustration: "digital illustration, flat design, vector art, minimal color palette"
   - 3D render: "3D render, isometric view, soft shadows, clay material, pastel colors"
   - Watercolor: "watercolor painting, soft edges, paper texture, muted tones"
   - App/UI art: "modern digital illustration, clean lines, gradient colors, app icon style"

5. **Always specify lighting** — it defines mood more than anything else:
   - "golden hour sunlight", "soft diffused studio light", "dramatic rim lighting", "neon glow", "overcast flat light"

6. **For photorealistic images, specify camera/composition**:
   - Framing: "close-up portrait", "wide establishing shot", "bird's eye view", "macro detail shot"
   - Composition: "rule of thirds", "centered composition", "negative space on left"

7. **For app assets (icons, onboarding illustrations, marketing)**:
   - Keep backgrounds simple or solid-colored (easier to remove if needed)
   - Use consistent style keywords across all prompts for visual coherence
   - Reference the project's design system colors if available
   - Add "isolated on white background" for elements that need bg removal

8. **For characters/mascots**:
   - Describe the character in full detail once, then reuse the exact same description
   - Always generate on simple background (white/solid) for easy bg removal
   - Specify framing: "full body", "bust shot", "headshot", "three-quarter view"

9. **For consistency across multiple images** (e.g. onboarding set):
   - Repeat the same style block in every prompt: "digital illustration, soft gradients, rounded shapes, pastel lavender and mint palette"
   - Keep lighting and perspective consistent
   - Use img2img with a previous result as reference for tighter visual coherence

### Prompt Examples

**App onboarding illustration**:
"A person journaling in a cozy armchair with a cup of tea, warm lamp light, modern digital illustration, soft gradients, rounded shapes, pastel lavender and mint color palette, clean minimal background, friendly welcoming mood"

**App icon**:
"A stylized water droplet with a subtle gradient from sky blue to teal, 3D render, glossy material, soft shadow underneath, centered on white background, app icon style, clean and minimal"

**Marketing screenshot background**:
"Abstract flowing gradient waves in soft purple and pink tones, smooth organic shapes, dreamy atmospheric depth, digital art, 4K, minimal and elegant"

**Character/mascot**:
"A friendly cartoon cat character wearing a tiny backpack, standing upright, waving one paw, big expressive eyes, soft round shapes, flat illustration style, pastel orange fur, isolated on white background, full body view"

### Aspect Ratio Guide

Default to **1:1** unless the use case clearly needs another ratio.

---

## Parameters Reference

| Parameter | Default | Options |
|-----------|---------|---------|
| prompt | (required) | Up to 20,000 characters |
| aspect_ratio | 1:1 | 1:1 |
| resolution | 1K | 1K |
| output_format | png | png |
| image_input | [] | Up to 14 image URLs, 30MB each |

## Available Models

| Model | Use case |
|-------|----------|
| `nano-banana-2` | General image generation (text2img + img2img) |
| `recraft/remove-background` | Background removal → outputs WebP |
