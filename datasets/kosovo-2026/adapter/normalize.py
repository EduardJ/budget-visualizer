"""Normalise raw CSV extractions into data.json (sources, refs, nodes, flows, checks)."""
import os as _os, sys as _sys; _sys.path.insert(0,_os.environ.get('BUDGET_ROOT') or _os.path.abspath(__file__+'/../../../..'))
from pipeline.paths import REPO, DATASET_DIR, ADAPTER_DIR, PDF as PDF_PATH; _os.chdir(DATASET_DIR)
import csv, json, re, sys, collections
from glossary import ORG_EN, CAT, SRC, REV, en_name
from tree import build as build_tree, issues as tree_issues, CATS
R=str(DATASET_DIR/'raw')+'/'
def rd(f): return list(csv.DictReader(open(R+f)))
def fnum(x): return float(x) if x not in ('',None) else 0.0
PDF=PDF_PATH.name
M=1_000_000

# ---------------- sources (inventory) ----------------
SOURCES=[
 dict(id='T1',table='Tabela 1',title_sq='Parashikimet fiskale (të Hyrat dhe Shpenzimet)',title_en='Fiscal projections (revenue and expenditure)',pages=[29,30],unit='EUR million',covers='Revenue by type, expenditure by category, balance, financing summary (2026 = 4th numeric column)'),
 dict(id='T1.1',table='Tabela 1.1',title_sq='Financimi i Bilancit Buxhetor',title_en='Financing of the budget balance',pages=[32,33],unit='EUR million',covers='External/domestic receipts and outflows, bank balance, special-purpose funds'),
 dict(id='T2',table='Tabela 2',title_sq='Përmbledhje e ndarjeve buxhetore',title_en='Summary of budget allocations',pages=[34],unit='EUR',covers='Central vs local by economic category, staff, interest'),
 dict(id='T3.1',table='Tabela 3.1',title_sq='Buxheti i Nivelit Qendror',title_en='Central level budget',pages=list(range(35,94)),unit='EUR',covers='Institution → programme → sub-programme × category × funding source'),
 dict(id='T3.1.B',table='Tabela 3.1.B',title_sq='Buxheti i Nivelit Qendror (Klauzola e Investimeve)',title_en='Central level – investment clause',pages=[94,95],unit='EUR',covers='Loan-financed capital (investment clause)'),
 dict(id='A1',table='Shtojca 1',title_sq='Buxheti për vitin 2026 dhe vlerësimet 2027–2028',title_en='Annex 1: budget 2026 and estimates 2027–28',pages=[96],unit='EUR',covers='One row per institution'),
 dict(id='T3.2',table='Tabela 3.2',title_sq='Projektet Kapitale për Nivelin Qendror',title_en='Central capital projects',pages=list(range(97,204)),unit='EUR',covers='Projects with multi-year amounts'),
 dict(id='T3.2.B',table='Tabela 3.2.B',title_sq='Projektet Kapitale Përmes Klauzolës së Investimeve',title_en='Capital projects via the investment clause (central)',pages=list(range(204,210)),unit='EUR',covers='Investment-clause projects'),
 dict(id='K1',table='Komunat – Tabela 1',title_sq='Bilanci i të hyrave dhe shpenzimeve komunale',title_en='Municipal revenue and expenditure balance',pages=[210],unit='EUR',covers='All municipalities: sources and structure, 2024–2028'),
 dict(id='KS',table='Struktura e shpenzimeve',title_sq='Struktura e shpenzimeve sipas kategorive',title_en='Municipal spending structure by category',pages=[211,212,213],unit='EUR',covers='Per municipality by fund source; subtotals A, B and the difference ("Bilanci")'),
 dict(id='T4.1',table='Tabela 4.1',title_sq='Plani i ndarjeve buxhetore të shpenzimeve totale të komunës',title_en='Municipal budget allocation plan',pages=list(range(214,356)),unit='EUR',covers='Municipality → programme → sub-programme × category × source'),
 dict(id='T4.1.B',table='Tabela 4.1.B',title_sq='Buxheti i Nivelit Komunal (Klauzola)',title_en='Municipal level – investment clause',pages=[356],unit='EUR',covers='Investment-clause allocations (Prishtinë, Prizren)'),
 dict(id='T4.2',table='Tabela 4.2',title_sq='Financimi i Investimeve Kapitale Komunale',title_en='Municipal capital projects',pages=list(range(357,646)),unit='EUR',covers='Projects with multi-year amounts'),
 dict(id='T4.2.B',table='Tabela 4.2.B',title_sq='Projektet Kapitale Përmes Klauzolës së Investimeve (komunale)',title_en='Municipal investment-clause projects',pages=[646],unit='EUR',covers='Investment-clause projects'),
 dict(id='T4.3',table='Tabela 4.3',title_sq='Plani Afatmesëm i të hyrave totale të Buxhetit Komunal',title_en='Municipal revenue plan',pages=list(range(647,672)),unit='EUR',covers='Own-source revenue by type and government grants per municipality'),
 dict(id='ANX',table='Aneksi / Deklarata e risqeve',title_sq='Aneksi i performancës, projeksionet, risqet fiskale',title_en='Performance annex, macro-fiscal and fiscal-risk statement',pages=list(range(672,729)),unit='mixed',covers='Context only — not allocations; Tables 1/1.1 copies on pp.703–705 match pp.29–33'),
]
TABLE_PAGES={s['table']:s for s in SOURCES}

