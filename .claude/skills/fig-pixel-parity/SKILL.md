---
name: fig-pixel-parity
description: Pixel-perfect transfer of a design from a local Figma .fig export into an iOS app (Swift/SwiftUI) — decode the .fig without a Figma account/token, read exact specs, export icons (vector), colors and images into Assets.xcassets, render reference frames and pixel-diff the app against them with a captioned "Figma reference | App (simulator) | Diff" image. Also .pen (Pencil) designs via Pencil MCP: spec, icons, images and reference renders exported the same way and diffed against the app. Use when: '.fig', '.pen', 'перенеси дизайн из фигмы', 'пиксель в пиксель', 'выгрузи иконки/картинки из макета', 'сверь с макетом', 'pixel diff', 'xcassets из фигмы'.
---

# .fig → приложение пиксель в пиксель

Работает с локальным `.fig` (Figma → File → Save local copy). Figma API и
токен не нужны. Скрипты — в `scripts/` рядом с этим файлом
(`S=$(git rev-parse --show-toplevel)/.claude/skills/fig-pixel-parity/scripts`).

Требования: Python 3, Google Chrome, ImageMagick (`magick`), `zstd`; для iOS —
Xcode (`actool`, `simctl`), для чернового проекта `xcodegen`.

## Правила

- Работать только на симуляторе проекта, не на реальном устройстве и не на
  симуляторах других проектов.
- ID узлов (`0:311`) привязаны к конкретному `.fig`. В другой копии макета
  («… (2).fig») они другие: сначала проверить, на каком файле сняты ID.
- Размеры в `digest.txt` округлены. Для точной геометрии брать
  `transform.m02/m12` и `size` из `doc.json`.
- Черновые проекты для проверки — в scratchpad, после сверки удалить и
  снять приложение с симулятора.

## 1. Распаковка и спека

```sh
mkdir fig && cd fig && unzip ~/Downloads/"<Design>.fig"
python3 -I $S/kiwi.py canvas.fig doc.json       # kiwi-бинарник → JSON
python3 -I $S/digest.py doc.json digest.txt     # дерево: размеры, цвета, шрифты, auto-layout, эффекты
grep -n "'06 — Weekly Plan'" digest.txt          # найти фрейм и его узлы
```

Точные позиции детей узла:

```sh
python3 -c "
import json;m=json.load(open('doc.json'));g=lambda x:f\"{x['sessionID']}:{x['localID']}\"
for n in m['nodeChanges']:
  p=n.get('parentIndex')
  if p and g(p['guid'])=='0:309': t=n['transform'];print(n['name'],t['m02'],t['m12'],n['size'])"
```

## 2. Ассеты → Assets.xcassets

```sh
python3 -I $S/swift/export_xcassets.py fig/doc.json App/Assets.xcassets   # иконки + цвета
$S/swift/export_raster.sh $PWD/fig App/Assets.xcassets oven=0:1031 logo=11:878   # картинки
mkdir -p /tmp/ac && xcrun actool App/Assets.xcassets --compile /tmp/ac \
  --platform iphonesimulator --minimum-deployment-target 17.0             # проверка каталога
```

- Иконки: `Icons/<name>.imageset/<name>.svg` в дизайн-рамке иконки,
  `preserves-vector-representation` + `template`. Список имя → узел —
  `ICONS` в `export_icons.py` (скрипт используется как библиотека геометрии), его надо заполнить под свой макет.
  В коде: `Image("Icons/plan").renderingMode(.template).foregroundStyle(...)`.
- Цвета: `Colors/<name>.colorset`. Словарь `COLORS` в `export_xcassets.py`
  заполняется из шапки `digest.txt` (`COLORS [...]`).
- Картинки: рендер @3x → `magick` @2x/@1x → imageset. Фото — оригиналами
  из `fig/images/` по хешу.
- Шрифт `.ttf` → в таргет + `Info.plist UIAppFonts`; трекинг `ls-1%` при
  12pt → `.tracking(-0.12)`.


## 3. Эффекты Figma → SwiftUI

| Figma (`digest`) | SwiftUI |
|---|---|
| `DROP_SHADOW(c r y)` | `.shadow(color: c, radius: r/2, y: y)` |
| `INNER_SHADOW(c r y)` | `.fill(color.shadow(.inner(color: c, radius: r/2, y: y)))` |
| `BACKGROUND_BLUR` | `.ultraThinMaterial` — в SVG-эталоне блюра нет, сверять на глаз |
| `fill ·o0.82` | `.opacity(0.82)` на цвете |
| `AL:VERTICAL gap=3 pad=…` | `VStack(spacing: 3).padding(...)` |

Радиус Figma ≈ 2× радиуса SwiftUI.

## 4. Пиксельная сверка

1. **Эталон**:
   ```sh
   read p w h <<< $(python3 -I $S/render.py doc.json . --node 0:309 ref)
   $S/shot.sh $PWD/ref.svg ref.png ${w%.*} ${h%.*}      # @3x
   ```
2. **Приложение**:
   - SwiftUI-компонент: `ImageRenderer(content: View()).scale = 3` →
     `Documents/x.png`, забрать через
     `xcrun simctl get_app_container <sim> <bundle> data`. Пример —
     `scripts/swift/TabBarParity.swift.txt`. После переустановки контейнер
     меняется, путь надо перечитывать после запуска.
   - Целый экран: `xcrun simctl io <sim> screenshot app.png`.
