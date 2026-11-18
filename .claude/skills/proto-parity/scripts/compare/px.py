#!/usr/bin/env python3
"""Point measurements on one screenshot, in pixels and points (1 pt = 3 px at @3x).

  px.py runs   <png> <x> <rgb> [--tol 12] [--min 3]      runs of one colour down column x
  px.py edges  <png> <x> <y0> <y1> [--page F2F2F7] [--card FFFFFF]
                                                         page / card / other transitions
  px.py ink-rows <png> <x0> <x1> <y0> <y1> [--thr 160]  text lines (rows holding dark pixels)
  px.py ink-x  <png> <y0> <y1> <x0> <x1> [--thr 150]    left and right ink of a line: its width
  px.py color  <png> <x> <y> [--box 6]                  darkest and mean colour around a point
  px.py button-gap <png> [--x 600] [--from 300]         first green(ish) run and the last white
                                                         row above it: card -> button gap

Coordinates are pixels of the PNG. Sample shapes, not glyphs, wherever there is a choice: a
card's edge at its centre column (corners are rounded differently), a separator, a button's
fill; text only for widths and line positions.
"""
import argparse
import sys

from imgutil import SCALE, _raw, band_gray, column, near, parse_rgb


def pt(px):
    return px / SCALE


def cmd_runs(a):
    rgb = parse_rgb(a.rgb)
    col = column(a.png, a.x)
    start = None
    for y, c in enumerate(col + [(-999, -999, -999)]):
        m = near(c, rgb, a.tol)
        if m and start is None:
            start = y
        elif not m and start is not None:
            if y - start >= a.min:
                print(f"{start}-{y - 1} px  ({pt(start):.2f}-{pt(y):.2f} pt, h {pt(y - start):.2f})")
            start = None


def cmd_edges(a):
    page, card = parse_rgb(a.page), parse_rgb(a.card)
    col = column(a.png, a.x)

    def kind(c):
        if near(c, card, 2):
            return 'C'
        if near(c, page, 3):
            return 'P'
        return 'x'
    prev = None
    out = []
    for y in range(a.y0, min(a.y1, len(col))):
        k = kind(col[y])
        if k != prev:
            out.append(f"{pt(y):.2f}{k}")
            prev = k
    print(' '.join(out))
    print("(P page, C card, x anything else: text, separators, shadows)")


def cmd_ink_rows(a):
    w, h = a.x1 - a.x0, a.y1 - a.y0
    raw = band_gray(a.png, a.x0, a.y0, w, h)
    rows = [min(raw[r * w:(r + 1) * w]) < a.thr for r in range(h)]
    start = None
    for r, v in enumerate(rows + [False]):
        if v and start is None:
            start = r
        if not v and start is not None:
            print(f"{pt(start + a.y0):.2f}-{pt(r + a.y0):.2f} pt (h {pt(r - start):.2f})")
            start = None


def cmd_ink_x(a):
    w, h = a.x1 - a.x0, a.y1 - a.y0
    raw = band_gray(a.png, a.x0, a.y0, w, h)
    cols = [min(raw[r * w + c] for r in range(h)) for c in range(w)]
    ink = [c for c, v in enumerate(cols) if v < a.thr]
    if not ink:
        print('no ink')
        return
    print(f"ink {pt(ink[0] + a.x0):.2f}-{pt(ink[-1] + a.x0 + 1):.2f} pt, width {pt(ink[-1] - ink[0] + 1):.2f} pt")


def cmd_color(a):
    b = a.box
    rgb = _raw(a.png, f'crop={2 * b + 1}:{2 * b + 1}:{max(0, a.x - b)}:{max(0, a.y - b)}', 'rgb24')
    px = [tuple(rgb[i:i + 3]) for i in range(0, len(rgb), 3)]
    darkest = min(px, key=sum)
    mean = tuple(round(sum(p[i] for p in px) / len(px)) for i in range(3))
    print(f"darkest {darkest} #{darkest[0]:02X}{darkest[1]:02X}{darkest[2]:02X}  mean {mean}")


def cmd_button_gap(a):
    col = column(a.png, a.x)

    def green(v):
        r, g, b = v
        return g - r > 15 and g - b > 10
    top = next((y for y in range(a.start, len(col) - 6) if all(green(col[y + k]) for k in range(6))), None)
    if top is None:
        print('no button')
        return
    bot = top
    while bot < len(col) and green(col[bot]):
        bot += 1
    wy = next((y for y in range(top - 1, 0, -1) if min(col[y]) >= 253), None)
    print(f"button {pt(top):.2f}-{pt(bot):.2f} pt; card bottom {pt(wy + 1) if wy else 0:.2f} pt; "
          f"gap {pt(top - (wy + 1)) if wy else 0:.2f} pt; fill {col[top + 20]}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('runs'); s.add_argument('png'); s.add_argument('x', type=int); s.add_argument('rgb')
    s.add_argument('--tol', type=int, default=12); s.add_argument('--min', type=int, default=3)
    s = sub.add_parser('edges'); s.add_argument('png'); s.add_argument('x', type=int)
    s.add_argument('y0', type=int); s.add_argument('y1', type=int)
    s.add_argument('--page', default='F2F2F7'); s.add_argument('--card', default='FFFFFF')
    s = sub.add_parser('ink-rows'); s.add_argument('png')
    for n in ('x0', 'x1', 'y0', 'y1'):
        s.add_argument(n, type=int)
    s.add_argument('--thr', type=int, default=160)
    s = sub.add_parser('ink-x'); s.add_argument('png')
    for n in ('y0', 'y1', 'x0', 'x1'):
        s.add_argument(n, type=int)
    s.add_argument('--thr', type=int, default=150)
    s = sub.add_parser('color'); s.add_argument('png'); s.add_argument('x', type=int); s.add_argument('y', type=int)
    s.add_argument('--box', type=int, default=6)
    s = sub.add_parser('button-gap'); s.add_argument('png'); s.add_argument('--x', type=int, default=600)
    s.add_argument('--from', dest='start', type=int, default=300)
    a = p.parse_args()
    {'runs': cmd_runs, 'edges': cmd_edges, 'ink-rows': cmd_ink_rows, 'ink-x': cmd_ink_x,
     'color': cmd_color, 'button-gap': cmd_button_gap}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
