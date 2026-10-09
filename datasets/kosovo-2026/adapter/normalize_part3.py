# ---- part 3: prior-year figures, GDP, per-tab headline figures (runs inside normalize_part2) ----
from pipeline.pdfutil import lines as plines, isnum as pisnum
# GDP (Tabela 1, p.30)
g=T(t1,'BPV'); gref=mkref('Tabela 1',g['page'],g['raw'],'BPV','EUR million',{'y2025':fnum(g['y2025']),'y2026':fnum(g['y2026'])},top=g['top'])
node('macro:gdp',kind='line',section='overview-fin',level=1,name_sq='Bruto Produkti Vendor (BPV)',name_en='Gross domestic product (GDP)',en_src='translated',amount=fnum(g['y2026'])*M,
     prev=fnum(g['y2025'])*M,prevCol='y2025',ref=gref,refCol='y2026',anchor='pool',macro=True,
     note_en='Nominal GDP projection used by the budget (Tabela 1 memo line). Context only — not money flowing through the budget.',
     note_sq='Projeksioni i BPV-së nominale i përdorur nga buxheti (rresht memo në Tabelën 1). Vetëm kontekst — nuk janë para që kalojnë nëpër buxhet.')
NODES['debt:total']['prev']=NODES['debt:ext']['prev']+NODES['debt:dom']['prev']
# p.701 tables: central and local spending 2025 vs 2026 (EUR million)
P701={'central':[],'local':[]}; cur='central'
for l in plines(701):
    ws=l['words']; nums=[w for w in ws if pisnum(w['text']) and w['x1']>330]
    lab=' '.join(w['text'] for w in ws if w['x1']<330 and not pisnum(w['text']))
    if len(nums)!=4 or not lab or lab.startswith(('Buxheti','krahasuar','rritje','Deficiti','Në','2.0%','vitet')): continue
    P701[cur].append(dict(label=lab,top=round(l['top']),raw=l['text'],v=[float(w['text'].replace(',','')) for w in nums]))
    if lab=='Gjithsej': cur='local'
CATMAP={'Paga dhe shtesa':'wages','Mallra dhe shërbime':'goods','Shpenzime komunale':'util','Subvencione dhe transfere':'subs','Shpenzime kapitale':'capital','Rezerva':'reserve'}
TAB701={'central':'Tabela 1. Shpenzimet në nivelin qendror (f.701)','local':'Tabela 2. Shpenzimet në nivelin lokal (f.701)'}
for lvl,did in (('central','dest:central'),('local','dest:local')):
    rows=P701[lvl]; tot=[r for r in rows if r['label']=='Gjithsej'][0]
    n=NODES[did]; n['prev']=tot['v'][0]*M; n['prevCol']='y2025'
    n['prev_ref']=mkref(TAB701[lvl],701,tot['raw'],'Gjithsej','EUR million',{'y2025':tot['v'][0],'y2026':tot['v'][1]},top=tot['top'])
    n['cats_prev']={CATMAP[r['label']]:r['v'][0]*M for r in rows if r['label'] in CATMAP}
    n['cats_prev_ref']={CATMAP[r['label']]:mkref(TAB701[lvl],701,r['raw'],r['label'],'EUR million',{'y2025':r['v'][0],'y2026':r['v'][1]},top=r['top']) for r in rows if r['label'] in CATMAP}
    check(f'p701_{lvl}','p.701 2026 total vs Tabela 2 '+('central' if lvl=='central' else 'local'),n['amount'],tot['v'][1]*M,[34,701],TOLM)
    s25=sum(r['v'][0] for r in rows if r['label'] in CATMAP)*M
    check(f'p701_{lvl}_sum','p.701 2025 categories sum to 2025 total ('+lvl+')',tot['v'][0]*M,s25,[701],TOLM)
c25=NODES['dest:central']['prev']; l25=NODES['dest:local']['prev']
check('p701_vs_t1_2025','2025: central + local (p.701) + interest + donor grants (Tabela 1) = Tabela 1 total spending 2025',NODES['exp:total']['prev'],c25+l25+NODES['exp:interest']['prev']+NODES['exp:donor']['prev'],[29,701],TOLM)
gc=(3024.7/2757.7-1)*100
check('p701_narr_central','Narrative growth claim, central level (“rritje prej 10.0%”, p.701) vs its own table',10.0,round(gc,2),[701],tol=0.05,kind='percent',
      note=f'Table on the same page: 2,757.7 → 3,024.7 = +{gc:.2f}%. The narrative figure does not match.',severity='finding')
