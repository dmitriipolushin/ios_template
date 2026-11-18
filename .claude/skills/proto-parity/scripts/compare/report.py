#!/usr/bin/env python3
"""Batch comparison: every prototype state that has an app screenshot of the same name gets a
montage, a masked difference and a shape-referenced gap; one report.md sums them up.

  report.py --config parity.json --out <dir> [--names a b c]
  report.py --proto-dir <dir> --app-dir <dir> --prefix fsc264_ --out <dir> [--offset-pt 48]

parity.json (see references/config.md): protoShots, appShotDirs, appPrefixes,
defaultOffsetPt, offsets {state: pt}, masks {"*" | state: [[x,y,w,h] pt]}, maskBottomPt,
maskTopPt, gapRef, fuzz. Paths in it are relative to the file.

Verdict per state (read references/method.md before acting on it):
  exact     |gap delta| = 0 px and no difference band outside masks
  rounding  |gap delta| <= 2 px, the same on every page (two pixel grids), small bands
  check     anything else: open the montage and the diff, then measure the band with px.py
"""
import argparse
import glob
import json
import os
import sys

from diff import diff
from gap import measure
from imgutil import SCALE, find_app_shots, size
from pair import aligned_crops, pair


def load_config(path):
    with open(path) as f:
        cfg = json.load(f)
    base = os.path.dirname(os.path.abspath(path))

    def rel(p):
        return p if os.path.isabs(p) else os.path.normpath(os.path.join(base, p))
    cfg['protoShots'] = rel(cfg['protoShots'])
    cfg['appShotDirs'] = [rel(p) for p in cfg.get('appShotDirs', [])]
    return cfg


def masks_for(cfg, name, proto, app, offset_pt):
    m = [tuple(x) for x in cfg.get('masks', {}).get('*', [])] + [tuple(x) for x in cfg.get('masks', {}).get(name, [])]
    py, ay, h, w = aligned_crops(proto, app, offset_pt)
    if cfg.get('maskTopPt'):
        m.append((0, 0, w / SCALE, cfg['maskTopPt']))
    if cfg.get('maskBottomPt'):
        m.append((0, h / SCALE - cfg['maskBottomPt'], w / SCALE, cfg['maskBottomPt']))
    return m


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--config')
    p.add_argument('--proto-dir'); p.add_argument('--app-dir', action='append', default=[])
    p.add_argument('--prefix', action='append', default=[])
    p.add_argument('--offset-pt', type=float, default=48.0)
    p.add_argument('--names', nargs='*')
    p.add_argument('--out', required=True)
    a = p.parse_args()
    if a.config:
        cfg = load_config(a.config)
    else:
        if not a.proto_dir or not a.app_dir:
            p.error('--config, or --proto-dir and --app-dir')
        cfg = {'protoShots': a.proto_dir, 'appShotDirs': a.app_dir, 'appPrefixes': a.prefix,
               'defaultOffsetPt': a.offset_pt}
    out = a.out
    for d in ('pairs', 'diff'):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    shots = find_app_shots(cfg['appShotDirs'], cfg.get('appPrefixes') or [''])
    names = a.names or sorted(os.path.basename(x)[:-4] for x in glob.glob(os.path.join(cfg['protoShots'], '*.png')))
    rows, missing = [], []
    for n in names:
        proto = os.path.join(cfg['protoShots'], n + '.png')
        if not os.path.exists(proto) or n not in shots:
            missing.append(n)
            continue
        app = shots[n]
        if size(proto) != size(app):
            rows.append((n, '-', '-', '-', '-', f'size differs {size(proto)} vs {size(app)}'))
            continue
        off = float(cfg.get('offsets', {}).get(n, cfg.get('defaultOffsetPt', 48.0)))
        pair(proto, app, os.path.join(out, 'pairs', n + '.png'), off)
        g = measure(proto, app, off, cfg.get('gapRef', 'button'))
        gap_px = g['delta_px'] if g else None
        # Diff on the content's real position (nominal offset + the measured rounding), so the
        # bands left are differences of drawing, not of a 1-2 px shift.
        fine = off + (g['card_dy_px'] / SCALE if g and abs(g['card_dy_px']) <= 3 else 0)
        st = diff(proto, app, os.path.join(out, 'diff', n), fine, float(cfg.get('fuzz', 8)),
                  masks_for(cfg, n, proto, app, fine))
        band = st['bands'][0] if st['bands'] else None
        if gap_px == 0 and st['differing_pct'] < 0.5:
            verdict = 'exact'
        elif gap_px is not None and abs(gap_px) <= 2 and st['differing_pct'] < float(cfg.get('noisePct', 1.5)):
            verdict = 'rounding'
        else:
            verdict = 'check'
        rows.append((n, f"{off:g}", '-' if gap_px is None else f"{gap_px:+d}", f"{st['differing_pct']}",
                     f"{band['from_pt']}-{band['to_pt']} ({band['pixels']})" if band else '-', verdict))
    with open(os.path.join(out, 'report.md'), 'w') as f:
        f.write('# Prototype parity\n\n')
        f.write('| state | offset pt | first card, px | differing % | largest band pt (px) | verdict | images |\n')
        f.write('|---|---|---|---|---|---|---|\n')
        for r in rows:
            n = r[0]
            f.write(f"| {n} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | "
                    f"[pair](pairs/{n}.png) [diff](diff/{n}_diff.png) [blend](diff/{n}_blend.png) |\n")
        if missing:
            f.write(f"\nNo app screenshot (or no prototype shot) for: {', '.join(missing)}\n")
    for r in rows:
        print(' | '.join(str(x) for x in r))
    print(f"report: {os.path.join(out, 'report.md')}  ({len(rows)} compared, {len(missing)} without a pair)")


if __name__ == '__main__':
    sys.exit(main())
