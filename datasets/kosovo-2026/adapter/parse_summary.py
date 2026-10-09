import os as _os, sys as _sys; _sys.path.insert(0,_os.environ.get('BUDGET_ROOT') or _os.path.abspath(__file__+'/../../../..'))
from pipeline.paths import DATASET_DIR; _os.chdir(DATASET_DIR)
import re, csv, json
from pipeline.pdfutil import lines, lines_merged, isnum, tonum
from layout import T1, T11, T2, A1, K210, KS, T43
def near(ws, cols, minx=0, tol=22):
    out={}
    for w in ws:
        t=w['text'].replace('(','-').replace(')','')
        if w['x1']<minx or not isnum(w['text']) and not re.fullmatch(r'-?[\d,]+',t): continue
        try: v=tonum(w['text'])
        except: continue
        c=min(cols,key=lambda c:abs(c[1]-w['x1']))
        if abs(c[1]-w['x1'])<=tol: out[c[0]]=v
    return out
def label(ws,maxx):
    return ' '.join(w['text'] for w in ws if w['x0']<maxx and not (isnum(w['text']) and w['x0']>maxx-40))
def wcsv(path,rows,fields):
    with open(path,'w',newline='') as f:
        w=csv.DictWriter(f,fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)

# ---- Table 1 & 1.1 (EUR millions) ----
def fiscal(lay, table):
    rows=[]; nx=lay['num_x']
    for pl in lay['pages']:
        p,cols,maxx=pl['page'],pl['cols'],pl['label_x']
        pend=''
        for l in lines(p):
            if l['top']<pl['top']: continue
            ws=l['words']
            vals=near(ws,cols,minx=nx,tol=lay['tol'])
            lab=label([w for w in ws if not (isnum(w['text']) and w['x1']>nx) and '%' not in w['text']],maxx).strip()
            if not vals:
                if lab and not any('%' in w['text'] for w in ws): pend=(pend+' '+lab).strip()
                continue
            if pend and (not lab or lab[0].islower() or lab.startswith(('TELEKOM','KOSTT','së','FS4','(1+2','rriten'))):
                lab=(pend+' '+lab).strip()
            elif pend and not lab: lab=pend
            pend=''
            rows.append(dict(table=table,page=p,top=round(l['top']),label=lab,raw=l['text'],**vals))
    return rows
t1=fiscal(T1,'1')
t11=fiscal(T11,'1.1')
F=['table','page','top','label','y2023','y2024','y2025','y2026','y2027','y2028','raw']
wcsv('raw/t1.csv',t1,F); wcsv('raw/t1_1.csv',t11,F)

# ---- Table 2 ----
t2=[]; pend=''
for l in lines(T2['page']):
    if l['top']<T2['top']: continue
    ws=l['words']; vals=near(ws,T2['cols'],minx=T2['num_x'],tol=T2['tol'])
    lab=' '.join(w['text'] for w in ws if w['x0']<T2['num_x'])
    if not vals:
        if lab not in ('Niveli Qendror','Niveli Lokal'): pend=(pend+' '+lab).strip()
        continue
    t2.append(dict(table='2',page=T2['page'],top=round(l['top']),label=(pend+' '+lab).strip(),raw=l['text'],**vals)); pend=''
wcsv('raw/t2.csv',t2,['table','page','top','label','staff','wages','goods','util','subs','capital','reserve','interest','total','raw'])

# ---- Annex 1 (p96) ----
an=[]; pend=''; sx0,sx1=A1['staff_x']; ax0,ax1=A1['name_x']
for l in lines_merged(A1['page']):
    if l['top']<A1['top']: continue
    ws=[w for w in l['words'] if w['x0']<A1['max_x']]
    # glue split staff digits like '6'@192 '0'@194
    if len(ws)>2:
        g=[]
        for w in ws:
            if g and re.fullmatch(r'\d',g[-1]['text']) and re.fullmatch(r'\d',w['text']) and sx0<g[-1]['x1']<sx1 and sx0<w['x1']<sx1: g[-1]['text']+=w['text']; g[-1]['x1']=w['x1']
            else: g.append(w)
        ws=g
    code=[w for w in ws if re.fullmatch(r'\d{3}',w['text']) and w['x1']<A1['code_x']]
    nm=''.join(w['text'] if len(w['text'])<3 else ' '+w['text'] for w in ws if ax0<w['x0']<ax1 and not isnum(w['text'])).strip()
    vals=near(ws,A1['cols'],minx=A1['num_x'],tol=A1['tol'])
    if not code and not vals:
        pend=(pend+' '+nm).strip(); continue
    if 'Totali' in l['text']:
        an.append(dict(table='Shtojca 1',page=A1['page'],top=round(l['top']),code='TOTAL',name='Totali i përgjithshëm',raw=l['text'],**vals)); continue
    an.append(dict(table='Shtojca 1',page=A1['page'],top=round(l['top']),code=code[0]['text'] if code else '',name=(pend+' '+nm).strip(),raw=l['text'],**vals)); pend=''
wcsv('raw/annex1.csv',an,['table','page','top','code','name','staff','wages','goods','util','subs','capital','reserve','total','raw'])

