# ---- part 2: aggregates, flows, reconciliation checks, findings, export ----
def compref(label,ids,formula,pages):
    _rc[0]+=1; rid=f'r{_rc[0]}'
    REFS[rid]=dict(page=min(pages),pages=sorted(set(pages)),table='computed',row=label,original_label=label,quote=formula,unit='EUR',values={},method='computed',components=ids)
    return rid
def pg(nid):
    r=REFS.get(NODES[nid]['ref']); return [r['page']] if r else []

# --- overview sankey nodes ---
TAXLEAVES=['rev:cit','rev:pit','rev:prop','rev:dother','rev:vatdom','rev:vatbor','rev:customs','rev:excise','rev:iother']
gross_tax=sum(NODES[i]['amount'] for i in TAXLEAVES)
node('grp:taxgross',kind='group',section='overview',level=1,name_sq='Të hyrat tatimore (bruto, para rimbursimeve)',name_en='Tax revenue (gross, before refunds)',en_src='translated',amount=gross_tax,
     ref=compref('Tax revenue gross',TAXLEAVES,'Sum of tax lines in Tabela 1 (p.29) before "Rimbursimet tatimore"',[29]))
NODES['rev:refunds']['amount_signed']=NODES['rev:refunds']['amount']; NODES['rev:refunds']['amount']=-NODES['rev:refunds']['amount']
NODES['rev:refunds']['note']='Shown as a positive outflow; the table lists it as −102.9 (deducted from tax revenue).'
NONTAX=['rev:feesc','rev:feesl','rev:conc','rev:mining','rev:mobile','rev:divid','rev:intinc']
GR=['rev:gbs','rev:gdon']
EXTIN=['fin:dbs','fin:onl_in','fin:projl04','fin:projl06']
DOMIN=['fin:newsec','fin:refin_in','fin:repay_in']
inflow=NODES['rev:tax']['amount']+NODES['rev:nontax']['amount']+NODES['rev:grants']['amount']+NODES['fin:extin']['amount']+NODES['fin:domin']['amount']
node('pool',kind='pool',section='overview',level=1,name_sq='Të gjitha paratë që hyjnë në 2026',name_en='All money coming in, 2026',en_src='translated',amount=inflow,
     ref=compref('All inflows',['rev:tax','rev:nontax','rev:grants','fin:extin','fin:domin'],'Tax (net) + non-tax + grants (Tabela 1, p.29) + external and domestic gross receipts (Tabela 1.1, p.32)',[29,32]))
for s in EXTIN+DOMIN: flow(s,'fin:extin' if s in EXTIN else 'fin:domin',NODES[s]['amount'],NODES[s]['ref'],'y2026')
for s in TAXLEAVES: flow(s,'grp:taxgross',NODES[s]['amount'],NODES[s]['ref'],'y2026')
for s in NONTAX:
    if NODES[s]['amount']: flow(s,'rev:nontax',NODES[s]['amount'],NODES[s]['ref'],'y2026')
for s in GR: flow(s,'rev:grants',NODES[s]['amount'],NODES[s]['ref'],'y2026')
flow('grp:taxgross','rev:refunds',NODES['rev:refunds']['amount'],NODES['rev:refunds']['ref'],'y2026')
flow('grp:taxgross','pool',NODES['rev:tax']['amount'],NODES['rev:tax']['ref'],'y2026')
for g in ['rev:nontax','rev:grants','fin:extin','fin:domin']: flow(g,'pool',NODES[g]['amount'],NODES[g]['ref'],'y2026')
# uses
DOMOUT=['fin:refin_out','fin:lend','fin:onl_out','fin:ifi','fin:capz']
NODES['fin:bank']['name_en']='Increase in bank balance (saved)'
uses=[('budget',NODES['budget']['amount'],NODES['budget']['ref'],'total'),('dest:donor',NODES['dest:donor']['amount'],NODES['dest:donor']['ref'],'y2026'),
      ('fin:principal',NODES['fin:principal']['amount'],NODES['fin:principal']['ref'],'y2026'),('fin:domout',NODES['fin:domout']['amount'],NODES['fin:domout']['ref'],'y2026'),
      ('fin:bank',NODES['fin:bank']['amount'],NODES['fin:bank']['ref'],'y2026')]
for t,a,r,c in uses: flow('pool',t,a,r,c)
outflow=sum(u[1] for u in uses)
gap=inflow-outflow
if abs(gap)>=1:
    node('pool/diff',kind='difference',section='overview',level=1,parent='pool',name_sq='Diferencë (rrumbullakim)',name_en='Difference (rounding of € million tables)',en_src='translated',amount=gap,
         ref=compref('pool gap',['pool'],'All inflows − all uses; Tables 1/1.1 are rounded to €0.1M',[29,32,34]),flags=['RECONCILIATION','ROUNDING'])
    flow('pool','pool/diff',abs(gap),NODES['pool/diff']['ref'],kind='difference')
for s in DOMOUT:
    if NODES[s]['amount']: flow('fin:domout',s,NODES[s]['amount'],NODES[s]['ref'],'y2026')
flow('budget','dest:central',NODES['dest:central']['amount'],ref_cen)
flow('budget','dest:local',NODES['dest:local']['amount'],ref_loc)
flow('budget','dest:interest',NODES['dest:interest']['amount'],ref_int)
# categories
grand=cats_of(r_tot); grand['interest']=fnum(r_tot['interest'])
for k,v in grand.items(): NODES['cat:'+k]['amount']=v; NODES['cat:'+k]['ref']=ref_tot; NODES['cat:'+k]['refCol']=k
NODES['cat:donor']['amount']=NODES['dest:donor']['amount']; NODES['cat:donor']['ref']=NODES['dest:donor']['ref']; NODES['cat:donor']['refCol']='y2026'
for k,v in cats_of(r_cen).items(): flow('dest:central','cat:'+k,v,ref_cen,k)
for k,v in cats_of(r_loc).items(): flow('dest:local','cat:'+k,v,ref_loc,k)
flow('dest:interest','cat:interest',NODES['dest:interest']['amount'],ref_int,'interest')
flow('dest:donor','cat:donor',NODES['dest:donor']['amount'],NODES['dest:donor']['ref'],'y2026')

