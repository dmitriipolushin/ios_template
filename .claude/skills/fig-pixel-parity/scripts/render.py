"""Render nodes of a decoded .fig (doc.json from kiwi.py) to SVG.

usage: render.py doc.json out_dir "Frame name" [more names...]
       render.py doc.json out_dir --node "Frame name/child/child" png_name
"""
import json, sys, struct, math, os, html, copy

doc = json.load(open(sys.argv[1]))
OUT = sys.argv[2]
BLOBS = doc['blobs']
gid = lambda g: f"{g['sessionID']}:{g['localID']}"
N = {gid(n['guid']): n for n in doc['nodeChanges']}
K = {}
for k, n in N.items():
    pi = n.get('parentIndex')
    if pi:
        K.setdefault(gid(pi['guid']), []).append((pi.get('position', ''), k))
for v in K.values():
    v.sort()
KIDS = {k: [c for _, c in v] for k, v in K.items()}

EXCLUDE = set(filter(None, os.environ.get('FIG_EXCLUDE', '').split(',')))
ROOT_FX = os.environ.get('FIG_ROOT_FX', '1') == '1'
_uid = [0]
def uid(p='d'):
    _uid[0] += 1
    return f"{p}{_uid[0]}"

def f(x):
    return f"{x:.4f}".rstrip('0').rstrip('.') if isinstance(x, float) else str(x)

def color(c, op=1.0):
    r, g, b = (round(c[k] * 255) for k in 'rgb')
    return f"rgb({r},{g},{b})", c.get('a', 1) * op

def cmds_path(blob, scale=1.0, sy=None, tx=0.0, ty=0.0):
    sy = scale if sy is None else sy
    b = bytes.fromhex(BLOBS[blob]['bytes'])
    i = 0; d = []
    while i < len(b):
        c = b[i]; i += 1
        n = {0: 0, 1: 2, 2: 2, 3: 4, 4: 6}.get(c)
        if n is None:
            break
        v = struct.unpack_from('<%df' % n, b, i); i += 4 * n
        pts = ' '.join(f"{f(tx + v[j] * scale)} {f(ty + v[j + 1] * sy)}" for j in range(0, n, 2))
        d.append({0: 'Z', 1: 'M', 2: 'L', 3: 'Q', 4: 'C'}[c] + pts)
    while d and d[0] == 'Z':
        d.pop(0)
    return ' '.join(d)

def inv(t):
    a, b, c, d, e, ff = t['m00'], t['m01'], t['m02'], t['m10'], t['m11'], t['m12']
    det = a * e - b * d
    if abs(det) < 1e-12:
        return (1, 0, 0, 0, 1, 0)
    ia, ib, id_, ie = e / det, -b / det, -d / det, a / det
    ic = -(ia * c + ib * ff); iff = -(id_ * c + ie * ff)
    return (ia, ib, ic, id_, ie, iff)

def svgmat(m):  # (a,b,c,d,e,f) row-major 2x3 -> svg matrix(a d b e c f)
    a, b, c, d, e, ff = m
    return f"matrix({f(a)} {f(d)} {f(b)} {f(e)} {f(c)} {f(ff)})"

