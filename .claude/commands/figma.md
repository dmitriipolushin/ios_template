---
description: "Fetch a Figma frame/component via REST API and return structured design data (sizes, colors, typography, auto-layout, hierarchy). Use when: 'figma', 'фигма', 'сверстай по макету', 'вот макет', 'design from figma'."
argument-hint: "[figma url | file-key node-id | images <url> | file-key <url>]"
allowed-tools: [Bash, Read, Write]
---

# Figma

Query Figma files via REST API and return design data suitable for SwiftUI generation.

## Configuration

Requires env var in shell profile (`~/.zshrc`):

```bash
export FIGMA_TOKEN="figd_..."   # https://www.figma.com/settings → Security → Personal access tokens
```

Scopes needed: `File content: Read-only`, `Dev resources: Read-only` (optional).

If `$FIGMA_TOKEN` is empty — stop and ask user to set it. Never hardcode tokens.

## Usage

Based on `$ARGUMENTS`, determine the action:

### 1. Default — fetch node structure from URL

Figma URL examples:
- `https://www.figma.com/design/ABC123xyz/FileName?node-id=42-1337`
- `https://www.figma.com/file/ABC123xyz/FileName?node-id=42%3A1337`

Parse:
- `fileKey` = path segment after `/design/` or `/file/`
- `node-id` in URL uses `-` (or URL-encoded `%3A`); **API expects `:`** → convert `42-1337` → `42:1337`

```bash
curl -s -H "X-Figma-Token: $FIGMA_TOKEN" \
  "https://api.figma.com/v1/files/$FILE_KEY/nodes?ids=$NODE_ID&geometry=paths"
```

If no `node-id` in URL — fetch whole file (heavy, warn user):

```bash
curl -s -H "X-Figma-Token: $FIGMA_TOKEN" \
  "https://api.figma.com/v1/files/$FILE_KEY?depth=2"
```

### 2. `images <url>` — render PNG preview of the node

```bash
curl -s -H "X-Figma-Token: $FIGMA_TOKEN" \
  "https://api.figma.com/v1/images/$FILE_KEY?ids=$NODE_ID&format=png&scale=2"
```

Response returns a signed S3 URL in `images[NODE_ID]`. Download it to a local temp path with a second `curl` so the user can preview.

### 3. Two positional args `<file-key> <node-id>` — direct fetch without URL parsing

Useful when the user already has the IDs.

## Response Format

Always respond in Russian. Structure the summary so a SwiftUI view can be built directly:

**Узел:** `name` (type, e.g. `FRAME`, `COMPONENT`, `INSTANCE`)
**Размер:** `width × height` pt, позиция если релевантна
**Layout:** auto-layout direction (`HORIZONTAL` / `VERTICAL` / `NONE`), `itemSpacing`, `padding{Top,Right,Bottom,Left}`, `primaryAxisAlignItems`, `counterAxisAlignItems`
**Фон:** `fills` → HEX + opacity
**Обводка:** `strokes`, `strokeWeight`, `cornerRadius` (или `rectangleCornerRadii` если разные углы)
**Эффекты:** тени/блюры (`effects[]`)
**Текст** (если `TEXT`): строка, `fontFamily`, `fontWeight`, `fontSize`, `lineHeightPx`, `letterSpacing`, `textAlignHorizontal`, цвет
**Дети:** иерархия вложенных узлов (имя + type + краткие габариты). Для глубоких деревьев — 2 уровня, спроси пользователя, нужно ли глубже.

Если узлов несколько (запрошен frame с кучей children) — сначала общая сводка, потом предложи:
- сгенерить SwiftUI `View` сразу
- разбить на подкомпоненты
- выгрузить PNG-превью через `figma images <url>`

## Conversions (Figma → SwiftUI)

Держи в уме типичные маппинги:
- `fills[0].color {r,g,b,a}` (0..1) → `Color(red:green:blue:opacity:)` или HEX
- `cornerRadius` → `.cornerRadius(N)` / `RoundedRectangle(cornerRadius: N)`
- auto-layout `HORIZONTAL` → `HStack(spacing: itemSpacing)`, `VERTICAL` → `VStack`, `NONE` → `ZStack`
- `paddingLeft/Right/Top/Bottom` → `.padding(.init(top:leading:bottom:trailing:))`
- `primaryAxisAlignItems: CENTER` → `HStack` с `.frame(maxWidth:.infinity)` детей или alignment контейнера
- шрифты — сверяйся с уже подключёнными в проекте (см. `Assets/Fonts/`, `Info.plist`). Не выдумывай имена.

## Rules

- Токен читай **только** из `$FIGMA_TOKEN`. Никогда не хардкодь и не логируй.
- Отвечай кратко и по-русски.
- Если API вернул ошибку (403 — нет доступа к файлу, 404 — file key неверный, 429 — rate limit) — покажи текст ошибки и подскажи действие.
- `node-id` из URL **всегда** конвертируй `-` → `:` перед запросом.
- Большие файлы (целиком, без `node-id`) качай только по явному запросу — сначала предупреди про размер.
- После fetch не начинай сразу верстать — покажи сводку и спроси: «сгенерировать SwiftUI сейчас или уточнить?»