# --- middle: destinations -> orgs / municipalities ---
orgs=[n for n in NODES.values() if n.get('kind')=='org']
muns=[n for n in NODES.values() if n.get('kind')=='municipality']
for o in orgs: flow('dest:central',o['id'],o['amount'],o['ref'])
for m in muns: flow('dest:local',m['id'],m['amount'],m['ref'])
def dest_diff(did,children,label_sq,label_en,note):
    d=NODES[did]['amount']-sum(c['amount'] for c in children)
    if abs(d)>=1:
        node(did+'/diff',kind='difference',section=NODES[did]['section'] if did!='dest:central' else 'central',level=2,parent=did,name_sq=label_sq,name_en=label_en,en_src='translated',amount=d,
             ref=compref(label_en,[did]+[c['id'] for c in children],note,[34]+[REFS[c['ref']]['page'] for c in children[:1]]),flags=['RECONCILIATION'],note=note)
        flow(did,did+'/diff',abs(d),NODES[did+'/diff']['ref'],kind='difference')
    return d
dc=dest_diff('dest:central',orgs,'Diferencë','Unallocated / difference',f'Table 2 central total (p.34) minus sum of 50 institutions in Tables 3.1 + 3.1.B (pp.35–95).')
NODES.get('dest:central/diff',{}).update(section='central')
dl=dest_diff('dest:local',muns,'Diferencë (“Bilanci”)','Unallocated / difference (document “Bilanci”)',
     'Table 2 local total (p.34) equals municipal budget ceilings; the 38 municipal plans in Tables 4.1 + 4.1.B (pp.214–356) sum to less. The document itself lists this gap as “Bilanci – Diferenca në staf dhe kategori të shpenzimeve” = 181,295 (p.213).')
NODES.get('dest:local/diff',{}).update(section='municipal')
# org/mun -> category (aggregated) and parent->child flows
for n in list(NODES.values()):
    if n.get('kind') in ('org','municipality'):
        for k,v in n['cats'].items():
            if v: flow(n['id'],'cat:'+k,v,n['ref'],k,kind='category')
    if n.get('kind') in ('programme','subprogramme','difference') and n.get('parent') and n['parent'] in NODES and NODES[n['parent']].get('kind') in ('org','municipality','programme'):
        flow(n['parent'],n['id'],abs(n['amount']),n['ref'],kind='hard' if n['kind']!='difference' else 'difference')
# projects -> owner link
for n in NODES.values():
    if n.get('kind')=='project' and n['amount']:
        flow(n['owner'],n['id'],n['amount'],n['ref'],'total_2026',kind='project')
# borrowing links (attributed by funding-source label)
clause_nodes=[n for n in NODES.values() if n['id'].endswith('/clause')]
for c in clause_nodes: flow('fin:projl06',c['id'],c['amount'],c['ref'],kind='source-link',note='Linked by funding source: "Klauzola e Investimeve" rows ↔ Tabela 1.1 "Projekt-kreditë, klauzola e investimeve (fondi 06)".')
fh_nodes=[]
for n in NODES.values():
    if n.get('kind') in ('org','municipality') and n.get('sources',{}).get('fh'):
        s=n['sources']['fh']; fh_nodes.append((n,s))
        flow('fin:projl04',n['id'],s['amount'],s['ref'],kind='source-link',note='Linked by funding source: "Financimi nga Huamarrja" rows ↔ Tabela 1.1 "Projekt-kreditë, trajtim brenda deficiti (fondi 04)".')

# ================= CHECKS =================
def V(i): return NODES[i]['amount']
def P(*ids): return sum((pg(i) for i in ids),[])
TOLM=0.15*M  # € million tables rounded to 0.1
check('t1_tax','Tax revenue = direct + indirect + refunds (Tabela 1)',V('rev:tax'),V('rev:direct')+V('rev:indirect')+NODES['rev:refunds']['amount_signed'],[29],TOLM)
check('t1_direct','Direct taxes = CIT + PIT + property + other',V('rev:direct'),sum(V(i) for i in ['rev:cit','rev:pit','rev:prop','rev:dother']),[29],TOLM)
check('t1_indirect','Indirect taxes = VAT + customs + excise + other',V('rev:indirect'),sum(V(i) for i in ['rev:vat','rev:customs','rev:excise','rev:iother']),[29],TOLM)
check('t1_vat','VAT = domestic + border',V('rev:vat'),V('rev:vatdom')+V('rev:vatbor'),[29],TOLM)
check('t1_nontax','Non-tax revenue = fees + concessions + mining + telecom + dividends + interest',V('rev:nontax'),V('rev:fees')+sum(V(i) for i in ['rev:conc','rev:mining','rev:mobile','rev:divid','rev:intinc']),[29],TOLM)
check('t1_fees','Fees and charges = central + local',V('rev:fees'),V('rev:feesc')+V('rev:feesl'),[29],TOLM)
check('t1_grants','Grants = budget support + donor-designated',V('rev:grants'),V('rev:gbs')+V('rev:gdon'),[29],TOLM)
check('t1_rev','Total revenue = tax + non-tax + grants',V('rev:total'),V('rev:tax')+V('rev:nontax')+V('rev:grants'),[29],TOLM)
check('t1_cur','Current spending = wages + goods + subsidies + reserve',V('exp:current'),sum(V(i) for i in ['exp:wages','exp:goods','exp:subs','exp:reserve']),[29],TOLM)
check('t1_cap','Capital = regular budget + investment clause',V('exp:capital'),V('exp:capreg')+V('exp:capclause'),[29],TOLM,note='"Klauzola e investimeve" is indented under "Financimi nga buxheti i rregullt" in the table; read as siblings because 897.8 + 100.7 ≈ 998.4.')
check('t1_exp','Total spending = current + interest + capital + donor grants',V('exp:total'),sum(V(i) for i in ['exp:current','exp:interest','exp:capital','exp:donor']),[29],TOLM)
check('t1_bal','Balance = revenue − spending',V('exp:balance'),V('rev:total')-V('exp:total'),[29],TOLM)
check('t1_fin','Change in bank balance = financing need + external net + domestic net',V('fin:bank'),V('fin:need')+V('fin:extnet')+V('fin:domnet'),[30],TOLM)
check('t11_ext','Net external financing = receipts − outflows (Tabela 1.1)',V('fin:t11ext'),V('fin:extin')-V('fin:extout'),[32],TOLM)
check('t11_extin','External receipts = budget support + on-lending + project loans',V('fin:extin'),V('fin:dbs')+V('fin:onl_in')+V('fin:projl'),[32],TOLM)
check('t11_projl','Project loans = fund 04 + fund 06',V('fin:projl'),V('fin:projl04')+V('fin:projl06'),[32],TOLM)
check('t11_dom','Net domestic financing = receipts − outflows',V('fin:t11dom'),V('fin:domin')-V('fin:domout'),[32],TOLM)
check('t11_domin','Domestic receipts = sum of lines',V('fin:domin'),sum(V(i) for i in DOMIN)+sum(fnum(r['y2026'])*M for r in dom_other),[32],TOLM)
check('t11_domout','Domestic outflows = sum of lines',V('fin:domout'),sum(V(i) for i in DOMOUT)+sum(fnum(r['y2026'])*M for r in dom_out_other),[32],TOLM)
check('t1_t11','Tabela 1 net external = Tabela 1.1 net external',V('fin:extnet'),V('fin:t11ext'),[30,32],TOLM)
check('pool','All money in = all uses (revenue + gross borrowing = spending + debt repayment + financing outflows + saving)',inflow,outflow,[29,32,34],TOLM,
      note='Inflows: net tax, non-tax, grants, external and domestic receipts. Uses: Table 2 total, donor grants, principal, domestic outflows, bank-balance increase.')