class R:
    def __init__(self):
        self.defs = []

    # ---------- paints ----------
    def paint_ref(self, p, w, h):
        """Return (fill attr, opacity) for a paint, adding defs as needed."""
        t = p.get('type'); op = p.get('opacity', 1.0)
        if t == 'SOLID':
            c, a = color(p['color'], op)
            return c, a
        if t and t.startswith('GRADIENT'):
            i = uid('g')
            T = inv(p.get('transform', {'m00': 1, 'm01': 0, 'm02': 0, 'm10': 0, 'm11': 1, 'm12': 0}))
            # gradient space -> node-normalized -> node px
            M = (T[0] * w, T[1] * w, T[2] * w, T[3] * h, T[4] * h, T[5] * h)
            stops = ''.join(
                f'<stop offset="{f(s["position"])}" stop-color="{color(s["color"])[0]}" stop-opacity="{f(s["color"].get("a", 1))}"/>'
                for s in p.get('stops', []))
            if t == 'GRADIENT_LINEAR':
                self.defs.append(f'<linearGradient id="{i}" gradientUnits="userSpaceOnUse" x1="0" y1="0.5" x2="1" y2="0.5" gradientTransform="{svgmat(M)}">{stops}</linearGradient>')
            else:
                self.defs.append(f'<radialGradient id="{i}" gradientUnits="userSpaceOnUse" cx="0.5" cy="0.5" r="0.5" gradientTransform="{svgmat(M)}">{stops}</radialGradient>')
            return f"url(#{i})", op
        if t == 'IMAGE':
            h_ = p.get('image', {}).get('hash')
            if not h_:
                return None, 0
            href = f"images/{h_}"
            mode = p.get('imageScaleMode', 'FILL')
            i = uid('p')
            if mode == 'TILE':
                sc = p.get('scale', 1.0) or 1.0
                iw, ih = p.get('originalImageWidth', 100), p.get('originalImageHeight', 100)
                self.defs.append(f'<pattern id="{i}" patternUnits="userSpaceOnUse" width="{f(iw*sc)}" height="{f(ih*sc)}"><image href="{href}" width="{f(iw*sc)}" height="{f(ih*sc)}" preserveAspectRatio="none"/></pattern>')
            elif mode == 'STRETCH' and p.get('transform'):
                T = inv(p['transform'])
                M = (T[0] * w, T[1] * w, T[2] * w, T[3] * h, T[4] * h, T[5] * h)
                self.defs.append(f'<pattern id="{i}" patternUnits="userSpaceOnUse" width="{f(w)}" height="{f(h)}"><image href="{href}" width="1" height="1" preserveAspectRatio="none" transform="{svgmat(M)}"/></pattern>')
            else:
                par = 'xMidYMid slice' if mode in ('FILL', 'CROP') else 'xMidYMid meet'
                rot = p.get('rotation', 0) or 0
                tr = f' transform="rotate({f(rot)} {f(w/2)} {f(h/2)})"' if rot else ''
                self.defs.append(f'<pattern id="{i}" patternUnits="userSpaceOnUse" width="{f(w)}" height="{f(h)}"><image href="{href}" width="{f(w)}" height="{f(h)}" preserveAspectRatio="{par}"{tr}/></pattern>')
            return f"url(#{i})", op
        return None, 0

    # ---------- geometry ----------
    def shape_d(self, n, inset=0.0):
        """Path for rect-like / ellipse nodes."""
        w, h = n['size']['x'], n['size']['y']
        x0, y0, x1, y1 = inset, inset, w - inset, h - inset
        if n['type'] == 'ELLIPSE':
            rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
            cx, cy = x0 + rx, y0 + ry
            return f"M{f(cx-rx)} {f(cy)}A{f(rx)} {f(ry)} 0 1 0 {f(cx+rx)} {f(cy)}A{f(rx)} {f(ry)} 0 1 0 {f(cx-rx)} {f(cy)}Z"
        if n.get('rectangleCornerRadiiIndependent'):
            rr = [n.get(k, 0) or 0 for k in ('rectangleTopLeftCornerRadius', 'rectangleTopRightCornerRadius', 'rectangleBottomRightCornerRadius', 'rectangleBottomLeftCornerRadius')]
        else:
            rr = [n.get('cornerRadius', 0) or 0] * 4
        lim = min(x1 - x0, y1 - y0) / 2
        tl, tr, br, bl = (max(0, min(r - inset, lim)) for r in rr)
        return (f"M{f(x0+tl)} {f(y0)}H{f(x1-tr)}" + (f"A{f(tr)} {f(tr)} 0 0 1 {f(x1)} {f(y0+tr)}" if tr else '') +
                f"V{f(y1-br)}" + (f"A{f(br)} {f(br)} 0 0 1 {f(x1-br)} {f(y1)}" if br else '') +
                f"H{f(x0+bl)}" + (f"A{f(bl)} {f(bl)} 0 0 1 {f(x0)} {f(y1-bl)}" if bl else '') +
                f"V{f(y0+tl)}" + (f"A{f(tl)} {f(tl)} 0 0 1 {f(x0+tl)} {f(y0)}" if tl else '') + "Z")

    def fill_paths(self, n):
        if n.get('fillGeometry'):
            return [(cmds_path(g['commandsBlob']), g.get('windingRule')) for g in n['fillGeometry']]
        if n['type'] in ('FRAME', 'RECTANGLE', 'ROUNDED_RECTANGLE', 'ELLIPSE', 'INSTANCE', 'SYMBOL', 'COMPONENT'):
            return [(self.shape_d(n), 'NONZERO')]
        return []

    def stroke_paths(self, n):
        if n.get('strokeGeometry'):
            return [(cmds_path(g['commandsBlob']), g.get('windingRule')) for g in n['strokeGeometry']]
        w = n.get('strokeWeight', 0) or 0
        if not w or n['type'] not in ('FRAME', 'RECTANGLE', 'ROUNDED_RECTANGLE', 'ELLIPSE', 'INSTANCE', 'SYMBOL'):
            return []
        al = n.get('strokeAlign', 'INSIDE')
        inset = {'INSIDE': w / 2, 'CENTER': 0, 'OUTSIDE': -w / 2}.get(al, w / 2)
        return [('STROKE:' + self.shape_d(n, inset), w)]

    def paint_layers(self, paths, paints, w, h):
        out = []
        for p in paints or []:
            if p.get('visible') is False:
                continue
            fill, op = self.paint_ref(p, w, h)
            if not fill or op <= 0:
                continue
            for d, wr in paths:
                if isinstance(d, str) and d.startswith('STROKE:'):
                    out.append(f'<path d="{d[7:]}" fill="none" stroke="{fill}" stroke-opacity="{f(op)}" stroke-width="{f(wr)}"/>')
                else:
                    rule = 'evenodd' if wr in ('ODD', 'EVENODD') else 'nonzero'
                    out.append(f'<path d="{d}" fill="{fill}" fill-opacity="{f(op)}" fill-rule="{rule}"/>')
        return out

    # ---------- text ----------
    def text(self, n):
        dt = n.get('derivedTextData') or {}
        glyphs = dt.get('glyphs') or []
        td = n.get('textData', {})
        styles = td.get('characterStyleIDs') or []
        table = {s.get('styleID'): s for s in td.get('styleOverrideTable') or []}
        out = []
        w, h = n['size']['x'], n['size']['y']
        for gl in glyphs:
            if gl.get('commandsBlob') is None:
                continue
            fs = gl.get('fontSize', n.get('fontSize', 12))
            px, py = gl['position']['x'], gl['position']['y']
            d = cmds_path(gl['commandsBlob'], fs, -fs, px, py)
            ci = gl.get('firstCharacter', 0)
            paints = n.get('fillPaints')
            sid = styles[ci] if ci < len(styles) else 0
            if sid and sid in table and table[sid].get('fillPaints'):
                paints = table[sid]['fillPaints']
            out += self.paint_layers([(d, 'NONZERO')], paints, w, h)
        return out

    # ---------- effects ----------
    def filter_for(self, n, w, h):
        fx = [e for e in n.get('effects') or [] if e.get('visible') is not False]
        if not fx:
            return None
        i = uid('f'); parts = []; merge = []
        pad = 200
        blur_src = 'SourceGraphic'
        for e in fx:
            t = e['type']; r = (e.get('radius', 0) or 0) / 2
            if t in ('FOREGROUND_BLUR', 'LAYER_BLUR'):
                parts.append(f'<feGaussianBlur in="SourceGraphic" stdDeviation="{f(r)}" result="lb"/>')
                blur_src = 'lb'
        for e in fx:
            t = e['type']; r = (e.get('radius', 0) or 0) / 2
            off = e.get('offset', {}); dx, dy = off.get('x', 0), off.get('y', 0)
            c, a = color(e.get('color', {'r': 0, 'g': 0, 'b': 0, 'a': .25}))
            sp = e.get('spread', 0) or 0
            k = uid('e')
            if t == 'DROP_SHADOW':
                morph = f'<feMorphology in="SourceAlpha" operator="{"dilate" if sp > 0 else "erode"}" radius="{f(abs(sp))}" result="{k}m"/>' if sp else ''
                src = f'{k}m' if sp else 'SourceAlpha'
                parts.append(f'{morph}<feOffset in="{src}" dx="{f(dx)}" dy="{f(dy)}" result="{k}o"/><feGaussianBlur in="{k}o" stdDeviation="{f(r)}" result="{k}b"/><feFlood flood-color="{c}" flood-opacity="{f(a)}"/><feComposite in2="{k}b" operator="in" result="{k}c"/>')
                if not e.get('showShadowBehindNode'):
                    parts.append(f'<feComposite in="{k}c" in2="SourceAlpha" operator="out" result="{k}c"/>')
                merge.insert(0, f'{k}c')
            elif t == 'INNER_SHADOW':
                # spread < 0 grows the hole (smaller shadow), > 0 shrinks it
                morph = f'<feMorphology in="SourceAlpha" operator="{"dilate" if sp < 0 else "erode"}" radius="{f(abs(sp))}" result="{k}m"/>' if sp else ''
                src = f'{k}m' if sp else 'SourceAlpha'
                parts.append(morph + f'<feComponentTransfer in="{src}" result="{k}i"><feFuncA type="table" tableValues="1 0"/></feComponentTransfer><feOffset in="{k}i" dx="{f(dx)}" dy="{f(dy)}" result="{k}o"/><feGaussianBlur in="{k}o" stdDeviation="{f(r)}" result="{k}b"/><feFlood flood-color="{c}" flood-opacity="{f(a)}"/><feComposite in2="{k}b" operator="in" result="{k}c"/><feComposite in="{k}c" in2="SourceAlpha" operator="in" result="{k}c"/>')
                merge.append(('INNER', f'{k}c'))
        drops = [m for m in merge if isinstance(m, str)]
        inners = [m[1] for m in merge if not isinstance(m, str)]
        nodes = ''.join(f'<feMergeNode in="{m}"/>' for m in drops) + f'<feMergeNode in="{blur_src}"/>' + ''.join(f'<feMergeNode in="{m}"/>' for m in inners)
        self.defs.append(f'<filter id="{i}" filterUnits="userSpaceOnUse" x="{-pad}" y="{-pad}" width="{f(w+2*pad)}" height="{f(h+2*pad)}" color-interpolation-filters="sRGB">{"".join(parts)}<feMerge>{nodes}</feMerge></filter>')
        return i

    # ---------- nodes ----------
    def node(self, k, ov=None, prefix=(), root=False):
        """Render node k. ov: overrides keyed by guid-path tuples (instances)."""
        base = N[k]
        n = base
        path = prefix + (k,)
        if ov is not None:
            okey = path_key(path, base)
            if okey in ov:
                n = dict(base); n.update(ov[okey])
        if n.get('visible') is False or k in EXCLUDE:
            return ''
        t = n['type']
        w, h = n['size']['x'], n['size']['y']
        tr = '' if root else f' transform="{svgmat((n["transform"]["m00"], n["transform"]["m01"], n["transform"]["m02"], n["transform"]["m10"], n["transform"]["m11"], n["transform"]["m12"]))}"' if n.get('transform') else ''
        op = n.get('opacity', 1.0)
        body = []
        if t == 'TEXT':
            body += self.text(n)
        else:
            body += self.paint_layers(self.fill_paths(n), n.get('fillPaints'), w, h)
        # children
        kids_out = []
        if t == 'INSTANCE':
            sym = n.get('symbolData', {}).get('symbolID')
            sk = gid(sym) if sym else None
            if sk and sk in N:
                inner = build_overrides(n, ov, path)
                kids_out = self.children(sk, inner, ())
        elif t not in ('TEXT', 'VECTOR'):
            kids_out = self.children(k, ov, prefix)
        if kids_out:
            clip = t in ('FRAME', 'INSTANCE', 'SYMBOL') and not n.get('frameMaskDisabled', False) and not n.get('resizeToFit')
            if clip:
                ci = uid('c')
                self.defs.append(f'<clipPath id="{ci}"><path d="{self.shape_d(n)}"/></clipPath>')
                body.append(f'<g clip-path="url(#{ci})">{"".join(kids_out)}</g>')
            else:
                body += kids_out
        body += self.paint_layers(self.stroke_paths(n), n.get('strokePaints'), w, h)
        fi = None if (root and not ROOT_FX) else self.filter_for(n, w, h)
        attrs = tr + (f' opacity="{f(op)}"' if op != 1 else '') + (f' filter="url(#{fi})"' if fi else '')
        return f'<g{attrs}>{"".join(body)}</g>'

    def children(self, k, ov, prefix):
        out = []; mask_id = None; masked = []
        for c in KIDS.get(k, []):
            cn = N[c]
            if cn.get('mask') and cn.get('visible') is not False:
                if mask_id and masked:
                    out.append(f'<g mask="url(#{mask_id})">{"".join(masked)}</g>')
                mask_id = uid('m'); masked = []
                mt = cn.get('maskType', 'ALPHA')
                self.defs.append(f'<mask id="{mask_id}" maskUnits="userSpaceOnUse" x="-5000" y="-5000" width="10000" height="10000" style="mask-type:{"luminance" if mt == "LUMINANCE" else "alpha"}">{self.node(c, ov, prefix)}</mask>')
                continue
            s = self.node(c, ov, prefix)
            (masked if mask_id else out).append(s)
        if mask_id and masked:
            out.append(f'<g mask="url(#{mask_id})">{"".join(masked)}</g>')
        return out

