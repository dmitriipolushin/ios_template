#!/usr/bin/env python3
"""Every string of the prototype, looked up in the app: exact, typography only, near, missing.

  copy_inventory.py --states <proto_out_dir> --catalog <Localizable.xcstrings> --swift <dir> [--swift ...]
                    --out copy_report.md [--min-words 2] [--ignore ignore.txt]
                    [--proto <prototype.html> --scripts] [--rendered strings.txt]

What to check, from narrow to wide:
  --states DIR     the visible text of the states you shot (shoot.mjs's <name>.txt): the copy
                   of the screens under comparison, reported per state. Start here.
  --rendered FILE  every screen's text (strings.mjs): the whole prototype, demo data included.
  --scripts        also string literals in the prototype's scripts (toasts, alerts, copy built in
                   JS; `${...}` becomes %@). Noisy: code fragments and demo data come along.
App strings are the catalog's keys and the Swift string literals (`\\(...)` becomes %@).

  exact       found as is, or the same once live values are taken out (prototype numbers vs
              the app's %@): "34 of 80 MB" matches "%@ of %@ MB"
  typography  found once quotes, dashes, ellipsis, non-breaking spaces/hyphens are unified:
              the app uses other punctuation than the prototype (a real copy difference)
  near        a close string exists (ratio >= 0.85): wording drifted; the diff is shown
  missing     nothing close: not built, built elsewhere (server text), or out of scope

Read the result with judgement: prototype-only demo strings, server-provided copy and owner
decisions are not defects. Put strings to skip, one per line, in --ignore.
"""
import argparse
import difflib
import html
import json
import os
import re
import sys
from collections import defaultdict

TYPO = str.maketrans({'\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2014': '-', '\u2013': '-',
                      '\u2011': '-', '\u00a0': ' ', '\u202f': ' ', '\u2026': '...'})


def strict(s):
    return re.sub(r'\s+', ' ', s).strip()


def loose(s):
    return strict(s.translate(TYPO)).lower()


def template(s):
    """Live values out: numbers (with $ , . %) in the prototype's demo copy and the app's
    format specifiers both become #, so "34 of 80 MB" matches "%@ of %@ MB"."""
    s = re.sub(r'%(\d+\$)?(@|lld|ld|d|f|\.\d+f)', '#', loose(s))
    return re.sub(r'[$€£]?\d[\d,.\u202f\u00a0]*%?', '#', s)


def js_unescape(s):
    s = re.sub(r'\\u\{([0-9a-fA-F]+)\}', lambda m: chr(int(m.group(1), 16)), s)
    s = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), s)
    return s.replace("\\'", "'").replace('\\"', '"').replace('\\n', '\n')


def state_strings(states_dir, min_words):
    """{state: [strings]} from shoot.mjs's <name>.txt files."""
    out = {}
    for f in sorted(os.listdir(states_dir)):
        if not f.endswith('.txt') or f == 'strings.txt':
            continue
        lines = []
        for line in open(os.path.join(states_dir, f), encoding='utf-8'):
            line = strict(line)
            if line and not line.startswith('###') and len(line.split()) >= min_words and re.search(r'[A-Za-z]{2}', line):
                lines.append(line)
        out[f[:-4]] = lines
    return out


def proto_strings(html_path, rendered, min_words, scripts=False):
    out = set()
    if rendered and os.path.exists(rendered):
        for line in open(rendered, encoding='utf-8'):
            line = strict(line)
            if line and not line.startswith('###'):
                out.add(line)
    if not scripts or not html_path:
        return {s for s in out if len(s.split()) >= min_words}
    src = open(html_path, encoding='utf-8').read()
    scripts = '\n'.join(re.findall(r'<script[^>]*>(.*?)</script>', src, flags=re.S))
    for m in re.finditer(r"'((?:[^'\\\n]|\\.){3,})'|\"((?:[^\"\\\n]|\\.){3,})\"|`((?:[^`\\]|\\.){3,})`", scripts):
        s = m.group(1) or m.group(2) or m.group(3) or ''
        s = re.sub(r'\$\{[^}]*\}', '%@', s)
        s = html.unescape(re.sub(r'<[^>]+>', ' ', js_unescape(s)))
        for piece in re.split(r'\s{2,}|\n', s):
            piece = strict(piece)
            if len(piece.split()) < min_words or not re.search(r'[A-Za-z]{3}', piece):
                continue
            if re.search(r'[{};=]|=>|\bfunction\b|\bpx\b|rgba?\(|var\(--|\.classList|document\.', piece):
                continue
            out.add(piece)
    return {s for s in out if len(s.split()) >= min_words}


