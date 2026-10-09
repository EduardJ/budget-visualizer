"""Re-read sampled values with pdftotext: the 20 largest distinct figures, 20 random ones (seed 2026) and every node behind a finding
-> spotcheck.json"""
import os as _os, sys as _sys; _sys.path.insert(0,_os.environ.get('BUDGET_ROOT') or _os.path.abspath(__file__+'/../../../..'))
from pipeline.paths import DATASET_DIR, PDF; _os.chdir(DATASET_DIR)
import json, random
from pipeline.spotcheck import page_text, locate, printed_value, report
D=json.load(open(DATASET_DIR/'data.json')); R=D['refs']; N={n['id']:n for n in D['nodes']}
def verify(n):
    r=R[n['ref']]; col=n.get('refCol') or 'total'; v=r['values'].get(col)
    if not v: return None
    found,lab_ok=locate(page_text(PDF,r['page']),v,r['original_label'])
    num=printed_value(v,1e6 if r['unit']=='EUR million' else 1)
    amt=n['amount']*( -1 if n['id']=='rev:refunds' else 1)
    if n.get('amount_31') is not None: amt=n['amount_31']
    if n.get('amount_41') is not None: amt=n['amount_41']
    return dict(id=n['id'],name=n['name_sq'][:55],page=r['page'],table=r['table'],orig=v,value_found=found,label_on_line=lab_ok,matches_node=abs(num-amt)<1)
cands=[n for n in D['nodes'] if n.get('ref') and R[n['ref']]['table']!='computed' and n['kind']!='difference']
largest=sorted([n for n in cands if n['kind'] in('org','municipality','programme','subprogramme','project','line','group','dest')],key=lambda n:-abs(n['amount']))
seen=set(); top=[]
for n in largest:
    k=(R[n['ref']]['page'],R[n['ref']]['values'].get(n.get('refCol') or 'total'))
    if k in seen: continue
    seen.add(k); top.append(n)
    if len(top)==20: break
random.seed(2026); rnd=random.sample([n for n in cands if n not in top],20)
flagged=[N[f['node']] for f in D['findings'] if f.get('node') and N[f['node']].get('ref') and N[f['node']]['kind']!='difference']
out={}
for name,grp in (('top20',top),('random20',rnd),('flagged',flagged)):
    rows=[verify(n) for n in grp]; rows=[r for r in rows if r]
    out[name]=rows
    report(name,rows,list_ok=name!='flagged')
json.dump(out,open(DATASET_DIR/'spotcheck.json','w'),ensure_ascii=False,indent=1)