def path_key(path, node):
    # overrides address nodes inside a symbol by their guid path; nodes
    # created from an instance carry overrideKey instead of their own guid
    return tuple(path)

def build_overrides(inst, outer, inst_path):
    """Map guid-path tuples (relative to the symbol) -> merged node props."""
    res = {}
    def put(guids, props):
        key = tuple(gid(g) for g in guids)
        res.setdefault(key, {}).update(props)
    sd = inst.get('symbolData', {})
    for o in sd.get('symbolOverrides') or []:
        props = {kk: vv for kk, vv in o.items() if kk not in ('guidPath',)}
        put(o['guidPath']['guids'], props)
    for o in inst.get('derivedSymbolData') or []:
        props = {kk: vv for kk, vv in o.items() if kk not in ('guidPath',)}
        put(o['guidPath']['guids'], props)
    # outer overrides addressed through this instance
    if outer:
        me = inst_path[-1:]
        for key, props in outer.items():
            if len(key) > len(inst_path) and key[:len(inst_path)] == inst_path:
                res.setdefault(key[len(inst_path):], {}).update(props)
    # symbol children are addressed by their overrideKey when present
    alias = {}
    for k, n in N.items():
        if n.get('overrideKey'):
            alias[gid(n['overrideKey'])] = k
    fixed = {}
    for key, props in res.items():
        fixed[tuple(alias.get(x, x) for x in key)] = props
    return fixed

def render(k, name, scale=3):
    r = R()
    n = N[k]
    w, h = n['size']['x'], n['size']['y']
    body = r.node(k, None, (), root=True)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{f(w)}" height="{f(h)}" viewBox="0 0 {f(w)} {f(h)}">'
           f'<defs>{"".join(r.defs)}</defs>{body}</svg>')
    p = os.path.join(OUT, name + '.svg')
    open(p, 'w').write(svg)
    return p, w, h

def find(path):
    parts = path.split('/')
    page = next(k for k, n in N.items() if n.get('type') == 'CANVAS' and n.get('name') == 'Page 1')
    k = next(c for c in KIDS[page] if N[c].get('name') == parts[0])
    for p in parts[1:]:
        k = next(c for c in KIDS[k] if N[c].get('name') == p)
    return k

if __name__ == '__main__':
    if sys.argv[3] == '--node':
        k = sys.argv[4] if ':' in sys.argv[4] and '/' not in sys.argv[4] else find(sys.argv[4])
        p, w, h = render(k, sys.argv[5])
        print(p, w, h)
    else:
        for name in sys.argv[3:]:
            p, w, h = render(find(name), name.split(' — ')[0].replace('.', '_'))
            print(p, w, h)
