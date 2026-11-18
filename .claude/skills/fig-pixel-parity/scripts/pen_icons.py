"""pen_icons.py <icons.json> <out> [--dart] — icons of a .pen design into code.

<icons.json>: the Pencil MCP `batch_get` answer for the icon frames
(`includePathGeometry: true`, `resolveVariables: true`, `readDepth: 3`),
saved as is. Each frame is one icon: its size is the design box, its
`path` children carry SVG geometry in the frame's coordinates (a nested
frame or the path itself may add an x/y offset).

Default: Xcode imagesets `<out>/Icons/<name>.imageset` (SVG, Preserve Vector
Data, template). `--dart`: prints `AppIconData` constants for the Flutter
`AppIcons` class (scripts/app_icon_runtime.dart.txt) and writes nothing.
"""
import json, os, re, sys

src, out = sys.argv[1], sys.argv[2]
dart = '--dart' in sys.argv
frames = json.load(open(src))


def camel(name):
    parts = re.split(r'[^A-Za-z0-9]+', name.strip()) or ['icon']
    s = parts[0].lower() + ''.join(p[:1].upper() + p[1:] for p in parts[1:])
    return s or 'icon'


def paths(node, dx=0.0, dy=0.0):
    """(fill-rule, d, dx, dy) of every visible path under node."""
    if node.get('enabled') is False:
        return []
    found = []
    for c in node.get('children') or []:
        if not isinstance(c, dict):
            continue
        ox, oy = dx + c.get('x', 0), dy + c.get('y', 0)
        if c.get('type') == 'path' and c.get('geometry'):
            found.append((c.get('fillRule', 'nonzero'), c['geometry'], ox, oy))
        else:
            found += paths(c, ox, oy)
    return found


def absolute(d, dx, dy):
    """SVG path data (M/L/H/V/C/S/Q/Z, upper or lower case) → absolute
    (cmd, points) in the icon box: 'M','L','Q','C','Z'."""
    toks = re.findall(r'[MLHVCSQZmlhvcsqz]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?', d)
    out, i, cmd = [], 0, None
    x = y = sx = sy = 0.0
    last_c = None
    def num():
        nonlocal i
        v = float(toks[i]); i += 1; return v
    while i < len(toks):
        if re.match(r'[A-Za-z]', toks[i]):
            cmd = toks[i]; i += 1
        rel = cmd.islower(); C = cmd.upper()
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if C == 'Z':
            out.append(('Z', [])); x, y = sx, sy; last_c = None; continue
        if C == 'M':
            x, y = ox + num(), oy + num(); sx, sy = x, y
            out.append(('M', [(x, y)])); cmd = 'l' if rel else 'L'; last_c = None
        elif C in 'LHV':
            if C == 'L': x, y = ox + num(), oy + num()
            elif C == 'H': x = ox + num() if rel else num()
            else: y = oy + num() if rel else num()
            out.append(('L', [(x, y)])); last_c = None
        elif C == 'C':
            p1 = (ox + num(), oy + num()); p2 = (ox + num(), oy + num()); x, y = ox + num(), oy + num()
            out.append(('C', [p1, p2, (x, y)])); last_c = p2
        elif C == 'S':
            p1 = (2 * x - last_c[0], 2 * y - last_c[1]) if last_c else (x, y)
            p2 = (ox + num(), oy + num()); x, y = ox + num(), oy + num()
            out.append(('C', [p1, p2, (x, y)])); last_c = p2
        elif C == 'Q':
            p1 = (ox + num(), oy + num()); x, y = ox + num(), oy + num()
            out.append(('Q', [p1, (x, y)])); last_c = None
    return [(c, [(px + dx, py + dy) for px, py in pts]) for c, pts in out]


def dart_icon(name, frame):
    f = lambda p: f"{p[0]:.3f}, {p[1]:.3f}"
    L = [f"  /// .pen {frame['id']}. Design box {frame['width']:g}x{frame['height']:g}.",
         f"  static const {name} = AppIconData(",
         f"    size: Size({frame['width']:.1f}, {frame['height']:.1f}),", "    commands: ["]
    for rule, d, x, y in paths(frame):
        L.append("      PathCmd.begin(evenOdd: true)," if rule == 'evenodd' else "      PathCmd.begin(),")
        for c, pts in absolute(d, x, y):
            L.append({'Z': lambda: "      PathCmd.close(),", 'M': lambda: f"      PathCmd.move({f(pts[0])}),",
                      'L': lambda: f"      PathCmd.line({f(pts[0])}),", 'Q': lambda: f"      PathCmd.quad({f(pts[0])}, {f(pts[1])}),",
                      'C': lambda: f"      PathCmd.cubic({f(pts[0])}, {f(pts[1])}, {f(pts[2])}),"}[c]())
    return '\n'.join(L + ["    ],", "  );"])


def svg(frame):
    w, h = frame['width'], frame['height']
    body = ''.join(
        f'<path fill-rule="{rule}" transform="translate({x:g} {y:g})" d="{d}"/>'
        for rule, d, x, y in paths(frame))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:g}" height="{h:g}" '
            f'viewBox="0 0 {w:g} {h:g}" fill="#000">{body}</svg>')


for frame in frames:
    name = camel(frame.get('name') or frame['id'])
    if not paths(frame):
        print(f'skip  {name}: no path geometry', file=sys.stderr)
        continue
    if dart:
        print(dart_icon(name, frame) + '\n')
        continue
    d = f'{out}/Icons/{name}.imageset'
    os.makedirs(d, exist_ok=True)
    open(f'{d}/{name}.svg', 'w').write(svg(frame))
    json.dump({'images': [{'filename': f'{name}.svg', 'idiom': 'universal'}],
               'info': {'author': 'xcode', 'version': 1},
               'properties': {'preserves-vector-representation': True,
                              'template-rendering-intent': 'template'}},
              open(f'{d}/Contents.json', 'w'), indent=2)
    print(f"icon  {name:18} {frame['width']:g}x{frame['height']:g}")
