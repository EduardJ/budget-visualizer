# ---- part 4: exhaustive exact checks (runs inside normalize_part2, before sq_text) ----
import re, json, csv
from decimal import Decimal as Dm
exec(open(REPO/'pipeline'/'exact.py').read())
from pipeline.pdfutil import lines as plines, lines_merged as plm, isnum as pisnum
YRS=['y2023','y2024','y2025','y2026','y2027','y2028']; YL={'y2023':'2023','y2024':'2024','y2025':'2025 LB','y2026':'2026','y2027':'2027','y2028':'2028'}
# superseded 2026-only / tolerance-based checks are rebuilt below for every year with exact arithmetic
DROP=('t1_','t11_','pool','t2_t1_','t2_vs_t1','p701_','borrow_06','proj_vs_t1cap','debt_gdp','t1_t11')
CHECKS[:]=[c for c in CHECKS if not c['id'].startswith(DROP)]
CLS_NOTE_EN={'rounding':'The printed figures do not add up exactly; the gap is within what rounding of the printed digits could produce.',
             'error':'The gap is larger than rounding of the printed digits could produce.'}
def X(id,group,title_en,title_sq,lhs,rhs,pages,refs=(),unit='EUR million',scale=M,note_en='',note_sq=''):
    exp,act,diff,cls=relation(lhs,rhs)
    c=check(id,title_en,float(exp)*scale,float(act)*scale,pages,refs=refs,kind='sum',title_sq=title_sq,group=group,unit=unit,
            cls=cls,note=note_en,note_sq=note_sq)
    c['printed_diff']=str(diff); c['printed_unit']=unit
    return c
def RT(id,group,title_en,title_sq,euro,printed_term,pages,refs=(),note_en='',note_sq=''):
    """a euro figure against the same figure printed in € million: it must round to the printed digits"""
    ok=rounds_to(Dm(str(euro))/Dm(1000000),printed_term)
    c=check(id,title_en,float(printed_term.v)*M,float(euro),pages,refs=refs,kind='rounds',title_sq=title_sq,group=group,
            cls=None if ok else 'error',note=note_en or f'€{euro:,.0f} rounds to {rnd(Dm(str(euro))/Dm(1000000),printed_term.dec)} million; printed {printed_term.v}.',
            note_sq=note_sq or f'€{euro:,.0f} rrumbullakohet në {rnd(Dm(str(euro))/Dm(1000000),printed_term.dec)} milionë; e shtypur {printed_term.v}.')
    c['status']='pass' if ok else 'fail'; c['cls']=None if ok else 'error'; c['diff']=0.0 if ok else c['diff']
    return c
def CL(id,group,title_en,title_sq,printed,f,terms,pages,refs=(),unit='%',dec=1,quote=''):
    """a percentage (or other derived figure) printed in the text against the same quantity computed from printed table figures"""
    exact=f(*[t.v for t in terms]); r=rnd(exact,dec)
    if r==printed: cls=None
    else:
        lo,hi=interval(f,terms); cls='rounding' if lo-half(dec)<=printed<=hi+half(dec) else 'error'
    c=check(id,title_en,float(printed),float(r),pages,refs=refs,kind='claim',title_sq=title_sq,group=group,unit=unit,cls=cls,
            note=f'Computed from the printed tables: {exact:.4f} → {r}. Printed: {printed}.'+(f' Text: “{quote}”' if quote else ''),
            note_sq=f'Llogaritur nga tabelat e shtypura: {exact:.4f} → {r}. E shtypur: {printed}.'+(f' Teksti: “{quote}”' if quote else ''))
    c['status']='pass' if cls is None else 'fail'; c['cls']=cls; c['diff']=float(r-printed); c['expected']=float(printed); c['actual']=float(r)
    return c
# ---------- Table 1 and 1.1, every year ----------
def rowmap(rows,table):
    m={}; occ={}
    for r in rows:
        k=r['label'].strip(); occ[k]=occ.get(k,-1)+1
        key=k if occ[k]==0 else f'{k}#{occ[k]}'
        r['_ref']=mkref(table,r['page'],r['raw'],k,'EUR million',{y:fnum(r[y]) for y in YRS if r.get(y) not in ('',None)},top=r['top'])
        m[key]=r
    return m
T1=rowmap(t1,'Tabela 1'); T11=rowmap(t11,'Tabela 1.1')
def tm(m,key,y,sign=1):
    r=m[key]; v=r.get(y)
    if v in ('',None): return Term(0,1,key,r['_ref'],sign)    # blank cell = 0, half-unit of the column
    return term_from(r['raw'],fnum(v),key,r['_ref'],sign)
REL1=[ # (id, lhs, [(sign, rhs)], title_en, title_sq)
 ('rev','1. GJITHSEJ TË HYRAT BUXHETORE [1]',[(1,'1.1 Të Hyra Tatimore'),(1,'1.2 Të Hyrat Jo-Tatimore'),(1,'1.3 Grantet dhe ndihmat')],'Total revenue = tax + non-tax + grants','Të hyrat totale = tatimore + jo-tatimore + grantet'),
 ('tax','1.1 Të Hyra Tatimore',[(1,'Tatimet Direkte'),(1,'Tatimet Indirekte'),(1,'Rimbursimet tatimore')],'Tax revenue = direct + indirect + refunds','Të hyrat tatimore = direkte + indirekte + rimbursimet'),
 ('direct','Tatimet Direkte',[(1,'Tatimi në të ardhurat e korporatave'),(1,'Tatimi në të ardhura personale'),(1,'Tatimi në pronë'),(1,'Të tjera')],'Direct taxes = CIT + PIT + property + other','Tatimet direkte = korporatat + personale + prona + të tjera'),
 ('indirect','Tatimet Indirekte',[(1,'Tatimi mbi Vlerën e Shtuar(TVSH)'),(1,'Detyrimi Doganor'),(1,'Akcizë'),(1,'Të tjera#1')],'Indirect taxes = VAT + customs + excise + other','Tatimet indirekte = TVSH + dogana + akciza + të tjera'),
 ('vat','Tatimi mbi Vlerën e Shtuar(TVSH)',[(1,'Vendore:'),(1,'Kufitare:')],'VAT = domestic + border','TVSH = vendore + kufitare'),
 ('nontax','1.2 Të Hyrat Jo-Tatimore',[(1,'Taksat, ngarkesa dhe të tjera'),(1,'Taksa koncesionare'),(1,'Renta Minerare'),(1,'Te hyrat nga liberalizimi i tregut te telefonise mobile'),(1,'Te hyrat nga dividenda dhe ndarja e fitimit'),(1,'Të hyrat nga interesi')],'Non-tax revenue = sum of its lines','Të hyrat jo-tatimore = shuma e rreshtave'),
 ('fees','Taksat, ngarkesa dhe të tjera',[(1,'Taksa, ngarkesa dhe të tjera - Niveli Qendror'),(1,'Taksa, ngarkesa dhe të tjera - Niveli Lokal')],'Fees and charges = central + local','Taksat dhe ngarkesat = qendror + lokal'),
 ('intinc','Të hyrat nga interesi',[(1,'Të hyrat nga interesi (KEK-hua)'),(1,'Të hyrat nga interesi (NP-ve) tjera'),(1,'Tw hyra nga interesi-tjera')],'Interest income = KEK + public enterprises + other','Të hyrat nga interesi = KEK + NP + tjera'),
 ('grants','1.3 Grantet dhe ndihmat',[(1,'Grante për mbështetje buxhetore'),(1,'Grante e përcaktuara të donatorëve')],'Grants = budget support + donor-designated','Grantet = mbështetje buxhetore + grante të donatorëve'),
 ('exp','2. GITHSEJ SHPENZIMET BUXHETORE[1]',[(1,'2.1 Shpenzimet Rrjedhëse'),(1,'2.2 Interesi për Borxhin Publik'),(1,'2.3 Shpenzimet Kapitale'),(1,'2.4 Grantet e Përcaktuara të Donatorve')],'Total spending = current + interest + capital + donor grants','Shpenzimet totale = rrjedhëse + interesi + kapitale + grantet e donatorëve'),
 ('cur','2.1 Shpenzimet Rrjedhëse',[(1,'Paga dhe shtesa'),(1,'Mallra dhe Shërbime'),(1,'Subvencione dhe Transfere'),(1,'Rezerva rrjedhëse')],'Current spending = wages + goods + subsidies + reserve','Shpenzimet rrjedhëse = paga + mallra + subvencione + rezerva'),
 ('cap','2.3 Shpenzimet Kapitale',[(1,'Financimi nga buxheti i rregullt'),(1,'Klauzola e investimeve'),(1,'Fondet e likuidimit (AKP)')],'Capital = regular budget + investment clause + AKP liquidation funds','Kapitale = buxheti i rregullt + klauzola + fondet e likuidimit (AKP)'),
 ('bal','3. Bilanci buxhetor (1-2)',[(1,'1. GJITHSEJ TË HYRAT BUXHETORE [1]'),(-1,'2. GITHSEJ SHPENZIMET BUXHETORE[1]')],'Balance = revenue − spending','Bilanci = të hyrat − shpenzimet'),
 ('excl','4. Shpenzimet e përjashtuara nga kufiri i rr. fiskale:',[(1,'Shpenzimet nga pranimet e dedikuara'),(1,'Shpenzimet nga të hyrat komunale të bartura'),(1,'Fondet e likuidimit nga AKP-ja'),(1,'Shpenzimet e financuara nga klauzola e investimeve')],'Spending excluded from the fiscal rule = sum of its lines','Shpenzimet e përjashtuara nga rregulla fiskale = shuma e rreshtave'),
 ('rulebal','(3+4)',[(1,'3. Bilanci buxhetor (1-2)'),(1,'4. Shpenzimet e përjashtuara nga kufiri i rr. fiskale:')],'Fiscal-rule balance = balance + excluded spending (3+4)','Bilanci sipas rregullës fiskale = 3 + 4'),
 ('need','A. Nevoja për financim',[(1,'3. Bilanci buxhetor (1-2)')],'Financing need = budget balance','Nevoja për financim = bilanci buxhetor'),
 ('D','D. Ndryshimi në bilancin e pashpërndarë bankar (A+B+C)',[(1,'A. Nevoja për financim'),(1,'B. Financimi i jashtëm(neto)'),(1,'C. Financimi i brendshëm(neto)')],'Change in unallocated bank balance = A + B + C','Ndryshimi në bilancin bankar = A + B + C'),
 ('G','G. Stoku i bilancit bankar në fundvit (BRUTO)',[(1,'E. Stoku i bilancit bankar (NETO)'),(1,'F. Fondet me Qëllime Specifike (gjendja në fundvit)')],'Gross bank balance = net balance + special-purpose funds','Bilanci bankar bruto = neto + fondet me qëllime specifike'),
 ('memo_refunds','Rimbursimet tatimore#1',[(1,'Rimbursimet tatimore')],'Memo “Rimbursimet tatimore” = tax refunds line','Memo “Rimbursimet tatimore” = rreshti i rimbursimeve'),
 ('memo_donor','Daljet nga Grantet e Percaktuara te Donatoreve',[(1,'2.4 Grantet e Përcaktuara të Donatorve')],'Memo donor-grant outflows = spending line 2.4','Memo daljet nga grantet e donatorëve = rreshti 2.4'),
]
for id_,lhs,rhs,te,ts in REL1:
    for y in YRS:
        try: L=tm(T1,lhs,y); RR=[tm(T1,k,y,sg) for sg,k in rhs]
        except KeyError as e: raise SystemExit('Table 1 label '+str(e))
        if all(T1[k].get(y) in ('',None) for _,k in rhs) and T1[lhs].get(y) in ('',None): continue
        X(f't1_{id_}_{y}','Tabela 1',f'{te} — {YL[y]}',f'{ts} — {YL[y]}',L,RR,[int(T1[lhs]['page'])]+[int(T1[k]['page']) for _,k in rhs],refs=[L.ref]+[t.ref for t in RR])
# stock-flow: net bank balance(t) = net(t−1) + change(t)
for a,b in zip(YRS,YRS[1:]):
    L=tm(T1,'E. Stoku i bilancit bankar (NETO)',b); RR=[tm(T1,'E. Stoku i bilancit bankar (NETO)',a),tm(T1,'D. Ndryshimi në bilancin e pashpërndarë bankar (A+B+C)',b)]
    X(f't1_Estock_{b}','Tabela 1',f'Net bank balance {YL[b]} = previous year + change',f'Bilanci bankar neto {YL[b]} = viti paraprak + ndryshimi',L,RR,[30],refs=[L.ref])
