import pdfplumber, re
from .paths import PDF
_pdf=None
def pdf():
    global _pdf
    if _pdf is None: _pdf=pdfplumber.open(str(PDF))
    return _pdf
NUM=re.compile(r'^-?\(?[\d]{1,3}(,\d{3})*(\.\d+)?\)?$|^-?\d+(\.\d+)?$')
def lines(pno, tol=2.5):
    p=pdf().pages[pno-1]
    ws=p.extract_words(keep_blank_chars=False, x_tolerance=1.5)
    ws.sort(key=lambda w:(w['top'],w['x0']))
    out=[]
    for w in ws:
        if out and abs(out[-1]['top']-w['top'])<=tol: out[-1]['words'].append(w)
        else: out.append({'top':w['top'],'words':[w]})
    for l in out:
        l['words'].sort(key=lambda w:w['x0'])
        l['text']=' '.join(w['text'] for w in l['words'])
    return out
def isnum(s): return bool(NUM.match(s)) and s not in ('-',)
def tonum(s):
    s=s.replace(',','')
    neg=s.startswith('(') or s.startswith('-')
    s=s.strip('()-')
    v=float(s)
    return -v if neg else v

THOU=re.compile(r'^-?\d{1,3}(,\d{3})+$')
def lines_merged(pno, tol=2.5, xt=3.5):
    """lines with split-digit words re-joined (e.g. '8' + ',098,353')."""
    p=pdf().pages[pno-1]
    ws=p.extract_words(x_tolerance=xt)
    ws.sort(key=lambda w:(round(w['top']),w['x0']))
    out=[]
    for w in ws:
        if out and abs(out[-1]['top']-w['top'])<=tol: out[-1]['words'].append(dict(w))
        else: out.append({'top':w['top'],'words':[dict(w)]})
    for l in out:
        l['words'].sort(key=lambda w:w['x0'])
        m=[]
        for w in l['words']:
            if m and re.fullmatch(r'\d{1,3}',m[-1]['text']) and re.fullmatch(r'[\d,]+',w['text']) and THOU.match(m[-1]['text']+w['text']) and w['x0']-m[-1]['x1']<14:
                m[-1]['text']+=w['text']; m[-1]['x1']=w['x1']
            else: m.append(w)
        l['words']=m; l['text']=' '.join(w['text'] for w in m)
    return out

_chars={}
def band_text(pno, top, x0, x1, tol=2.5):
    """text of the characters on one printed line whose left edge lies in [x0, x1)"""
    if pno not in _chars: _chars.clear(); _chars[pno]=pdf().pages[pno-1].chars
    cs=sorted((c for c in _chars[pno] if abs(c['top']-top)<=tol and x0<=c['x0']<x1), key=lambda c:c['x0'])
    out=''; last=None
    for c in cs:
        if last is not None and c['x0']-last>1.5: out+=' '
        out+=c['text']; last=c['x1']
    return out.strip()