# Table 2 internal
for lab,r in [('Central',r_cen),('Local',r_loc)]:
    check(f't2_{lab}_cats',f'Tabela 2 {lab.lower()}: categories sum to total',fnum(r['total']),sum(fnum(r[k]) for k in ['wages','goods','util','subs','capital','reserve','interest']),[34])
check('t2_central','Tabela 2: central = 3.1 + 3.1.B',fnum(r_cen['total']),fnum(r_c31['total'])+fnum(r_c31b['total']),[34])
check('t2_local','Tabela 2: local = 4.1 + 4.1.B',fnum(r_loc['total']),fnum(r_l41['total'])+fnum(r_l41b['total']),[34])
check('t2_grand','Tabela 2: grand total = central + local + interest',fnum(r_tot['total']),fnum(r_cen['total'])+fnum(r_loc['total'])+fnum(r_int['total']),[34])
check('t2_vs_t1','Tabela 2 grand total vs Tabela 1 total spending',V('exp:total'),fnum(r_tot['total']),[29,34],TOLM,
      note='Gap equals line 2.4 "Grantet e Përcaktuara të Donatorve" (12.0M), which Table 2 does not allocate. Shown on the canvas as its own destination.',severity='finding')
check('t2_vs_t1_donor','Tabela 2 grand total + donor grants = Tabela 1 total spending',V('exp:total'),fnum(r_tot['total'])+V('exp:donor'),[29,34],TOLM)
for k,t1id in [('wages','exp:wages'),('subs','exp:subs'),('capital','exp:capital'),('reserve','exp:reserve')]:
    check(f't2_t1_{k}',f'Tabela 2 {CAT[k][1].lower()} vs Tabela 1',V(t1id),fnum(r_tot[k]),[29,34],TOLM)
check('t2_t1_goods','Tabela 2 goods + utilities vs Tabela 1 "Mallra dhe Shërbime"',V('exp:goods'),fnum(r_tot['goods'])+fnum(r_tot['util']),[29,34],TOLM)
check('t2_t1_int','Tabela 2 interest vs Tabela 1',V('exp:interest'),fnum(r_tot['interest']),[29,34],TOLM)
# 3.1
tt31=[r for r in rows31 if r['kind']=='table_total'][0]
s31=sum(o['total'] for o in orgs31)
check('t31_total','Tabela 3.1: sum of 50 institutions vs printed "Total"',fnum(tt31['total']),s31,[93],severity='finding' if abs(s31-fnum(tt31['total']))>=1 else None)
check('t31_t2','Tabela 3.1 printed total vs Tabela 2 row 3.1',fnum(r_c31['total']),fnum(tt31['total']),[34,93])
for k in ['wages','goods','util','subs','capital','reserve']:
    check(f't31_t2_{k}',f'Tabela 3.1 {CAT[k][1].lower()}: printed total vs Tabela 2',fnum(r_c31[k]),fnum(tt31[k]),[34,93])
for r in rows31:
    if r['kind']=='table_total_src': pass
iss=tree_issues(orgs31)
nrows31=sum(1 for r in rows31 if r['kind'] in('org','prog','sub'))
check('t31_rows','Tabela 3.1: every row categories = row total, sources = row total, children = parent',0,len(iss),list(range(35,94)),tol=0,
      note=f'{nrows31} rows checked; {len(iss)} mismatches listed in findings.',kind='count')
for kind,path,a,b,page,n in iss:
    FINDINGS.append(dict(type='mismatch',title=f'Tabela 3.1 {kind}: {path}',expected=a,actual=b,diff=b-a,pages=[int(page)],table='Tabela 3.1',cls='rounding' if abs(b-a)<=0.5*(n+1) else 'error'))
check('t31b_t2','Tabela 3.1.B total vs Tabela 2 row 3.1.B',fnum(r_c31b['total']),sum(o['total'] for o in orgs31b),[34,95])
fh31=[r for r in rows31 if r['kind']=='table_total_src' and 'Huamarrja' in r['source']][0]
# Annex 1 per institution
for a in annex:
    if a['code']=='TOTAL':
        check('a1_total','Shtojca 1 grand total vs Tabela 2 central',fnum(r_cen['total']),fnum(a['total']),[34,96],severity='finding'); 
        check('a1_wages','Shtojca 1 wages total vs Tabela 2 central wages',fnum(r_cen['wages']),fnum(a['wages']),[34,96]); continue
    n=NODES.get('org:'+a['code'])
    if not n: FINDINGS.append(dict(type='missing',title=f"Shtojca 1 code {a['code']} has no Tabela 3.1 row",pages=[96])); continue
    n['annex_ref']=mkref('Shtojca 1',96,a['raw'],annex_names.get(a['code'],a['name']),'EUR',{k:fnum(a[k]) for k in ['staff','wages','goods','util','subs','capital','reserve','total'] if a[k]},top=a['top'])
    d=fnum(a['total'])-n['amount']
    if abs(d)>=1: FINDINGS.append(dict(type='mismatch',title=f"Shtojca 1 vs Tabela 3.1+3.1.B: {n['name_sq']}",expected=n['amount'],actual=fnum(a['total']),diff=d,pages=[96,int(REFS[n['ref']]['page'])],node=n['id']))
