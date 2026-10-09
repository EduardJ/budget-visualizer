"""Albanian text for checks and findings. Every check and finding must get an Albanian title;
an unmatched finding stops the build so nothing ships English-only."""
import re
CAT_SQ={'y2027':'vlerësimi 2027','y2028':'vlerësimi 2028','wages':'paga dhe shtesa','goods':'mallra dhe shërbime','util':'shpenzime komunale','subs':'subvencione dhe transfere','capital':'investime kapitale','reserve':'rezerva','total':'totali','staff':'stafi'}
CAT_EN={'y2027':'2027 estimate','y2028':'2028 estimate','wages':'wages','goods':'goods and services','util':'utilities','subs':'subsidies and transfers','capital':'capital','reserve':'reserves','total':'total','staff':'staff'}
CHECK_SQ={
't1_tax':'Të hyrat tatimore = direkte + indirekte + rimbursimet (Tabela 1)','t1_direct':'Tatimet direkte = korporatat + të ardhurat personale + prona + të tjera',
't1_indirect':'Tatimet indirekte = TVSH + dogana + akciza + të tjera','t1_vat':'TVSH = vendore + kufitare',
't1_nontax':'Të hyrat jo-tatimore = taksat + koncesionet + renta minerare + telefonia + dividendat + interesi','t1_fees':'Taksat dhe ngarkesat = niveli qendror + niveli lokal',
't1_grants':'Grantet = mbështetje buxhetore + grante të donatorëve','t1_rev':'Të hyrat totale = tatimore + jo-tatimore + grantet',
't1_cur':'Shpenzimet rrjedhëse = paga + mallra + subvencione + rezerva','t1_cap':'Shpenzimet kapitale = buxheti i rregullt + klauzola e investimeve',
't1_exp':'Shpenzimet totale = rrjedhëse + interesi + kapitale + grantet e donatorëve','t1_bal':'Bilanci = të hyrat − shpenzimet',
't1_fin':'Ndryshimi në bilancin bankar = nevoja për financim + financimi i jashtëm neto + i brendshëm neto',
't11_ext':'Financimi i jashtëm neto = pranimet − daljet (Tabela 1.1)','t11_extin':'Pranimet e jashtme = mbështetja buxhetore + nën-huazimet + projekt-kreditë',
't11_projl':'Projekt-kreditë = fondi 04 + fondi 06','t11_dom':'Financimi i brendshëm neto = pranimet − daljet','t11_domin':'Pranimet e brendshme = shuma e rreshtave',
't11_domout':'Daljet e brendshme = shuma e rreshtave','t1_t11':'Financimi i jashtëm neto: Tabela 1 = Tabela 1.1',
'pool':'Të gjitha hyrjet = të gjitha përdorimet (të hyrat + huamarrja bruto = shpenzimet + kthimi i borxhit + daljet financiare + kursimi)',
't2_Central_cats':'Tabela 2 niveli qendror: kategoritë = totali','t2_Local_cats':'Tabela 2 niveli lokal: kategoritë = totali',
't2_central':'Tabela 2: niveli qendror = 3.1 + 3.1.B','t2_local':'Tabela 2: niveli lokal = 4.1 + 4.1.B','t2_grand':'Tabela 2: totali = qendror + lokal + interesi',
't2_vs_t1':'Totali i Tabelës 2 kundrejt shpenzimeve totale në Tabelën 1','t2_vs_t1_donor':'Totali i Tabelës 2 + grantet e donatorëve = shpenzimet totale në Tabelën 1',
't2_t1_goods':'Tabela 2 mallra + shpenzime komunale kundrejt Tabelës 1 “Mallra dhe Shërbime”','t2_t1_int':'Tabela 2 interesi kundrejt Tabelës 1',
't31_total':'Tabela 3.1: shuma e 50 institucioneve kundrejt “Total” të shtypur','t31_t2':'Totali i shtypur i Tabelës 3.1 kundrejt rreshtit 3.1 në Tabelën 2',
't31_rows':'Tabela 3.1: për çdo rresht kategoritë = totali, burimet = totali, nënrreshtat = prindi','t31b_t2':'Totali i Tabelës 3.1.B kundrejt rreshtit 3.1.B në Tabelën 2',
'a1_total':'Totali i Shtojcës 1 kundrejt nivelit qendror në Tabelën 2','a1_wages':'Pagat në Shtojcën 1 kundrejt pagave të nivelit qendror në Tabelën 2',
'a1_rows':'Shtojca 1: totali i çdo institucioni = Tabela 3.1 + 3.1.B','t41_total':'Tabela 4.1: shuma e 38 komunave kundrejt totalit të shtypur',
't41_rows':'Tabela 4.1: çdo rresht përputhet (kategoritë, burimet, nënrreshtat)','t2_local_vs_41':'Niveli lokal në Tabelën 2 kundrejt Tabelave 4.1 + 4.1.B (shuma e planeve komunale)',
'ks_rows':'Përmbledhja komunale f.211–213: çdo komunë = Tabela 4.1 + 4.1.B','ks_ab':'Përmbledhja komunale A+B kundrejt Tabelave 4.1 + 4.1.B',
'ks_bil':'Përmbledhja komunale: A+B + “Bilanci” = niveli lokal në Tabelën 2','k1_sources':'Bilanci komunal f.210: burimet totale = niveli lokal në Tabelën 2',
'k1_struct':'Bilanci komunal f.210: struktura + bilanci = burimet','k1_lines':'Bilanci komunal f.210: rreshtat + “Bilanci” = burimet',
't43_total':'Përmbledhja e Tabelës 4.3 (f.671) kundrejt planeve komunale (4.1 + 4.1.B)','t43_vs_k1':'Përmbledhja e Tabelës 4.3 kundrejt “Burimet e financimit” në f.210',
't43_internal':'Tabela 4.3: të hyrat vetanake mblidhen saktë, dhe vetanake + transfere + huamarrje = totali (për komunë)',
't43_rows':'Tabela 4.3: të hyrat e çdo komune = plani i shpenzimeve (4.1 + 4.1.B)','t32_t31':'Projektet e Tabelës 3.2 (2026) kundrejt investimeve kapitale në Tabelën 3.1',
't32b_t31b':'Projektet e Tabelës 3.2.B kundrejt totalit të Tabelës 3.1.B','t42_t41':'Projektet e Tabelës 4.2 (2026) kundrejt investimeve kapitale në Tabelën 4.1',
't42b_t41b':'Projektet e Tabelës 4.2.B kundrejt Tabelës 4.1.B','t32_byorg':'Projektet e Tabelës 3.2 për institucion = investimet kapitale në Tabelën 3.1',
't42_bymun':'Projektet e Tabelës 4.2 për komunë = investimet kapitale në Tabelën 4.1','proj_cols':'Çdo projekt: kolona 4 = 2 + 3 dhe kolona 8 = 1 + 4 + 5 + 6 + 7',
'borrow_06':'Projekt-kreditë fondi 06 (Tabela 1.1) kundrejt ndarjeve të klauzolës së investimeve (3.1.B + 4.1.B)',
'borrow_04':'Projekt-kreditë fondi 04 (Tabela 1.1) kundrejt rreshtave “Financimi nga Huamarrja” (3.1 + 4.1)',
'cen_diff':'Niveli qendror në Tabelën 2 kundrejt shumës së institucioneve (3.1 + 3.1.B)','loc_diff':'Niveli lokal në Tabelën 2 kundrejt shumës së komunave (4.1 + 4.1.B)',
'refs':'Nyje pa referencë në dokument',
'p701_central':'Totali 2026 në f.701 kundrejt nivelit qendror në Tabelën 2','p701_local':'Totali 2026 në f.701 kundrejt nivelit lokal në Tabelën 2',
'p701_central_sum':'f.701: kategoritë e 2025 mblidhen në totalin e 2025 (niveli qendror)','p701_local_sum':'f.701: kategoritë e 2025 mblidhen në totalin e 2025 (niveli lokal)',
'p701_vs_t1_2025':'2025: niveli qendror + lokal (f.701) + interesi + grantet e donatorëve (Tabela 1) = shpenzimet totale 2025 në Tabelën 1',
'p701_narr_central':'Pretendimi për rritje në tekst, niveli qendror (“rritje prej 10.0%”, f.701) kundrejt tabelës në të njëjtën faqe',
'p701_narr_local':'Pretendimi për rritje në tekst, niveli lokal (“rritje prej 10.1%”, f.701) kundrejt tabelës në të njëjtën faqe',
'proj_vs_t1cap':'Projektet kapitale në Tabelat 3.2/3.2.B/4.2/4.2.B (2026) kundrejt shpenzimeve kapitale në Tabelën 1','refs_flows':'Rrjedha pa referencë në dokument','debt_gdp':'Borxhi publik në fund të 2026: i brendshëm + i jashtëm, si % e BPV-së',
}
for k in CAT_SQ:
    CHECK_SQ.setdefault(f't2_t1_{k}',f'Tabela 2 {CAT_SQ[k]} kundrejt Tabelës 1')
    CHECK_SQ.setdefault(f't31_t2_{k}',f'Tabela 3.1 {CAT_SQ[k]}: totali i shtypur kundrejt Tabelës 2')
    CHECK_SQ.setdefault(f't2_local_{k}',f'Tabela 2 niveli lokal {CAT_SQ[k]} kundrejt planeve komunale')
