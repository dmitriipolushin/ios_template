"""export_xcassets.py <doc.json> <Assets.xcassets> — icons and colors of the
.fig straight into an Xcode asset catalog.

- Icons: the glyph geometry export_icons.py collects, written as one-colour
  SVG imagesets (Preserve Vector Data, template rendering: tinted with
  .foregroundStyle in SwiftUI, like the Flutter AppIcon's color).
- Colors: the design's solid fills, as named colorsets.
Raster art goes through export_raster.sh (render.py → @3x → @2x/@1x).
"""
import json, os, sys

doc, OUT = sys.argv[1], sys.argv[2]
T = os.path.dirname(os.path.abspath(__file__))
# The reused render.py / export_icons.py live one level up.
FLUTTER_TOOLS = os.environ.get("FIG_TOOLS", os.path.dirname(T))
sys.argv = [sys.argv[0], doc]
src = open(os.path.join(FLUTTER_TOOLS, 'export_icons.py')).read()
src = src.split("print('\\n\\n'.join(")[0]  # the module without its Dart printout
g = {'__file__': os.path.join(FLUTTER_TOOLS, 'export_icons.py')}
exec(compile(src, 'export_icons.py', 'exec'), g)
walk, N, ICONS = g['walk'], g['N'], g['ICONS']

def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(obj, open(path, 'w'), indent=2)

INFO = {'author': 'xcode', 'version': 1}
write_json(f'{OUT}/Contents.json', {'info': INFO})
for folder in ('Icons', 'Colors', 'Images'):
    write_json(f'{OUT}/{folder}/Contents.json',
               {'info': INFO, 'properties': {'provides-namespace': True}})

def svg(k, only):
    acc = []
    walk(k, (1, 0, 0, 0, 1, 0), None, (), acc, set(only) if only else None, root=True)
    w, h = N[k]['size']['x'], N[k]['size']['y']
    paths = []
    for wr, cs in acc:
        d = []
        for c, p in cs:
            pts = ' '.join(f'{x:.3f} {y:.3f}' for x, y in p)
            d.append({0: 'Z', 1: f'M{pts}', 2: f'L{pts}', 3: f'Q{pts}', 4: f'C{pts}'}[c])
        rule = 'evenodd' if wr in ('ODD', 'EVENODD') else 'nonzero'
        paths.append(f'<path fill-rule="{rule}" d="{" ".join(d)}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:g}" height="{h:g}" '
            f'viewBox="0 0 {w:g} {h:g}" fill="#000">{"".join(paths)}</svg>'), w, h

for name, k, only, _ in ICONS:
    body, w, h = svg(k, only)
    d = f'{OUT}/Icons/{name}.imageset'
    os.makedirs(d, exist_ok=True)
    open(f'{d}/{name}.svg', 'w').write(body)
    write_json(f'{d}/Contents.json', {
        'images': [{'filename': f'{name}.svg', 'idiom': 'universal'}],
        'info': INFO,
        'properties': {'preserves-vector-representation': True,
                       'template-rendering-intent': 'template'},
    })
    print(f'icon  {name:18} {w:g}x{h:g}')

# Named design colors — the same values as AppColors in the Flutter app.
COLORS = {
    'background': 'F7F6F6', 'ink': '151517', 'inkSecondary': '6C6C74',
    'surface': 'FFFFFF', 'inkTertiary': 'A3A3AB', 'separator': 'BDBDC4',
    'olive': '55621F', 'oliveDark': '3B4219', 'chip': 'E7E7EB',
    'terracotta': 'C4643E', 'mustard': 'D6A23A',
}
for name, hx in COLORS.items():
    r, gg, b = (int(hx[i:i + 2], 16) for i in (0, 2, 4))
    write_json(f'{OUT}/Colors/{name}.colorset/Contents.json', {
        'colors': [{'idiom': 'universal', 'color': {'color-space': 'srgb',
                    'components': {'red': f'0x{r:02X}', 'green': f'0x{gg:02X}',
                                   'blue': f'0x{b:02X}', 'alpha': '1.000'}}}],
        'info': INFO,
    })
    print(f'color {name:18} #{hx}')