a1=[a for a in annex if a['code']!='TOTAL']
check('a1_rows','Shtojca 1: each institution total = Tabela 3.1 + 3.1.B',0,sum(1 for a in a1 if NODES.get('org:'+a['code']) and abs(fnum(a['total'])-NODES['org:'+a['code']]['amount'])>=1),[96],tol=0,kind='count',note=f'{len(a1)} institutions compared')
# 4.1
tt41=[r for r in rows41 if r['kind']=='table_total'][0]
s41=sum(o['total'] for o in orgs41)
check('t41_total','Tabela 4.1: sum of 38 municipalities vs printed total',fnum(tt41['total']),s41,[355])
iss41=tree_issues(orgs41); nrows41=sum(1 for r in rows41 if r['kind'] in('org','prog','sub'))
check('t41_rows','Tabela 4.1: every row categories/sources/children reconcile',0,len(iss41),list(range(214,356)),tol=0,kind='count',note=f'{nrows41} rows checked')
for kind,path,a,b,page,n in iss41:
    FINDINGS.append(dict(type='mismatch',title=f'Tabela 4.1 {kind}: {path}',expected=a,actual=b,diff=b-a,pages=[int(page)],table='Tabela 4.1',cls='rounding' if abs(b-a)<=0.5*(n+1) else 'error'))
loc_plan=s41+sum(o['total'] for o in orgs41b)
check('t2_local_vs_41','Tabela 2 local total vs Tabelat 4.1 + 4.1.B (sum of municipal plans)',fnum(r_loc['total']),loc_plan,[34,355,356],severity='finding',
      note='Document explains this on p.213 as “Bilanci” 181,295 (staff −27, wages +159,426, goods −31,200, utilities −2,200, subsidies +388, capital +4,099,880, reserves −4,045,000).')
for k in ['wages','goods','util','subs','capital','reserve']:
    planned=sum(o[k] for o in orgs41)+sum(o[k] for o in orgs41b)
    check(f't2_local_{k}',f'Tabela 2 local {CAT[k][1].lower()} vs municipal plans',fnum(r_loc[k]),planned,[34,355,356],severity='finding')
# municipal summary pp.211-213 vs 4.1
msum={r['muni']:r for r in ms if r['fund']=='Total' and r['aggregate']=='False'}
name_alias={'Prishtina':'Prishtinë','Prizeren':'Prizreni','Graçanicë':'Graçanic','Hani i Elezit':'Han i Elezit'}
bad=0
for nm,r in msum.items():
    code=[c for c,v in MUNI_NAME.items() if v==name_alias.get(nm,nm)]
    if not code: FINDINGS.append(dict(type='ambiguity',title=f'Municipality "{nm}" (p.{r["page"]}) has no exact name match in Tabela 4.1',pages=[int(r['page'])])); continue
    n=NODES['mun:'+code[0]]
    n['summary_ref']=mkref('Struktura e shpenzimeve',r['page'],r['raw'],nm,'EUR',{k:fnum(r[k]) for k in ['staff','wages','goods','util','subs','capital','reserve','total'] if r[k]},top=r['top'])
    d=fnum(r['total'])-n['amount']
    if abs(d)>=1: bad+=1; FINDINGS.append(dict(type='mismatch',title=f'Municipal summary (p.{r["page"]}) vs Tabela 4.1+4.1.B: {nm}',expected=n['amount'],actual=fnum(r['total']),diff=d,pages=[int(r['page'])],node=n['id']))
    if name_alias.get(nm): FINDINGS.append(dict(type='naming',title=f'Same municipality spelled "{nm}" (p.{r["page"]}) and "{name_alias[nm]}" (Tabela 4.1)',pages=[int(r['page'])]))
check('ks_rows','Municipal summary pp.211–213: each municipality = Tabela 4.1 + 4.1.B',0,bad,[211,212,213],tol=0,kind='count',note=f'{len(msum)} municipalities compared')
agg=lambda sec,f: [r for r in ms if r['section']==sec and r['fund']==f and r['aggregate']=='True']
ab=agg('A+B','Total')[0]; bil=agg('Bilanci','Total')[0]; abb=agg('A+B+Bilanci','Total')[0]
check('ks_ab','Municipal summary A+B vs Tabela 4.1 + 4.1.B',loc_plan,fnum(ab['total']),[213,355,356])
check('ks_bil','Municipal summary: A+B + “Bilanci” = Tabela 2 local',fnum(r_loc['total']),fnum(ab['total'])+fnum(bil['total']),[34,213])
zb=[r for r in ms if r['section']=='B' and r['fund']=='Total' and r['aggregate']=='False']
if zb: FINDINGS.append(dict(type='note',title=f'{zb[0]["muni"]} is listed as the only municipality that had not approved its budget in the municipal assembly (Nëntotali B, p.213); its figures are still included.',pages=[213]))
# p210 municipal balance
m210=rd('muni_balance_p210.csv')
def p210(lbl):
    r=[x for x in m210 if x['label'].startswith(lbl)][0]; nums=json.loads(r['nums'])
    v=[t for t,x in nums if 465<=x<=490]
    return (tonum_s(v[0]) if v else 0.0),r
