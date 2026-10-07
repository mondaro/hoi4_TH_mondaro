import os,re,sys,json
LINE=re.compile(r'^(\s*)([^#\s"][^:"\s]*):(\d*)(\s*)"(.*)"(\s*(?:#.*)?)$')
PROT=re.compile(r'\$[^$\s]*\$|\[[^\]]*\]|§.|£[A-Za-z0-9_]+(?:\|[0-9]+)?£?|\\n|@[A-Za-z0-9_]+|\{[^}]*\}|%')
DLC=('wuw','sea','aat','bftb','bba','nsb','goe','taog','toa','lar','mtg','wtt','dod','mun','poland','events','focus')
def core_files(src):
    return sorted(f for f in os.listdir(src) if f.endswith('.yml') and f.lower().split('_')[0] not in DLC)
def needs(text):
    rest=PROT.sub('',text)
    return re.search(r'[A-Za-z]{2,}',rest) is not None
def toks(s): return sorted(PROT.findall(s))
def extract(src,out,maxc=12000):
    os.makedirs(out,exist_ok=True); n=0; buf=[]; size=0; man=[]
    def flush():
        nonlocal buf,size,n
        if buf:
            n+=1; p=os.path.join(out,f'c{n:03d}.tsv')
            open(p,'w',encoding='utf-8').write(''.join(f'{i}\t{t}\n' for i,t in buf)); man.append((p,size)); buf=[];size=0
    tot=0
    for f in core_files(src):
        for ln,l in enumerate(open(os.path.join(src,f),encoding='utf-8-sig').read().split('\n')):
            m=LINE.match(l.rstrip('\r'))
            if m and needs(m.group(5)):
                t=m.group(5)
                if '\t' in t: continue
                buf.append((f'{f}:{ln}',t)); size+=len(t); tot+=len(t)
                if size>=maxc: flush()
    flush(); print('chunks',n,'chars',tot)
if __name__=='__main__':
    extract(sys.argv[1],sys.argv[2])
