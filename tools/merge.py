import sys,os,glob
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from hoi import LINE,core_files
from check import load,check
from thai_pua import apply as pua
src,chunks,out=sys.argv[1:4]
tr={}
for s in sorted(glob.glob(chunks+'/[csr]*.tsv')):
    if s.endswith('.th.tsv'): continue
    th=s.replace('.tsv','.th.tsv')
    if not os.path.exists(th): continue
    bad={e.split(':')[0]+':'+e.split(':')[1] for e in check(s,th)}
    en=dict(load(s))
    for i,t in load(th):
        if i in en and i not in bad: tr[i]=t
files={i.split(':')[0] for i in tr}
os.makedirs(out,exist_ok=True); n=0
for f in sorted(files):
    lines=open(os.path.join(src,f),encoding='utf-8-sig').read().split('\n')
    for ln,l in enumerate(lines):
        k=f'{f}:{ln}'
        if k in tr:
            m=LINE.match(l.rstrip('\r'))
            lines[ln]=f'{m.group(1)}{m.group(2)}:{m.group(3)}{m.group(4)}"{pua(tr[k])}"{m.group(6)}'; n+=1
    open(os.path.join(out,f),'w',encoding='utf-8-sig').write('\n'.join(lines))
print('files',len(files),'lines translated',n)