# ---------------- refs ----------------
REFS={}; _rc=[0]
def tok_for(raw,val,unit):
    toks=re.findall(r'\(?-?[\d][\d,]*(?:\.\d+)?\)?',raw)
    for t in toks:
        try:
            v=float(t.replace(',','').strip('()'))*(-1 if t.startswith(('(','-')) else 1)
        except: continue
        if abs(v-val)<1e-6: return t
    return None
def mkref(table,page,raw,label,unit,cols,row=None,method='parsed',top=None,note=None):
    _rc[0]+=1; rid=f'r{_rc[0]}'
    vals={}
    for k,v in cols.items():
        if v is None: continue
        if unit=='EUR million': o=tok_for(raw,v,unit)
        else: o=tok_for(raw,v,unit)
        vals[k]=o if o is not None else ('{:,.0f}'.format(v) if unit=='EUR' else str(v))
    REFS[rid]=dict(page=int(page),table=table,row=row or label,original_label=label,quote=raw,unit=unit,values=vals,method=method,top=top)
    if note: REFS[rid]['note']=note
    return rid

NODES={}; FLOWS=[]; CHECKS=[]; FINDINGS=[]
def node(id,**k):
    k.setdefault('flags',[]); k['id']=id
    NODES[id]=k; return k
def flow(fr,to,amount,ref,col='total',kind='hard',note=None):
    f=dict(id=f'f{len(FLOWS)+1}',source=fr,target=to,amount=round(amount,2),ref=ref,col=col,kind=kind)
    if note: f['note']=note
    FLOWS.append(f); return f
def check(id,title,expected,actual,pages,tol=0.0,refs=(),note='',kind='sum',severity=None,title_sq=None,note_sq=None,cls=None,group=None,unit=None):
    # no tolerance: a check passes only when the printed figures agree exactly.
    # 'tol' is only the largest gap that rounding of the summed printed figures could explain; it decides the label of a failure.
    diff=round(actual-expected,6)
    status='pass' if abs(diff)<1e-6 else 'fail'
    if status=='fail' and cls is None: cls='rounding' if abs(diff)<=tol+1e-9 else 'error'
    c=dict(id=id,title=title,expected=round(expected,6),actual=round(actual,6),diff=diff,bound=tol,status=status,cls=cls if status=='fail' else None,
           pages=sorted(set(pages)),refs=list(refs),note=note,kind=kind)
    if severity: c['severity']=severity
    if title_sq: c['title_sq']=title_sq
    if note_sq: c['note_sq']=note_sq
    if group: c['group']=group
    if unit: c['unit']=unit
    CHECKS.append(c); return c

# ---------------- Table 1 / 1.1 (millions) ----------------
t1=rd('t1.csv'); t11=rd('t1_1.csv')
def T(rows,label,occ=0):
    m=[r for r in rows if r['label'].strip()==label]
    if not m: raise KeyError(label)
    return m[occ]
def mval(r): return fnum(r['y2026'])*M
def mref(r,table,label=None):
    cols={'y2026':fnum(r['y2026'])}
    if r.get('y2025') not in ('',None): cols['y2025']=fnum(r['y2025'])
    return mkref(table,r['page'],r['raw'],label or r['label'],'EUR million',cols,top=r['top'])