# percentages of GDP printed in Table 1 memo
pct_rows=[r for r in t1 if '%' in r['raw']]
def pcts(raw): return [Dm(x.replace('%','')) for x in re.findall(r'-?[\d.]+%',raw)]
for r in pct_rows:
    lab=r['raw']; vals=pcts(lab)
    if len(vals)!=6: continue
    for i,y in enumerate(YRS):
        g=tm(T1,'BPV',y)
        if 'fiskal I përgjithshem' in lab: num=tm(T1,'3. Bilanci buxhetor (1-2)',y); f=lambda a,b:a/b*100; nm_en='General fiscal balance % GDP'; nm_sq='Bilanci fiskal i përgjithshëm % e BPV'
        elif 'shfrytezueshem' in lab: num=tm(T1,'E. Stoku i bilancit bankar (NETO)',y); f=lambda a,b:a/b*100; nm_en='Usable bank balance % GDP'; nm_sq='Bilanci bankar i shfrytëzueshëm % e BPV'
        elif 'rregullës fiskale' in lab or lab.startswith('së '): num=tm(T1,'(3+4)',y); f=lambda a,b:a/b*100; nm_en='Fiscal-rule deficit % GDP'; nm_sq='Deficiti sipas rregullës fiskale % e BPV'
        else: continue
        CL(f't1_pct_{nm_en[:8]}_{y}','Tabela 1',f'{nm_en} — {YL[y]}',f'{nm_sq} — {YL[y]}',vals[i],f,[num,g],[30],refs=[num.ref,g.ref],dec=len(str(vals[i]).split('.')[1]) if '.' in str(vals[i]) else 0)
# the fiscal-rule % row is split over two lines in the PDF; parse it from the raw page text
for l in plines(30):
    if l['text'].startswith('së ') and '%' in l['text']:
        vals=pcts(l['text'])
        for i,y in enumerate(YRS):
            num=tm(T1,'(3+4)',y); g=tm(T1,'BPV',y)
            CL(f't1_pct_rule_{y}','Tabela 1',f'Fiscal-rule balance % GDP — {YL[y]}',f'Bilanci sipas rregullës fiskale % e BPV — {YL[y]}',vals[i],lambda a,b:a/b*100,[num,g],[30],refs=[num.ref,g.ref],dec=len(str(vals[i]).split('.')[1]))
REL11=[
 ('need','1. NEVOJA PËR FINANCIM',[(1,'Të Hyrat Buxhetore'),(-1,'Shpenzimet Buxhetore')],'Financing need = revenue − spending','Nevoja për financim = të hyrat − shpenzimet'),
 ('ext','2. Neto financimi nga burimet e jashtme për vitin',[(1,'2.1. Pranimet:'),(-1,'2.2. Daljet:')],'Net external financing = receipts − outflows','Financimi i jashtëm neto = pranimet − daljet'),
 ('extin','2.1. Pranimet:',[(1,'Financim Direkt Buxhetor - FMN, BB, BE, etj.'),(1,'Nën-huazimet, bruto pranimet'),(1,'Projekt-kreditë')],'External receipts = budget support + on-lending + project loans','Pranimet e jashtme = mbështetja + nën-huazimet + projekt-kreditë'),
 ('onlin','Nën-huazimet, bruto pranimet',[(1,'Terheqjet nga kreditoret'),(1,'Pranimet nga subjektet publike huazuese')],'On-lending receipts = drawings + receipts from public borrowers','Nën-huazimet bruto = tërheqjet + pranimet nga subjektet'),
 ('projl','Projekt-kreditë',[(1,'Projekt-kreditë, trajtim brenda deficiti (fondi 04)'),(1,'Projekt-kreditë, klauzola e investimeve (fondi 06)')],'Project loans = fund 04 + fund 06','Projekt-kreditë = fondi 04 + fondi 06'),
 ('extout','2.2. Daljet:',[(1,'Pagesa e kryegjesë së borxhit')],'External outflows = principal repayment','Daljet e jashtme = kthimi i kryegjësë'),
 ('dom','3. Neto financimi nga burimet e brendshme për vitin',[(1,'3.1. Pranimet:'),(-1,'3.2. Daljet:')],'Net domestic financing = receipts − outflows','Financimi i brendshëm neto = pranimet − daljet'),
 ('domin','3.1. Pranimet:',[(1,'Emetimet e reja të letrave me vlerë'),(1,'Pranimet nga emetimet e letrave me vlerë për qëllime rifinancimi'),(1,'Pranimet nga kthimet prej entitetet publike (kryegjesë)'),(1,'Financimi i njehereshem nga likuidimi/privatizimi dhe të tjera'),(1,'Pranimet e dedikuara nga AKP'),(1,'Pranimet e dedikuara -tjera (ASHNA )'),(1,'Ndryshimi nga stoku i fondeve me qellime specifike (kur FS2; FS3;')],'Domestic receipts = sum of lines','Pranimet e brendshme = shuma e rreshtave'),
 ('repay','Pranimet nga kthimet prej entitetet publike (kryegjesë)',[(1,'Pranimet nga kthimi i kryegjesë së borxhit të KEK'),(1,'Pranimet nga kthimi i kryegjesë së borxhit të KOSST'),(1,'Pranimet nga kthimi i kryegjesë së borxhitpër Ristrukturim e TELEKOM-it'),(1,'Pranimet nga kthimi i kryegjesë së borxhit për Likuiditet e KOSTT-it'),(1,'Pranimet nga kthimi i kryegjesë së borxhit për Likuiditet e RTK- së')],'Repayments by public entities = sum of lines','Kthimet nga entitetet publike = shuma e rreshtave'),
 ('onlout','Nen-huazimet, bruto daljet',[(1,'Daljet per nen-huazim tek subjektet publike huazuese'),(1,'Daljet per sherbim te borxhit tek kreditoret')],'On-lending outflows = to public borrowers + debt service to creditors','Nën-huazimet bruto daljet = te subjektet + shërbimi i borxhit'),
 ('chg','rriten) 4. NDRYSHIMI NË BILANCIN E PASHPËRNDARË BANKAR',[(1,'1. NEVOJA PËR FINANCIM'),(1,'2. Neto financimi nga burimet e jashtme për vitin'),(1,'3. Neto financimi nga burimet e brendshme për vitin')],'Change in unallocated bank balance = 1 + 2 + 3','Ndryshimi në bilancin bankar = 1 + 2 + 3'),
 ('fs','6. FONDET ME QELLIME SPECIFIKE, gjendja e stoqeve',[(1,'FS1_Grantet e përcaktuara nga donatorët'),(1,'FS2_Të hyrat vetanake të bartura - Niveli Qendror'),(1,'FS3_Të hyrat vetanake të bartura - Niveli Lokal'),(1,'FS4_Pranimet e dedikuara për bartje'),(1,'FS5_Fondi zhvillimor në mirëbesim'),(1,'FS6_Të tjera-fondet në mirëbesim'),(1,'FS7_Fondet e pashpenzuara nga huamarrja'),(1,'FS7_Fondet e pashpenzuara nga Grante BE për energjinë')],'Special-purpose funds = FS1 … FS7','Fondet me qëllime specifike = FS1 … FS7'),
 ('gross','7. BRUTO BILANCI BANKAR NE FUNDVIT',[(1,'5. NETO BILANCI BANKAR FUNDVIT'),(1,'6. FONDET ME QELLIME SPECIFIKE, gjendja e stoqeve')],'Gross bank balance = net + special-purpose funds','Bilanci bankar bruto = neto + fondet me qëllime specifike'),
]
# 3.2 outflows: the "Nen-huazimet, bruto daljet" 2023/2024 values are printed split over three lines (18.752/1 and 18.481/0); use them as printed
T11['Nen-huazimet, bruto daljet']=dict(T11['Nen-huazimet, bruto daljet'])
for y,v in (('y2023','18.7521'),('y2024','18.4810')): T11['Nen-huazimet, bruto daljet'][y]=v
FINDINGS.append(dict(type='note',title='Tabela 1.1 p.32: the 2023 and 2024 values of “Nen-huazimet, bruto daljet” are printed broken over three lines (18.752 / 1 and 18.481 / 0); read as 18.7521 and 18.4810, as in the reprint on p.705.',pages=[32,705],
                     title_sq='Tabela 1.1 f.32: vlerat e 2023 dhe 2024 të “Nen-huazimet, bruto daljet” janë shtypur të ndara në tre rreshta (18.752 / 1 dhe 18.481 / 0); lexohen 18.7521 dhe 18.4810, si në ribotimin në f.705.'))
REL11.append(('domout','3.2. Daljet:',[(1,'Huadhënia për entitete publike'),(1,'Nen-huazimet, bruto daljet'),(1,'Daljet nga emetimet e letrave me vlerë për qëllime rifinancimi'),(1,'Daljet për anëtarsim dhe rritje te kuotave në INF'),(1,'Dalje për Kapitalizim dhe blerje të aksioneve'),(1,'Dalje për rritjen e fondeve me qellime specifike (FS2;FS3;FS4;FS5')],'Domestic outflows = sum of lines','Daljet e brendshme = shuma e rreshtave'))
def tm11(key,y,sign=1):
    r=T11[key]; v=r.get(y)
    if v in ('',None): return Term(0,1,key,r['_ref'],sign)
    t=term_from(r['raw'],fnum(v),key,r['_ref'],sign)
    if t.v==0 and fnum(v)!=0: t=Term(Dm(str(v)),len(str(v).split('.')[1]) if '.' in str(v) else 0,key,r['_ref'],sign)
    return t
for id_,lhs,rhs,te,ts in REL11:
    for y in YRS:
        L=tm11(lhs,y); RR=[tm11(k,y,sg) for sg,k in rhs]
        X(f't11_{id_}_{y}','Tabela 1.1',f'{te} — {YL[y]}',f'{ts} — {YL[y]}',L,RR,[32,33],refs=[L.ref]+[t.ref for t in RR])
for a,b in zip(YRS,YRS[1:]):
    L=tm11('5. NETO BILANCI BANKAR FUNDVIT',b); RR=[tm11('5. NETO BILANCI BANKAR FUNDVIT',a),tm11('rriten) 4. NDRYSHIMI NË BILANCIN E PASHPËRNDARË BANKAR',b)]
    X(f't11_net_{b}','Tabela 1.1',f'Net bank balance {YL[b]} = previous year + change',f'Bilanci bankar neto {YL[b]} = viti paraprak + ndryshimi',L,RR,[32],refs=[L.ref])
    L=tm11('8. NDRYSHIMI NE BRUTO BILANCIN BANKAR',b); RR=[tm11('7. BRUTO BILANCI BANKAR NE FUNDVIT',b),tm11('7. BRUTO BILANCI BANKAR NE FUNDVIT',a,-1)]
    X(f't11_grosschg_{b}','Tabela 1.1',f'Change in gross bank balance {YL[b]} = gross(t) − gross(t−1)',f'Ndryshimi në bilancin bankar bruto {YL[b]} = bruto(t) − bruto(t−1)',L,RR,[33],refs=[L.ref])
# Table 1 vs Table 1.1 (same quantities printed twice)
PAIRS=[('1. GJITHSEJ TË HYRAT BUXHETORE [1]','Të Hyrat Buxhetore'),('2. GITHSEJ SHPENZIMET BUXHETORE[1]','Shpenzimet Buxhetore'),('A. Nevoja për financim','1. NEVOJA PËR FINANCIM'),
       ('B. Financimi i jashtëm(neto)','2. Neto financimi nga burimet e jashtme për vitin'),('C. Financimi i brendshëm(neto)','3. Neto financimi nga burimet e brendshme për vitin'),
       ('D. Ndryshimi në bilancin e pashpërndarë bankar (A+B+C)','rriten) 4. NDRYSHIMI NË BILANCIN E PASHPËRNDARË BANKAR'),('E. Stoku i bilancit bankar (NETO)','5. NETO BILANCI BANKAR FUNDVIT'),
       ('F. Fondet me Qëllime Specifike (gjendja në fundvit)','6. FONDET ME QELLIME SPECIFIKE, gjendja e stoqeve'),('G. Stoku i bilancit bankar në fundvit (BRUTO)','7. BRUTO BILANCI BANKAR NE FUNDVIT'),
       ('Klauzola e investimeve','Projekt-kreditë, klauzola e investimeve (fondi 06)')]
