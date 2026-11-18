import sys,struct,zlib,json
def inflate(b):
    try: return zlib.decompress(b,-15)
    except Exception:
        import subprocess; return subprocess.run(['zstd','-dc'],input=b,capture_output=True).stdout
class R:
    def __init__(s,b): s.b=b; s.i=0
    def byte(s): v=s.b[s.i]; s.i+=1; return v
    def vu(s):
        r=0;sh=0
        while True:
            c=s.byte(); r|=(c&127)<<sh; sh+=7
            if c<128 or sh>=70: return r
    def vi(s): v=s.vu(); return (v>>1)^-(v&1)
    def fl(s):
        if s.b[s.i]==0: s.i+=1; return 0.0
        bits=struct.unpack_from('<I',s.b,s.i)[0]; s.i+=4
        bits=((bits<<23)|(bits>>9))&0xffffffff
        return struct.unpack('<f',struct.pack('<I',bits))[0]
    def st(s):
        j=s.b.index(0,s.i); v=s.b[s.i:j].decode('utf8','replace'); s.i=j+1; return v
data=open(sys.argv[1],'rb').read(); p=12; chunks=[]
while p<len(data):
    n=struct.unpack_from('<I',data,p)[0]; chunks.append(data[p+4:p+4+n]); p+=4+n
sr=R(inflate(chunks[0])); defs=[]
for _ in range(sr.vu()):
    name=sr.st(); kind=sr.byte(); fs=[]
    for _ in range(sr.vu()):
        fn=sr.st(); t=sr.vi(); arr=sr.byte(); val=sr.vu(); fs.append((fn,t,arr,val))
    defs.append((name,kind,fs))
byname={d[0]:d for d in defs}
B={-1:'bool',-2:'byte',-3:'int',-4:'uint',-5:'float',-6:'string',-7:'int64',-8:'uint64'}
def rd(r,t):
    if t<0:
        k=B[t]
        if k=='bool': return bool(r.byte())
        if k=='byte': return r.byte()
        if k=='int': return r.vi()
        if k in('uint','int64','uint64'): return r.vu() if k!='int64' else r.vi()
        if k=='float': return r.fl()
        if k=='string': return r.st()
    name,kind,fs=defs[t]
    if kind==0:
        v=r.vu()
        for f in fs:
            if f[3]==v: return f[0]
        return v
    if kind==1:
        return {f[0]:rdf(r,f) for f in fs}
    o={}
    while True:
        fid=r.vu()
        if fid==0: return o
        f=next(x for x in fs if x[3]==fid); o[f[0]]=rdf(r,f)
def rdf(r,f):
    if f[2]:
        n=r.vu()
        if f[1]==-2: v=bytes(r.b[r.i:r.i+n]); r.i+=n; return v.hex()
        return [rd(r,f[1]) for _ in range(n)]
    return rd(r,f[1])
msg=rd(R(inflate(chunks[1])),defs.index(byname['Message']))
json.dump(msg,open(sys.argv[2],'w'),default=str)
print(len(msg.get('nodeChanges',[])))
