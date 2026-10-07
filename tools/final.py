import os,sys,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from hoi import LINE,toks
src,out=sys.argv[1:3]; bad=0; tr=0; tot=0
for f in sorted(os.listdir(out)):
    a=open(os.path.join(src,f),encoding='utf-8-sig').read().split('\n')
    braw=open(os.path.join(out,f),'rb').read(); assert braw[:3]==b'\xef\xbb\xbf',f
    b=braw.decode('utf-8-sig').split('\n')
    if len(a)!=len(b): print('LINECOUNT',f); bad+=1; continue
    for x,y in zip(a,b):
        mx,my=LINE.match(x.rstrip('\r')),LINE.match(y.rstrip('\r'))
        if bool(mx)!=bool(my): print('PARSE',f,y[:80]); bad+=1; continue
        if not mx: 
            if x!=y: print('DIFF',f); bad+=1
            continue
        tot+=1
        if mx.group(2)!=my.group(2) or toks(mx.group(5))!=toks(my.group(5)): print('BAD',f,mx.group(2)); bad+=1
        if mx.group(5)!=my.group(5): tr+=1
print('files',len(os.listdir(out)),'entries',tot,'translated',tr,'problems',bad)
