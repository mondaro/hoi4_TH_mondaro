import sys,os,glob,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from hoi import toks
def load(p):
    d=[]
    for l in open(p,encoding='utf-8-sig').read().split('\n'):
        if not l.strip(): continue
        if '\t' not in l: d.append((None,l)); continue
        i,t=l.split('\t',1); d.append((i,t))
    return d
def check(src,th):
    a=load(src); b=load(th) if os.path.exists(th) else []
    bd={i:t for i,t in b if i}
    errs=[]
    for i,t in a:
        if i not in bd: errs.append(f'{i}: MISSING'); continue
        u=bd[i]
        if toks(t)!=toks(u): errs.append(f'{i}: CODE MISMATCH en={toks(t)} th={toks(u)}')
        elif t.count('"')!=u.count('"'): errs.append(f'{i}: QUOTE COUNT')
        elif '\t' in u: errs.append(f'{i}: TAB')
        elif not re.search('[฀-๿]',u) and re.search('[a-z]{4,} [a-z]{3,}',t): errs.append(f'{i}: NOT TRANSLATED?')
    extra=[i for i,_ in b if i is None or i not in dict(a)]
    if extra: errs.append(f'EXTRA/BAD LINES: {len(extra)}')
    return errs
if __name__=='__main__':
    bad=0
    for s in sys.argv[1:]:
        e=check(s,s.replace('.tsv','.th.tsv'))
        print(os.path.basename(s), 'OK' if not e else f'{len(e)} problems'); bad+=len(e)
        for x in e[:40]: print('  ',x)
    sys.exit(1 if bad else 0)