for a,b in PAIRS:
    for y in YRS:
        L=tm(T1,a,y); RR=[tm11(b,y)]
        X(f't1v11_{a[:6]}_{y}','Tabela 1 ↔ 1.1',f'Same figure in Tabela 1 and 1.1: “{a}” — {YL[y]}',f'E njëjta shifër në Tabelën 1 dhe 1.1: “{a}” — {YL[y]}',L,RR,[29,30,32,33],refs=[L.ref,RR[0].ref])
# debt % GDP (Table 1.1 memo prints it; the narrative and p.700 repeat it)
dg_line=[l for l in plines(33) if 'Borxhi i përgjithshëm' in l['text']][0]; dg_vals=pcts(dg_line['text'])
for i,y in enumerate(YRS):
    terms=[tm11('Stoku i borxhit të brendshëm',y),tm11('Stoku i borxhit të jashtëm',y),tm11('Garancionet shtetërore',y),tm(T1,'BPV',y)]
    CL(f't11_debtpct_{y}','Tabela 1.1',f'Debt incl. guarantees % GDP — {YL[y]}',f'Borxhi përfshirë garancionet % e BPV — {YL[y]}',dg_vals[i],lambda a,b,c,d:(a+b+c)/d*100,terms,[30,33],refs=[t.ref for t in terms],quote=dg_line['text'][:90])
ip_line=[l for l in plines(33) if 'Shpenzimet e interesit' in l['text']][0]; ip_vals=pcts(ip_line['text'])
for i,y in enumerate(YRS):
    terms=[tm(T1,'2.2 Interesi për Borxhin Publik',y),tm(T1,'BPV',y)]
    CL(f't11_intpct_{y}','Tabela 1.1',f'Interest % GDP — {YL[y]}',f'Interesi % e BPV — {YL[y]}',ip_vals[i],lambda a,b:a/b*100,terms,[29,30,33],refs=[t.ref for t in terms])
# ---------- Table 2 against Table 1 (euros vs € million) ----------
for k,lab in [('wages','Paga dhe shtesa'),('subs','Subvencione dhe Transfere'),('capital','2.3 Shpenzimet Kapitale'),('reserve','Rezerva rrjedhëse'),('interest','2.2 Interesi për Borxhin Publik')]:
    RT(f't2t1_{k}','Tabela 2 ↔ Tabela 1',f'Tabela 2 {CAT[k][1].lower()} vs Tabela 1 (2026)',f'Tabela 2 {CAT[k][0].lower()} kundrejt Tabelës 1 (2026)',fnum(r_tot[k]),tm(T1,lab,'y2026'),[29,34],refs=[ref_tot,T1[lab]['_ref']])
RT('t2t1_goods','Tabela 2 ↔ Tabela 1','Tabela 2 goods + utilities vs Tabela 1 “Mallra dhe Shërbime” (2026)','Tabela 2 mallra + komunale kundrejt Tabelës 1 “Mallra dhe Shërbime” (2026)',fnum(r_tot['goods'])+fnum(r_tot['util']),tm(T1,'Mallra dhe Shërbime','y2026'),[29,34],refs=[ref_tot])
RT('t2t1_total','Tabela 2 ↔ Tabela 1','Tabela 2 grand total vs Tabela 1 total spending (2026)','Totali i Tabelës 2 kundrejt shpenzimeve totale në Tabelën 1 (2026)',fnum(r_tot['total']),tm(T1,'2. GITHSEJ SHPENZIMET BUXHETORE[1]','y2026'),[29,34],refs=[ref_tot],
   note_en='Gap equals line 2.4 “Grantet e Përcaktuara të Donatorve” (12.0M), which Table 2 does not allocate.',note_sq='Diferenca është sa rreshti 2.4 “Grantet e Përcaktuara të Donatorve” (12.0M), të cilin Tabela 2 nuk e ndan.')
RT('t2t1_total_donor','Tabela 2 ↔ Tabela 1','Tabela 2 grand total + donor grants (12.0M) vs Tabela 1 total spending (2026)','Totali i Tabelës 2 + grantet e donatorëve (12.0M) kundrejt shpenzimeve totale në Tabelën 1 (2026)',fnum(r_tot['total'])+12_000_000,tm(T1,'2. GITHSEJ SHPENZIMET BUXHETORE[1]','y2026'),[29,34],refs=[ref_tot])
RT('t2t1_clause','Tabela 2 ↔ Tabela 1','Investment clause in Tabela 2 (3.1.B + 4.1.B) vs Tabela 1 “Klauzola e investimeve” (2026)','Klauzola në Tabelën 2 (3.1.B + 4.1.B) kundrejt Tabelës 1 “Klauzola e investimeve” (2026)',fnum(r_c31b['total'])+fnum(r_l41b['total']),tm(T1,'Klauzola e investimeve','y2026'),[29,34],refs=[ref_c31b,ref_l41b])
RT('t2t1_clause06','Tabela 2 ↔ Tabela 1.1','Investment clause allocations vs Tabela 1.1 project loans fund 06 (2026)','Ndarjet e klauzolës kundrejt projekt-kredive fondi 06 në Tabelën 1.1 (2026)',fnum(r_c31b['total'])+fnum(r_l41b['total']),tm11('Projekt-kreditë, klauzola e investimeve (fondi 06)','y2026'),[32,34],refs=[ref_c31b])
pr=[n for n in NODES.values() if n.get('kind')=='project']
RT('t1_projects','Projektet ↔ Tabela 1','Capital projects (2026) in Tabelat 3.2/3.2.B/4.2/4.2.B vs Tabela 1 capital spending','Projektet kapitale (2026) në Tabelat 3.2/3.2.B/4.2/4.2.B kundrejt shpenzimeve kapitale në Tabelën 1',sum(n['amount'] for n in pr),tm(T1,'2.3 Shpenzimet Kapitale','y2026'),[29,97,357],
   note_en='Gap ≈ €4.09M, matching the municipal capital difference between Tabela 2 and Tabela 4.1 (“Bilanci”, p.213).',note_sq='Diferenca ≈ €4.09M, përputhet me diferencën kapitale komunale ndërmjet Tabelës 2 dhe Tabelës 4.1 (“Bilanci”, f.213).')
# ---------- p.701 tables, every year ----------
P701Y=['2025','2026','2027','2028']
for lvl in ('central','local'):
    rows=P701[lvl]; tot=[r for r in rows if r['label']=='Gjithsej'][0]
    for i,yy in enumerate(P701Y):
        L=Term(Dm(str(tot['v'][i])),1,'Gjithsej'); RR=[Term(Dm(str(r['v'][i])),1,r['label']) for r in rows if r['label'] in CATMAP]
        X(f'p701_{lvl}_sum_{yy}','f.701',f'p.701 {lvl} table: categories = total — {yy}',f'f.701 tabela {"qendrore" if lvl=="central" else "lokale"}: kategoritë = totali — {yy}',L,RR,[701])
    dn=NODES['dest:central' if lvl=='central' else 'dest:local']
    RT(f'p701_{lvl}_t2','f.701 ↔ Tabela 2',f'p.701 {lvl} total 2026 vs Tabela 2',f'f.701 totali {"qendror" if lvl=="central" else "lokal"} 2026 kundrejt Tabelës 2',dn['amount'],Term(Dm(str(tot['v'][1])),1),[34,701],refs=[dn['ref'],dn['prev_ref']])
    for r in rows:
        if r['label'] in CATMAP:
            k=CATMAP[r['label']]; src=r_cen if lvl=='central' else r_loc
            RT(f'p701_{lvl}_{k}','f.701 ↔ Tabela 2',f'p.701 {lvl} {CAT[k][1].lower()} 2026 vs Tabela 2',f'f.701 {CAT[k][0].lower()} 2026 ({"qendror" if lvl=="central" else "lokal"}) kundrejt Tabelës 2',fnum(src.get(k) or 0),Term(Dm(str(r['v'][1])),1),[34,701])
c25=[r for r in P701['central'] if r['label']=='Gjithsej'][0]; l25=[r for r in P701['local'] if r['label']=='Gjithsej'][0]
for i,y in enumerate(['y2025','y2026','y2027','y2028']):
    L=tm(T1,'2. GITHSEJ SHPENZIMET BUXHETORE[1]',y); RR=[Term(Dm(str(c25['v'][i])),1,'central'),Term(Dm(str(l25['v'][i])),1,'local'),tm(T1,'2.2 Interesi për Borxhin Publik',y),tm(T1,'2.4 Grantet e Përcaktuara të Donatorve',y)]
    X(f'p701_t1_{y}','f.701 ↔ Tabela 1',f'Central + local (p.701) + interest + donor grants = Tabela 1 total spending — {YL[y]}',f'Qendror + lokal (f.701) + interesi + grantet e donatorëve = shpenzimet totale në Tabelën 1 — {YL[y]}',L,RR,[29,701])
# narrative growth claims on p.701
def c701(lvl,lab): return [r for r in P701[lvl] if r['label']==lab][0]['v']
GROWTH=[('central','Gjithsej',Dm('10.0'),'rritje prej 10.0%'),('central','Paga dhe shtesa',Dm('2.7'),'pagave dhe shtesave ... rritje prej 2.7%'),('central','Subvencione dhe transfere',Dm('17.4'),'subvencioneve dhe transfereve me rritje prej 17.4%'),
        ('central','Shpenzime kapitale',Dm('7.2'),'Shpenzimet kapitale planifikohet të rriten për 7.2%'),('local','Gjithsej',Dm('10.1'),'rritje prej 10.1%'),('local','Paga dhe shtesa',Dm('13.1'),'paga dhe mëditje ... 13.1%'),
        ('local','Subvencione dhe transfere',Dm('17.0'),'subvencioneve dhe transfereve ... 17.0%'),('local','Mallra dhe shërbime',Dm('5.6'),'mallra dhe shërbime pritet të rriten për 5.6%'),('local','Shpenzime kapitale',Dm('7.2'),'shpenzimet kapitale me 7.2%')]
for lvl,lab,pr_,q in GROWTH:
    v=c701(lvl,lab); terms=[Term(Dm(str(v[1])),1),Term(Dm(str(v[0])),1)]
    CL(f'p701_claim_{lvl}_{lab[:6]}','Teksti ↔ tabelat',f'p.701 text: {lvl} “{lab}” grows {pr_}%',f'f.701 teksti: {"qendror" if lvl=="central" else "lokal"} “{lab}” rritet {pr_}%',pr_,lambda a,b:(a/b-1)*100,terms,[701],quote=q)
