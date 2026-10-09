"""Parse hierarchical budget tables (3.1, 3.1.B) by word x-positions."""
import os as _os, sys as _sys; _sys.path.insert(0,_os.environ.get('BUDGET_ROOT') or _os.path.abspath(__file__+'/../../../..'))
from pipeline.paths import DATASET_DIR; _os.chdir(DATASET_DIR)
import csv, re
from pipeline.pdfutil import lines, isnum, tonum
from layout import T31, T31B
SOURCES=['Grantet Qeveritare','Të Hyrat vetanake','Te Hyrat Vetanake','Financimi nga Huamarrja','Të Hyrat nga AKP','Klauzola e Investimeve','Financim i Jashtem']
def assign(words, cols, tol):
    vals={}
    for w in words:
        if not isnum(w['text']): continue
        c=min(cols,key=lambda c:abs(c[1]-w['x1']))
        if abs(c[1]-w['x1'])>tol: raise ValueError(f"unplaced {w['text']} at {w['x1']}")
        vals[c[0]]=tonum(w['text'])
    return vals
def parse(lay, table, stop_words=('Total:',)):
    rows=[]; cur=None; cols,tol,nx,srcx=lay['cols'],lay['tol'],lay['num_x'],lay['src_x']; y0,y1=lay['band']
    for p in lay['pages']:
        L=lines(p)
        for l in L:
            if l['top']<y0 or l['top']>y1: continue
            ws=l['words']
            txt=l['text']
            if any(w['text'] in stop_words for w in ws):
                rows.append(dict(table=table,page=p,top=round(l['top']),kind='table_total',code='',func='',name=' '.join(w['text'] for w in ws if not isnum(w['text'])),source='',raw=txt,**assign(ws,cols,tol)))
                continue
            left=[w for w in ws if w['x0']<srcx[0] and not (isnum(w['text']) and w['x1']>nx)]
            mid=[w for w in ws if srcx[0]<=w['x0']<srcx[1] and not isnum(w['text'])]
            vals=assign([w for w in ws if w['x1']>nx],cols,tol)
            if mid and not left:
                src=' '.join(w['text'] for w in mid)
                if any(r['kind']=='table_total' for r in rows):
                    rows.append(dict(table=table,page=p,top=round(l['top']),kind='table_total_src',code='',func='',name='',source=src,raw=txt,**vals)); continue
                rows.append(dict(table=table,page=p,top=round(l['top']),kind='source',code=cur['code'] if cur else '',func='',name=cur['name'] if cur else '',source=src,raw=txt,**vals))
                continue
            if not left: 
                if rows and rows[-1]['table']==table and table_total_cont(rows): 
                    rows.append(dict(table=table,page=p,top=round(l['top']),kind='table_total_cont',code='',func='',name='',source='',raw=txt,**vals))
                continue
            first=left[0]
            if re.fullmatch(r'\d{3}',first['text']) and first['x0']<20:
                kind='org'; code=first['text']; func=''; name=' '.join(w['text'] for w in left[1:])
            elif re.fullmatch(r'\d{5}',first['text']) and first['x0']<30:
                kind='sub'; code=first['text']
                func=left[1]['text'] if len(left)>1 and re.fullmatch(r'\d{4}',left[1]['text']) else ''
                name=' '.join(w['text'] for w in left[(2 if func else 1):])
            elif re.fullmatch(r'\d{3}',first['text']) and 25<first['x1']<36:
                kind='prog'; code=first['text']; func=''; name=' '.join(w['text'] for w in left[1:])
            elif re.fullmatch(r'\d{4}',first['text']) and 38<first['x0']<50 and len(left)>1 and 190<left[1]['x0']<215:
                kind='prog'; code=''; func=first['text']; name=' '.join(w['text'] for w in left[1:])
            elif first['x0']>190 and first['x0']<215:
                kind='prog'; code=''; func=''; name=' '.join(w['text'] for w in left)
            else:
                kind='other'; code=''; func=''; name=' '.join(w['text'] for w in left)
                if any(r['kind']=='table_total' for r in rows):
                    srcw=[w for w in ws if lay['total_src_x'][0]<w['x0']<lay['total_src_x'][1] and not isnum(w['text'])]
                    rows.append(dict(table=table,page=p,top=round(l['top']),kind='table_total_src',code='',func='',name=name,source=' '.join(w['text'] for w in srcw),raw=txt,**vals)); continue
            cur=dict(table=table,page=p,top=round(l['top']),kind=kind,code=code,func=func,name=name,source='',raw=txt,**vals)
            rows.append(cur)
    return rows
def table_total_cont(rows):
    return any(r['kind']=='table_total' for r in rows[-6:])
FIELDS=['table','page','top','kind','code','func','name','source','staff','wages','goods','util','subs','capital','reserve','total','y2027','y2028','raw']
def write(rows,path):
    with open(path,'w',newline='') as f:
        w=csv.DictWriter(f,FIELDS,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
if __name__=='__main__':
    r=parse(T31,'3.1'); write(r,'raw/t3_1.csv'); print('3.1',len(r))
    r=parse(T31B,'3.1.B'); write(r,'raw/t3_1B.csv'); print('3.1.B',len(r))