gl=(867.7/788.3-1)*100
check('p701_narr_local','Narrative growth claim, local level (“rritje prej 10.1%”, p.701) vs its own table',10.1,round(gl,2),[701],tol=0.05,kind='percent')
FINDINGS.append(dict(type='mismatch',title=f'p.701 narrative says central-level spending grows 10.0% vs the 2025 budget; the table on the same page (2,757.7 → 3,024.7) gives {gc:.1f}%.',expected=10.0,actual=round(gc,2),diff=round(gc-10.0,2),pages=[701],unit='percent'))
# municipalities: 2025 from Tabela 4.3 "Të Hyrat Komunale Totale"
for code,d in mrev.items():
    if code=='TOTAL': continue
    n=NODES.get('mun:'+code); tl=[x for x in d['lines'] if x['label']=='Të Hyrat Komunale Totale']
    if n and tl: n['prev']=tl[0]['prev']; n['prev_ref']=tl[0]['ref']; n['prevCol']='y2025'; n['prev_note']='4.3'
FINDINGS.append(dict(type='ambiguity',title='The 2025 municipal column is headed “2025 Aktuale” on p.210 and in the per-municipality pages of Tabela 4.3, but “2025 Buxheti” on the Tabela 4.3 summary (p.671); the values are the same (788,294,719/720).',pages=[210,647,671]))
# ---------- headline figures per tab ----------
def K(tab,key,label_sq,label_en,value,ref,col,prev=None,prev_ref=None,prev_col=None,node=None,unit='eur',sub_sq='',sub_en=''):
    return dict(tab=tab,key=key,label_sq=label_sq,label_en=label_en,value=value,ref=ref,col=col,prev=prev,prev_ref=prev_ref or (ref if prev is not None else None),prev_col=prev_col or ('y2025' if prev is not None else None),node=node,unit=unit,sub_sq=sub_sq,sub_en=sub_en)
gdp=V('macro:gdp'); E=NODES
KPI=[]
KPI+=[K('flow','spend','Shpenzimet totale 2026','Total spending 2026',V('exp:total'),E['exp:total']['ref'],'y2026',E['exp:total']['prev'],node='exp:total',sub_sq=f"{V('exp:total')/gdp:.1%} e BPV-së",sub_en=f"{V('exp:total')/gdp:.1%} of GDP"),
      K('flow','rev','Të hyrat 2026','Revenue 2026',V('rev:total'),E['rev:total']['ref'],'y2026',E['rev:total']['prev'],node='rev:total'),
      K('flow','deficit','Deficiti','Deficit',V('exp:balance'),E['exp:balance']['ref'],'y2026',E['exp:balance']['prev'],node='exp:balance',sub_sq=f"{-V('exp:balance')/gdp:.1%} e BPV-së",sub_en=f"{-V('exp:balance')/gdp:.1%} of GDP"),
      K('flow','gdp','BPV 2026','GDP 2026',gdp,gref,'y2026',E['macro:gdp']['prev'],node='macro:gdp'),
      K('flow','debt','Borxhi publik, fund 2026','Public debt, end 2026',V('debt:total'),E['debt:total']['ref'],None,E['debt:total']['prev'],prev_ref=E['debt:ext']['ref'],node='debt:total',sub_sq=f"{V('debt:total')/gdp:.1%} e BPV-së",sub_en=f"{V('debt:total')/gdp:.1%} of GDP")]
dc=E['dest:central']; dl=E['dest:local']
big_org=max((n for n in NODES.values() if n.get('kind')=='org'),key=lambda n:n['amount'])
KPI+=[K('central','total','Niveli qendror 2026','Central government 2026',dc['amount'],dc['ref'],'total',dc['prev'],dc['prev_ref'],node='dest:central'),
      K('central','subs','Subvencione dhe transfere','Subsidies and transfers',dc['cats']['subs'],dc['ref'],'subs',dc['cats_prev']['subs'],dc['cats_prev_ref']['subs']),
      K('central','capital','Investime kapitale','Capital investment',dc['cats']['capital'],dc['ref'],'capital',dc['cats_prev']['capital'],dc['cats_prev_ref']['capital']),
      K('central','wages','Paga dhe shtesa','Wages and salaries',dc['cats']['wages'],dc['ref'],'wages',dc['cats_prev']['wages'],dc['cats_prev_ref']['wages']),
      K('central','staff','Të punësuar','Staff',dc['staff'],dc['ref'],'staff',unit='count'),
      K('central','biggest','Më i madhi','Largest',big_org['amount'],big_org['ref'],'total',node=big_org['id'],sub_sq=big_org['name_sq'],sub_en=big_org.get('name_en',''))]