NOTE_SQ={
'proj_vs_t1cap':'Diferenca përputhet me diferencën kapitale komunale ndërmjet Tabelës 2 dhe Tabelës 4.1 (≈4.1M, “Bilanci” në f.213).',
'debt_gdp':'Rillogaritur nga stoqet e borxhit dhe BPV-ja; krahasuar me 21.9% të shtypur.',
't1_cap':'“Klauzola e investimeve” është e dhëmbëzuar nën “Financimi nga buxheti i rregullt”; lexohen si rreshta paralelë sepse 897.8 + 100.7 ≈ 998.4.',
'pool':'Hyrjet: tatimet neto, jo-tatimoret, grantet, pranimet e jashtme dhe të brendshme. Përdorimet: totali i Tabelës 2, grantet e donatorëve, kryegjëja, daljet e brendshme, rritja e bilancit bankar.',
't2_vs_t1':'Diferenca është sa rreshti 2.4 “Grantet e Përcaktuara të Donatorve” (12.0M), të cilin Tabela 2 nuk e ndan. Në kanavacë shfaqet si destinacion më vete.',
't2_local_vs_41':'Dokumenti e shpjegon në f.213 si “Bilanci” 181,295 (stafi −27, paga +159,426, mallra −31,200, komunale −2,200, subvencione +388, kapitale +4,099,880, rezerva −4,045,000).',
'k1_struct':'Totali i strukturës së shtypur është i barabartë me burimet; “Bilanci” 181,295 është pjesa e burimeve që nuk mbulohet nga rreshtat.',
't43_vs_k1':'E njëjta diferencë 181,296: f.210 tregon tavanet, f.671 mbledh planet komunale.',
'borrow_04':'Dokumenti nuk thotë se fondi 04 përputhet një-me-një me “Financimi nga Huamarrja”; lidhja është supozim. Diferenca mund të përfshijë shpenzime nga projekt-kreditë të regjistruara gjetiu.',
}
def note_sq(c):
    if c['id'] in NOTE_SQ: return NOTE_SQ[c['id']]
    m=re.match(r'Table on the same page: ([\d,.]+) → ([\d,.]+) = \+([\d.]+)%\. The narrative figure does not match\.',c.get('note',''))
    if m: return f'Tabela në të njëjtën faqe: {m.group(1)} → {m.group(2)} = +{m.group(3)}%. Shifra në tekst nuk përputhet.'
    n=c.get('note','')
    if not n: return ''
    n=re.sub(r'(\d[\d,]*) rows checked; (\d+) mismatches listed in findings\.',r'\1 rreshta të kontrolluar; \2 mospërputhje te gjetjet.',n)
    n=re.sub(r'(\d[\d,]*) rows checked',r'\1 rreshta të kontrolluar',n)
    n=re.sub(r'(\d+) institutions compared',r'\1 institucione të krahasuara',n)
    n=re.sub(r'(\d+) municipalities compared',r'\1 komuna të krahasuara',n)
    n=re.sub(r'(\d+) projects checked',r'\1 projekte të kontrolluara',n)
    n=re.sub(r'(\d+) nodes, (\d+) flows checked',r'\1 nyje, \2 rrjedha të kontrolluara',n)
    if re.search(r'[a-z]{4,} (the|and|of|is) ',n): raise SystemExit('untranslated check note: '+c['id']+' '+n)
    return n
