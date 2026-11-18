import json,sys,collections
m=json.load(open(sys.argv[1])); out=sys.argv[2]
def gid(g): return f"{g['sessionID']}:{g['localID']}"
N={gid(n['guid']):n for n in m['nodeChanges']}; K={}
for k,n in N.items():
    pi=n.get('parentIndex')
    if pi: K.setdefault(gid(pi['guid']),[]).append((pi.get('position',''),k))
for v in K.values(): v.sort()
def hexc(c): return '#%02X%02X%02X'%tuple(round(c[k]*255) for k in 'rgb')+('' if round(c.get('a',1),2)==1 else f"/{c['a']:.2f}")
def fills(n,key='fillPaints'):
    r=[]
    for p in n.get(key) or []:
        if p.get('visible') is False: continue
        t=p.get('type')
        if t=='SOLID': r.append(hexc(p['color'])+('' if p.get('opacity',1)==1 else f"·o{p['opacity']:.2f}"))
        elif t=='IMAGE': r.append('IMG')
        elif t and 'GRADIENT' in t: r.append('grad('+','.join(hexc(s['color']) for s in p.get('stops',[]))+')')
    return r
colors=collections.Counter(); fonts=collections.Counter()
def line(n):
    s=n.get('size',{}); t=n.get('transform',{})
    a=[f"{n.get('type')} '{n.get('name')}' {round(s.get('x',0))}x{round(s.get('y',0))} @{round(t.get('m02',0))},{round(t.get('m12',0))}"]
    f=fills(n); st=fills(n,'strokePaints')
    if f: a.append('fill='+','.join(f)); colors.update(f)
    if st: a.append(f"stroke={','.join(st)}w{n.get('strokeWeight')}")
    if n.get('cornerRadius'): a.append(f"r={n['cornerRadius']}")
    if n.get('stackMode'):
        a.append(f"AL:{n['stackMode']} gap={n.get('stackSpacing',0)} pad={n.get('stackHorizontalPadding',n.get('stackPaddingLeft',0))},{n.get('stackVerticalPadding',n.get('stackPaddingTop',0))},{n.get('stackPaddingRight','')},{n.get('stackPaddingBottom','')} main={n.get('stackPrimaryAlignItems','')} cross={n.get('stackCounterAlignItems','')}")
    for e in n.get('effects') or []:
        if e.get('visible') is not False: a.append(f"fx={e.get('type')}({hexc(e['color']) if 'color' in e else ''} r{e.get('radius')} y{e.get('offset',{}).get('y')})")
    if n.get('opacity',1)!=1: a.append(f"op={n['opacity']:.2f}")
    if n.get('type')=='TEXT':
        fn=n.get('fontName',{}); fs=f"{fn.get('family')} {fn.get('style')} {n.get('fontSize')}"
        lh=n.get('lineHeight',{}); ls=n.get('letterSpacing',{})
        fs+=f" lh{lh.get('value')}{'%' if lh.get('units')=='PERCENT' else ''} ls{ls.get('value')}{'%' if ls.get('units')=='PERCENT' else ''}"
        fonts[fs]+=1; a.append(fs); a.append('«'+n.get('textData',{}).get('characters','').replace('\n','⏎')+'»')
    if n.get('type')=='INSTANCE':
        sid=n.get('symbolData',{}).get('symbolID')
        if sid: a.append('of '+N.get(gid(sid),{}).get('name','?'))
    return ' '.join(a)
def walk(k,d,fh):
    n=N[k]
    if n.get('visible') is False: return
    fh.write('  '*d+line(n)+'\n')
    for _,c in K.get(k,[]): walk(c,d+1,fh)
page=[k for k,n in N.items() if n.get('type')=='CANVAS' and n.get('name')=='Page 1'][0]
with open(out,'w') as fh:
    for _,f in K[page]: walk(f,0,fh); fh.write('\n')
print('COLORS',colors.most_common(40)); print('FONTS'); [print(' ',c,f) for f,c in fonts.most_common(40)]