v=c701('local','Gjithsej'); CL('p701_claim_local_abs','Teksti ↔ tabelat','p.701 text: local spending up “about €79.4 million”','f.701 teksti: shpenzimet lokale rriten “rreth 79.4 milionë euro”',Dm('79.4'),lambda a,b:a-b,[Term(Dm(str(v[1])),1),Term(Dm(str(v[0])),1)],[701],unit='€ million')
# ---------- narrative chapter (pp.696–702) against Tables 1/1.1 ----------
def T(key,y): return tm(T1,key,y)
NAR=[('n_exp',698,'Total spending grows 9.9% (2026 vs 2025)','Shpenzimet totale rriten 9.9%',Dm('9.9'),lambda a,b:(a/b-1)*100,[T('2. GITHSEJ SHPENZIMET BUXHETORE[1]','y2026'),T('2. GITHSEJ SHPENZIMET BUXHETORE[1]','y2025')]),
     ('n_cur',698,'Current spending grows 10.7%','Shpenzimet rrjedhëse rriten 10.7%',Dm('10.7'),lambda a,b:(a/b-1)*100,[T('2.1 Shpenzimet Rrjedhëse','y2026'),T('2.1 Shpenzimet Rrjedhëse','y2025')]),
     ('n_wag',698,'Wages grow 6.9%','Pagat rriten 6.9%',Dm('6.9'),lambda a,b:(a/b-1)*100,[T('Paga dhe shtesa','y2026'),T('Paga dhe shtesa','y2025')]),
     ('n_goods',699,'Goods and services grow 1.6%','Mallrat dhe shërbimet rriten 1.6%',Dm('1.6'),lambda a,b:(a/b-1)*100,[T('Mallra dhe Shërbime','y2026'),T('Mallra dhe Shërbime','y2025')]),
     ('n_subs',699,'Subsidies and transfers grow 17.4%','Subvencionet dhe transferet rriten 17.4%',Dm('17.4'),lambda a,b:(a/b-1)*100,[T('Subvencione dhe Transfere','y2026'),T('Subvencione dhe Transfere','y2025')]),
     ('n_cap',699,'Capital spending grows 7.2%','Shpenzimet kapitale rriten 7.2%',Dm('7.2'),lambda a,b:(a/b-1)*100,[T('2.3 Shpenzimet Kapitale','y2026'),T('2.3 Shpenzimet Kapitale','y2025')]),
     ('n_capsh',699,'Capital spending is 25.2% of total spending','Shpenzimet kapitale janë 25.2% e totalit',Dm('25.2'),lambda a,b:a/b*100,[T('2.3 Shpenzimet Kapitale','y2026'),T('2. GITHSEJ SHPENZIMET BUXHETORE[1]','y2026')]),
     ('n_cap27',699,'Capital spending grows 9.6% in 2027','Shpenzimet kapitale rriten 9.6% në 2027',Dm('9.6'),lambda a,b:(a/b-1)*100,[T('2.3 Shpenzimet Kapitale','y2027'),T('2.3 Shpenzimet Kapitale','y2026')]),
     ('n_cap28',699,'Capital spending grows 2.4% in 2028','Shpenzimet kapitale rriten 2.4% në 2028',Dm('2.4'),lambda a,b:(a/b-1)*100,[T('2.3 Shpenzimet Kapitale','y2028'),T('2.3 Shpenzimet Kapitale','y2027')]),
     ('n_capavg',699,'Capital spending grows 6.0% on average 2027–2028','Shpenzimet kapitale rriten mesatarisht 6.0% (2027–2028)',Dm('6.0'),lambda a,b,c:((a/b-1)+(b/c-1))/2*100,[T('2.3 Shpenzimet Kapitale','y2028'),T('2.3 Shpenzimet Kapitale','y2027'),T('2.3 Shpenzimet Kapitale','y2026')]),
     ('n_expavg',699,'Total spending grows 4.1% on average 2027–2028','Shpenzimet totale rriten mesatarisht 4.1% (2027–2028)',Dm('4.1'),lambda a,b,c:((a/b-1)+(b/c-1))/2*100,[T('2. GITHSEJ SHPENZIMET BUXHETORE[1]','y2028'),T('2. GITHSEJ SHPENZIMET BUXHETORE[1]','y2027'),T('2. GITHSEJ SHPENZIMET BUXHETORE[1]','y2026')]),
     ('n_curavg',699,'Current spending grows 3.7% on average 2027–2028','Shpenzimet rrjedhëse rriten mesatarisht 3.7% (2027–2028)',Dm('3.7'),lambda a,b,c:((a/b-1)+(b/c-1))/2*100,[T('2.1 Shpenzimet Rrjedhëse','y2028'),T('2.1 Shpenzimet Rrjedhëse','y2027'),T('2.1 Shpenzimet Rrjedhëse','y2026')]),
     ('n_ind',697,'Indirect taxes are 74.4% of revenue in 2026','Tatimet indirekte janë 74.4% e të hyrave',Dm('74.4'),lambda a,b:a/b*100,[T('Tatimet Indirekte','y2026'),T('1. GJITHSEJ TË HYRAT BUXHETORE [1]','y2026')]),
     ('n_indg',697,'Indirect taxes grow 11.4% vs 2025','Tatimet indirekte rriten 11.4%',Dm('11.4'),lambda a,b:(a/b-1)*100,[T('Tatimet Indirekte','y2026'),T('Tatimet Indirekte','y2025')]),
     ('n_dirg',698,'Direct taxes grow 11.3% vs 2025','Tatimet direkte rriten 11.3%',Dm('11.3'),lambda a,b:(a/b-1)*100,[T('Tatimet Direkte','y2026'),T('Tatimet Direkte','y2025')]),
     ('n_dirs',698,'Direct taxes are 17.9% of revenue','Tatimet direkte janë 17.9% e të hyrave',Dm('17.9'),lambda a,b:a/b*100,[T('Tatimet Direkte','y2026'),T('1. GJITHSEJ TË HYRAT BUXHETORE [1]','y2026')]),
     ('n_ntg',698,'Non-tax revenue grows 0.2% vs 2025','Të hyrat jo-tatimore rriten 0.2%',Dm('0.2'),lambda a,b:(a/b-1)*100,[T('1.2 Të Hyrat Jo-Tatimore','y2026'),T('1.2 Të Hyrat Jo-Tatimore','y2025')]),
     ('n_revavg',698,'Revenue grows 6.9% on average 2027–2028','Të hyrat rriten mesatarisht 6.9% (2027–2028)',Dm('6.9'),lambda a,b,c:((a/b-1)+(b/c-1))/2*100,[T('1. GJITHSEJ TË HYRAT BUXHETORE [1]','y2028'),T('1. GJITHSEJ TË HYRAT BUXHETORE [1]','y2027'),T('1. GJITHSEJ TË HYRAT BUXHETORE [1]','y2026')]),
     ('n_diravg',698,'Direct taxes grow 8.3% on average 2027–2028','Tatimet direkte rriten mesatarisht 8.3%',Dm('8.3'),lambda a,b,c:((a/b-1)+(b/c-1))/2*100,[T('Tatimet Direkte','y2028'),T('Tatimet Direkte','y2027'),T('Tatimet Direkte','y2026')]),
     ('n_indavg',698,'Indirect taxes grow 7.3% on average 2027–2028','Tatimet indirekte rriten mesatarisht 7.3%',Dm('7.3'),lambda a,b,c:((a/b-1)+(b/c-1))/2*100,[T('Tatimet Indirekte','y2028'),T('Tatimet Indirekte','y2027'),T('Tatimet Indirekte','y2026')]),
     ('n_ntavg',698,'Non-tax revenue grows 4.0% on average 2027–2028','Të hyrat jo-tatimore rriten mesatarisht 4.0%',Dm('4.0'),lambda a,b,c:((a/b-1)+(b/c-1))/2*100,[T('1.2 Të Hyrat Jo-Tatimore','y2028'),T('1.2 Të Hyrat Jo-Tatimore','y2027'),T('1.2 Të Hyrat Jo-Tatimore','y2026')]),
     ('n_revmt',697,'Revenue grows about 7.9% over the medium term (2025→2028, yearly average)','Të hyrat rriten rreth 7.9% në afat të mesëm',Dm('7.9'),lambda a,b:((a/b)**(Dm(1)/Dm(3))-1)*100 if False else (pow(float(a/b),1/3)-1)*100,[T('1. GJITHSEJ TË HYRAT BUXHETORE [1]','y2028'),T('1. GJITHSEJ TË HYRAT BUXHETORE [1]','y2025')]),
     ('n_gdp25',695,'Nominal GDP grows 7.8% in 2025','BPV nominale rritet 7.8% në 2025',Dm('7.8'),lambda a,b:(a/b-1)*100,[T('BPV','y2025'),T('BPV','y2024')]),
     ('n_gdp26',696,'Nominal GDP grows 7.7% in 2026','BPV nominale rritet 7.7% në 2026',Dm('7.7'),lambda a,b:(a/b-1)*100,[T('BPV','y2026'),T('BPV','y2025')]),
     ('n_def26',701,'Deficit 2026 is “about 2.7%” of GDP','Deficiti 2026 “rreth 2.7%” e BPV',Dm('2.7'),lambda a,b:-a/b*100,[T('3. Bilanci buxhetor (1-2)','y2026'),T('BPV','y2026')]),
     ('n_def27',701,'Deficit 2027 is 2.0% of GDP','Deficiti 2027 2.0% e BPV',Dm('2.0'),lambda a,b:-a/b*100,[T('3. Bilanci buxhetor (1-2)','y2027'),T('BPV','y2027')]),
     ('n_def28',701,'Deficit 2028 is 1.0% of GDP','Deficiti 2028 1.0% e BPV',Dm('1.0'),lambda a,b:-a/b*100,[T('3. Bilanci buxhetor (1-2)','y2028'),T('BPV','y2028')]),
     ('n_bank26',701,'Usable bank balance about 3.0% of GDP in 2026','Bilanci bankar rreth 3.0% e BPV në 2026',Dm('3.0'),lambda a,b:a/b*100,[T('E. Stoku i bilancit bankar (NETO)','y2026'),T('BPV','y2026')]),
     ('n_bank27',701,'Usable bank balance about 3.5% of GDP in 2027','Bilanci bankar rreth 3.5% e BPV në 2027',Dm('3.5'),lambda a,b:a/b*100,[T('E. Stoku i bilancit bankar (NETO)','y2027'),T('BPV','y2027')]),
     ('n_bank28',701,'Usable bank balance about 4.0% of GDP in 2028','Bilanci bankar rreth 4.0% e BPV në 2028',Dm('4.0'),lambda a,b:a/b*100,[T('E. Stoku i bilancit bankar (NETO)','y2028'),T('BPV','y2028')]),
     ('n_debt26',702,'Debt incl. guarantees reaches 22.0% of GDP in 2026','Borxhi përfshirë garancionet arrin 22.0% e BPV në 2026',Dm('22.0'),lambda a,b,c,d:(a+b+c)/d*100,[tm11('Stoku i borxhit të brendshëm','y2026'),tm11('Stoku i borxhit të jashtëm','y2026'),tm11('Garancionet shtetërore','y2026'),T('BPV','y2026')]),
     ('n_debt27',702,'Debt incl. guarantees reaches 23.7% of GDP in 2027','Borxhi arrin 23.7% e BPV në 2027',Dm('23.7'),lambda a,b,c,d:(a+b+c)/d*100,[tm11('Stoku i borxhit të brendshëm','y2027'),tm11('Stoku i borxhit të jashtëm','y2027'),tm11('Garancionet shtetërore','y2027'),T('BPV','y2027')]),
     ('n_debt28',702,'Debt incl. guarantees reaches 24.1% of GDP in 2028','Borxhi arrin 24.1% e BPV në 2028',Dm('24.1'),lambda a,b,c,d:(a+b+c)/d*100,[tm11('Stoku i borxhit të brendshëm','y2028'),tm11('Stoku i borxhit të jashtëm','y2028'),tm11('Garancionet shtetërore','y2028'),T('BPV','y2028')]),
]
for id_,page,te,ts,printed,f,terms in NAR:
    CL(id_,'Teksti ↔ tabelat',f'p.{page} text: {te}',f'f.{page} teksti: {ts}',printed,f,terms,[page,29,30],refs=[t.ref for t in terms if t.ref])
for id_,page,te,ts,printed,lab,y in [('n_curv',698,'current spending “2,893.9 million”','shpenzimet rrjedhëse “2,893.9 milionë”',Dm('2893.9'),'2.1 Shpenzimet Rrjedhëse','y2026'),
                                     ('n_wagv',698,'wages “980.4 million”','pagat “980.4 milionë”',Dm('980.4'),'Paga dhe shtesa','y2026'),('n_ntv',698,'non-tax revenue “about 357.7 million”','të hyrat jo-tatimore “rreth 357.7 milionë”',Dm('357.7'),'1.2 Të Hyrat Jo-Tatimore','y2026'),
                                     ('n_grv',698,'grants “22.5 million”','grantet “22.5 milionë”',Dm('22.5'),'1.3 Grantet dhe ndihmat','y2026'),('n_resv',699,'current reserve “10.0 million”','rezerva rrjedhëse “10.0 milionë”',Dm('10.0'),'Rezerva rrjedhëse','y2026'),
                                     ('n_defv',701,'deficit “330.3 million”','deficiti “330.3 milionë”',Dm('-330.3'),'3. Bilanci buxhetor (1-2)','y2026')]:
    t_=T(lab,y); X(id_,'Teksti ↔ tabelat',f'p.{page} text: {te} vs Tabela 1',f'f.{page} teksti: {ts} kundrejt Tabelës 1',Term(printed,1),[t_],[page,29],refs=[t_.ref])
# ---------- p.700 Tabela 4, p.706 KASH table, p.712 Tabela 3 ----------
def numrow(p,prefix,occ=0):
    m=[l for l in plines(p) if re.sub(r'\s+',' ',l['text']).startswith(prefix)]
    l=m[occ]; toks=re.findall(r'-?[\d,]*\.?\d+%?',l['text'][len(prefix):])
    return l,[t for t in toks if t]
