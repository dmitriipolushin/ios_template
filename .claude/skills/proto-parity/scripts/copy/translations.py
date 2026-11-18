#!/usr/bin/env python3
"""The prototype's translation table against the app's String Catalog.

  translations.py --proto <prototype.html> --catalog <Localizable.xcstrings>
                  [--var T] [--source en] [--apply] [--out translations_report.md]

The prototype keeps its translations in a JS object, `const T = { en: {key: '...'}, es: {...} }`
(name with --var). For every key, the source-language text is looked up in the catalog
(`{name}` placeholders read as %@, whitespace and non-breaking hyphens unified) and each other
language's value is compared with the catalog's.

  same            the catalog says what the prototype says
  diff            a translation exists and reads differently: the prototype's wording wins
                  (--apply writes it)
  no-translation  the key is in the catalog without that language (--apply adds it)
  no-key          the source text is not a catalog key: a fragment, a template the app builds
                  differently, or a string the app does not show; check by hand

A language the prototype does not carry (no block in T) is not compared. If the app follows the
phone's language, a phone in that language sees these strings even when a language picker is
hidden, so the table matters.

--apply rewrites the catalog the way Xcode lays it out (indent 2, ' : ', no key sorting).
"""
import argparse
import html
import json
import re
import sys


def js_unescape(s):
    s = re.sub(r'\\u\{([0-9a-fA-F]+)\}', lambda m: chr(int(m.group(1), 16)), s)
    s = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), s)
    return html.unescape(s.replace("\\'", "'").replace('\\"', '"'))


def table(src, var):
    i = src.find(f'const {var}=')
    if i < 0:
        i = src.find(f'const {var} =')
    if i < 0:
        raise SystemExit(f'no `const {var} = {{...}}` in the prototype')
    j = src.index('{', i)
    depth, k = 0, j
    while k < len(src):
        if src[k] == '{':
            depth += 1
        elif src[k] == '}':
            depth -= 1
            if depth == 0:
                break
        k += 1
    body = src[j + 1:k]
    langs = {}
    for m in re.finditer(r'(?:^|[,{\s])([a-z]{2}(?:-[A-Za-z]{2})?|\'[a-z-]+\'|"[a-z-]+")\s*:\s*\{', body):
        lang = m.group(1).strip('\'"')
        s = m.end()
        d, e = 1, s
        while e < len(body) and d:
            d += {'{': 1, '}': -1}.get(body[e], 0)
            e += 1
        seg = body[s:e - 1]
        pairs = {}
        for pm in re.finditer(r"(\w+)\s*:\s*(?:'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"|`((?:[^`\\]|\\.)*)`)", seg):
            pairs[pm.group(1)] = js_unescape(pm.group(2) or pm.group(3) or pm.group(4) or '')
        langs[lang] = pairs
    return langs


def norm(s):
    s = re.sub(r'\{\w+\}', '%@', s).replace('\u2011', '-').replace('\u00a0', ' ')
    return re.sub(r'\s+', ' ', s).strip()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--proto', required=True); p.add_argument('--catalog', required=True)
    p.add_argument('--var', default='T'); p.add_argument('--source', default='en')
    p.add_argument('--apply', action='store_true'); p.add_argument('--out')
    a = p.parse_args()
    langs = table(open(a.proto, encoding='utf-8').read(), a.var)
    if a.source not in langs:
        raise SystemExit(f"no '{a.source}' block in {a.var}; blocks: {sorted(langs)}")
    raw = open(a.catalog, encoding='utf-8').read()
    doc = json.loads(raw)
    cat = doc['strings']
    by_norm = {norm(k): k for k in cat}
    lines, counts, changed = [], {}, 0
    for lang, pairs in langs.items():
        if lang == a.source:
            continue
        for key, text in langs[a.source].items():
            if key not in pairs:
                continue
            ck = by_norm.get(norm(text))
            want = pairs[key]
            if not ck:
                kind = 'no-key'
                lines.append(f"| {lang} | {key} | `{text}` | | `{want}` | {kind} |")
            else:
                loc = cat[ck].setdefault('localizations', {})
                have = (loc.get(lang) or {}).get('stringUnit', {}).get('value')
                if have is not None and norm(have) == norm(want):
                    kind = 'same'
                else:
                    kind = 'diff' if have is not None else 'no-translation'
                    lines.append(f"| {lang} | {key} | `{ck}` | `{have or ''}` | `{want}` | {kind} |")
                    if a.apply:
                        loc[lang] = {'stringUnit': {'state': 'translated', 'value': re.sub(r'\{\w+\}', '%@', want)}}
                        changed += 1
            counts[(lang, kind)] = counts.get((lang, kind), 0) + 1
    summary = ', '.join(f"{l} {k}: {n}" for (l, k), n in sorted(counts.items()))
    report = ['# Translations: prototype table vs catalog', '', summary, '',
              '| lang | key | source / catalog key | catalog | prototype | result |', '|---|---|---|---|---|---|'] + lines
    if a.out:
        open(a.out, 'w', encoding='utf-8').write('\n'.join(report) + '\n')
    print(summary)
    for l in lines:
        print(l)
    if a.apply and changed:
        txt = json.dumps(doc, indent=2, separators=(',', ' : '), ensure_ascii=False)
        if raw.endswith('\n'):
            txt += '\n'
        open(a.catalog, 'w', encoding='utf-8').write(txt)
        print(f"applied {changed} values to {a.catalog}")


if __name__ == '__main__':
    sys.exit(main())