def tonum_s(s): return float(s.replace(',',''))
src210,r_src210=p210('1 BURIMET'); str210,_=p210('2 STRUKTURA'); bal210,r_bal=p210('3 BILANCI')
check('k1_sources','Municipal balance p.210: total sources = Tabela 2 local',fnum(r_loc['total']),src210,[34,210])
check('k1_struct','Municipal balance p.210: structure + balance = sources',src210,str210,[210],note='Printed structure total equals sources; the printed “Bilanci” 181,295 is the part of sources not covered by the line items.')
lines210=[p210(l)[0] for l in ['2.1 Shpenzimet','2.2 Shpenzime Kapitale','2.3 Klauzola','2.4 Rezerva']]
check('k1_lines','Municipal balance p.210: line items + “Bilanci” = sources',src210,sum(lines210)+bal210,[210])
FINDINGS.append(dict(type='ambiguity',title='p.210 “BILANCI I BUXHETIT” row: values sit under 2025–2028 by position, but 2025 sources and structure are both printed as 788,294,719 while the balance shows 8,108,785; the 2025 line items sum to 780,760,626.',pages=[210]))
# 4.3 revenue vs 4.1
bad=0; bad43b=[]
for code,d in mrev.items():
    tot=[l for l in d['lines'] if l['label']=='Të Hyrat Komunale Totale']
    if code=='TOTAL':
        check('t43_total','Tabela 4.3 summary (p.671) total revenue vs municipal plans (4.1 + 4.1.B)',loc_plan,tot[0]['amount'],[671,355,356]); 
        check('t43_vs_k1','Tabela 4.3 summary total vs p.210 “Burimet e financimit”',src210,tot[0]['amount'],[210,671],severity='finding',note='Same 181,296 gap: p.210 shows ceilings, p.671 sums the municipal plans.'); continue
    n=NODES.get('mun:'+code)
    if not n or not tot: continue
    dd=tot[0]['amount']-n['amount']
    if abs(dd)>=1: bad+=1; FINDINGS.append(dict(type='mismatch',title=f'Tabela 4.3 revenue vs Tabela 4.1 spending: {n["name_sq"]}',expected=n['amount'],actual=tot[0]['amount'],diff=dd,pages=[REFS[tot[0]['ref']]['page'],REFS[n['ref']]['page']],node=n['id']))
    TOP_OWN=('Tatimi në tokë','Tatimi në pronë','Taksat Komunale','Ngarkesat Komunale','Te hyrat tjera','Shitja e aseteve')
    own=[l for l in d['lines'] if l['label']=='Të Hyrat Vetanake']; tr=[l for l in d['lines'] if l['label']=='Transferet Qeveritare']
    if own:
        sown=sum(l['amount'] for l in d['lines'] if l['label'] in TOP_OWN)
        if abs(sown-own[0]['amount'])>=1: bad43b.append(1); FINDINGS.append(dict(type='mismatch',title=f'Tabela 4.3 {n["name_sq"]}: own-source lines vs “Të Hyrat Vetanake”',expected=own[0]['amount'],actual=sown,diff=sown-own[0]['amount'],pages=[REFS[own[0]['ref']]['page']],node=n['id']))
    hua=[l for l in d['lines'] if l['label']=='Financimi nga Huamarrja']
    if own and tr:
        s3=own[0]['amount']+tr[0]['amount']+(hua[0]['amount'] if hua else 0)
        if abs(s3-tot[0]['amount'])>=1: bad43b.append(1); FINDINGS.append(dict(type='mismatch',title=f'Tabela 4.3 {n["name_sq"]}: own-source + transfers + borrowing vs total',expected=tot[0]['amount'],actual=s3,diff=s3-tot[0]['amount'],pages=[REFS[tot[0]['ref']]['page']],node=n['id']))
check('t43_internal','Tabela 4.3: own-source lines add up, and own-source + transfers + borrowing = total (per municipality)',0,len(bad43b),list(range(647,671)),tol=0,kind='count')
check('t43_rows','Tabela 4.3: each municipality revenue = its spending plan (4.1 + 4.1.B)',0,bad,list(range(647,671)),tol=0,kind='count',note=f'{len([c for c in mrev if c!="TOTAL"])} municipalities compared')
# capital projects
def projsum(table,owner=None): return sum(n['amount'] for n in NODES.values() if n.get('kind')=='project' and n['table']==table and (owner is None or n['org']==owner))
check('t32_t31','Tabela 3.2 projects (2026) vs Tabela 3.1 capital total',fnum(tt31['capital']),projsum('Tabela 3.2'),[93,203])
check('t32b_t31b','Tabela 3.2.B projects vs Tabela 3.1.B total',sum(o['capital'] for o in orgs31b),projsum('Tabela 3.2.B'),[95,209])
check('t42_t41','Tabela 4.2 projects (2026) vs Tabela 4.1 capital total',fnum(tt41['capital']),projsum('Tabela 4.2'),[355,645])
check('t42b_t41b','Tabela 4.2.B projects vs Tabela 4.1.B',sum(o['capital'] for o in orgs41b),projsum('Tabela 4.2.B'),[356,646])
bad=0
for o in orgs31:
    d=projsum('Tabela 3.2',o['code'])-o['capital']
    if abs(d)>=1: bad+=1; FINDINGS.append(dict(type='mismatch',title=f'Capital projects (3.2) vs capital in 3.1: {NODES["org:"+o["code"]]["name_sq"]}',expected=o['capital'],actual=o['capital']+d,diff=d,pages=[int(o['page'])],node='org:'+o['code']))
check('t32_byorg','Tabela 3.2 projects per institution = its capital in Tabela 3.1',0,bad,list(range(97,204)),tol=0,kind='count',note='50 institutions compared')
bad=0
for o in orgs41:
    d=projsum('Tabela 4.2',o['code'])-o['capital']
    if abs(d)>=1: bad+=1; FINDINGS.append(dict(type='mismatch',title=f'Capital projects (4.2) vs capital in 4.1: {o["name"]}',expected=o['capital'],actual=o['capital']+d,diff=d,pages=[int(o['page'])],node='mun:'+o['code']))
