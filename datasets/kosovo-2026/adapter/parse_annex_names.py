"""Full institution names from Shtojca 1 (p.96) -> raw/org_names_annex1.json; Tabela 3.1 cuts many of them off.
Read by character position, not by word: one-letter words ("e", "i") sit tight against their neighbours, a name wraps
onto the lines just above and below its coded row, and one name has invisible spaces printed over its bold glyphs."""
import os as _os, sys as _sys; _sys.path.insert(0,_os.environ.get('BUDGET_ROOT') or _os.path.abspath(__file__+'/../../../..'))
from pipeline.paths import DATASET_DIR; _os.chdir(DATASET_DIR)
import re, json
from pipeline.pdfutil import pdf, lines
from layout import A1
P=A1['page']; X0,X1=A1['name_chars_x']
chars=[c for c in pdf().pages[P-1].chars if X0<=c['x0']<X1]
def text_at(top, tol=2.5):
    cs=sorted((c for c in chars if abs(c['top']-top)<=tol),key=lambda c:c['x0'])
    ink=[c for c in cs if c['text'].strip()]
    # a space mostly covered by visible glyphs is an overprinted artefact, not a word break
    covered=lambda c:sum(max(0,min(c['x1'],g['x1'])-max(c['x0'],g['x0'])) for g in ink)>0.5*(c['x1']-c['x0'])
    keep=[c for c in cs if c['text'].strip() or not covered(c)]
    out=''; last=None
    for c in keep:
        if last is not None and c['x0']-last>1.5: out+=' '
        out+=c['text']; last=c['x1']
    return re.sub(r'\s+',' ',out).strip()
rows=[]
for l in lines(P):
    if l['top']<A1['top']: continue
    code=[w['text'] for w in l['words'] if re.fullmatch(r'\d{3}',w['text']) and w['x1']<A1['code_x']]
    rows.append((l['top'],code[0] if code else None,text_at(l['top'])))
coded=[(t,c) for t,c,_ in rows if c]
parts={c:[] for _,c in coded}
for t,c,name in rows:
    if not name or name.startswith('Totali'): continue
    # a wrapped line belongs to the nearest coded row: the PDF centres the code within its multi-line cell
    parts[c or min(coded,key=lambda x:abs(x[0]-t))[1]].append((t,name))
names={c:' '.join(n for _,n in sorted(v)) for c,v in parts.items()}
open('raw/org_names_annex1.json','w').write(json.dumps(names,ensure_ascii=False,indent=0))
print('Shtojca 1 names',len(names))