def mnode(id,rows,label,table,parent=None,section='overview',occ=0,**kw):
    r=T(rows,label,occ); rid=mref(r,table)
    en=REV.get(label) or REV.get(label.strip())
    return node(id,kind=kw.pop('kind','line'),section=section,level=kw.pop('level',1),parent=parent,name_sq=label.strip().rstrip(':'),name_en=en or label,en_src='translated' if en else 'sq-only',
                amount=mval(r),ref=rid,refCol='y2026',unit_note='EUR million (1 decimal) ×1,000,000',**({'prev':fnum(r['y2025'])*M,'prevCol':'y2025'} if r.get('y2025') not in ('',None) else {}),**kw)

# revenue tree
mnode('rev:total',t1,'1. GJITHSEJ TË HYRAT BUXHETORE [1]','Tabela 1',kind='group')
mnode('rev:tax',t1,'1.1 Të Hyra Tatimore','Tabela 1',parent='rev:total',kind='group')
mnode('rev:direct',t1,'Tatimet Direkte','Tabela 1',parent='rev:tax',kind='group')
mnode('rev:cit',t1,'Tatimi në të ardhurat e korporatave','Tabela 1',parent='rev:direct')
mnode('rev:pit',t1,'Tatimi në të ardhura personale','Tabela 1',parent='rev:direct')
mnode('rev:prop',t1,'Tatimi në pronë','Tabela 1',parent='rev:direct')
mnode('rev:dother',t1,'Të tjera','Tabela 1',parent='rev:direct',occ=0); NODES['rev:dother']['name_en']='Other direct taxes'
mnode('rev:indirect',t1,'Tatimet Indirekte','Tabela 1',parent='rev:tax',kind='group')
mnode('rev:vat',t1,'Tatimi mbi Vlerën e Shtuar(TVSH)','Tabela 1',parent='rev:indirect',kind='group')
mnode('rev:vatdom',t1,'Vendore:','Tabela 1',parent='rev:vat'); NODES['rev:vatdom']['name_sq']='TVSH – Vendore'
mnode('rev:vatbor',t1,'Kufitare:','Tabela 1',parent='rev:vat'); NODES['rev:vatbor']['name_sq']='TVSH – Kufitare'
mnode('rev:customs',t1,'Detyrimi Doganor','Tabela 1',parent='rev:indirect')
mnode('rev:excise',t1,'Akcizë','Tabela 1',parent='rev:indirect')
mnode('rev:iother',t1,'Të tjera','Tabela 1',parent='rev:indirect',occ=1); NODES['rev:iother']['name_en']='Other indirect taxes'
mnode('rev:refunds',t1,'Rimbursimet tatimore','Tabela 1',parent='rev:tax')
mnode('rev:nontax',t1,'1.2 Të Hyrat Jo-Tatimore','Tabela 1',parent='rev:total',kind='group')
mnode('rev:fees',t1,'Taksat, ngarkesa dhe të tjera','Tabela 1',parent='rev:nontax',kind='group')
mnode('rev:feesc',t1,'Taksa, ngarkesa dhe të tjera - Niveli Qendror','Tabela 1',parent='rev:fees')
mnode('rev:feesl',t1,'Taksa, ngarkesa dhe të tjera - Niveli Lokal','Tabela 1',parent='rev:fees')
mnode('rev:conc',t1,'Taksa koncesionare','Tabela 1',parent='rev:nontax')
mnode('rev:mining',t1,'Renta Minerare','Tabela 1',parent='rev:nontax')
mnode('rev:mobile',t1,'Te hyrat nga liberalizimi i tregut te telefonise mobile','Tabela 1',parent='rev:nontax')
mnode('rev:divid',t1,'Te hyrat nga dividenda dhe ndarja e fitimit','Tabela 1',parent='rev:nontax')
mnode('rev:intinc',t1,'Të hyrat nga interesi','Tabela 1',parent='rev:nontax')
mnode('rev:grants',t1,'1.3 Grantet dhe ndihmat','Tabela 1',parent='rev:total',kind='group')
mnode('rev:gbs',t1,'Grante për mbështetje buxhetore','Tabela 1',parent='rev:grants')
mnode('rev:gdon',t1,'Grante e përcaktuara të donatorëve','Tabela 1',parent='rev:grants')
# expenditure (Table 1)
mnode('exp:total',t1,'2. GITHSEJ SHPENZIMET BUXHETORE[1]','Tabela 1',kind='group',section='overview-exp')
for i,(lab,id) in enumerate([('2.1 Shpenzimet Rrjedhëse','exp:current'),('Paga dhe shtesa','exp:wages'),('Mallra dhe Shërbime','exp:goods'),('Subvencione dhe Transfere','exp:subs'),
    ('Rezerva rrjedhëse','exp:reserve'),('2.2 Interesi për Borxhin Publik','exp:interest'),('2.3 Shpenzimet Kapitale','exp:capital'),('Financimi nga buxheti i rregullt','exp:capreg'),
    ('Klauzola e investimeve','exp:capclause'),('2.4 Grantet e Përcaktuara të Donatorve','exp:donor'),('3. Bilanci buxhetor (1-2)','exp:balance')]):
    par={'exp:wages':'exp:current','exp:goods':'exp:current','exp:subs':'exp:current','exp:reserve':'exp:current','exp:capreg':'exp:capital','exp:capclause':'exp:capital'}.get(id,'exp:total')
    if id=='exp:balance': par=None
    mnode(id,t1,lab,'Tabela 1',parent=par,section='overview-exp',kind='line')