3. **Общий фон** для полупрозрачных элементов:
   `magick -size WxH xc:'#F7F6F6' x.png -composite x_bg.png` (оба файла).
4. **Сравнение**: `$S/diff.sh ref_bg.png app_bg.png out` → `mismatch N%` и
   `out_side.png` с подписями над панелями:

   ![Figma reference | App (simulator) | Diff](assets/tabbar_parity.png)

   Слева рендер макета, в центре снимок с симулятора, справа красным то,
   что не совпало (fuzz 6%).
5. **Сдвиги** — по рамкам тёмных пикселей, в физических px (3 px @3x = 1 pt):
   ```sh
   python3 -c "
   from PIL import Image
   for f in ('ref_bg','app_bg'):
     c=Image.open(f+'.png').convert('L').crop((24,0,231,90)).point(lambda v:255 if v<110 else 0)
     print(f,c.getbbox())"
   ```
6. **Что осталось**: процент отдельно по полосам (иконки / текст) — так видно,
   что остаток от шрифта, а не от геометрии.

Пример (таб-бар Mealum в SwiftUI): 10.57% → 4.45% после внутренних теней
кнопки → 3.72% после точной геометрии (ячейки 68.6, отступ 9 вместо
округлённых 69/8). Остаток: 1.8% в полосе иконок, 8.9% в подписях —
Inter вместо Suisse Intl.

## Другие форматы дизайна

Скрипты `kiwi.py`, `digest.py` и `render.py` читают только `.fig`. Остальная
цепочка от формата не зависит: эталон → PNG @3x → общий фон → `diff.sh`.
Для любого источника нужно получить три вещи: спеку (размеры, цвета,
шрифты), векторы иконок и эталонную картинку узла.

`diff.sh` принимает подписи панелей: `diff.sh ref.png app.png out "Pencil (.pen)" "App (simulator)"`.

### `.pen` (Pencil) → код и сверка

Читать `.pen` можно только инструментами Pencil MCP, они же заменяют
`kiwi.py`, `digest.py` и `render.py`:

| Из `.fig` | Из `.pen` |
|---|---|
| `digest.txt` (спека) | `batch_get(nodeIds, readDepth: 3, resolveVariables: true)` — размеры, `layout/gap/padding`, `fill`, `cornerRadius`, `effect`, шрифты |
| точные позиции | `snapshot_layout(parentId, maxDepth: 2)` — посчитанные x/y/width/height |
| цвета `COLORS` | `get_variables` → colorsets / `AppColors` |
| `export_icons.py` | `batch_get(…, includePathGeometry: true)` → `pen_icons.py` |
| `export_assets.sh` | `export_nodes(nodeIds, scale: 3)` → PNG @3x |
| `render.py` + `shot.sh` (эталон) | `export_nodes(frameId, scale: 3)` |

**Иконки.** Ответ `batch_get` по рамкам иконок (`includePathGeometry: true`)
сохраняется в `icons.json` как есть, без правок:

```sh
python3 -I $S/pen_icons.py icons.json App/Assets.xcassets   # iOS: SVG-imagesets, вектор + template
python3 -I $S/pen_icons.py icons.json - --dart              # Flutter: AppIconData для AppIcons
```

Имя иконки берётся из имени рамки в `.pen`, размер рамки — дизайн-бокс.
Геометрия в `.pen` хранится в координатах рамки, сдвиги вложенных узлов
скрипт учитывает.

Проверено: иконки, выгруженные из `.pen` и из `.fig` для одного и того же
макета, совпадают попиксельно (0 px разницы), Dart-код идентичен.

**Эталон и сверка.** `export_nodes` добавляет к картинке поля под тени
(таб-бар 361×64 с тенью выгружается как 1251×483 вместо 1083×192). Узел
надо вырезать по его рамке из `snapshot_layout` и полям тени:

```sh
magick export.png -crop 1083x192+84+76 +repage ref.png
magick -size 1083x192 xc:'#F7F6F6' ref.png -composite ref_bg.png
$S/diff.sh ref_bg.png app_bg.png out "Pencil (.pen)" "App (simulator)"
```

Снимок приложения и дальнейшие шаги такие же, как для `.fig`.

Эффекты в `.pen` записаны прямо в формате кода: тень — `blur`, `offset`,
`spread`, `color`. В SwiftUI радиус — `blur/2`, во Flutter
`blurRadius: blur`.

Для примера ниже в `.pen` собрали тот же таб-бар, что в `.fig`, и сравнили
два эталона между собой — так проверяется, что выгрузка из `.pen` даёт ту же
картинку:

![Figma (.fig) | Pencil (.pen) | Diff](assets/pen_parity.png)

### HTML-прототип

Отдельный скилл `proto-parity`: Playwright снимает состояния прототипа в
размере устройства.

### `.sketch`, `.xd`, Penpot — не проверено

Таких файлов на машине не было. Если появятся:
- `.sketch` — zip с JSON (`pages/*.json`, `images/`): спеку и пути можно
  читать напрямую. Эталон — `sketchtool export` (идёт с Sketch.app).
- Penpot — экспорт SVG/PNG из приложения или API.
- `.xd` — проще экспортировать нужные артборды в PNG/SVG из Adobe XD.

Эталонная картинка обязательно @3x. Дальше та же сверка.

## 5. Отчёт

По-русски: что выгружено (иконки/цвета/картинки, сколько), таблица
«шаг → mismatch %», картинка `out_side.png` и чем объясняется остаток.
