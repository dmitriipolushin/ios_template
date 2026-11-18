#!/usr/bin/env python3
"""Aligned difference of a prototype screenshot and the app's, with masks.

  diff.py <proto.png> <app.png> <out_prefix> [--offset-pt 48] [--fuzz 8]
          [--mask x,y,w,h ...] [--mask-top 14] [--mask-bottom 110] [--band-min 4]

Writes
  <out_prefix>_diff.png    the prototype faded, differing pixels in red (ImageMagick compare)
  <out_prefix>_blend.png   both at 50 %: a shifted edge shows as a double line
  <out_prefix>_abs.png     |proto - app|, contrast-stretched: where, and how strongly
  <out_prefix>_stats.json  differing pixels (count, %), and the horizontal bands they gather in
and prints the same summary.

Masks are in points, in the prototype's coordinates after alignment (x, y, width, height).
Mask what cannot match by design: the app's status bar remnant (--mask-top), the floating tab
bar (--mask-bottom), live data (codes, dates, prices), the simulator-only camera notice. A
whole-screen diff without masks is mostly noise; read the bands, then measure the shapes they
point at with px.py / gap.py.

--fuzz: per-pixel colour tolerance in percent (antialiasing of the same glyph differs between
Chromium and Core Text; 8-12 keeps text edges from flooding the result).
"""
import argparse
import json
import os
import sys
import tempfile

from imgutil import SCALE, has_magick, run, size
from pair import aligned_crops


def _prepare(proto, app, offset_pt, masks, tmp):
    py, ay, h, w = aligned_crops(proto, app, offset_pt)
    boxes = ''.join(f",drawbox=x={round(x * SCALE)}:y={round(y * SCALE)}:w={round(mw * SCALE)}:h={round(mh * SCALE)}:color=black:t=fill"
                    for x, y, mw, mh in masks)
    a = os.path.join(tmp, 'a.png')
    b = os.path.join(tmp, 'b.png')
    for src, y, dst in ((proto, py, a), (app, ay, b)):
        r = run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', f"crop={w}:{h}:0:{y}{boxes},format=rgb24", dst])
        if r.returncode != 0:
            raise SystemExit(r.stderr.decode()[:300])
    return a, b, w, h


def _gray_diff(a, b, fuzz):
    """Thresholded |a-b| as gray bytes (255 = differs)."""
    if has_magick():
        r = run(['magick', a, b, '-compose', 'difference', '-composite', '-colorspace', 'gray',
                 '-threshold', f'{fuzz}%', '-depth', '8', 'gray:-'])
        return r.stdout
    thr = round(255 * fuzz / 100)
    r = run(['ffmpeg', '-v', 'error', '-i', a, '-i', b, '-filter_complex',
             f"[0][1]blend=all_mode=difference,format=gray,lut=y='if(gt(val,{thr}),255,0)'",
             '-f', 'rawvideo', '-pix_fmt', 'gray', '-'])
    return r.stdout


def diff(proto, app, prefix, offset_pt=48.0, fuzz=8.0, masks=(), band_min=4):
    os.makedirs(os.path.dirname(os.path.abspath(prefix)) or '.', exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        a, b, w, h = _prepare(proto, app, offset_pt, masks, tmp)
        if has_magick():
            run(['magick', 'compare', '-fuzz', f'{fuzz}%', '-highlight-color', 'red',
                 '-lowlight-color', '#ffffffb0', a, b, prefix + '_diff.png'])
            run(['magick', a, b, '-compose', 'blend', '-define', 'compose:args=50', '-composite', prefix + '_blend.png'])
            run(['magick', a, b, '-compose', 'difference', '-composite', '-auto-level', prefix + '_abs.png'])
        else:
            run(['ffmpeg', '-v', 'error', '-y', '-i', a, '-i', b, '-filter_complex',
                 '[0][1]blend=all_mode=difference,eq=contrast=4', prefix + '_abs.png'])
            run(['ffmpeg', '-v', 'error', '-y', '-i', a, '-i', b, '-filter_complex',
                 '[0][1]blend=all_mode=average', prefix + '_blend.png'])
        g = _gray_diff(a, b, fuzz)
    rows = [sum(1 for v in g[r * w:(r + 1) * w] if v > 127) for r in range(len(g) // w)] if g else []
    total = sum(rows)
    bands, start = [], None
    for y, n in enumerate(rows + [0]):
        if n >= band_min and start is None:
            start = y
        elif n < band_min and start is not None:
            bands.append({'from_pt': round(start / SCALE, 2), 'to_pt': round(y / SCALE, 2),
                          'pixels': sum(rows[start:y])})
            start = None
    bands.sort(key=lambda b: -b['pixels'])
    stats = {'proto': proto, 'app': app, 'offset_pt': offset_pt, 'fuzz': fuzz,
             'masks_pt': [list(m) for m in masks], 'size_px': [w, len(rows)],
             'differing_px': total, 'differing_pct': round(100 * total / max(1, w * len(rows)), 3),
             'bands': bands[:12]}
    with open(prefix + '_stats.json', 'w') as f:
        json.dump(stats, f, indent=1)
    return stats


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('proto'); p.add_argument('app'); p.add_argument('prefix')
    p.add_argument('--offset-pt', type=float, default=48.0)
    p.add_argument('--fuzz', type=float, default=8.0)
    p.add_argument('--mask', action='append', default=[], help='x,y,w,h in pt (repeatable)')
    p.add_argument('--mask-top', type=float, default=0.0, help='mask this many pt at the top')
    p.add_argument('--mask-bottom', type=float, default=0.0, help='mask this many pt at the bottom')
    p.add_argument('--band-min', type=int, default=4, help='differing px in a row to count it')
    a = p.parse_args()
    masks = [tuple(float(v) for v in m.split(',')) for m in a.mask]
    py, ay, h, w = aligned_crops(a.proto, a.app, a.offset_pt)
    if a.mask_top:
        masks.append((0, 0, w / SCALE, a.mask_top))
    if a.mask_bottom:
        masks.append((0, h / SCALE - a.mask_bottom, w / SCALE, a.mask_bottom))
    s = diff(a.proto, a.app, a.prefix, a.offset_pt, a.fuzz, masks, a.band_min)
    print(f"differing: {s['differing_px']} px ({s['differing_pct']}%) of {s['size_px'][0]}x{s['size_px'][1]}")
    for b in s['bands']:
        print(f"  {b['from_pt']:7.2f}-{b['to_pt']:7.2f} pt  {b['pixels']} px")
    print(f"images: {a.prefix}_diff.png  {a.prefix}_blend.png  {a.prefix}_abs.png")


if __name__ == '__main__':
    sys.exit(main())