check('t42_bymun','Tabela 4.2 projects per municipality = its capital in Tabela 4.1',0,bad,list(range(357,646)),tol=0,kind='count',note='38 municipalities compared')
projs=[n for n in NODES.values() if n.get('kind')=='project']
b1=sum(1 for n in projs if abs(n['multi']['cont_2026']+n['multi']['new_2026']-n['multi']['total_2026'])>=1)
b2=sum(1 for n in projs if abs(n['multi']['spent_to_2025']+n['multi']['total_2026']+n['multi']['y2027']+n['multi']['y2028']+n['multi']['y2029plus']-n['multi']['project_total'])>=1)
for n in projs:
    m=n['multi']
    for lab,a,b in [('column 4 ≠ 2 + 3',m['total_2026'],m['cont_2026']+m['new_2026']),('column 8 ≠ 1 + 4 + 5 + 6 + 7',m['project_total'],m['spent_to_2025']+m['total_2026']+m['y2027']+m['y2028']+m['y2029plus'])]:
        if abs(a-b)>=1: FINDINGS.append(dict(type='mismatch',title=f'{n["table"]} project {lab}: {n["name_sq"][:70]} ({n["org"]})',expected=a,actual=b,diff=b-a,pages=[REFS[n['head_ref']]['page']],node=n['id']))
check('proj_cols','Every project: column 4 = 2 + 3 and column 8 = 1 + 4 + 5 + 6 + 7',0,b1+b2,[97,357],tol=0,kind='count',note=f'{len(projs)} projects checked')
for n in projs:
    if 'AMBIGUITY' in n['flags']: FINDINGS.append(dict(type='ambiguity',title='Tabela 3.2.B p.205: a funding row (FHKI, 33,438,206 spent to 2025, €0 in 2026) has no project line — no project code or name.',pages=[205],node=n['id']))
# muni borrowing
fh41=sum(o['sources'].get('Financimi nga Huamarrja',{}).get('total',0) for o in orgs41)
fh42=sum(n['amount'] for n in projs if n['table']=='Tabela 4.2' and 'FH' in n['fund'])
FINDINGS.append(dict(type='ambiguity',title=f'Municipal borrowing: Tabela 4.1 shows €{fh41:,.0f} financed from borrowing (goods and services), Tabela 4.2 shows €{fh42:,.0f} of FH-funded projects in 2026.',pages=[355,645]))
# borrowing attribution
fh_central=sum(s['amount'] for n,s in fh_nodes)
check('borrow_06','Project loans fund 06 (Tabela 1.1) vs investment-clause allocations (3.1.B + 4.1.B)',V('fin:projl06'),sum(c['amount'] for c in clause_nodes),[32,95,356],TOLM)
check('borrow_04','Project loans fund 04 (Tabela 1.1) vs rows financed “nga Huamarrja” (3.1 + 4.1)',V('fin:projl04'),fh_central,[32,93,355],TOLM,severity='finding',
      note='The document does not state that fund 04 maps one-to-one to “Financimi nga Huamarrja”; the link is an assumption. Gap may include project-loan spending recorded elsewhere.')
check('cen_diff','Tabela 2 central total vs sum of institutions (3.1 + 3.1.B)',fnum(r_cen['total']),sum(o['amount'] for o in orgs),[34,93,95])
check('loc_diff','Tabela 2 local total vs sum of municipalities (4.1 + 4.1.B)',fnum(r_loc['total']),sum(m['amount'] for m in muns),[34,355,356],severity='finding')
# references completeness
missing=[n['id'] for n in NODES.values() if not n.get('ref') or n['ref'] not in REFS]
check('refs','Nodes without a source reference',0,len(missing),[1],tol=0,kind='count',note=f'{len(NODES)} nodes, {len(FLOWS)} flows checked')
missing_f=[f['id'] for f in FLOWS if not f.get('ref') or f['ref'] not in REFS]
check('refs_flows','Flows without a source reference',0,len(missing_f),[1],tol=0,kind='count')
# annex copies
FINDINGS.append(dict(type='note',title='Tables 1 and 1.1 are reprinted on pp.703–705; all values match pp.29–33 (only display rounding differs: 2,707.38 vs 2,707.4).',pages=[29,703]))
FINDINGS.append(dict(type='note',title='No municipal population figures appear anywhere in the document, so per-capita amounts are not shown.',pages=[]))
FINDINGS.append(dict(type='note',title='Several institution and programme names are cut off inside Tabela 3.1 (e.g. "Agjencia Kosovare për Krahasim Ver"). Full names are taken from Shtojca 1 (p.96).',pages=[93,96]))

# ---- public debt stock (Tabela 1.1 memo, p.33) ----
def debtnode(id,label,en,anchor):
    r=T(t11,label); rid=mkref('Tabela 1.1',r['page'],r['raw'],label,'EUR million',{'y2025':fnum(r['y2025']),'y2026':fnum(r['y2026'])},top=r['top'])
    node(id,kind='line',section='overview-fin',level=1,name_sq=label,name_en=en,en_src='translated',amount=fnum(r['y2026'])*M,ref=rid,refCol='y2026',anchor=anchor,stock=True,
         prev=fnum(r['y2025'])*M,note_en=f"Stock at end of 2026 (end of 2025: €{fnum(r['y2025']):,.1f}M). A stock, not a flow: it is not part of the 2026 flows.",
         note_sq=f"Stoku në fund të 2026 (fundi i 2025: €{fnum(r['y2025']):,.1f}M). Është stok, jo rrjedhë: nuk hyn në rrjedhat e 2026.")
debtnode('debt:ext','Stoku i borxhit të jashtëm','External debt stock','fin:extin')
debtnode('debt:dom','Stoku i borxhit të brendshëm','Domestic debt stock','fin:domin')
gdp=T(t1,'BPV'); gdp_ref=mkref('Tabela 1',gdp['page'],gdp['raw'],'BPV','EUR million',{'y2026':fnum(gdp['y2026'])},top=gdp['top'])
dg=[r for r in t11 if 'Borxhi i përgjithshëm' in r['raw']]
node('debt:total',kind='group',section='overview-fin',level=1,name_sq='Borxhi publik (stoku në fund të 2026)',name_en='Public debt (stock, end of 2026)',en_src='translated',
     amount=V('debt:ext')+V('debt:dom'),ref=compref('Public debt stock',['debt:ext','debt:dom'],'Stoku i borxhit të jashtëm + i brendshëm (Tabela 1.1, f.33)',[33]),anchor='fin:extin',stock=True,
     note_en=f"{(V('debt:ext')+V('debt:dom'))/(fnum(gdp['y2026'])*M):.1%} of 2026 GDP (€{fnum(gdp['y2026']):,.1f}M, Tabela 1 p.30). Table 1.1 prints 21.9%.",
     note_sq=f"{(V('debt:ext')+V('debt:dom'))/(fnum(gdp['y2026'])*M)*100:.1f}% e BPV-së 2026 (€{fnum(gdp['y2026']):,.1f}M, Tabela 1 f.30). Tabela 1.1 shtyp 21.9%.")
