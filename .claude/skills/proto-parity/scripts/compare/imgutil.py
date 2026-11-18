"""Raw pixel access through ffmpeg (no numpy, no PIL): a column, a row or a band of a PNG.

Screenshots of the prototype (Playwright, deviceScaleFactor 3) and of the app (simulator @3x)
share one grid: 1 pt = SCALE px. Everything here works in pixels; callers convert.
"""
import glob
import os
import shutil
import subprocess

SCALE = 3


def run(cmd):
    return subprocess.run(cmd, capture_output=True, check=False)


def size(png):
    r = run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
             'stream=width,height', '-of', 'csv=p=0', png])
    w, h = r.stdout.decode().strip().split(',')[:2]
    return int(w), int(h)


def _raw(png, vf, fmt):
    r = run(['ffmpeg', '-v', 'error', '-i', png, '-vf', vf, '-f', 'rawvideo', '-pix_fmt', fmt, '-'])
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg failed on {png}: {r.stderr.decode()[:300]}")
    return r.stdout


def column(png, x):
    """RGB tuples down column x."""
    raw = _raw(png, f'crop=1:ih:{x}:0', 'rgb24')
    return [tuple(raw[i * 3:i * 3 + 3]) for i in range(len(raw) // 3)]


def row(png, y):
    """RGB tuples along row y."""
    raw = _raw(png, f'crop=iw:1:0:{y}', 'rgb24')
    return [tuple(raw[i * 3:i * 3 + 3]) for i in range(len(raw) // 3)]


def band_gray(png, x0, y0, w, h):
    """Luma bytes of a w x h band, row-major."""
    return _raw(png, f'crop={w}:{h}:{x0}:{y0}', 'gray')


def parse_rgb(s):
    s = s.strip().lstrip('#')
    if ',' in s:
        return tuple(int(v) for v in s.split(','))
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def near(c, rgb, tol):
    return all(abs(c[i] - rgb[i]) <= tol for i in range(3))


def has_magick():
    return shutil.which('magick') is not None


def find_app_shots(dirs, prefixes):
    """name -> newest screenshot whose file name is <prefix><name>.png, under any of `dirs`
    (Maestro writes them to <out>/**/takeScreenshot/)."""
    found = {}
    for d in dirs:
        for p in glob.glob(os.path.join(d, '**', '*.png'), recursive=True):
            base = os.path.basename(p)[:-4]
            for pre in prefixes:
                if pre and base.startswith(pre):
                    k = base[len(pre):]
                    if k not in found or os.path.getmtime(p) > os.path.getmtime(found[k]):
                        found[k] = p
    return found
