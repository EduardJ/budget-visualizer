import os as _os, sys as _sys; _sys.path.insert(0,_os.environ.get('BUDGET_ROOT') or _os.path.abspath(__file__+'/../../../..'))
from pipeline.paths import DATASET_DIR; _os.chdir(DATASET_DIR)
import re
from pipeline.pdfutil import lines, isnum
from parse_tree import assign, write, parse
from layout import T41, T41B
def parse41(lay):
    rows=[]; cur=None; done=False; y0,y1=lay['band']; sx0,sx1=lay['src_x']
    for p in lay['pages']:
        for l in lines(p):
            if l['top']<y0 or l['top']>y1: continue
            ws=l['words']; txt=l['text']
            vals=assign([w for w in ws if w['x1']>lay['num_x'] and isnum(w['text'])],lay['cols'],lay['tol'])
            lab=[w for w in ws if sx0<=w['x0']<sx1 and not isnum(w['text'])]
            left=[w for w in ws if w['x0']<sx0]
            labt=' '.join(w['text'] for w in lab)
            base=dict(table='4.1',page=p,top=round(l['top']),raw=txt,**vals)
            if labt.startswith('Total Shpenzimet') and left==[] :
                rows.append(dict(base,kind='table_total',code='',func='',name='Total Shpenzimet',source='')); done=True; continue
            if done:
                rows.append(dict(base,kind='table_total_src' if lab else 'note',code='',func='',name=' '.join(w['text'] for w in left),source=labt)); continue
            if not left:
                if lab and cur: rows.append(dict(base,kind='source',code=cur['code'],func='',name=cur['name'],source=labt))
                continue
            f=left[0]
            if re.fullmatch(r'\d{3}',f['text']) and f['x1']<25:
                kind='org'; code=f['text']; func=''; name=' '.join(w['text'] for w in left[1:])
            elif re.fullmatch(r'\d{3}',f['text']) and 28<f['x1']<40:
                kind='prog'; code=f['text']; func=''; name=' '.join(w['text'] for w in left[1:])
            elif re.fullmatch(r'\d{5}',f['text']) and 50<f['x1']<62:
                kind='sub'; code=f['text']; func=left[1]['text'] if len(left)>1 and re.fullmatch(r'\d{4}',left[1]['text']) else ''
                name=' '.join(w['text'] for w in left[(2 if func else 1):])
            else:
                kind='other'; code=''; func=''; name=' '.join(w['text'] for w in left)
            cur=dict(base,kind=kind,code=code,func=func,name=name,source=labt); rows.append(cur)
    return rows
if __name__=='__main__':
    r=parse41(T41); write(r,'raw/t4_1.csv'); print(len(r))
    # 4.1.B: prog code at x1~32 (3 digits) -> treat like 3.1 programme
    r=parse(T41B,'4.1.B'); write(r,'raw/t4_1B.csv'); print(len(r))