tot43={x['label']:x for x in mrev['TOTAL']['lines']}
big_mun=max((n for n in NODES.values() if n.get('kind')=='municipality'),key=lambda n:n['amount'])
KPI+=[K('municipal','total','Komunat 2026','Municipalities 2026',dl['amount'],dl['ref'],'total',dl['prev'],dl['prev_ref'],node='dest:local'),
      K('municipal','grants','Transferet qeveritare','Government grants',tot43['Transferet Qeveritare']['amount'],tot43['Transferet Qeveritare']['ref'],'y2026',tot43['Transferet Qeveritare']['prev']),
      K('municipal','own','Të hyrat vetanake','Own-source revenue',tot43['Të Hyrat Vetanake']['amount'],tot43['Të Hyrat Vetanake']['ref'],'y2026',tot43['Të Hyrat Vetanake']['prev']),
      K('municipal','staff','Të punësuar','Staff',dl['staff'],dl['ref'],'staff',unit='count'),
      K('municipal','biggest','Më e madhja','Largest',big_mun['amount'],big_mun['ref'],'total',node=big_mun['id'],sub_sq=big_mun['name_sq'],sub_en=big_mun['name_sq'])]
pr=[n for n in NODES.values() if n.get('kind')=='project']
p26=sum(n['amount'] for n in pr); pval=sum(n['multi']['project_total'] for n in pr); n26=sum(1 for n in pr if n['amount']>0)
big_p=max(pr,key=lambda n:n['amount'])
ref_p26=compref('Projects 2026',[],'Shuma e kolonës “Totali 2026” në Tabelat 3.2, 3.2.B, 4.2, 4.2.B',[97,204,357,646])
ref_pv=compref('Projects total value',[],'Shuma e kolonës “Vlera totale e projektit” në Tabelat 3.2, 3.2.B, 4.2, 4.2.B',[97,204,357,646])
ref_pn=compref('Projects count',[],f'{len(pr)} rreshta projektesh; {n26} me ndarje në 2026',[97,204,357,646])
KPI+=[K('capital','capital','Shpenzimet kapitale 2026','Capital spending 2026',V('exp:capital'),E['exp:capital']['ref'],'y2026',E['exp:capital']['prev'],node='exp:capital'),
      K('capital','listed','Në tabelat e projekteve','In the project tables',p26,ref_p26,None,sub_sq=f"diferencë {V('exp:capital')-p26:,.0f} €",sub_en=f"gap €{V('exp:capital')-p26:,.0f}"),
      K('capital','count','Projekte me para në 2026','Projects funded in 2026',n26,ref_pn,None,unit='count',sub_sq=f'nga {len(pr):,} gjithsej',sub_en=f'of {len(pr):,} listed'),
      K('capital','value','Vlera totale shumëvjeçare','Total multi-year value',pval,ref_pv,None),
      K('capital','biggest','Projekti më i madh','Largest project',big_p['amount'],big_p['ref'],'total_2026',node=big_p['id'],sub_sq=big_p['name_sq'],sub_en=big_p['name_sq'])]
check('proj_vs_t1cap','Capital projects in Tabelat 3.2/3.2.B/4.2/4.2.B (2026) vs Tabela 1 capital spending',V('exp:capital'),p26,[29,97,357],TOLM,severity='finding',
      note='Gap matches the municipal capital difference between Tabela 2 and Tabela 4.1 (≈4.1M, the “Bilanci” on p.213).')
SUM.update(gdp=gdp,gdp_prev=E['macro:gdp']['prev'],spend_prev=E['exp:total']['prev'],central_prev=dc['prev'],local_prev=dl['prev'],proj26=p26)

clipped=[n for n in NODES.values() if n.get('kind')=='project' and n.get('dates') and not re.fullmatch(r'\d\d\.\d{4}-\d\d\.\d{4}',n['dates'])]
if clipped:
    ex=', '.join(f'“{n["dates"]}”' for n in clipped[:3])
    FINDINGS.append(dict(type='note',title=f'{len(clipped)} project date ranges are printed in a malformed or non-standard form in the PDF (e.g. {ex}); they are shown exactly as printed.',pages=sorted({REFS[n['head_ref']]['page'] for n in clipped})[:12],count=len(clipped),examples=ex))
