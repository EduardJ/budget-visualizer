"""Exact arithmetic on printed figures.
A relation passes only if the printed numbers satisfy it exactly. A failure is classed as
'rounding' when the rounding of the printed digits could explain it, otherwise 'error'."""
from decimal import Decimal as Dm, ROUND_HALF_UP
import re
def tok_dec(tok):
    s=tok.replace(',','').replace('€','').strip()
    neg=s.startswith('(') or s.startswith('-') or s.startswith('−')
    s=s.strip('()-−%')
    return (-Dm(s) if neg else Dm(s)), (len(s.split('.')[1]) if '.' in s else 0)
def half(dec): return Dm(5)/(Dm(10)**(dec+1))
def find_tok(raw, val):
    """the printed token in a raw line that has numeric value val (first match), else None"""
    for t in re.findall(r'\(?[-−]?[\d][\d,]*(?:\.\d+)?\)?%?',raw):
        try: v,d=tok_dec(t)
        except Exception: continue
        if abs(float(v)-float(val))<1e-9: return t
    return None
class Term:
    __slots__=('v','dec','label','ref','sign')
    def __init__(s,v,dec,label='',ref=None,sign=1): s.v=Dm(v) if not isinstance(v,Dm) else v; s.dec=dec; s.label=label; s.ref=ref; s.sign=sign
def term_from(raw,val,label='',ref=None,sign=1,dec=None):
    t=find_tok(raw,val) if raw else None
    if t is not None: v,d=tok_dec(t)
    else: v,d=Dm(str(val)), (dec if dec is not None else 0)
    return Term(v,d,label,ref,sign)
def relation(lhs, rhs):
    """lhs: Term, rhs: list of Terms (with sign). returns (expected, actual, diff, cls)"""
    act=sum((t.v*t.sign for t in rhs),Dm(0))
    diff=act-lhs.v
    if diff==0: return lhs.v,act,diff,None
    bound=half(lhs.dec)+sum((half(t.dec) for t in rhs),Dm(0))
    return lhs.v,act,diff,('rounding' if abs(diff)<=bound else 'error')
def rnd(x,dec): return Dm(x).quantize(Dm(1)/(Dm(10)**dec),rounding=ROUND_HALF_UP)
def rounds_to(exact_value, printed):
    """exact (e.g. euros/1e6) against a printed rounded figure: no rounding excuse beyond the printed precision"""
    ok=rnd(exact_value,printed.dec)==printed.v
    return ok
def interval(f, terms, n=0):
    """min/max of f over all corners of the rounding intervals of terms (monotone functions)"""
    import itertools
    vals=[]
    for corner in itertools.product(*[(t.v-half(t.dec), t.v+half(t.dec)) for t in terms]):
        try: vals.append(f(*corner))
        except ZeroDivisionError: pass
    return min(vals),max(vals)