def TT(t): v,d=tok_dec(t); return Term(v,d)
for pref,lab_sq in [('Gjithsej të hyrat','Të hyrat'),('Tatimet Direkte','Tatimet direkte'),('Tatimet Indirekte','Tatimet indirekte'),('Rimbursimet tatimore','Rimbursimet'),('Të Hyrat Jo-Tatimore','Jo-tatimore'),('Grante','Grante'),
                    ('Gjithsej Shpenzimet','Shpenzimet'),('Shpenzimet Rrjedhëse','Rrjedhëse'),('Shpenzimet Kapitale','Kapitale'),('Bilanci Buxhetor, sipas kufirit','Bilanci (rregulla fiskale)'),('Stoku i bilancit bankar','Stoku i bilancit bankar'),('BPV 11','BPV')]:
    l,tk=numrow(700,pref if pref!='BPV 11' else 'BPV')
    a,b,d=TT(tk[0]),TT(tk[1]),TT(tk[2])
    X(f'p700_{pref[:10]}','f.700 Tabela 4',f'p.700 Tabela 4 “{pref}”: deviation = LB 2026 − LB 2025',f'f.700 Tabela 4 “{pref}”: devijimi = LB 2026 − LB 2025',d,[Term(b.v,b.dec,'',None,1),Term(a.v,a.dec,'',None,-1)],[700])
l,tk=numrow(700,'Gjithsej të hyrat'); tot=TT(tk[1])
parts=[TT(numrow(700,p_)[1][1]) for p_ in ('Tatimet Direkte','Tatimet Indirekte','Rimbursimet tatimore','Të Hyrat Jo-Tatimore','Grante')]
X('p700_revsum','f.700 Tabela 4','p.700 Tabela 4: LB 2026 revenue = direct + indirect + refunds + non-tax + grants','f.700 Tabela 4: të hyrat LB 2026 = direkte + indirekte + rimbursime + jo-tatimore + grante',tot,parts,[700])
tot0=TT(tk[0]); parts0=[TT(numrow(700,p_)[1][0]) for p_ in ('Tatimet Direkte','Tatimet Indirekte','Rimbursimet tatimore','Të Hyrat Jo-Tatimore','Grante')]
X('p700_revsum25','f.700 Tabela 4','p.700 Tabela 4: LB 2025 projection for 2026, revenue = sum of its lines','f.700 Tabela 4: projeksioni LB 2025 për 2026, të hyrat = shuma e rreshtave',tot0,parts0,[700])
for pref,lab in [('Gjithsej të hyrat','1. GJITHSEJ TË HYRAT BUXHETORE [1]'),('Tatimet Direkte','Tatimet Direkte'),('Tatimet Indirekte','Tatimet Indirekte'),('Rimbursimet tatimore','Rimbursimet tatimore'),('Të Hyrat Jo-Tatimore','1.2 Të Hyrat Jo-Tatimore'),
                 ('Gjithsej Shpenzimet','2. GITHSEJ SHPENZIMET BUXHETORE[1]'),('Shpenzimet Rrjedhëse','2.1 Shpenzimet Rrjedhëse'),('Shpenzimet Kapitale','2.3 Shpenzimet Kapitale'),('Bilanci Buxhetor, sipas kufirit','(3+4)'),('BPV','BPV')]:
    v=TT(numrow(700,pref)[1][1]); t_=T(lab,'y2026'); X(f'p700_t1_{pref[:10]}','f.700 ↔ Tabela 1',f'p.700 “{pref}” LB 2026 vs Tabela 1',f'f.700 “{pref}” LB 2026 kundrejt Tabelës 1',v,[t_],[29,30,700],refs=[t_.ref])
v=TT(numrow(700,'Stoku i bilancit bankar')[1][1]); t_=T('G. Stoku i bilancit bankar në fundvit (BRUTO)','y2026')
X('p700_bankstock','f.700 ↔ Tabela 1','p.700 “Stoku i bilancit bankar të pashpërndarë” vs Tabela 1 gross bank balance (2026)','f.700 “Stoku i bilancit bankar të pashpërndarë” kundrejt bilancit bruto në Tabelën 1 (2026)',v,[t_],[30,700],refs=[t_.ref],
  note_en='The value equals the GROSS balance (G = 475.6) although p.700 calls it the unallocated balance; Table 1 gives the net (unallocated) balance as 359.6.',note_sq='Vlera është e barabartë me bilancin BRUTO (G = 475.6), ndonëse f.700 e quan bilanc të pashpërndarë; Tabela 1 jep bilancin neto (të pashpërndarë) 359.6.')
CHECKS[-1]['status']='fail'; CHECKS[-1]['cls']='error'   # same number, different meaning: a labelling error
CL('p700_debtpct','f.700 ↔ Tabela 1.1','p.700 Tabela 4: debt 22.0% of GDP in LB 2026','f.700 Tabela 4: borxhi 22.0% e BPV në LB 2026',Dm('22.0'),lambda a,b,c,d:(a+b+c)/d*100,[tm11('Stoku i borxhit të brendshëm','y2026'),tm11('Stoku i borxhit të jashtëm','y2026'),tm11('Garancionet shtetërore','y2026'),T('BPV','y2026')],[33,700])
# p.706
for pref in ('GJITHSEJ TË HYRAT BUXHETORE','Të Hyra Tatimore','Tatimet Direkte','Tatimet Indirekte','Të Hyrat Jo-Tatimore','Grantet dhe ndihmat','GJITHSEJ SHPENZIMET','Shpenzimet Rrjedhëse','Investimet Kapitale','Grantet e Përcaktuara të Donatorve','Bilanci buxhetor'):
    l,tk=numrow(706,pref if pref!='GJITHSEJ SHPENZIMET' else 'GJITHSEJ SHPENZIMET')
    a,b,d=TT(tk[0]),TT(tk[1]),TT(tk[2])
    X(f'p706_{pref[:10]}','f.706 KASH',f'p.706 KASH table “{pref}”: deviation = LB 2026 − KASH',f'f.706 KASH “{pref}”: devijimi = LB 2026 − KASH',d,[b,Term(a.v,a.dec,'',None,-1)],[706])
for col,nm_ in ((0,'KASH 2025–2027'),(1,'LB 2026')):
    r_=[TT(numrow(706,p_)[1][col]) for p_ in ('Të Hyra Tatimore','Të Hyrat Jo-Tatimore','Grantet dhe ndihmat')]
    X(f'p706_revsum_{col}','f.706 KASH',f'p.706 {nm_}: revenue = tax + non-tax + grants',f'f.706 {nm_}: të hyrat = tatimore + jo-tatimore + grante',TT(numrow(706,'GJITHSEJ TË HYRAT BUXHETORE')[1][col]),r_,[706])
for pref in ('Konsumi','Investimet','Eksportet','Importet','BPV'):
    ls=[l for l in plines(706) if re.match(rf'^\s*{pref}\s+[\d,]+\s+[\d,]+\s+-?[\d,]+',l['text'])]
    if not ls: continue
    tk=re.findall(r'-?[\d,]+',ls[-1]['text'])
    X(f'p706_mac_{pref}','f.706 KASH',f'p.706 macro table “{pref}”: deviation = LB 2026 − KASH',f'f.706 tabela makro “{pref}”: devijimi = LB 2026 − KASH',TT(tk[2]),[TT(tk[1]),Term(TT(tk[0]).v,0,'',None,-1)],[706])
for col,nm_ in ((0,'KASH'),(1,'LB 2026')):
    g=lambda p_: TT(re.findall(r'-?[\d,]+',[l for l in plines(706) if re.match(rf'^\s*{p_}\s+[\d,]+\s+[\d,]+',l['text'])][-1]['text'])[col])
    X(f'p706_gdpid_{col}','f.706 KASH',f'p.706 {nm_}: GDP = consumption + investment + exports − imports',f'f.706 {nm_}: BPV = konsumi + investimet + eksportet − importet',g('BPV'),[g('Konsumi'),g('Investimet'),g('Eksportet'),Term(g('Importet').v,0,'',None,-1)],[706])
# p.712 Tabela 3 (budget execution Jan–Sep 2025)
rows712=[]
NAMES712=['Gjithsej të hyrat','Të Hyrat Tatimore','Tatimet Direkte','Tatimet Indirekte','Rimbursimet tatimore','Të Hyrat Jo-tatimore','Grantet','Gjithsej shpenzimet','Shpenzimet Rrjedhëse','Shpenzimet Kapitale','Interesi']
for l in plines(712):
    if l['top']>350: break
    tk=re.findall(r'-?[\d,]+(?:\.\d+)?%?',l['text'])
    if len(tk)>=3 and '%' in tk[2] and '.' in tk[0]: rows712.append((NAMES712[len(rows712)],tk,l))
FINDINGS.append(dict(type='note',title='p.712 Tabela 3: five of the eleven rows (total revenue, refunds, total spending, interest and one more) are printed without a row label.',pages=[712],
     title_sq='f.712 Tabela 3: pesë nga njëmbëdhjetë rreshtat (të hyrat totale, rimbursimet, shpenzimet totale, interesi etj.) janë shtypur pa emër rreshti.'))
for lab,tk,l in rows712:
    a,b=TT(tk[0]),TT(tk[1]); p_=Dm(tk[2].rstrip('%'))
    CL(f'p712_{lab[:10]}','f.712 Tabela 3',f'p.712 Tabela 3 “{lab}”: actual / projection = {tk[2]}',f'f.712 Tabela 3 “{lab}”: aktuale / projeksioni = {tk[2]}',p_,lambda x,y:x/y*100,[b,a],[712],dec=1)
names=[r[0] for r in rows712]
def r712(i,col): return TT(rows712[i][1][col])
# rows: 0 total rev,1 tax,2 direct,3 indirect,4 refunds,5 non-tax,6 grants,7 total exp,8 current,9 capital,10 interest
for col,nm_ in ((0,'projection'),(1,'actual')):
    X(f'p712_tax_{col}','f.712 Tabela 3',f'p.712 Tabela 3 ({nm_}): tax = direct + indirect + refunds',f'f.712 Tabela 3 ({nm_}): tatimore = direkte + indirekte + rimbursime',r712(1,col),[r712(2,col),r712(3,col),r712(4,col)],[712])
    X(f'p712_rev_{col}','f.712 Tabela 3',f'p.712 Tabela 3 ({nm_}): revenue = tax + non-tax + grants',f'f.712 Tabela 3 ({nm_}): të hyrat = tatimore + jo-tatimore + grante',r712(0,col),[r712(1,col),r712(5,col),r712(6,col)],[712])
X('p697_nontax','Teksti ↔ tabelat','p.697 text: Jan–Sep 2025 non-tax revenue “260.4 million” vs p.712 Tabela 3','f.697 teksti: të hyrat jo-tatimore jan–sht 2025 “260.4 milionë” kundrejt f.712 Tabela 3',Term(Dm('260.4'),1),[r712(5,1)],[697,712])
for id_,pg,val,i,te,ts in [('p696_rev',696,'2493.1',0,'revenue','të hyrat'),('p696_exp',696,'2256.7',7,'spending','shpenzimet'),('p697_dir',697,'425.8',2,'direct taxes','tatimet direkte'),('p697_ind',697,'1836.5',3,'indirect taxes','tatimet indirekte'),('p697_int',697,'37.8',10,'interest','interesi')]:
    X(id_,'Teksti ↔ tabelat',f'p.{pg} text: Jan–Sep 2025 {te} “{val}” vs p.712',f'f.{pg} teksti: {ts} jan–sht 2025 “{val}” kundrejt f.712',Term(Dm(val),1),[r712(i,1)],[pg,712])
X('p696_surplus','Teksti ↔ tabelat','p.696 text: surplus 236.4 = revenue 2,493.1 − spending 2,256.7','f.696 teksti: suficiti 236.4 = 2,493.1 − 2,256.7',Term(Dm('236.4'),1),[Term(Dm('2493.1'),1),Term(Dm('2256.7'),1,'',None,-1)],[696])
# ---------- risk statement tables ----------
def pct_rows(p,labels):
    out={}; L=plines(p)
    for i,l in enumerate(L):
        for lab in labels:
            if re.sub(r'\s+',' ',l['text']).startswith(lab):
                vals=[Dm(x.rstrip('%')) for x in re.findall(r'[\d.]+%?',l['text'][len(lab):]) if x.strip('.%')]
                j=i
                while not vals and j+1<len(L) and j<i+3:   # label wrapped: the numbers sit on a nearby line
                    j+=1; vals=[Dm(x.rstrip('%')) for x in re.findall(r'\b\d+\.\d\b%?',L[j]['text'])]
                    if len(vals)<3: vals=[]
                if not vals:
                    for k in range(i-1,max(-1,i-3),-1):
                        v2=[Dm(x) for x in re.findall(r'\b\d+\.\d\b',L[k]['text'])]
                        if len(v2)==3 and not re.search(r'[a-zë]{3}',L[k]['text'],re.I): vals=v2; break
                out[lab]=vals
    return out