def kind_txt(kind):
    if kind.startswith('sources_'):
        k=kind[8:]; return (f'funding sources ≠ row – {CAT_EN.get(k,k)}', f'burimet e financimit ≠ rreshti – {CAT_SQ.get(k,k)}')
    m=re.match(r'children_(\w+)',kind)
    if m: return (f'sum of lines – {CAT_EN[m.group(1)]}', f'shuma e rreshtave – {CAT_SQ[m.group(1)]}')
    return {'row_cats':('row categories ≠ row total','kategoritë e rreshtit ≠ totali'),'sources':('funding sources ≠ row total','burimet e financimit ≠ totali')}[kind]
RULES=[
 (r'^Shtojca 1 vs Tabela 3\.1\+3\.1\.B: (.+)$', r'Shtojca 1 kundrejt Tabelës 3.1+3.1.B: \1'),
 (r'^Municipal summary \(p\.(\d+)\) vs Tabela 4\.1\+4\.1\.B: (.+)$', r'Përmbledhja komunale (f.\1) kundrejt Tabelës 4.1+4.1.B: \2'),
 (r'^Same municipality spelled "(.+)" \(p\.(\d+)\) and "(.+)" \(Tabela 4\.1\)$', r'E njëjta komunë shkruhet “\1” (f.\2) dhe “\3” (Tabela 4.1)'),
 (r'^(.+) is listed as the only municipality that had not approved its budget in the municipal assembly \(Nëntotali B, p\.213\); its figures are still included\.$', r'\1 është e vetmja komunë që nuk e ka miratuar buxhetin në Kuvendin Komunal (Nëntotali B, f.213); shifrat e saj përfshihen.'),
 (r'^p\.210 “BILANCI I BUXHETIT” row.*$', 'Rreshti “BILANCI I BUXHETIT” në f.210: vlerat bien nën 2025–2028 sipas pozitës, por për 2025 burimet dhe struktura janë të dyja 788,294,719 ndërsa bilanci tregon 8,108,785; rreshtat e 2025 mblidhen në 780,760,626.'),
 (r'^Tabela 4\.3 (.+): own-source lines vs “Të Hyrat Vetanake”$', r'Tabela 4.3 \1: rreshtat e të hyrave vetanake kundrejt “Të Hyrat Vetanake”'),
 (r'^Tabela 4\.3 (.+): own-source \+ transfers \+ borrowing vs total$', r'Tabela 4.3 \1: vetanake + transfere + huamarrje kundrejt totalit'),
 (r'^Tabela 4\.3 revenue vs Tabela 4\.1 spending: (.+)$', r'Të hyrat në Tabelën 4.3 kundrejt shpenzimeve në Tabelën 4.1: \1'),
 (r'^Capital projects \((3\.2|4\.2)\) vs capital in (3\.1|4\.1): (.+)$', r'Projektet kapitale (\1) kundrejt investimeve kapitale në \2: \3'),
 (r'^(Tabela [\d.B]+) project column 4 ≠ 2 \+ 3: (.+)$', r'\1 projekti: kolona 4 ≠ 2 + 3: \2'),
 (r'^(Tabela [\d.B]+) project column 8 ≠ 1 \+ 4 \+ 5 \+ 6 \+ 7: (.+)$', r'\1 projekti: kolona 8 ≠ 1 + 4 + 5 + 6 + 7: \2'),
 (r'^Tabela 3\.2\.B p\.205: .*$', 'Tabela 3.2.B f.205: një rresht financimi (FHKI, 33,438,206 shpenzuar deri në 2025, 0 € në 2026) nuk ka rresht projekti — as kod as emër.'),
 (r'^Municipal borrowing: Tabela 4\.1 shows €([\d,]+) financed from borrowing \(goods and services\), Tabela 4\.2 shows €([\d,]+) of FH-funded projects in 2026\.$', r'Huamarrja komunale: Tabela 4.1 tregon €\1 të financuara nga huamarrja (mallra dhe shërbime), Tabela 4.2 tregon €\2 projekte të financuara nga FH në 2026.'),
 (r'^Tables 1 and 1\.1 are reprinted.*$', 'Tabelat 1 dhe 1.1 ribotohen në f.703–705; të gjitha vlerat përputhen me f.29–33 (ndryshon vetëm rrumbullakimi: 2,707.38 kundrejt 2,707.4).'),
 (r'^No municipal population figures.*$', 'Dokumenti nuk ka të dhëna për popullsinë e komunave, ndaj nuk shfaqen shuma për banor.'),
 (r'^Several institution and programme names are cut off.*$', 'Disa emra institucionesh dhe programesh janë të prera në Tabelën 3.1 (p.sh. “Agjencia Kosovare për Krahasim Ver”). Emrat e plotë merren nga Shtojca 1 (f.96).'),

 (r'^p\.701 narrative says central-level spending grows 10\.0% vs the 2025 budget; the table on the same page \(2,757\.7 → 3,024\.7\) gives ([\d.]+)%\.$', r'Teksti në f.701 thotë se shpenzimet e nivelit qendror rriten 10.0% krahasuar me buxhetin 2025; tabela në të njëjtën faqe (2,757.7 → 3,024.7) jep \1%.'),
 (r'^The 2025 municipal column is headed.*$', 'Kolona komunale e 2025 titullohet “2025 Aktuale” në f.210 dhe në faqet për komunë të Tabelës 4.3, por “2025 Buxheti” në përmbledhjen e Tabelës 4.3 (f.671); vlerat janë të njëjta (788,294,719/720).'),
 (r'^(\d+) project date ranges are printed in a malformed or non-standard form in the PDF \(e\.g\. (.+)\); they are shown exactly as printed\.$', r'\1 periudha datash projektesh janë shtypur në formë të gabuar ose jo-standarde në PDF (p.sh. \2); shfaqen saktësisht siç janë shtypur.'),
 (r'^Shtojca 1 code (\d+) has no Tabela 3\.1 row$', r'Kodi \1 në Shtojcën 1 nuk ka rresht në Tabelën 3.1'),
 (r'^Municipality "(.+)" \(p\.(\d+)\) has no exact name match in Tabela 4\.1$', r'Komuna “\1” (f.\2) nuk ka përputhje të saktë emri në Tabelën 4.1'),
]
TYPE_SQ={'mismatch':'mospërputhje','ambiguity':'paqartësi','note':'shënim','naming':'emërtim','missing':'mungesë'}
def apply(CHECKS,FINDINGS):
    for c in CHECKS:
        if not c.get('title_sq'):
            if c['id'] not in CHECK_SQ: raise SystemExit('no Albanian title for check '+c['id'])
            c['title_sq']=CHECK_SQ[c['id']]
        if 'note_sq' not in c: c['note_sq']=note_sq(c)
    for f in FINDINGS:
        if f.get('title_sq'): f['type_sq']=TYPE_SQ.get(f['type'],f['type']); continue
        m=re.match(r'^(Tabela [\d.]+) (row_cats|sources_\w+|sources|children_\w+): (.+)$',f['title'])
        if m:
            en,sq=kind_txt(m.group(2)); f['title']=f'{m.group(1)} {en}: {m.group(3)}'; f['title_sq']=f'{m.group(1)} {sq}: {m.group(3)}'
        else:
            for pat,rep in RULES:
                if re.match(pat,f['title']): f['title_sq']=re.sub(pat,rep,f['title']); break
            else: raise SystemExit('no Albanian title for finding: '+f['title'])
        f['type_sq']=TYPE_SQ.get(f['type'],f['type'])
