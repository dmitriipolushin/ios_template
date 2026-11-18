#!/usr/bin/env python3
"""The first card's top edge measured from a shape above it, prototype vs app, per state.

  gap.py --proto-dir <dir> --app-dir <dir> [--app-dir ...] --prefix fsc264_ [--prefix ...]
         --names 35_support 40_faq ... [--offset-pt 48] [--ref button|title]
         [--button-x 80] [--card-x 600] [--page F2F2F7]

--ref button  (default) the bottom edge of the top bar's round back button (a shape: no glyph
              rendering in it). Its column (--button-x, px) must cross the circle away from the
              chevron inside it; the run is found within the first ~107 pt of the page.
--ref title   the first dark row of the page title (glyphs: Chromium and Core Text rasterise
              them differently, so expect a constant 1 px).
The card's top is the first row of >= 12 white px at --card-x (the card's centre: its rounded
corners are drawn differently, circular in CSS, continuous on iOS, so never sample near them).

A uniform 1-2 px over every page is rounding of the two pixel grids; a page that differs from
the others has a real cause (a header-less first group, a different title margin).
"""
import argparse
import os
import sys

from imgutil import SCALE, band_gray, column, find_app_shots


def white(c):
    return min(c) >= 253


def back_bottom(png, y0, y1, x):
    c = column(png, x)
    best, y = None, y0
    while y < min(y1, len(c)):
        if white(c[y]):
            s = y
            while y < len(c) and white(c[y]):
                y += 1
            if 50 <= y - s <= 110:
                best = y
        y += 1
    return best


def title_top(png, y0):
    w, h = 640, 400
    raw = band_gray(png, 60, y0, w, h)
    for r in range(len(raw) // w):
        if min(raw[r * w:(r + 1) * w]) < 60:
            return y0 + r
    return None


def card_top(png, start, x):
    c = column(png, x)
    for y in range(start, len(c) - 12):
        if all(white(c[y + k]) for k in range(12)):
            return y
    return None


def measure(proto, app, offset_pt=48.0, ref='button', button_x=80, card_x=600):
    off = round(offset_pt * SCALE)
    if ref == 'button':
        pr, ar = back_bottom(proto, 20, 320, button_x), back_bottom(app, 20 + off, 320 + off, button_x)
        lead = 60
    else:
        pr, ar = title_top(proto, 180), title_top(app, 180 + off)
        lead = 150
    if pr is None or ar is None:
        return None
    pc, ac = card_top(proto, pr + lead, card_x), card_top(app, ar + lead, card_x)
    if pc is None or ac is None:
        return None
    gp, ga = (pc - pr) / SCALE, (ac - ar) / SCALE
    return {'proto_pt': round(gp, 2), 'app_pt': round(ga, 2), 'delta_pt': round(ga - gp, 2),
            'delta_px': round((ga - gp) * SCALE), 'ref_dy_pt': round((ar - pr) / SCALE, 2),
            # where the first card really is, beyond the nominal offset: the fine alignment
            # a difference image needs so a 1 px rounding does not light up every text line
            'card_dy_px': (ac - pc) - off}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--proto-dir', required=True)
    p.add_argument('--app-dir', action='append', required=True)
    p.add_argument('--prefix', action='append', default=[''])
    p.add_argument('--names', nargs='+', required=True)
    p.add_argument('--offset-pt', type=float, default=48.0)
    p.add_argument('--ref', choices=['button', 'title'], default='button')
    p.add_argument('--button-x', type=int, default=80)
    p.add_argument('--card-x', type=int, default=600)
    a = p.parse_args()
    shots = find_app_shots(a.app_dir, [x for x in a.prefix if x])
    print(f"{'state':28s} {'proto':>8s} {'app':>8s} {'delta':>8s}   ref dy")
    for n in a.names:
        pp = os.path.join(a.proto_dir, n + '.png')
        if n not in shots or not os.path.exists(pp):
            print(f"{n:28s} missing {'app' if n not in shots else 'prototype'} shot")
            continue
        m = measure(pp, shots[n], a.offset_pt, a.ref, a.button_x, a.card_x)
        if not m:
            print(f"{n:28s} reference or card not found")
            continue
        print(f"{n:28s} {m['proto_pt']:8.2f} {m['app_pt']:8.2f} {m['delta_pt']:+8.2f} pt ({m['delta_px']:+d} px)   {m['ref_dy_pt']:.2f}")


if __name__ == '__main__':
    sys.exit(main())