t5=pct_rows(716,['Borxhi me normë fikse (% e totalit)','Pjesa e borxhit në monedhën vendase (EUR, %','Pjesa e borxhit në valutë (% e totalit)'])
cur=t5['Pjesa e borxhit në monedhën vendase (EUR, %']; fx=t5['Pjesa e borxhit në valutë (% e totalit)']
for i,yy in enumerate(['2022','2023','2024']):
    X(f'p716_cur_{yy}','f.716 Tabela 5',f'p.716 Tabela 5: euro share + foreign-currency share = 100% — {yy}',f'f.716 Tabela 5: pjesa në euro + pjesa në valutë = 100% — {yy}',Term(Dm(100),0),[Term(cur[i],1),Term(fx[i],1)],[716],unit='%',scale=1)
fixed=t5['Borxhi me normë fikse (% e totalit)']
X('p716_float24','Teksti ↔ tabelat','p.716 text: floating-rate debt “8.3%” in 2024 vs 100% − fixed-rate 91.6%','f.716 teksti: borxhi me normë të luhatshme “8.3%” në 2024 kundrejt 100% − 91.6%',Term(Dm('8.3'),1),[Term(Dm(100),0),Term(fixed[2],1,'',None,-1)],[716],unit='%',scale=1,
  note_en='The same paragraph first says “vetëm 8.4% është e luhatshme”.',note_sq='I njëjti paragraf më parë thotë “vetëm 8.4% është e luhatshme”.')
X('p716_float23','Teksti ↔ tabelat','p.716 text: floating-rate debt “5.8%” in 2023 vs 100% − fixed-rate 94.2%','f.716 teksti: borxhi me normë të luhatshme “5.8%” në 2023 kundrejt 100% − 94.2%',Term(Dm('5.8'),1),[Term(Dm(100),0),Term(fixed[1],1,'',None,-1)],[716],unit='%',scale=1)
t6=pct_rows(721,['E ulët','E moderuar','E lartë','Shumë e lartë'])
t6['E ulët']=[Dm(0)]+t6['E ulët']   # 2020 cell is “-”
for i,yy in enumerate(['2020','2021','2022','2023','2024']):
    X(f'p721_{yy}','f.721 Tabela 6',f'p.721 Tabela 6: risk shares of public enterprises add to 100% — {yy}',f'f.721 Tabela 6: pjesët sipas riskut të NP-ve japin 100% — {yy}',Term(Dm(100),0),[Term(t6[k][i],0) for k in ('E ulët','E moderuar','E lartë','Shumë e lartë')],[721],unit='%',scale=1)
l7=[l for l in plines(722) if re.match(r'^\s*(Shumë e ulët|E ulët|E moderuar|E lartë)\s',l['text']) or (re.match(r'^\s*\d+%(\s+\d+%){5}\s*$',l['text']))]
rows7=[[Dm(x.rstrip('%')) for x in re.findall(r'\d+%',l['text'])] for l in l7][:5]
cols7=['Likuiditeti 1','Likuiditeti 2','Solvenca 1','Solvenca 2','Rentabiliteti','Rikuperimi i kostos']
if len(rows7)==5:
    for j in range(6):
        X(f'p722_c{j}','f.722 Tabela 7',f'p.722 Tabela 7: column {j+1} shares add to 100%',f'f.722 Tabela 7: kolona {j+1} jep 100%',Term(Dm(100),0),[Term(r[j],0) for r in rows7],[722],unit='%',scale=1)
t8=[l for l in plines(722) if re.match(r'^\s*(Minierat|Aktivitete të tjera|Transporti|Ujësjellësi)\s',l['text'])]
s24=sum(Dm(re.findall(r'[\d,]+\.\d',l['text'])[-1].replace(',','')) for l in t8)
CL('p722_t8gdp','f.722 Tabela 8','p.722 text: transfers to public enterprises = 0.14% of GDP in 2024','f.722 teksti: transferet te NP = 0.14% e BPV në 2024',Dm('0.14'),lambda a,b:a/1000/b*100,[Term(s24,1),T('BPV','y2024')],[30,722],dec=2)
X('p723_ppp','f.723 Tabela 9','p.723: “operational PPP portfolio 129.4 million” vs the three operational PPPs in Tabela 9','f.723: “portofoli operacional i PPP-ve 129.4 milionë” kundrejt tri PPP-ve operacionale në Tabelën 9',Term(Dm('129.4'),1),[Term(Dm('100.015'),3),Term(Dm('0.8'),3),Term(Dm('12.0'),3)],[723],
  note_en='129.4 = 112.815 + 16.6, i.e. it includes the three-school project that the same page says is still under construction.',note_sq='129.4 = 112.815 + 16.6, pra përfshin projektin e tri shkollave që e njëjta faqe thotë se është ende në ndërtim.')
X('p725_roe','Teksti ↔ tabelat','p.725 text: return on equity “from 14.3%” vs lowest ROE in Tabela 10 (14.2%)','f.725 teksti: kthimi në ekuitet “prej 14.3%” kundrejt më të ulëtit në Tabelën 10 (14.2%)',Term(Dm('14.3'),1),[Term(Dm('14.2'),1)],[724,725],unit='%',scale=1)
X('p715_guar','f.715 ↔ Tabela 1.1','p.715 Tabela 4: state-guarantee portfolio 2025 vs Tabela 1.1 “Garancionet shtetërore” 2025','f.715 Tabela 4: garancionet shtetërore 2025 kundrejt Tabelës 1.1 2025',Term(Dm('3.1'),1),[tm11('Garancionet shtetërore','y2025')],[33,715])
CL('p715_debt24','Teksti ↔ tabelat','p.715 text: debt-to-GDP “16.91%” in 2024 vs Tabela 1.1','f.715 teksti: borxhi ndaj BPV “16.91%” në 2024 kundrejt Tabelës 1.1',Dm('16.91'),lambda a,b,c,d:(a+b+c)/d*100,[tm11('Stoku i borxhit të brendshëm','y2024'),tm11('Stoku i borxhit të jashtëm','y2024'),tm11('Garancionet shtetërore','y2024'),T('BPV','y2024')],[33,715],dec=2)
# ---------- law articles ----------
ann={a['code']:a for a in annex}
RT_law=lambda *a,**k: None
def LAW(id_,title_en,title_sq,expected,actual,pages,cls=None,note_en='',note_sq=''):
    c=check(id_,title_en,expected,actual,pages,kind='law',title_sq=title_sq,group='Ligji ↔ tabelat',note=note_en,note_sq=note_sq,cls=cls)
    return c
LAW('law_rtk','Law art. (p.10): RTK €8,960,000 in “Subvencione dhe Transfere” vs RTK (248) subsidies in Shtojca 1','Neni (f.10): RTK 8,960,000 € në “Subvencione dhe Transfere” kundrejt subvencioneve të RTK (248) në Shtojcën 1',8_960_000,fnum(ann['248']['subs']),[10,96])
sub11301=[n for n in NODES.values() if n.get('kind')=='subprogramme' and n.get('code')=='11301'][0]
c=LAW('law_11301','Law art. (p.15): €3,000,000 budgeted in sub-programme 11301 “Administrata Qendrore” (MFPT)','Neni (f.15): 3,000,000 € në nënprogramin 11301 “Administrata Qendrore” (MFPT)',3_000_000,sub11301['cats'].get('subs',0),[15,44],
      note_en=f'Code 11301 exists in MFPT with €{sub11301["cats"].get("subs",0):,.0f} in subsidies, but Tabela 3.1 names it “{sub11301["name_sq"]}”, not “Administrata Qendrore”. The €3,000,000 is not a separate line.',
      note_sq=f'Kodi 11301 ekziston te MFPT me €{sub11301["cats"].get("subs",0):,.0f} subvencione, por Tabela 3.1 e quan “{sub11301["name_sq"]}”, jo “Administrata Qendrore”. Shuma 3,000,000 € nuk është rresht më vete.')
c['cls']='error'
me=NODES['org:213']
c=LAW('law_me','Law art. (p.9): €5,289,720 in Ministry of Economy “Subvencione dhe Transfere” for capital projects in public enterprises','Neni (f.9): 5,289,720 € në “Subvencione dhe Transfere” të Ministrisë së Ekonomisë për projekte kapitale në NP',5_289_720,0,[9,50],
      note_en=f'No line or combination of lines in the Ministry of Economy budget (subsidies €{me["cats"].get("subs",0):,.0f}) equals €5,289,720, so the amount cannot be traced to the tables.',
      note_sq=f'Asnjë rresht apo kombinim rreshtash në buxhetin e Ministrisë së Ekonomisë (subvencione €{me["cats"].get("subs",0):,.0f}) nuk jep 5,289,720 €, ndaj shuma nuk mund të gjurmohet në tabela.')
c['cls']='error'; c['kind']='law-untraceable'
LAW('law_liq','Law art. 19 (p.21): €46,000,000 emergency-liquidity reserve vs Tabela 1.1 “Fondi për Likuiditet Emergjent” (2026)','Neni 19 (f.21): 46,000,000 € rezervë likuiditeti kundrejt Tabelës 1.1 (2026)',46_000_000,fnum(T11['Nga te cilat: Fondi për Likuiditet Emergjent']['y2026'])*M,[21,32])
for code_,org_,name_,page_ in [('18782','221','Programi për Zhvillim Rajonal',14),('10041','205','Programi i bashkëfinancimit me kuvendin komunal',14),('12688','207','Masat Preventive, intervenime emergjente',15)]:
    found=[n for n in pr if n.get('code')==code_ and n.get('org')==org_]
    LAW(f'law_proj_{code_}',f'Law art. (p.{page_}): project {code_} “{name_}” exists under institution {org_}',f'Neni (f.{page_}): projekti {code_} “{name_}” ekziston te institucioni {org_}',1,len(found[:1]),[page_,97])
found=[n for n in pr if n.get('org')=='212' and 'Programi komunal' in n.get('name_sq','')]
LAW('law_proj_212','Law art. (p.14): MAPL (212) project “Programi komunal për zhvillim të infrastrukturës socio-ekonomike …” exists','Neni (f.14): projekti i MAPL (212) “Programi komunal për zhvillim …” ekziston',1,len(found[:1]),[14,172])
s341=[n for n in NODES.values() if n.get('code')=='34100' and n.get('kind')=='subprogramme']
LAW('law_34100','Law art. (p.14): MFPT sub-programme 34100 “Marrëveshjet me trupat e OKB” exists with subsidies','Neni (f.14): nënprogrami 34100 i MFPT ekziston me subvencione',1,1 if s341 and s341[0]['cats'].get('subs') else 0,[14,47])
CL('law_rule','Ligji ↔ tabelat','Law art. 33 (p.26): fiscal-rule deficit must not exceed 2% of GDP — 2026 fiscal-rule balance','Neni 33 (f.26): deficiti sipas rregullës fiskale ≤ 2% e BPV — 2026',Dm('1.9'),lambda a,b:-a/b*100,[T('(3+4)','y2026'),T('BPV','y2026')],[26,30])
# ---------- p.210 municipal balance, every year ----------
X210={}
for r in m210:
    nums=json.loads(r['nums']); xs=[313,397,482,569,657]
    vals={}
    for t_,x in nums:
        j=min(range(5),key=lambda i:abs(xs[i]-x))
        if abs(xs[j]-x)<20: vals[j]=t_
    X210[r['label'].split(' ')[0]]=(r,vals)
KY=['2024','2025','2026','2027','2028']
def k210(code,j,sign=1):
    r,vals=X210[code]; t_=vals.get(j)
    return Term(Dm(0),0,code,None,sign) if t_ is None else Term(tok_dec(t_)[0],0,code,None,sign)