ratio=(V('debt:ext')+V('debt:dom'))/(fnum(gdp['y2026'])*M)*100
check('debt_gdp','Public debt at end of 2026: domestic + external, as % of GDP',21.9,round(ratio,2),[30,33],tol=0.05,kind='percent',note='Recomputed from the debt stocks and GDP; compared with the printed 21.9%.')
NOTE_PCT=None
# ---- totals for headline summary ----
SUM=dict(revenue=V('rev:total'),tax=V('rev:tax'),nontax=V('rev:nontax'),grants=V('rev:grants'),spending=V('exp:total'),balance=V('exp:balance'),
         need=V('fin:need'),extnet=V('fin:extnet'),domnet=V('fin:domnet'),extin=V('fin:extin'),domin=V('fin:domin'),inflow=inflow,outflow=outflow,
         t2total=fnum(r_tot['total']),central=fnum(r_cen['total']),local=fnum(r_loc['total']),interest=fnum(r_int['total']),
         borrow_rows=fh_central+sum(c['amount'] for c in clause_nodes))

# ---- tours ----
def fid(s,t):
    m=[f for f in FLOWS if f['source']==s and f['target']==t]; return m[0]['id'] if m else None
def big_child(pid,kind=None):
    c=[n for n in NODES.values() if n.get('parent')==pid and (kind is None or n['kind']==kind)]
    return max(c,key=lambda n:n['amount'])['id'] if c else None
def top_proj(owner,fund=None):
    c=[n for n in projs if n['owner']==owner and (fund is None or fund in n['fund'])]
    return max(c,key=lambda n:n['amount']) if c else None
mesti_wage=None
pens=[n for n in NODES.values() if n.get('parent')=='org:201' and 'Pension' in n['name_sq']]
p616=top_proj('mun:616'); pclause=top_proj('org:205','FHKI')
TOURS=[
 dict(id='debt',title_en='Where the debt comes from — and where it goes',title_sq='Nga vjen borxhi — dhe ku shkon',steps=[
   dict(node='fin:dbs',flow=fid('fin:dbs','fin:extin'),text_en='The largest new borrowing: €270.3M of direct budget financing from the IMF, World Bank, EU and others.',text_sq='Huamarrja më e madhe e re: €270.3M financim direkt buxhetor nga FMN, Banka Botërore, BE etj.'),
   dict(node='fin:projl06',flow=fid('fin:projl06','fin:extin'),text_en='Project loans: €100.7M under the investment clause (fund 06) plus €45.8M treated within the deficit (fund 04).',text_sq='Projekt-kreditë: €100.7M sipas klauzolës së investimeve (fondi 06) plus €45.8M brenda deficitit (fondi 04).'),
   dict(node='fin:onl_in',flow=fid('fin:onl_in','fin:extin'),text_en='€67.9M is borrowed abroad and lent on to public companies (on-lending).',text_sq='€67.9M merren hua jashtë dhe u jepen ndërmarrjeve publike (nën-huazime).'),
   dict(node='fin:extin',flow=fid('fin:extin','pool'),text_en='Together: €484.7M of external borrowing comes in during 2026.',text_sq='Gjithsej: €484.7M huamarrje e jashtme hyn gjatë 2026.'),
   dict(node='fin:refin_in',flow=fid('fin:refin_in','fin:domin'),text_en='At home, €190.3M of new securities are sold just to repay securities that mature…',text_sq='Brenda vendit, €190.3M letra me vlerë të reja shiten vetëm për të shlyer ato që maturohen…'),
   dict(node='fin:newsec',flow=fid('fin:newsec','fin:domin'),text_en='…and €100.0M of genuinely new domestic debt is issued.',text_sq='…dhe €100.0M borxh i ri i brendshëm emetohet.'),
   dict(node='fin:refin_out',flow=fid('fin:domout','fin:refin_out'),text_en='Most domestic borrowing goes straight back out to repay maturing securities.',text_sq='Shumica e huamarrjes së brendshme del menjëherë për shlyerjen e letrave me vlerë që maturohen.'),
   dict(node='fin:principal',flow=fid('pool','fin:principal'),text_en='€48.8M repays the principal of foreign loans.',text_sq='€48.8M shlyejnë kryegjënë e huave të jashtme.'),
   dict(node='dest:interest',flow=fid('budget','dest:interest'),text_en='Interest on public debt costs €63.2M in 2026.',text_sq='Interesi për borxhin publik kushton €63.2M në 2026.'),
   dict(node='fin:bank',flow=fid('pool','fin:bank'),text_en='Borrowing exceeds the €330.3M deficit, so the bank balance grows by €81.8M.',text_sq='Huamarrja e tejkalon deficitin prej €330.3M, ndaj bilanci bankar rritet për €81.8M.'),
   dict(node='debt:total',flow=None,text_en='Result: public debt reaches about €2.63 billion by the end of 2026 — external €1,574.6M, domestic €1,059.8M.',text_sq='Rezultati: borxhi publik arrin rreth €2.63 miliardë në fund të 2026 — i jashtëm €1,574.6M, i brendshëm €1,059.8M.')]),
 dict(id='borrowing-capital',title_en='Follow borrowed money into capital projects',title_sq='Ndiq huamarrjen deri te projektet kapitale',steps=[
   dict(node='fin:projl06',flow=fid('fin:projl06','fin:extin'),text_en='Project loans under the “investment clause” (fund 06) arrive as external receipts.',text_sq='Projekt-kreditë sipas klauzolës së investimeve (fondi 06).'),
   dict(node='fin:extin',flow=fid('fin:extin','pool'),text_en='All external borrowing receipts for 2026.',text_sq='Të gjitha pranimet nga huamarrja e jashtme për 2026.'),
   dict(node='org:205/clause',flow=fid('fin:projl06','org:205/clause'),text_en='Linked by funding source to investment-clause allocations; the Ministry of Environment, Spatial Planning and Infrastructure is the largest.',text_sq='Lidhur sipas burimit të financimit me ndarjet e klauzolës.'),
   dict(node=pclause['id'] if pclause else 'org:205',flow=fid('org:205',pclause['id']) if pclause else None,text_en='…down to individual loan-financed projects in Tabela 3.2.B.',text_sq='…deri te projektet individuale në Tabelën 3.2.B.')]),
 dict(id='municipal',title_en='Follow money to a municipality',title_sq='Ndiq paratë deri te një komunë',steps=[
   dict(node='dest:local',flow=fid('budget','dest:local'),text_en='Municipalities receive general, education and health grants plus their own-source revenue.',text_sq='Komunat marrin grante dhe të hyra vetanake.'),
   dict(node='mun:616',flow=fid('dest:local','mun:616'),text_en='Prishtinë has the largest municipal budget.',text_sq='Prishtina ka buxhetin më të madh komunal.'),
   dict(node='cat:wages',flow=fid('mun:616','cat:wages'),text_en='Wages are the biggest municipal category (teachers, health workers, administration).',text_sq='Pagat janë kategoria më e madhe.'),
   dict(node=p616['id'] if p616 else 'mun:616',flow=fid('mun:616',p616['id']) if p616 else None,text_en='Its biggest capital project in 2026.',text_sq='Projekti më i madh kapital për 2026.'),
   dict(node='dest:local/diff',flow=fid('dest:local','dest:local/diff'),text_en='The municipal plans add up to less than the ceiling in Table 2 — the document calls this gap “Bilanci”.',text_sq='Planet komunale janë më të vogla se tavani në Tabelën 2 — “Bilanci”.')]),
 dict(id='pensions',title_en='Where transfers go: pensions',title_sq='Ku shkojnë transferet: pensionet',steps=[
   dict(node='budget',flow=fid('budget','dest:central'),text_en='Subsidies and transfers are the largest spending category.',text_sq='Subvencionet dhe transferet janë kategoria më e madhe.'),
   dict(node='org:201',flow=fid('dest:central','org:201'),text_en='Most of them sit in the Ministry of Finance, Labour and Transfers.',text_sq='Shumica janë te MFPT.'),
   dict(node=pens[0]['id'] if pens else 'org:201',flow=fid('org:201',pens[0]['id']) if pens else None,text_en='The pensions and compensation programme.',text_sq='Programi i pensioneve dhe kompensimeve.'),
   dict(node='cat:subs',flow=fid('org:201','cat:subs'),text_en='Paid out as subsidies and transfers.',text_sq='Paguhen si subvencione dhe transfere.')]),
 dict(id='gaps',title_en='Where the totals don’t add up',title_sq='Ku totalet nuk përputhen',steps=[
   dict(node='dest:donor',flow=fid('pool','dest:donor'),text_en='€12.0M of donor-designated grants is in Table 1 spending but not allocated in Table 2.',text_sq='12.0M grante të donatorëve janë në Tabelën 1 por jo në Tabelën 2.'),
   dict(node='dest:local/diff',flow=fid('dest:local','dest:local/diff'),text_en='Municipal ceilings exceed the sum of municipal plans by €181,296.',text_sq='Tavanet komunale tejkalojnë planet me 181,296 €.'),
   dict(node='org:204/diff' if 'org:204/diff' in NODES else 'org:204',flow=None,text_en='Small row-level gaps inside Tabela 3.1 (a few euros) are kept as difference nodes.',text_sq='Diferenca të vogla brenda Tabelës 3.1.'),
   dict(node='pool/diff' if 'pool/diff' in NODES else 'pool',flow=None,text_en='Tables 1 and 1.1 are rounded to €0.1M, so the top-level balance carries a rounding difference.',text_sq='Tabelat 1 dhe 1.1 janë të rrumbullakuara në 0.1M.')]),
]
for t in TOURS:
    for s in t['steps']:
        if s['node'] not in NODES: raise SystemExit('tour node missing '+s['node'])