def app_strings(catalog, swift_dirs):
    out = set()
    if catalog and os.path.exists(catalog):
        out.update(strict(k) for k in json.load(open(catalog, encoding='utf-8')).get('strings', {}))
    lit = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
    for d in swift_dirs:
        for root, _, files in os.walk(d):
            for f in files:
                if not f.endswith('.swift'):
                    continue
                for m in lit.finditer(open(os.path.join(root, f), encoding='utf-8', errors='ignore').read()):
                    s = re.sub(r'\\\((?:[^()]|\([^()]*\))*\)', '%@', m.group(1))
                    s = js_unescape(s)
                    if re.search(r'[A-Za-z]{3}', s):
                        out.add(strict(s))
    return out


def tokens(s):
    return {t for t in re.findall(r'[a-z]{3,}', loose(s))}


class Matcher:
    def __init__(self, apps):
        self.strict = set(apps)
        self.loose = {loose(s): s for s in apps}
        self.template = {template(s): s for s in apps}
        self.index = defaultdict(set)
        for s in apps:
            for t in tokens(s):
                self.index[t].add(s)

    def classify(self, s):
        """('exact'|'typography'|'near'|'missing', app string or None, ratio)."""
        if s in self.strict:
            return 'exact', s, 1.0
        if loose(s) in self.loose:
            return 'typography', self.loose[loose(s)], 1.0
        if template(s) in self.template:
            return 'exact', self.template[template(s)], 1.0
        cand = defaultdict(int)
        for t in tokens(s):
            for c in self.index.get(t, ()):
                cand[c] += 1
        best, br = None, 0.0
        for c, _ in sorted(cand.items(), key=lambda kv: -kv[1])[:60]:
            r = difflib.SequenceMatcher(None, loose(s), loose(c)).ratio()
            if r > br:
                best, br = c, r
        if best and br >= 0.85:
            return 'near', best, br
        return 'missing', None, br


def write_section(f, title, items):
    f.write(f"\n### {title}\n\n")
    for kind, s, c, r in items:
        if kind == 'typography':
            f.write(f"- typography\n  prototype: `{s}`\n  app:       `{c}`\n")
        elif kind == 'near':
            f.write(f"- near {r:.2f}\n  prototype: `{s}`\n  app:       `{c}`\n")
        else:
            f.write(f"- missing: `{s}`\n")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--states', help="shoot.mjs output dir: check each shot state's visible text")
    p.add_argument('--proto'); p.add_argument('--rendered'); p.add_argument('--scripts', action='store_true')
    p.add_argument('--catalog'); p.add_argument('--swift', action='append', default=[])
    p.add_argument('--out', required=True); p.add_argument('--min-words', type=int, default=2)
    p.add_argument('--ignore')
    a = p.parse_args()
    if not (a.states or a.rendered or (a.proto and a.scripts)):
        p.error('give --states, --rendered, or --proto with --scripts')
    ignore = {strict(l) for l in open(a.ignore, encoding='utf-8')} if a.ignore else set()
    m = Matcher(app_strings(a.catalog, a.swift))
    counts = defaultdict(int)
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write('# Copy check: prototype vs app\n')
        if a.states:
            f.write('\n## Per state (the screens under comparison)\n')
            for state, lines in state_strings(a.states, a.min_words).items():
                items = []
                for s in dict.fromkeys(lines):
                    if s in ignore:
                        continue
                    kind, c, r = m.classify(s)
                    counts[kind] += 1
                    if kind != 'exact':
                        items.append((kind, s, c, r))
                if items:
                    write_section(f, state, items)
        if a.rendered or (a.proto and a.scripts):
            rest = sorted(proto_strings(a.proto, a.rendered, a.min_words, a.scripts) - ignore)
            items = []
            for s in rest:
                kind, c, r = m.classify(s)
                counts['all:' + kind] += 1
                if kind in ('typography', 'near'):
                    items.append((kind, s, c, r))
            f.write('\n## Whole prototype: typography and near only (missing omitted: demo data dominates)\n')
            write_section(f, 'all screens', items)
    summary = ', '.join(f"{k} {v}" for k, v in sorted(counts.items()))
    with open(a.out, 'a', encoding='utf-8') as f:
        f.write(f"\n---\n{summary}\n")
    print(f"{summary} -> {a.out}")


if __name__ == '__main__':
    sys.exit(main())