mnode('fin:need',t1,'A. Nevoja për financim','Tabela 1',section='overview-fin')
mnode('fin:extnet',t1,'B. Financimi i jashtëm(neto)','Tabela 1',section='overview-fin')
mnode('fin:domnet',t1,'C. Financimi i brendshëm(neto)','Tabela 1',section='overview-fin')
mnode('fin:bank',t1,'D. Ndryshimi në bilancin e pashpërndarë bankar (A+B+C)','Tabela 1',section='overview-fin')
# Table 1.1 gross financing
for lab,id,par in [('2.1. Pranimet:','fin:extin',None),('Financim Direkt Buxhetor - FMN, BB, BE, etj.','fin:dbs','fin:extin'),('Nën-huazimet, bruto pranimet','fin:onl_in','fin:extin'),
    ('Projekt-kreditë','fin:projl','fin:extin'),('Projekt-kreditë, trajtim brenda deficiti (fondi 04)','fin:projl04','fin:projl'),('Projekt-kreditë, klauzola e investimeve (fondi 06)','fin:projl06','fin:projl'),
    ('2.2. Daljet:','fin:extout',None),('Pagesa e kryegjesë së borxhit','fin:principal','fin:extout'),
    ('3.1. Pranimet:','fin:domin',None),('Emetimet e reja të letrave me vlerë','fin:newsec','fin:domin'),('Pranimet nga emetimet e letrave me vlerë për qëllime rifinancimi','fin:refin_in','fin:domin'),
    ('Pranimet nga kthimet prej entitetet publike (kryegjesë)','fin:repay_in','fin:domin'),
    ('3.2. Daljet:','fin:domout',None),('Huadhënia për entitete publike','fin:lend','fin:domout'),('Nen-huazimet, bruto daljet','fin:onl_out','fin:domout'),
    ('Daljet nga emetimet e letrave me vlerë për qëllime rifinancimi','fin:refin_out','fin:domout'),('Daljet për anëtarsim dhe rritje te kuotave në INF','fin:ifi','fin:domout'),
    ('Dalje për Kapitalizim dhe blerje të aksioneve','fin:capz','fin:domout'),('2. Neto financimi nga burimet e jashtme për vitin','fin:t11ext',None),('3. Neto financimi nga burimet e brendshme për vitin','fin:t11dom',None)]:
    mnode(id,t11,lab,'Tabela 1.1',parent=par,section='overview-fin',kind='line')
# zero-valued Table 1.1 domestic receipt lines (kept for completeness of the sum check)
dom_other=[r for r in t11 if r['label'].startswith(('Financimi i njehereshem','Pranimet e dedikuara','Ndryshimi nga stoku'))]
dom_out_other=[r for r in t11 if r['label'].startswith('Dalje për rritjen')]

