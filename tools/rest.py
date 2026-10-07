import os,re,sys,glob
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from hoi import LINE,needs,core_files
src,out=sys.argv[1:3]
done=set()
for p in glob.glob(out+'/s[0-9]*.tsv'):
    if p.endswith('.th.tsv'): continue
    for l in open(p,encoding='utf-8'): done.add(l.split('\t',1)[0])
core=set(core_files(src))
files=[f for f in os.listdir(src) if f not in core]
pri=lambda f:(0 if f.split('_')[0] in('events','focus') else 1 if f.startswith('TAOG') else 2 if f.startswith('SEA') else 3, f)
buf=[];size=0;n=0;tot=0;files_by_chunk=[]
def flush():
    global buf,size,n
    if buf:
        n+=1; open(f'{out}/r{n:03d}.tsv','w',encoding='utf-8').write(''.join(f'{i}\t{t}\n' for i,t in buf)); buf=[];size=0
for f in sorted(files,key=pri):
    for ln,l in enumerate(open(os.path.join(src,f),encoding='utf-8-sig').read().split('\n')):
        m=LINE.match(l.rstrip('\r')); k=f'{f}:{ln}'
        if m and k not in done and needs(m.group(5)) and '\t' not in m.group(5):
            buf.append((k,m.group(5)));size+=len(m.group(5));tot+=len(m.group(5))
            if size>=12000: flush()
flush(); print('chunks',n,'chars',tot)
