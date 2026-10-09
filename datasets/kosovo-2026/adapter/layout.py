"""Where each table sits in budget-2026.pdf (Ligji Nr. 10/L-001, 728 pp.). Pages are 1-based; y values are pdfplumber `top`
(pt from the top of the page). A column anchor is the right edge (x1) of the numbers printed in that column: a number goes to
the nearest anchor if it lies within `tol`. num_x: numbers left of it belong to the label, not a column. (x0, x1) pairs are text
columns by left edge. The parsers keep only the indentation tests that tell row kinds apart."""

# Tabela 1 fiscal projections (€ million), pp.29–30; p.29 has header rows above top 140, p.30 is printed 13pt further right
T1_COLS=[('y2023',328),('y2024',376),('y2025',424),('y2026',473),('y2027',521),('y2028',569)]
T1=dict(num_x=300,tol=22,pages=[dict(page=29,top=140,label_x=300,cols=T1_COLS),
                                dict(page=30,top=0,label_x=300,cols=[(k,x+13) for k,x in T1_COLS])])
# Tabela 1.1 financing of the budget balance (€ million), pp.32–33; p.32 has header rows above top 140
T11_COLS=[('y2023',373),('y2024',416),('y2025',459),('y2026',502),('y2027',546),('y2028',589)]
T11=dict(num_x=300,tol=22,pages=[dict(page=32,top=140,label_x=350,cols=T11_COLS),dict(page=33,top=0,label_x=350,cols=T11_COLS)])
# Tabela 2 summary of allocations, central vs local (€), p.34; body below top 220, labels left of x 200
T2=dict(page=34,top=220,num_x=200,tol=22,
        cols=[('staff',241),('wages',305),('goods',368),('util',432),('subs',495),('capital',558),('reserve',622),('interest',685),('total',748)])

# Tabela 3.1 central budget (€), pp.35–93: institution > programme > sub-programme, one row per funding source below each
T31=dict(pages=range(35,94),band=(80,585),num_x=500,tol=25,src_x=(400,520),total_src_x=(370,470),
         cols=[('staff',567),('wages',608),('goods',648),('util',693),('subs',743),('capital',788),('reserve',828),('total',878),('y2027',927),('y2028',981)])
# Tabela 3.1.B central investment clause (€), pp.94–95: rows as in 3.1, columns further left
T31B=dict(T31,pages=range(94,96),
          cols=[('staff',522),('wages',563),('goods',603),('util',644),('subs',689),('capital',729),('reserve',770),('total',815),('y2027',864),('y2028',914)])

# Shtojca 1 (Annex 1) budget per institution (€), p.96; body below top 85, nothing right of x 495; codes end left of x 60,
# names in x 55–185, staff digits split into single glyphs end in x 185–196; name characters start in x 55–180
# (the first staff glyph of 11,901 starts at 182)
A1=dict(page=96,top=85,max_x=495,num_x=150,tol=12,code_x=60,name_x=(55,185),staff_x=(185,196),name_chars_x=(55,180),
        cols=[('staff',194),('wages',233),('goods',267),('util',303),('subs',354),('capital',409),('reserve',441),('total',488)])

# capital projects (€): 3.2 central pp.97–203, 3.2.B central clause pp.204–209, 4.2 municipal pp.357–645, 4.2.B municipal clause p.646,
# all in one layout: body in top 165–570, dates x 145–209, project name right of 209 (wrapped name lines start right of 200),
# funding source x 360–400
CAP=dict(tables={'3.2':range(97,204),'3.2.B':range(204,210),'4.2':range(357,646),'4.2.B':[646]},
         band=(165,570),num_x=448,tol=20,dates_x=(145,209),name_x=209,wrap_x=200,src_x=(360,400),
         cols=[('spent_to_2025',464),('cont_2026',512),('new_2026',555),('total_2026',609),('y2027',660),('y2028',711),('y2029plus',756),('project_total',821)])

# Komunat Tabela 1 municipal revenue/expenditure balance (€), p.210; labels left of x 250
K210=dict(page=210,num_x=250)
# Struktura e shpenzimeve per municipality and fund (€), pp.211–213; p.211 has header rows above top 60; row numbers end left of x 60,
# municipality names in x 55–110, fund labels (Total/Grant/THV) in x 70–115
KS=dict(pages=(211,212,213),top=60,num_x=150,tol=12,idx_x=60,name_x=(55,110),fund_x=(70,115),
        cols=[('staff',173),('wages',208),('goods',243),('util',279),('subs',316),('capital',361),('reserve',401),('total',446),('y2027',491),('y2028',535)])

# Tabela 4.1 municipal budgets (€), pp.214–355; body in top 95–565, funding-source labels in x 370–470, numbers right of x 480
T41=dict(pages=range(214,356),band=(95,565),num_x=480,tol=25,src_x=(370,470),
         cols=[('staff',508),('wages',553),('goods',603),('util',652),('subs',706),('capital',760),('reserve',816),('total',868),('y2027',922),('y2028',976)])
# Tabela 4.1.B municipal investment clause (€), p.356: laid out like 3.1, so parsed with the 3.1 rules
T41B=dict(T31,pages=[356],
          cols=[('staff',522),('wages',563),('goods',603),('util',644),('subs',689),('capital',729),('reserve',765),('total',815),('y2027',864),('y2028',914)])

# Tabela 4.3 municipal revenue plan (€), pp.647–671; p.671 is the summary of all municipalities; labels left of x 230
T43=dict(pages=range(647,672),summary_page=671,num_x=230,tol=14,
         cols=[('y2024',284),('y2025',360),('y2026',441),('y2027',518),('y2028',599)])