# ---------------- Table 2 ----------------
t2=rd('t2.csv')
def t2row(prefix): return [r for r in t2 if r['label'].startswith(prefix)][0]
T2C=['staff','wages','goods','util','subs','capital','reserve','interest','total']
def t2ref(r): return mkref('Tabela 2',34,r['raw'],r['label'],'EUR',{k:fnum(r[k]) for k in T2C if r.get(k) not in ('',None)},top=r['top'])
r_c31=t2row('3.1. Buxheti'); r_c31b=t2row('3.1.B'); r_cen=t2row('Gjithesej Niveli Qendror')
r_l41=t2row('4.1. Buxheti'); r_l41b=t2row('4.1.B'); r_loc=t2row('Gjithesej Niveli lokal'); r_int=t2row('Interesi'); r_tot=t2row('Gjithesej Buxheti')
ref_cen=t2ref(r_cen); ref_loc=t2ref(r_loc); ref_int=t2ref(r_int); ref_tot=t2ref(r_tot); ref_c31=t2ref(r_c31); ref_c31b=t2ref(r_c31b); ref_l41=t2ref(r_l41); ref_l41b=t2ref(r_l41b)
def cats_of(r): return {k:fnum(r[k]) for k in CATS if fnum(r.get(k,0))}
node('budget',kind='pool',section='overview',level=1,name_sq='Buxheti i Republikës së Kosovës 2026',name_en='Kosovo budget 2026',en_src='translated',amount=fnum(r_tot['total']),ref=ref_tot,refCol='total',
     note='Table 2 grand total (allocations incl. interest). Table 1 total expenditure also includes €12.0M donor-designated grants.')
node('dest:central',kind='dest',section='overview',level=1,name_sq='Niveli Qendror',name_en='Central government',en_src='translated',amount=fnum(r_cen['total']),ref=ref_cen,refCol='total',cats=cats_of(r_cen),staff=fnum(r_cen['staff']))
node('dest:local',kind='dest',section='overview',level=1,name_sq='Niveli Lokal (Komunat)',name_en='Municipalities',en_src='translated',amount=fnum(r_loc['total']),ref=ref_loc,refCol='total',cats=cats_of(r_loc),staff=fnum(r_loc['staff']))
node('dest:interest',kind='dest',section='overview',level=1,name_sq='Interesi',name_en='Interest on public debt',en_src='translated',amount=fnum(r_int['total']),ref=ref_int,refCol='total')
node('dest:donor',kind='dest',section='overview',level=1,name_sq=NODES['exp:donor']['name_sq'],name_en='Donor-designated grants (outside Table 2)',en_src='translated',amount=NODES['exp:donor']['amount'],ref=NODES['exp:donor']['ref'],refCol='y2026',
     flags=['RECONCILIATION'],note='Counted in Table 1 total expenditure (p.29) but not allocated in Table 2 (p.34).')
for k in ['wages','goods','util','subs','capital','reserve','interest','donor']:
    sq,en=CAT[k]
    node('cat:'+k,kind='category',section='overview',level=1,name_sq=sq,name_en=en,en_src='translated',amount=0,ref=None)

# ---------------- Central: Table 3.1 / 3.1.B ----------------
orgs31,rows31=build_tree(R+'t3_1.csv'); orgs31b,_=build_tree(R+'t3_1B.csv')
annex=rd('annex1.csv'); annex_names=json.load(open(R+'org_names_annex1.json'))
annex_names['255']=annex_names['255'].replace('Klasifik uar','Klasifikuar')
COLS31=['staff','wages','goods','util','subs','capital','reserve','total','y2027','y2028']
def rowref(table,r,label=None):
    return mkref(table,r['page'],r['raw'],label or r['name'],'EUR',{k:r[k] for k in COLS31 if r.get(k) not in ('',None) and (r[k] or k=='total')},top=r['top'])
SRCKEY={'Grantet Qeveritare':'gq','Të Hyrat vetanake':'thv','Te Hyrat Vetanake':'thv','Financimi nga Huamarrja':'fh','Të Hyrat nga AKP':'akp','Klauzola e Investimeve':'fhki','Financim i Jashtem':'ext'}
def srcs_of(n,table):
    out={}
    for k,v in n['sources'].items():
        if v['total']: out[SRCKEY.get(k,k)]=dict(amount=v['total'],ref=rowref(table,v,f"{n['name']} – {k}"),label_sq=k,cats={c:v[c] for c in CATS if v[c]})
    return out