# ---- p210 municipal balance ----
m210=[]
L=lines(K210['page'])
for l in L:
    ws=l['words']
    if not re.fullmatch(r'[\d.]+',ws[0]['text']) and ws[0]['text']!='BILANCI': pass
    nums=[w for w in ws if isnum(w['text']) and w['x1']>K210['num_x']]
    if not nums: continue
    lab=' '.join(w['text'] for w in ws if w['x1']<=K210['num_x'])
    m210.append(dict(table='Komunat Tabela 1',page=K210['page'],top=round(l['top']),label=lab,raw=l['text'],nums=json.dumps([(w['text'],round(w['x1'])) for w in nums])))
wcsv('raw/muni_balance_p210.csv',m210,['table','page','top','label','nums','raw'])

# ---- p211-213 per-municipality category summary ----
ms=[]; section=''; cur=[]; fx0,fx1=KS['fund_x']; nx0,nx1=KS['name_x']
for p in KS['pages']:
    L=lines_merged(p)
    for l in L:
        ws=l['words']; t=l['text']
        if t.startswith('Nëntotali A'): section='A'; continue
        if t.startswith('Nëntotali B'): section='B'; continue
        if t.startswith('Gjithsej: Nëntotal A+B +'): section='A+B+Bilanci'; continue
        if t.startswith('Gjithsej: Nëntotal A+B'): section='A+B'; continue
        if t.startswith('Bilanci'): section='Bilanci'; continue
        if t.startswith('Komuna Fondi') or (p==KS['pages'][0] and l['top']<KS['top']): continue
        fund=[w for w in ws if w['text'] in('Total','Grant','THV') and fx0<w['x0']<fx1]
        hua='Huamarrja' in t
        vals=near(ws,KS['cols'],minx=KS['num_x'],tol=KS['tol'])
        namew=[w for w in ws if nx0<w['x0']<nx1 and not isnum(w['text']) and w['text'] not in('Total','Grant','THV','Financimi','nga','Huamarrja','komuna')]
        if namew: cur.append(' '.join(w['text'] for w in namew))
        if fund or hua:
            f='Total' if fund and fund[0]['text']=='Total' else ('Grant' if fund and fund[0]['text']=='Grant' else ('THV' if fund else 'Huamarrja'))
            agg=bool(re.search(r'Total \d+ komuna',t)) or section in('A+B','A+B+Bilanci','Bilanci') or (f!='Total' and ws[0]['x0']<95 and ws[0]['text'] in('Grant','THV','Financimi'))
            idx=[w['text'] for w in ws if re.fullmatch(r'\d+',w['text']) and w['x1']<KS['idx_x']]
            ms.append(dict(page=p,top=round(l['top']),section=section,fund=f,aggregate=agg,idx=idx[0] if idx else '',raw=t,**vals))
# attach names: each muni block = Total,Grant,THV,Huamarrja (4 rows, non-aggregate); names collected by top proximity
blocks=[]
for p in KS['pages']:
    L=lines_merged(p)
    names=[(l['top'],' '.join(w['text'] for w in l['words'] if nx0<w['x0']<nx1 and not isnum(w['text']) and w['text'] not in('Total','Grant','THV','Financimi','nga','Huamarrja','komuna'))) for l in L]
    names=[(t,n) for t,n in names if n and not n.startswith(('Komuna','Nëntotali','Gjithsej','Bilanci','Diferenca'))]
    for r in [r for r in ms if r['page']==p and not r['aggregate']]:
        r['_names']=names
for r in ms:
    if r['aggregate'] or r['fund']!='Total': continue
    nm=[n for t,n in r.get('_names',[]) if r['top']-2<t<r['top']+30]
    r['muni']=' '.join(nm)
cur=None
for r in ms:
    if r['aggregate']: r['muni']='(aggregate)'; continue
    if r['fund']=='Total': cur=r['muni']
    else: r['muni']=cur
wcsv('raw/muni_summary_p211.csv',ms,['page','top','section','muni','fund','aggregate','idx','staff','wages','goods','util','subs','capital','reserve','total','y2027','y2028','raw'])

# ---- Table 4.3 municipal revenue ----
rev=[]; muni=None
for p in T43['pages']:
    for l in lines(p):
        ws=l['words']; t=l['text']
        m=re.match(r'^(6\d\d)\s+(.+?)\s+2024',t)
        if m: muni=(m.group(1),m.group(2)); continue
        if t.startswith('Pershkrimi') and p==T43['summary_page']: muni=('TOTAL','Përmbledhje'); continue
        vals=near(ws,T43['cols'],minx=T43['num_x'],tol=T43['tol'])
        if not vals: continue
        lab=' '.join(w['text'] for w in ws if w['x1']<T43['num_x'])
        rev.append(dict(table='4.3',page=p,top=round(l['top']),code=muni[0] if muni else '',muni=muni[1] if muni else '',label=lab,raw=t,**vals))
wcsv('raw/t4_3.csv',rev,['table','page','top','code','muni','label','y2024','y2025','y2026','y2027','y2028','raw'])
print(len(t1),len(t11),len(t2),len(an),len(m210),len(ms),len(rev))
