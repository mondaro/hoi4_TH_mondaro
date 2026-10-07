import os,re,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from hoi import LINE,needs,core_files
src,out=sys.argv[1:3]; os.makedirs(out,exist_ok=True)
core=set(core_files(src)); buf=[];size=0;n=0;tot=0
def flush():
    global buf,size,n
    if buf:
        n+=1; open(f'{out}/s{n:03d}.tsv','w',encoding='utf-8').write(''.join(f'{i}\t{t}\n' for i,t in buf)); buf=[];size=0
for f in sorted(os.listdir(src)):
    if f in core: continue
    for ln,l in enumerate(open(os.path.join(src,f),encoding='utf-8-sig').read().split('\n')):
        m=LINE.match(l.rstrip('\r'))
        if m and re.search(r'(^|[_.])SIA([_.]|$)|siam',m.group(2),re.I) and needs(m.group(5)) and '\t' not in m.group(5):
            buf.append((f'{f}:{ln}',m.group(5)));size+=len(m.group(5));tot+=len(m.group(5))
            if size>=12000: flush()
flush(); print('chunks',n,'chars',tot)