def add_tree(n,table,parent,prefix,section,level,org_code):
    if n['kind']=='org': nid=f'{prefix}:{n["code"]}'
    elif n['kind']=='prog': nid=f'{parent}/p{len([x for x in NODES.values() if x.get("parent")==parent])}'
    else: nid=f'{parent}/s{n["code"]}'
    sq=n['name']; en,src=en_name(sq)
    if n['kind']=='org':
        sq=annex_names.get(n['code'],sq) if prefix=='org' else sq; en=ORG_EN.get(n['code']); src='translated' if en else 'sq-only'
    rid=rowref(table,n)
    nd=node(nid,kind={'org':'org','prog':'programme','sub':'subprogramme'}[n['kind']],section=section,level=level,parent=parent,name_sq=sq,name_en=en or sq,en_src=src,
         amount=n['total'],ref=rid,refCol='total',cats={c:n[c] for c in CATS if n[c]},staff=n['staff'] or 0,code=n['code'],func=n.get('func',''),
         y2027=n['y2027'],y2028=n['y2028'],sources=srcs_of(n,table),table=table,org=org_code)
    if prefix=='org' and n['kind']=='org' and len(n['name'])<len(sq)-3: nd['flags'].append('NAME_TRUNCATED_IN_TABLE'); nd['table_name']=n['name']
    for ch in n['children']: add_tree(ch,table,nid,prefix,section,level+1,org_code)
    # children-sum reconciliation
    if n['children']:
        cs=sum(c['total'] for c in n['children']); d=n['total']-cs
        if abs(d)>=1:
            did=nid+'/diff'
            node(did,kind='difference',section=section,level=level+1,parent=nid,name_sq='E pashpërndarë / diferencë',name_en='Unallocated / difference',en_src='translated',amount=d,ref=rid,refCol='total',flags=['RECONCILIATION'],
                 note=f'{n["name"]} total {n["total"]:,.0f} vs sum of its {len(n["children"])} lines {cs:,.0f} (Table {table}, p.{n["page"]}).')
    return nid
for o in orgs31:
    oid=add_tree(o,'Tabela 3.1','dest:central','org','central',2,o['code'])
for o in orgs31b:
    oid=f'org:{o["code"]}'
    if oid not in NODES: raise SystemExit('3.1.B org without 3.1 row '+o['code'])
    gid=oid+'/clause'
    rid=rowref('Tabela 3.1.B',o)
    node(gid,kind='programme',section='central',level=3,parent=oid,name_sq='Klauzola e Investimeve (Tabela 3.1.B)',name_en='Investment clause (loan-financed, Table 3.1.B)',en_src='translated',amount=o['total'],ref=rid,refCol='total',
         cats={c:o[c] for c in CATS if o[c]},staff=0,code='3.1.B',sources=srcs_of(o,'Tabela 3.1.B'),table='Tabela 3.1.B',org=o['code'])
    for ch in o['children']: add_tree(ch,'Tabela 3.1.B',gid,'org','central',4,o['code'])
    on=NODES[oid]; on['amount_31']=on['amount']; on['amount']+=o['total']; on['cats']['capital']=on['cats'].get('capital',0)+o['capital']
    on['sources']['fhki']=dict(amount=o['total'],ref=rid,label_sq='Klauzola e Investimeve',cats={'capital':o['capital']})
    on['note']=f"Table 3.1 total {on['amount_31']:,.0f} + investment clause (Table 3.1.B) {o['total']:,.0f}"

# ---------------- Municipal: Table 4.1 / 4.1.B ----------------
orgs41,rows41=build_tree(R+'t4_1.csv'); orgs41b,_=build_tree(R+'t4_1B.csv')
ms=rd('muni_summary_p211.csv')
MUNI_NAME={o['code']:o['name'] for o in orgs41}
for o in orgs41:
    add_tree(o,'Tabela 4.1','dest:local','mun','municipal',2,o['code'])
    n=NODES['mun:'+o['code']]; n['kind']='municipality'; n['name_en']=o['name']; n['en_src']='proper noun'
for o in orgs41b:
    mid='mun:'+o['code']; gid=mid+'/clause'; rid=rowref('Tabela 4.1.B',o)
    node(gid,kind='programme',section='municipal',level=3,parent=mid,name_sq='Klauzola e Investimeve (Tabela 4.1.B)',name_en='Investment clause (Table 4.1.B)',en_src='translated',amount=o['total'],ref=rid,refCol='total',cats={'capital':o['capital']},staff=0,code='4.1.B',table='Tabela 4.1.B',org=o['code'],sources={})
    for ch in o['children']: add_tree(ch,'Tabela 4.1.B',gid,'mun','municipal',4,o['code'])
    n=NODES[mid]; n['amount_41']=n['amount']; n['amount']+=o['total']; n['cats']['capital']=n['cats'].get('capital',0)+o['capital']
    n['sources']['fhki']=dict(amount=o['total'],ref=rid,label_sq='Klauzola e Investimeve',cats={'capital':o['capital']})
    n['note']=f"Table 4.1 total {n['amount_41']:,.0f} + investment clause (Table 4.1.B) {o['total']:,.0f}"