exec(open(ADAPTER_DIR/'normalize_part3.py').read())
exec(open(ADAPTER_DIR/'normalize_part4.py').read())
exec(open(ADAPTER_DIR/'sq_text.py').read()); apply(CHECKS,FINDINGS); apply_notes(NODES.values(),FLOWS)
# ---- export ----
for r in REFS.values():
    if r.get('row')==r.get('original_label'): r.pop('row',None)
    if r.get('top') is not None: r['top']=int(r['top'])
for n in NODES.values():
    if n.get('name_en')==n.get('name_sq') and n.get('en_src')!='proper noun': n.pop('name_en',None)
    for k in [k for k,v in n.items() if v in ('',None,[],{}) and k not in ('flags',)]: n.pop(k)
    n.pop('prog_label',None)
    if not n.get('flags'): n.pop('flags',None)
for n in NODES.values():
    for k in ('amount','staff','y2027','y2028'):
        if isinstance(n.get(k),float): n[k]=round(n[k],2)
order=['overview','overview-fin','overview-exp','central','municipal','capital']
DATA=dict(meta=dict(title_sq='Buxheti i Kosovës 2026',title_en='Kosovo budget 2026',law='Ligji Nr. 10/L-001 mbi ndarjet buxhetore për Buxhetin e Republikës së Kosovës për vitin 2026',
     gazette='Gazeta Zyrtare Nr. 4, 2 mars 2026',pdf=PDF,pages=728,extracted='pdfplumber word positions; raw CSV in raw/'),
     sources=SOURCES,kpis=KPI,refs=REFS,nodes=list(NODES.values()),flows=FLOWS,checks=CHECKS,findings=FINDINGS,tours=TOURS,summary=SUM)
js='window.BUDGET_DATA='+json.dumps(DATA,ensure_ascii=False,separators=(',',':'))+';\n'
open(DATASET_DIR/'data.json','w').write(js[len('window.BUDGET_DATA='):-2])
print('nodes',len(NODES),'flows',len(FLOWS),'refs',len(REFS),'checks',len(CHECKS),'pass',sum(c['status']=='pass' for c in CHECKS),'findings',len(FINDINGS),'size MB',round(len(js)/1e6,2))
for c in CHECKS:
    if c['status']=='fail': print('FAIL',c['id'],c['title'],c['expected'],c['actual'],c['diff'])