for j,yy in enumerate(KY):
    X(f'k210_src_{yy}','f.210 Komunat',f'p.210: sources = grants + own revenue + investment clause + borrowing — {yy}',f'f.210: burimet = grante + vetanake + klauzolë + huamarrje — {yy}',k210('1',j),[k210('1.1',j),k210('1.2',j),k210('1.3',j),k210('1.4',j)],[210],unit='EUR',scale=1)
    X(f'k210_str_{yy}','f.210 Komunat',f'p.210: spending structure = current + capital + clause/borrowing + reserve — {yy}',f'f.210: struktura = rrjedhëse + kapitale + klauzolë/huamarrje + rezervë — {yy}',k210('2',j),[k210('2.1',j),k210('2.2',j),k210('2.3',j),k210('2.4',j)],[210],unit='EUR',scale=1)
    X(f'k210_cur_{yy}','f.210 Komunat',f'p.210: current spending = wages + goods + utilities + subsidies — {yy}',f'f.210: rrjedhëse = paga + mallra + komunale + subvencione — {yy}',k210('2.1',j),[k210('2.1.1',j),k210('2.1.2',j),k210('2.1.3',j),k210('2.1.4',j)],[210],unit='EUR',scale=1)
    X(f'k210_bal_{yy}','f.210 Komunat',f'p.210: balance = sources − (current + capital + clause + reserve) — {yy}',f'f.210: bilanci = burimet − (rrjedhëse + kapitale + klauzolë + rezervë) — {yy}',k210('3',j),[k210('1',j),k210('2.1',j,-1),k210('2.2',j,-1),k210('2.3',j,-1),k210('2.4',j,-1)],[210],unit='EUR',scale=1)
for j,yy,col in [(3,'2027','y2027'),(4,'2028','y2028')]:
    tot=sum(n['y2027' if yy=='2027' else 'y2028'] or 0 for n in NODES.values() if n.get('kind')=='municipality')
    X(f'k210_41_{yy}','f.210 ↔ Tabela 4.1',f'p.210 sources {yy} vs sum of municipal estimates in Tabela 4.1',f'f.210 burimet {yy} kundrejt shumës së vlerësimeve komunale në Tabelën 4.1',k210('1',j),[Term(Dm(str(round(tot))),0)],[210,355],unit='EUR',scale=1)
    X(f'p701_k210_{yy}','f.701 ↔ f.210',f'p.701 local total {yy} vs p.210 sources {yy}',f'f.701 totali lokal {yy} kundrejt f.210 burimet {yy}',Term(Dm(str(l25['v'][j-1]))*M,0),[k210('1',j)],[210,701],unit='EUR',scale=1)
    CHECKS[-1]['kind']='rounds'; ok=rounds_to(k210('1',j).v/Dm(M),Term(Dm(str(l25['v'][j-1])),1)); CHECKS[-1]['status']='pass' if ok else 'fail'; CHECKS[-1]['cls']=None if ok else 'error'
# ---------- Tabela 4.3, every municipality, every year ----------
TAKS=('Licencat dhe lejet','Certifikatat dhe dokumentet zyrtare','Taksat e pajisjeve motorike','Lejet per ndertesa','Taksat tjera komunale','Taksat për Mbeturinat')
NGAR=('Ngarkesat rregullatore','Te hyrat nga qiraja','Bashke-pagesat per arsim','Bashke-pagesat per shendetesi','Ngarkesat tjera komunale')
OWN=('Tatimi në tokë','Tatimi në pronë','Taksat Komunale','Ngarkesat Komunale','Te hyrat tjera','Shitja e aseteve')
TRF=('Granti i Përgjithshëm','Granti për Arsim','Granti për Shëndetësi','Financimi për Shërbime Rezidenciale','Granti specifik për Kulturë','Financimi për Obiliqin','Financimi për Shëndetesi Sekondare','Financimi për Teatrot','Financimi për QHP, QKHFZ dhe KHM','Granti shtesë për Kryeqytetin-Prishtinën')
by=collections.defaultdict(list)
for r in rev:
    if r['code'] and r['label'].strip() not in ('Buxheti i','19 February 2026',''): by[r['code']].append(r)
Y43=['y2024','y2025','y2026','y2027','y2028']
bad43=[]
sums=collections.defaultdict(lambda: collections.defaultdict(Dm))
for code,rows in by.items():
    first={}
    for r in rows: first.setdefault(r['label'].strip(),r)
    def g(lab,y):
        r=first.get(lab); 
        if not r or r.get(y) in ('',None): return Dm(0)
        return Dm(str(int(round(fnum(r[y])))))
    nm_=rows[0]['muni']; pg=int(rows[0]['page'])
    if code!='TOTAL':
        for lab in set(first): 
            for y in Y43: sums[lab][y]+=g(lab,y)
    for y in Y43:
        rels=[('Taksat Komunale',TAKS),('Ngarkesat Komunale',NGAR),('Të Hyrat Vetanake',OWN),('Transferet Qeveritare',TRF)]
        for lab,parts in rels:
            if lab not in first: continue
            d=sum(g(p_,y) for p_ in parts)-g(lab,y)
            if d: bad43.append((code,nm_,lab,y,g(lab,y),d,pg))
        d=g('Të Hyrat Vetanake',y)+g('Transferet Qeveritare',y)+g('Financimi nga Huamarrja',y)-g('Të Hyrat Komunale Totale',y)
        if d: bad43.append((code,nm_,'Të Hyrat Komunale Totale',y,g('Të Hyrat Komunale Totale',y),d,pg))
for code,nm_,lab,y,v,d,pg in bad43:
    FINDINGS.append(dict(type='mismatch',title=f'Tabela 4.3 {nm_}: “{lab}” ≠ sum of its lines — {y[1:]}',title_sq=f'Tabela 4.3 {nm_}: “{lab}” ≠ shuma e rreshtave — {y[1:]}',
                         expected=float(v),actual=float(v+d),diff=float(d),pages=[pg],cls='rounding' if abs(d)<=Dm('0.5')*10 else 'error'))
check('t43_all','Tabela 4.3: every subtotal and total adds up, every municipality, 2024–2028',0,len(bad43),list(range(647,672)),title_sq='Tabela 4.3: çdo nëntotal dhe total mblidhet saktë, çdo komunë, 2024–2028',kind='count',
      group='Tabela 4.3',cls='error' if any(abs(x[5])>5 for x in bad43) else ('rounding' if bad43 else None))
CHECKS[-1]['title_sq']='Tabela 4.3: çdo nëntotal dhe total mblidhet saktë, çdo komunë, 2024–2028'; CHECKS[-1]['title']='Tabela 4.3: every subtotal and total adds up, every municipality, 2024–2028'
tot_rows={r['label'].strip():r for r in by['TOTAL']}
badsum=[]
for lab,r in tot_rows.items():
    for y in Y43:
        if r.get(y) in ('',None): continue
        d=sums[lab][y]-Dm(str(int(round(fnum(r[y])))))
        if d: badsum.append((lab,y,fnum(r[y]),d))
for lab,y,v,d in badsum:
    FINDINGS.append(dict(type='mismatch',title=f'Tabela 4.3 summary (p.671) “{lab}” {y[1:]} ≠ sum of the 38 municipalities',title_sq=f'Përmbledhja e Tabelës 4.3 (f.671) “{lab}” {y[1:]} ≠ shuma e 38 komunave',expected=v,actual=v+float(d),diff=float(d),pages=[671],cls='rounding' if abs(d)<=19 else 'error'))
check('t43_summary','Tabela 4.3 summary (p.671): every line and year = sum of the 38 municipalities',0,len(badsum),[671],title_sq='Përmbledhja e Tabelës 4.3 (f.671): çdo rresht dhe vit = shuma e 38 komunave',kind='count',group='Tabela 4.3',
      cls='error' if any(abs(x[3])>19 for x in badsum) else ('rounding' if badsum else None))
CHECKS[-1]['title']='Tabela 4.3 summary (p.671): every line and year = sum of the 38 municipalities'
# 4.3 totals 2027/2028 vs Tabela 4.1 estimates per municipality
bad=[]
for code,rows in by.items():
    if code=='TOTAL': continue
    n=NODES.get('mun:'+code); t_=[r for r in rows if r['label'].strip()=='Të Hyrat Komunale Totale']
    if not n or not t_: continue
    for y in ('y2027','y2028'):
        d=round(fnum(t_[0][y]))-round(n.get(y) or 0)
        if d: bad.append(1); FINDINGS.append(dict(type='mismatch',title=f'Tabela 4.3 revenue {y[1:]} vs Tabela 4.1 estimate {y[1:]}: {n["name_sq"]}',title_sq=f'Të hyrat në Tabelën 4.3 {y[1:]} kundrejt vlerësimit në Tabelën 4.1 {y[1:]}: {n["name_sq"]}',
                                                 expected=n.get(y) or 0,actual=fnum(t_[0][y]),diff=d,pages=[int(t_[0]['page'])],cls='rounding' if abs(d)<=1 else 'error'))
check('t43_41_est','Tabela 4.3 revenue 2027/2028 = Tabela 4.1 estimates, per municipality',0,len(bad),[647,214],title_sq='Të hyrat e Tabelës 4.3 2027/2028 = vlerësimet e Tabelës 4.1, për komunë',kind='count',group='Tabela 4.3')
# ---------- municipal summary pp.211–213: every category, fund and year ----------
bad=[]
for r in ms:
    if r['aggregate']=='True' or r['fund']!='Total': continue
    code=[c for c,v in MUNI_NAME.items() if v==name_alias.get(r['muni'],r['muni'])]
    if not code: continue
    n=NODES['mun:'+code[0]]; o=[x for x in orgs41 if x['code']==code[0]][0]
    for k in ['staff','wages','goods','util','subs','capital','reserve','y2027','y2028']:
        tbl=(o.get(k) or 0)+(n['sources'].get('fhki',{}).get('cats',{}).get(k,0) if k=='capital' else 0)
        d=fnum(r.get(k))-tbl
        if d: bad.append(1); FINDINGS.append(dict(type='mismatch',title=f'Municipal summary (p.{r["page"]}) “{k}” vs Tabela 4.1: {r["muni"]}',title_sq=f'Përmbledhja komunale (f.{r["page"]}) “{k}” kundrejt Tabelës 4.1: {r["muni"]}',expected=tbl,actual=fnum(r.get(k)),diff=d,pages=[int(r['page'])],cls='rounding' if abs(d)<=1 else 'error'))