# municipal revenue (Table 4.3)
rev=rd('t4_3.csv')
REVKEYS={'Të Hyrat Komunale Totale':'total','Të Hyrat Vetanake':'own','Transferet Qeveritare':'transfers','Granti i Përgjithshëm':'g_general','Granti për Arsim':'g_edu','Granti për Shëndetësi':'g_health'}
mrev=collections.defaultdict(dict)
for r in rev:
    if r['code'] in ('',): continue
    key=r['code']; lab=r['label'].strip()
    if lab in ('Buxheti i','19 February 2026'): continue
    mrev[key].setdefault('lines',[]).append(dict(label=lab,amount=fnum(r['y2026']),prev=fnum(r['y2025']),ref=mkref('Tabela 4.3',r['page'],r['raw'],f"{r['muni']} – {lab}",'EUR',{'y2025':fnum(r['y2025']),'y2026':fnum(r['y2026'])},top=r['top'])))
for code,d in mrev.items():
    if code=='TOTAL': continue
    n=NODES.get('mun:'+code)
    if n: n['revenue']=d['lines']

# ---------------- Capital projects ----------------
PROJ=[]
def load_proj(f,table,section):
    rows=rd(f); cur=None
    for r in rows:
        if r['kind']=='project':
            org=re.match(r'(\d{3})',r['org']).group(1) if r['org'] else ''
            cur=dict(table=table,section=section,org=org,prog=r['prog'],sub=r['sub'],func=r['func'],prop_code=r['prop_code'],proj_code=r['proj_code'],dates=r['dates'],name=r['name'].strip(),
                     page=int(r['page']),top=int(r['top']),raw=r['raw'],srcs=[],flag=r.get('flag',''))
            PROJ.append(cur)
        elif r['kind']=='source' and cur is not None:
            cur['srcs'].append(r)
load_proj('t3_2.csv','Tabela 3.2','central'); load_proj('t3_2B.csv','Tabela 3.2.B','central'); load_proj('t4_2.csv','Tabela 4.2','municipal'); load_proj('t4_2B.csv','Tabela 4.2.B','municipal')
PC=['spent_to_2025','cont_2026','new_2026','total_2026','y2027','y2028','y2029plus','project_total']
for i,p in enumerate(PROJ):
    agg={k:sum(fnum(s[k]) for s in p['srcs']) for k in PC}
    srcref=[mkref(p['table'],s['page'],s['raw'],f"{p['name'][:60]} – {s['source']}",'EUR',{k:fnum(s[k]) for k in PC},top=s['top']) for s in p['srcs']]
    head=mkref(p['table'],p['page'],p['raw'],p['name'] or '(no project line)','EUR',{},top=p['top'])
    owner=('org:' if p['section']=='central' else 'mun:')+p['org']
    pid=f"proj:{p['table'].split()[-1]}:{p['proj_code'] or i}:{i}"
    flags=[]
    if p['flag']=='orphan_funding_row': flags.append('AMBIGUITY')
    if agg['total_2026']==0 and not flags: flags.append('ZERO_2026')
    node(pid,kind='project',section='capital',level=3,parent=None,owner=owner,name_sq=p['name'] or '(rresht financimi pa emër projekti)',name_en=p['name'] or '(funding row without a project line)',en_src='sq-only',
         amount=agg['total_2026'],ref=srcref[0] if len(srcref)==1 else head,refCol='total_2026',head_ref=head,src_refs=srcref,multi={k:agg[k] for k in PC},
         fund=[s['source'] for s in p['srcs']],code=p['proj_code'],prop_code=p['prop_code'],dates=p['dates'],func=p['func'],table=p['table'],org=p['org'],sub_label=p['sub'],prog_label=p['prog'],flags=flags)

json.dump(dict(PROJ_COUNT=len(PROJ)),sys.stdout); print()
exec(open(ADAPTER_DIR/'normalize_part2.py').read())
