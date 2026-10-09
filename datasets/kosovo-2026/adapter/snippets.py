"""Which references get a highlighted page snippet -> snippets/<rid>.jpg"""
import os as _os, sys as _sys; _sys.path.insert(0,_os.environ.get('BUDGET_ROOT') or _os.path.abspath(__file__+'/../../../..'))
from pipeline.paths import DATASET_DIR, PDF; _os.chdir(DATASET_DIR)
import json
from pipeline.snippets import render
D=json.load(open(DATASET_DIR/'data.json'))
REFS=D['refs']; N={n['id']:n for n in D['nodes']}
want=set()
for rid,r in REFS.items():
    if r['table'] in ('Tabela 1','Tabela 1.1','Tabela 2','Shtojca 1','Struktura e shpenzimeve') : want.add(rid)
for n in D['nodes']:
    if n['kind'] in ('org','municipality','dest','pool','category','line','group','difference') and n.get('ref'): want.add(n['ref'])
    for k in ('annex_ref','summary_ref'):
        if n.get(k): want.add(n[k])
projs=sorted([n for n in D['nodes'] if n['kind']=='project'],key=lambda n:-n.get('amount',0))[:80]
for p in projs:
    want.add(p['head_ref']); want.update(p.get('src_refs',[])[:2])
for f in D['findings']:
    if f.get('node') and N.get(f['node'],{}).get('ref'): want.add(N[f['node']]['ref'])
want={w for w in want if REFS[w].get('top') is not None and REFS[w]['table']!='computed'}
n,size=render(REFS,want,PDF,DATASET_DIR/'snippets')
print(n,'snippets',round(size/1e6,2),'MB')