check('ks_cats','Municipal summary pp.211–213: every category, staff and 2027/2028 figure = Tabela 4.1',0,len(bad),[211,212,213],title_sq='Përmbledhja komunale f.211–213: çdo kategori, staf dhe vlerësim 2027/2028 = Tabela 4.1',kind='count',group='Komunat')
# ---------- Shtojca 1, every column incl. 2027/2028 ----------
CA2=[('staff',194),('wages',233),('goods',267),('util',303),('subs',354),('capital',409),('reserve',441),('total',488),('op27',535),('cap27',573),('t27',615),('op28',655),('cap28',695),('t28',744)]
bad=[]
for l in plm(96):
    ws=l['words']; code=[w for w in ws if re.fullmatch(r'\d{3}',w['text']) and w['x1']<60]
    g=[]
    for w in ws:
        if g and re.fullmatch(r'\d',g[-1]['text']) and re.fullmatch(r'\d',w['text']) and 185<g[-1]['x1']<196 and 185<w['x1']<196: g[-1]['text']+=w['text']; g[-1]['x1']=w['x1']
        else: g.append(w)
    vals={}
    for w in g:
        if not pisnum(w['text']) or w['x1']<150: continue
        c_=min(CA2,key=lambda c:abs(c[1]-w['x1']))
        if abs(c_[1]-w['x1'])<=12: vals[c_[0]]=Dm(w['text'].replace(',',''))
    if not vals or 'total' not in vals: continue
    is_tot='Totali' in l['text']
    lab=code[0]['text'] if code else ('TOTAL' if is_tot else None)
    if not lab: continue
    def v_(k): return vals.get(k,Dm(0))
    for nm_,lhs,parts in [('2026 categories',v_('total'),[v_(k) for k in ('wages','goods','util','subs','capital','reserve')]),('2027 operating + capital',v_('t27'),[v_('op27'),v_('cap27')]),('2028 operating + capital',v_('t28'),[v_('op28'),v_('cap28')])]:
        d=sum(parts)-lhs
        if d: bad.append(1); FINDINGS.append(dict(type='mismatch',title=f'Shtojca 1 {lab}: {nm_} ≠ total',title_sq=f'Shtojca 1 {lab}: {"kategoritë 2026" if "2026" in nm_ else ("operative + kapitale " + nm_[:4])} ≠ totali',expected=float(lhs),actual=float(lhs+d),diff=float(d),pages=[96],cls='rounding' if abs(d)<=3 else 'error'))
    if lab=='TOTAL':
        for k,col in (('t27','y2027'),('t28','y2028')):
            tt=Dm(str(int(round(fnum(tt31[col])))))+0   # Tabela 3.1 printed totals for 2027/2028 (3.1.B has none)
            d=v_(k)-tt
            if d: bad.append(1); FINDINGS.append(dict(type='mismatch',title=f'Shtojca 1 grand total {col[1:]} vs Tabela 3.1 printed total {col[1:]}',title_sq=f'Totali i Shtojcës 1 {col[1:]} kundrejt totalit të shtypur të Tabelës 3.1 {col[1:]}',expected=float(tt),actual=float(v_(k)),diff=float(d),pages=[93,96],cls='error'))
        for k,col in (('cap27','y2027'),('cap28','y2028')):
            ps=sum(n['multi'][col] for n in pr if n['table']=='Tabela 3.2')
            d=v_(k)-Dm(str(int(round(ps))))
            if d: bad.append(1); FINDINGS.append(dict(type='mismatch',title=f'Shtojca 1 capital {col[1:]} vs Tabela 3.2 projects {col[1:]}',title_sq=f'Kapitalet e Shtojcës 1 {col[1:]} kundrejt projekteve të Tabelës 3.2 {col[1:]}',expected=ps,actual=float(v_(k)),diff=float(d),pages=[96,203],cls='error'))
        continue
    n=NODES.get('org:'+lab)
    if not n: continue
    o=[x for x in orgs31 if x['code']==lab][0]; ob=[x for x in orgs31b if x['code']==lab]
    for k in ('staff','wages','goods','util','subs','capital','reserve'):
        tbl=Dm(str(int(round((o.get(k) or 0)+(ob[0].get(k) or 0 if ob else 0)))))
        d=v_(k)-tbl
        if d: bad.append(1); FINDINGS.append(dict(type='mismatch',title=f'Shtojca 1 vs Tabela 3.1+3.1.B “{k}”: {n["name_sq"]}',title_sq=f'Shtojca 1 kundrejt Tabelës 3.1+3.1.B “{k}”: {n["name_sq"]}',expected=float(tbl),actual=float(v_(k)),diff=float(d),pages=[96,int(o['page'])],cls='rounding' if abs(d)<=1 else 'error'))
    for k,col in (('t27','y2027'),('t28','y2028')):
        tbl=Dm(str(int(round((o.get(col) or 0)+(ob[0].get(col) or 0 if ob else 0)))))
        d=v_(k)-tbl
        if d: bad.append(1); FINDINGS.append(dict(type='mismatch',title=f'Shtojca 1 vs Tabela 3.1 estimate {col[1:]}: {n["name_sq"]}',title_sq=f'Shtojca 1 kundrejt vlerësimit {col[1:]} në Tabelën 3.1: {n["name_sq"]}',expected=float(tbl),actual=float(v_(k)),diff=float(d),pages=[96,int(o['page'])],cls='rounding' if abs(d)<=1 else 'error'))
check('a1_all','Shtojca 1: every column of every institution (staff, categories, 2027, 2028) = Tabela 3.1 + 3.1.B, and its own totals add up',0,len(bad),[96],title_sq='Shtojca 1: çdo kolonë e çdo institucioni (stafi, kategoritë, 2027, 2028) = Tabela 3.1 + 3.1.B, dhe totalet e veta mblidhen',kind='count',group='Shtojca 1')
# ---------- every subtotal row of the capital-project tables ----------
PC8=['spent_to_2025','cont_2026','new_2026','total_2026','y2027','y2028','y2029plus','project_total']
def fold_(s): return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFD',s.lower()).encode('ascii','ignore').decode())
import unicodedata
badsub=[]; nsub=0
for f_,table in (('t3_2','Tabela 3.2'),('t3_2B','Tabela 3.2.B'),('t4_2','Tabela 4.2'),('t4_2B','Tabela 4.2.B')):
    rows=rd(f_+'.csv'); srcrows=[]; nxt='sub'; seen_here=False
    SRCMAP={'GQ':'GQ','THV':'THV','FH':'FH','FHKI':'FHKI','THD':'THD','THAKP':'THAKP','Te Hyrat Vetanake':'THV','Të Hyrat Vetanake':'THV','Financimi nga Huamarrja':'FH','Grantet Qeveritare':'GQ','FH Klauzolës se Investimeve':'FHKI'}
    ORDER=['sub','prog','org','all']
    for r in rows:
        if r['kind']=='source': srcrows.append((r['org'],r['prog'],r['sub'],r['source'],{k:fnum(r[k]) for k in PC8}))
        if r['kind'] in ('project','source'): nxt='sub'; seen_here=False; continue
        if r['kind']!='subtotal': continue
        nm=re.sub(r'\s+',' ',r['name'])
        m=re.match(r'Totali\s*(?:\(\s*([^)]*?)\s*\))?\s*(?:-\s*(.*))?$',nm)
        srcname=(m.group(1) or '').strip() if m else ''; target=(m.group(2) or '').strip() if m else ''
        src=SRCMAP.get(srcname, srcname)
        level='all' if not target else nxt
        if target:   # an exact name match with a header wins over position; a prefix match only when this level has no subtotal yet
            tf=fold_(target); hit=None
            hdrs=(('sub',r['sub']),('prog',r['prog']),('org',r['org']))
            for lv,hdr in hdrs:
                hn=fold_(hdr.split(' - ',1)[1]) if ' - ' in hdr else ''
                if hn and tf==hn: hit=lv; break
            if hit is None and not seen_here:
                for lv,hdr in hdrs:
                    hn=fold_(hdr.split(' - ',1)[1]) if ' - ' in hdr else ''
                    if hn and len(tf)>=10 and (hn.startswith(tf) or tf.startswith(hn)): hit=lv; break
            for lv in ([hit] if hit else []):
                if True:
                    if ORDER.index(lv)>ORDER.index(nxt) and nxt=='sub' and not seen_here:
                        FINDINGS.append(dict(type='ambiguity',title=f'{table} p.{r["page"]}: sub-programme “{r["sub"]}” has no subtotal rows; the table goes straight to “{nm[:60]}”',
                            title_sq=f'{table} f.{r["page"]}: nënprogrami “{r["sub"]}” nuk ka rreshta nëntotali; tabela kalon direkt te “{nm[:60]}”',pages=[int(r['page'])]))
                    level=lv; break
        key={'all':lambda x:True,'org':lambda x:x[0]==r['org'],'prog':lambda x:x[0]==r['org'] and x[1]==r['prog'],'sub':lambda x:x[0]==r['org'] and x[1]==r['prog'] and x[2]==r['sub']}[level]
        sel=[x for x in srcrows if key(x) and (not src or x[3]==src)]
        nsub+=1
        for k in PC8:
            sv=round(sum(x[4][k] for x in sel)); v=round(fnum(r[k]))
            if sv!=v:
                d=sv-v; badsub.append(1)
                FINDINGS.append(dict(type='mismatch',title=f'{table} p.{r["page"]}: “{nm[:80]}” {k} ≠ sum of its projects',title_sq=f'{table} f.{r["page"]}: “{nm[:80]}” {k} ≠ shuma e projekteve',expected=v,actual=sv,diff=d,pages=[int(r['page'])],cls='rounding' if abs(d)<=len(sel)*0.5 else 'error'))
        seen_here=True
        if not src and target: nxt=ORDER[min(ORDER.index(level)+1,3)]; seen_here=False   # a plain “Totali - X” closes this level
check('proj_subtotals',f'Capital-project tables: every subtotal row (sub-programme, programme, institution, table) = sum of its projects, all 8 columns',0,len(badsub),[97,204,357,646],title_sq=f'Tabelat e projekteve: çdo rresht nëntotali (nënprogram, program, institucion, tabelë) = shuma e projekteve, të 8 kolonat',kind='count',group='Projektet',
      note=f'{nsub} subtotal rows × 8 columns checked',note_sq=f'{nsub} rreshta nëntotalesh × 8 kolona të kontrolluara')
# ---------- labels for count checks from their findings ----------
for c in CHECKS:
    if c['kind']=='count' and c['status']=='fail' and not c.get('cls'): c['cls']='error'
for f in FINDINGS:
    if f.get('diff') is not None and not f.get('cls'): f['cls']='error'
# ---------- explanatory notes on specific failures ----------
NOTES={
 't1_exp_y2023':('In 2023 the printed total (2,876.6) equals current + interest + capital only; it leaves out line 2.4 donor grants (11.9), which every other year includes.',
                 'Në 2023 totali i shtypur (2,876.6) = rrjedhëse + interes + kapitale; nuk përfshin rreshtin 2.4 grantet e donatorëve (11.9), që përfshihet në çdo vit tjetër.'),
 't1_Estock_y2024':('The net bank balance does not follow from the printed yearly change: 218.5 + 38.7 = 257.2, but 307.9 is printed for 2024.',
                    'Bilanci bankar neto nuk rrjedh nga ndryshimi vjetor i shtypur: 218.5 + 38.7 = 257.2, por për 2024 shtypet 307.9.'),
 't11_net_y2024':('Same break as in Tabela 1: 218.5 + 38.7 = 257.2, printed 307.9.','I njëjti ndërprerje si në Tabelën 1: 218.5 + 38.7 = 257.2, e shtypur 307.9.'),
 'k210_str_2026':('The printed structure total equals sources (867,648,415) but its lines add to 867,467,120; the gap is the printed “Bilanci” 181,295.',
                  'Totali i strukturës së shtypur = burimet (867,648,415), por rreshtat mblidhen në 867,467,120; diferenca është “Bilanci” 181,295.'),
}
for c in CHECKS:
    if c['id'] in NOTES: c['note'],c['note_sq']=NOTES[c['id']]
# ---------- consistent labelling ----------
# 1) individual rows: sums of n printed whole-euro lines may drift by up to n×0.5 through rounding; two prints of the same figure may not
for f in FINDINGS:
    t=f.get('title','')
    if f.get('diff') is None: continue
    if 'project column 8' in t: f['cls']='rounding' if abs(f['diff'])<=2.5 else 'error'
    elif 'project column 4' in t: f['cls']='rounding' if abs(f['diff'])<=1.5 else 'error'
    elif t.startswith('Capital projects ('): f['cls']='rounding' if abs(f['diff'])<=0.5*60 else 'error'
# 2) checks that compare a sum of many printed lines with a printed total get the matching rounding bound
BOUNDS={'t31_total':0.5*50,'t41_total':0.5*38,'cen_diff':0.5*50,'ks_ab':0.5*38,'t43_total':0.5*38,'t42_t41':0.5*2044,'t32_t31':0.5*908}
for c in CHECKS:
    if c['id'] in BOUNDS and c['status']=='fail':
        c['bound']=BOUNDS[c['id']]; c['cls']='rounding' if abs(c['diff'])<=c['bound'] else 'error'
# 3) a summary check takes the worst label of the rows it summarises
SUMMARY={'t31_rows':lambda t:t.startswith('Tabela 3.1 '),'t41_rows':lambda t:t.startswith('Tabela 4.1 '),'a1_rows':lambda t:t.startswith('Shtojca 1 vs Tabela 3.1+3.1.B:'),
         'ks_rows':lambda t:t.startswith('Municipal summary (p.') and '“' not in t,'t43_rows':lambda t:t.startswith('Tabela 4.3 revenue vs Tabela 4.1 spending'),
         't42_bymun':lambda t:t.startswith('Capital projects (4.2)'),'t32_byorg':lambda t:t.startswith('Capital projects (3.2)'),'proj_cols':lambda t:'project column' in t,
         't43_internal':lambda t:t.startswith('Tabela 4.3 ') and (': own-source' in t),'t43_all':lambda t:t.startswith('Tabela 4.3 ') and '≠ sum of its lines' in t,
         't43_summary':lambda t:t.startswith('Tabela 4.3 summary (p.671)'),'t43_41_est':lambda t:t.startswith('Tabela 4.3 revenue 20'),'ks_cats':lambda t:t.startswith('Municipal summary (p.') and '“' in t,
         'a1_all':lambda t:t.startswith('Shtojca 1 '),'proj_subtotals':lambda t:'sum of its projects' in t}
for c in CHECKS:
    if c['id'] in SUMMARY and c['status']=='fail':
        rows=[f for f in FINDINGS if f.get('diff') is not None and SUMMARY[c['id']](f.get('title',''))]
        c['cls']='error' if any(f.get('cls')=='error' for f in rows) or not rows else 'rounding'
        c['rows']=len(rows); c['rows_error']=sum(1 for f in rows if f.get('cls')=='error')
