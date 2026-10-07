import os,re,sys,collections
root=sys.argv[1]
pat=re.compile(r'^\s*([^#\s][^:]*):\d*\s*"(.*)"\s*(#.*)?$')
rows=[];tot_e=tot_w=tot_c=0
for dp,_,fs in os.walk(root):
  for f in fs:
    p=os.path.join(dp,f)
    t=open(p,encoding='utf-8-sig',errors='replace').read()
    e=w=c=0
    for l in t.splitlines():
      m=pat.match(l)
      if m and m.group(2).strip():
        e+=1;s=m.group(2);c+=len(s);w+=len(s.split())
    rows.append((c,e,w,f));tot_e+=e;tot_w+=w;tot_c+=c
rows.sort(reverse=True)
print("files",len(rows),"entries",tot_e,"words",tot_w,"chars",tot_c)
for r in rows[:30]:print(r)
# group by prefix
g=collections.Counter()
for c,e,w,f in rows:
  g[f.split('_')[0]]+=c
print(g.most_common(25))