NOTE_RULES=[
 (r'^Table (4\.1|3\.1) total ([\d,]+) \+ investment clause \(Table (\S+)\) ([\d,]+)$', r'Totali në Tabelën \1: \2 + klauzola e investimeve (Tabela \3): \4'),
 (r'^(.+) total ([\d,-]+) vs sum of its (\d+) lines ([\d,-]+) \(Table (Tabela [\d.B]+), p\.(\d+)\)\.$', r'\1: totali \2 kundrejt shumës së \3 rreshtave \4 (\5, f.\6).'),
 (r'^Shown as a positive outflow.*$', 'Shfaqet si dalje pozitive; tabela e jep si −102.9 (zbritet nga të hyrat tatimore).'),
 (r'^Table 2 grand total \(allocations incl\. interest\)\..*$', 'Totali i Tabelës 2 (ndarjet përfshirë interesin). Shpenzimet totale në Tabelën 1 përfshijnë edhe €12.0M grante të donatorëve.'),
 (r'^Counted in Table 1 total expenditure.*$', 'Llogaritet në shpenzimet totale të Tabelës 1 (f.29), por nuk ndahet në Tabelën 2 (f.34).'),
 (r'^Table 2 central total \(p\.34\) minus sum of 50 institutions.*$', 'Totali i nivelit qendror në Tabelën 2 (f.34) minus shuma e 50 institucioneve në Tabelat 3.1 + 3.1.B (f.35–95).'),
 (r'^Table 2 local total \(p\.34\) equals municipal budget ceilings.*$', 'Totali lokal në Tabelën 2 (f.34) është i barabartë me tavanet buxhetore komunale; planet e 38 komunave në Tabelat 4.1 + 4.1.B (f.214–356) janë më të vogla. Vetë dokumenti e jep këtë diferencë si “Bilanci – Diferenca në staf dhe kategori të shpenzimeve” = 181,295 (f.213).'),
 (r'^Linked by funding source: "Klauzola e Investimeve".*$', 'Lidhur sipas burimit të financimit: rreshtat “Klauzola e Investimeve” ↔ Tabela 1.1 “Projekt-kreditë, klauzola e investimeve (fondi 06)”.'),
 (r'^Linked by funding source: "Financimi nga Huamarrja".*$', 'Lidhur sipas burimit të financimit: rreshtat “Financimi nga Huamarrja” ↔ Tabela 1.1 “Projekt-kreditë, trajtim brenda deficiti (fondi 04)”.'),
]
def apply_notes(nodes,flows):
    for o in list(nodes)+list(flows):
        if 'note' not in o or 'note_sq' in o: continue
        for pat,rep in NOTE_RULES:
            if re.match(pat,o['note']): o['note_sq']=re.sub(pat,rep,o['note']); break
        else: raise SystemExit('no Albanian note: '+o['note'][:100])
        o['note_en']=o.pop('note')
