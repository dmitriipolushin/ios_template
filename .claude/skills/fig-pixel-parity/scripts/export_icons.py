"""Export icon glyph geometry (fills + outlined strokes) as Dart AppIconData."""
import sys, struct, importlib.util
doc_path = sys.argv[1]
sys.argv = [sys.argv[0], doc_path, '.', 'x']
spec = importlib.util.spec_from_file_location('render', __file__.replace('export_icons', 'render'))
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
N, KIDS, gid = r.N, r.KIDS, r.gid

def mul(a, b):
    return (a[0]*b[0]+a[1]*b[3], a[0]*b[1]+a[1]*b[4], a[0]*b[2]+a[1]*b[5]+a[2],
            a[3]*b[0]+a[4]*b[3], a[3]*b[1]+a[4]*b[4], a[3]*b[2]+a[4]*b[5]+a[5])
def mat(n):
    t = n.get('transform') or {}
    return (t.get('m00', 1), t.get('m01', 0), t.get('m02', 0), t.get('m10', 0), t.get('m11', 1), t.get('m12', 0))
def cmds(blob):
    b = bytes.fromhex(r.BLOBS[blob]['bytes']); i = 0; out = []
    while i < len(b):
        c = b[i]; i += 1; k = {0: 0, 1: 2, 2: 2, 3: 4, 4: 6}[c]
        v = struct.unpack_from('<%df' % k, b, i); i += 4 * k
        if c == 0 and not out: continue
        out.append((c, v))
    return out

def walk(k, M, ov, prefix, acc, only, root=False):
    base = N[k]; n = base; path = prefix + (k,)
    if ov is not None and path in ov:
        n = dict(base); n.update(ov[path])
    if n.get('visible') is False: return
    if not root: M = mul(M, mat(n))
    if (only is None or k in only) and n['type'] in ('VECTOR', 'BOOLEAN_OPERATION', 'ELLIPSE', 'ROUNDED_RECTANGLE', 'RECTANGLE') or (n['type'] in ('FRAME','INSTANCE') and only and k in only):
        if n['type'] not in ('FRAME', 'INSTANCE') or (only and k in only and n.get('fillPaints')):
            for key, paints in (('fillGeometry', 'fillPaints'), ('strokeGeometry', 'strokePaints')):
                if not [p for p in n.get(paints) or [] if p.get('visible') is not False]: continue
                for g in n.get(key) or []:
                    acc.append((g.get('windingRule'), [(c, [(M[0]*v[j]+M[1]*v[j+1]+M[2], M[3]*v[j]+M[4]*v[j+1]+M[5]) for j in range(0, len(v), 2)]) for c, v in cmds(g['commandsBlob'])]))
    if n['type'] == 'INSTANCE':
        sk = gid(n['symbolData']['symbolID'])
        inner = r.build_overrides(n, ov, path)
        for c in KIDS.get(sk, []): walk(c, M, inner, (), acc, only)
    else:
        for c in KIDS.get(k, []): walk(c, M, ov, prefix, acc, only)

def dart(name, k, only=None, doc=''):
    n = N[k]; acc = []
    walk(k, (1, 0, 0, 0, 1, 0), None, (), acc, set(only) if only else None, root=True)
    assert acc, f'no geometry for {name}'
    w, h = n['size']['x'], n['size']['y']
    f = lambda p: f"{p[0]:.3f}, {p[1]:.3f}"
    L = [f"  /// {doc} Design box {w:g}x{h:g}.", f"  static const {name} = AppIconData(", f"    size: Size({w:.1f}, {h:.1f}),", "    commands: ["]
    for wr, cs in acc:
        L.append("      PathCmd.begin(evenOdd: true)," if wr in ('ODD', 'EVENODD') else "      PathCmd.begin(),")
        for c, p in cs:
            L.append({0: lambda: "      PathCmd.close(),", 1: lambda: f"      PathCmd.move({f(p[0])}),", 2: lambda: f"      PathCmd.line({f(p[0])}),",
                      3: lambda: f"      PathCmd.quad({f(p[0])}, {f(p[1])}),", 4: lambda: f"      PathCmd.cubic({f(p[0])}, {f(p[1])}, {f(p[2])}),"}[c]())
    L += ["    ],", "  );"]
    return '\n'.join(L)

def parent(k): return gid(N[k]['parentIndex']['guid'])

ICONS = [
    # name, node, only-vectors, doc
    ('plan', '0:311', None, 'Tab bar · Plan.'),
    ('shopping', '0:315', None, 'Tab bar · Shopping.'),
    ('scan', '0:320', None, 'Tab bar · centre Scan button.'),
    ('calories', '0:323', None, 'Tab bar · Calories.'),
    ('budget', '0:327', None, 'Tab bar · Budget.'),
    ('bell', '0:282', None, 'Header · notifications.'),
    ('chevronLeft', '0:189', None, 'Header · back.'),
    ('chevronDown', '0:286', None, 'Header week/day pill disclosure.'),
    ('chevronDownSmall', '0:555', None, 'Store picker disclosure.'),
    ('close', '0:755', None, 'Paywall · close.'),
    ('check', '0:198', None, 'Plan generation · step done.'),
    ('checkboxMark', '0:484', None, 'Shopping item checkbox mark (on an accent square).'),
    ('checkSmall', '0:1107', None, 'Recipe · "in your kitchen" badge mark.'),
    ('checkChip', '11:880', ['11:1017'], 'Store chip selected mark (on an accent circle).'),
    ('trendDown', '0:303', None, 'Insight chip · savings.'),
    ('swap', '0:718', None, 'Meal card · swap dish.'),
    ('swapLarge', '0:1141', None, 'Recipe · swap dish.'),
    ('share', '0:1152', None, 'Recipe header · share.'),
    ('saveHeart', '0:1155', None, 'Recipe header · save.'),
    ('minus', '0:1114', None, 'Servings stepper · decrease.'),
    ('plus', '0:1118', None, 'Servings stepper · increase.'),
    ('add', '0:1351', None, 'Calories · add meal.'),
    ('edit', '11:212', None, 'Store picker · change store.'),
    ('benefitShopping', '0:738', None, 'Paywall benefit · smart shopping list.'),
    ('benefitScan', '0:744', None, 'Paywall benefit · AI calorie scan.'),
    ('benefitBudget', '0:750', None, 'Paywall benefit · budget control.'),
    ('rescan', '0:1201', None, 'AI scan result · retake.'),
    ('camera', '0:1239', None, 'AI scan · camera.'),
    ('swoosh', '0:116', None, 'Welcome · hand-drawn underline under the headline.'),
]
print('\n\n'.join(dart(*i) for i in ICONS))
for name, k, only, _ in ICONS:
    print(f"// {name}: {N[k]['type']} {N[k]['name']} {N[k]['size']['x']:g}x{N[k]['size']['y']:g}", file=sys.stderr)
