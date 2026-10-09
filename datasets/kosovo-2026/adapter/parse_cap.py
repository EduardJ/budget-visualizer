import os as _os, sys as _sys; _sys.path.insert(0,_os.environ.get('BUDGET_ROOT') or _os.path.abspath(__file__+'/../../../..'))
from pipeline.paths import DATASET_DIR; _os.chdir(DATASET_DIR)
import re, csv
from pipeline.pdfutil import lines, isnum, tonum, band_text
from layout import CAP
CC=CAP['cols']; NX=CAP['num_x']
FIELDS=['table','page','top','kind','org','prog','sub','func','prop_code','proj_code','dates','name','source','flag']+[c[0] for c in CC]+['raw']
def assign(ws):
    out={}
    for w in ws:
        if not isnum(w['text']) or w['x1']<NX: continue
        c=min(CC,key=lambda c:abs(c[1]-w['x1']))
        if abs(c[1]-w['x1'])>CAP['tol']: raise ValueError((w['text'],w['x1']))
        out[c[0]]=tonum(w['text'])
    return out
def parse(pages, table):
    rows=[]; org=prog=sub=''; proj=None; last_hdr=None; y0,y1=CAP['band']; WX=CAP['wrap_x']
    for p in pages:
        L=lines(p)
        for l in L:
            if l['top']<y0 or l['top']>y1: continue
            ws=l['words']; txt=l['text']
            isproj=re.fullmatch(r'\d{4}',ws[0]['text']) and ws[0]['x1']<45 and len(ws)>2 and re.match(r'\d{6}-\d+',ws[1]['text'])
            try: vals={} if isproj else assign(ws)
            except ValueError:
                if proj is not None and all(w['x0']>=WX for w in ws): proj['name']+=' '+txt; proj['raw']+=' / '+txt; continue
                raise
            base=dict(table=table,page=p,top=round(l['top']),raw=txt,org=org,prog=prog,sub=sub,**vals)
            f=ws[0]
            if f['text'].startswith('Totali'):
                lab=' '.join(w['text'] for w in ws if not (isnum(w['text']) and w['x1']>=NX))
                m=re.match(r'Totali\s*\(\s*(\w+)\s*\)',lab)
                rows.append(dict(base,kind='subtotal',name=lab,source=m.group(1) if m else ''))
                proj=None; continue
            m=re.fullmatch(r'(\d{5,6})',f['text'])
            if m and len(ws)>1 and ws[1]['text']=='-' and f['x1']<80:
                name=' '.join(w['text'] for w in ws[2:]); c=f['text']
                if f['x1']<50: org=c+' - '+name; prog=sub=''
                elif f['x1']<65: prog=c+' - '+name; sub=''
                else: sub=c+' - '+name
                proj=None; continue
            if re.fullmatch(r'\d{4}',f['text']) and f['x1']<45 and len(ws)>2 and re.match(r'\d{6}-\d+',ws[1]['text']):
                pc=ws[2]['text'] if re.fullmatch(r'\d{4,6}',ws[2]['text']) else ''
                rest=ws[3:] if pc else ws[2:]
                # the date column and the name column are separated by position, not by word shape
                dates=band_text(p, l['top'], *CAP['dates_x']).replace(' ','')
                name=band_text(p, l['top'], CAP['name_x'], 10000)
                name=re.sub(r'\s+[\d,]+(\s+[\d,]+)*$','',name) if re.search(r'\s[\d,]{5,}$',name) and False else name
                proj=dict(base,kind='project',func=f['text'],prop_code=ws[1]['text'],proj_code=pc,dates=dates,name=name,source='')
                rows.append(proj); continue
            srcw=[w for w in ws if CAP['src_x'][0]<=w['x0']<CAP['src_x'][1] and not isnum(w['text'])]
            if srcw and proj is None and vals:
                proj=dict(base,kind='project',func='',prop_code='',proj_code='',dates='',name='',source='',flag='orphan_funding_row')
                for k in [c[0] for c in CC]: proj.pop(k,None)
                rows.append(proj)
            if srcw and proj is not None and vals:
                rows.append(dict(base,kind='source',func=proj['func'],prop_code=proj['prop_code'],proj_code=proj['proj_code'],dates=proj['dates'],name=proj['name'],source=srcw[0]['text']))
                continue
            if proj is not None and not vals and all(w['x0']>=WX for w in ws):
                proj['name']+=' '+txt; proj['raw']+=' / '+txt; continue
            rows.append(dict(base,kind='unparsed',name=txt,source=''))
    return rows
def write(rows,path):
    with open(path,'w',newline='') as f:
        w=csv.DictWriter(f,FIELDS,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
if __name__=='__main__':
    import collections
    for t,fn in (('3.2','t3_2'),('3.2.B','t3_2B'),('4.2','t4_2'),('4.2.B','t4_2B')):
        r=parse(CAP['tables'][t],t); write(r,f'raw/{fn}.csv')
        print(t,collections.Counter(x['kind'] for x in r))
        for x in r:
            if x['kind']=='unparsed': print('  UNPARSED',x['page'],x['raw'][:120])
