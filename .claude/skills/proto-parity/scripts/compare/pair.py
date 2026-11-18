#!/usr/bin/env python3
"""Side by side: prototype | app, aligned by the screen's offset, for looking at.

  pair.py <proto.png> <app.png> <out.png> [--offset-pt 48] [--width 543]

--offset-pt: how much lower the same content sits in the app than in the prototype, in points
(the prototype's own safe-area formula decides it, see references/method.md): 48 for a page
under a `max(14px, env(safe-area-inset-top))` bar, 62 for `calc(Npx + env(...))`, 0 for a
full-screen layout, negative for content anchored to the bottom.
"""
import argparse
import sys

from imgutil import SCALE, run, size


def aligned_crops(proto, app, offset_pt):
    """(proto_y, app_y, height) in px so both crops show the same content."""
    off = round(offset_pt * SCALE)
    pw, ph = size(proto)
    aw, ah = size(app)
    py, ay = (0, off) if off >= 0 else (-off, 0)
    h = min(ph - py, ah - ay)
    return py, ay, h, min(pw, aw)


def pair(proto, app, out, offset_pt=48.0, width=543):
    py, ay, h, w = aligned_crops(proto, app, offset_pt)
    vf = (f"[0:v]crop={w}:{h}:0:{py},scale={width}:-1[p];"
          f"[1:v]crop={w}:{h}:0:{ay},scale={width}:-1[a];[p][a]hstack=inputs=2")
    r = run(['ffmpeg', '-v', 'error', '-y', '-i', proto, '-i', app, '-filter_complex', vf, out])
    if r.returncode != 0:
        raise SystemExit(r.stderr.decode()[:300])
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('proto'); p.add_argument('app'); p.add_argument('out')
    p.add_argument('--offset-pt', type=float, default=48.0)
    p.add_argument('--width', type=int, default=543)
    a = p.parse_args()
    print(pair(a.proto, a.app, a.out, a.offset_pt, a.width))


if __name__ == '__main__':
    sys.exit(main())
