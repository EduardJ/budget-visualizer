"""Independent re-read with poppler's pdftotext (a different extractor than the pdfplumber pipeline): a printed value
counts as confirmed when it appears on the referenced page, on a line that also carries the row label."""
import re, subprocess, unicodedata
_cache={}
def page_text(pdf, p):
    if (str(pdf),p) not in _cache: _cache[str(pdf),p]=subprocess.run(['pdftotext','-layout','-f',str(p),'-l',str(p),str(pdf),'-'],capture_output=True,text=True).stdout
    return _cache[str(pdf),p]
def norm(s): return re.sub(r'\s+',' ',unicodedata.normalize('NFC',s)).strip().lower()
def locate(txt, v, label):
    """(value_found, label_on_line) for the printed token v and the first three words (>3 letters) of label"""
    words=[w for w in norm(label).split() if len(w)>3][:3]
    lines=[l for l in txt.splitlines() if v in l]
    lab_ok=any(all(w in norm(l) for w in words) for l in lines) if words else bool(lines)
    # the label can sit on the line above when it wraps
    if lines and not lab_ok:
        L=txt.splitlines()
        for i,l in enumerate(L):
            if v in l and any(all(w in norm(x) for w in words) for x in L[max(0,i-3):i+2]): lab_ok=True
    return bool(lines),lab_ok
def printed_value(v, scale=1):
    sign=-1 if v.startswith(('-','(')) else 1
    return sign*float(v.strip('()-').replace(',',''))*scale
def confirmed(r): return r['value_found'] and r['label_on_line'] and r['matches_node']
def report(name, rows, list_ok=True):
    """prints '<name>: k/n confirmed' and one line per row (only the unconfirmed ones unless list_ok)"""
    print(f'{name}: {sum(map(confirmed,rows))}/{len(rows)} confirmed')
    for r in rows:
        flag='' if confirmed(r) else '   <-- CHECK'
        if list_ok or flag: print(f"  p.{r['page']:<4}{r['table']:<12}{r['orig']:>16}  {r['name']}{flag}")
