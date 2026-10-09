"""Print a PDF page the way the parsers see it: one row per printed line, with its `top`, and every number tagged with
the x of its right edge (the column anchor the parsers match against). Use it to fill in adapter/layout.py for a new
document or a new edition: find the table pages, the y-band of the body, and one anchor per column.
usage: BUDGET_DATASET=<id> python pipeline/inspect_page.py <page> [<page>...] [--words]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.pdfutil import lines, isnum
args = [a for a in sys.argv[1:] if not a.startswith('--')]
if not args: sys.exit(__doc__)
for p in map(int, args):
    print(f'--- page {p}')
    for l in lines(p):
        if '--words' in sys.argv: cells = [f"{w['text']}[{w['x0']:.0f}-{w['x1']:.0f}]" for w in l['words']]
        else: cells = [f"{w['text']}@{w['x1']:.0f}" if isnum(w['text']) else w['text'] for w in l['words']]
        print(f"{l['top']:6.1f}  " + ' '.join(cells))
