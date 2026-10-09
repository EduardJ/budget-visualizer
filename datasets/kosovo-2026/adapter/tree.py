import csv
CATS=['wages','goods','util','subs','capital','reserve']
def f(x): return float(x) if x not in ('',None) else 0.0
def build(path):
    rows=list(csv.DictReader(open(path)))
    orgs=[];cur_org=cur_prog=cur=None
    for r in rows:
        for k in CATS+['staff','total','y2027','y2028']: r[k]=f(r.get(k))
        k=r['kind']
        if k in('org','prog','sub'):
            r['sources']={}; r['children']=[]
            if k=='org': orgs.append(r); cur_org=r; cur_prog=None
            elif k=='prog': cur_org['children'].append(r); cur_prog=r
            else: (cur_prog or cur_org)['children'].append(r)
            cur=r
        elif k=='source': cur['sources'][r['source']]=r
    return orgs,rows
def issues(orgs, tol=0.0):
    # every printed relation in a hierarchical table, all columns including the 2027/2028 estimates;
    # each issue carries how many printed figures were summed (n) so the failure can be labelled
    out=[]
    def chk(node, path):
        s=sum(node[c] for c in CATS)
        if abs(s-node['total'])>tol: out.append(('row_cats',path,node['total'],s,node['page'],len(CATS)))
        if node['sources']:
            for col in ('total','y2027','y2028')+tuple(CATS):
                st=sum(v.get(col,0) or 0 for v in node['sources'].values())
                if abs(st-(node.get(col) or 0))>tol: out.append((f'sources_{col}' if col!='total' else 'sources',path,node.get(col) or 0,st,node['page'],len(node['sources'])))
        if node['children']:
            for c in CATS+['total','staff','y2027','y2028']:
                cs=sum(ch[c] for ch in node['children'])
                if abs(cs-node[c])>tol: out.append((f'children_{c}',path,node[c],cs,node['page'],len(node['children'])))
            for ch in node['children']: chk(ch,path+' > '+ch['name'])
    for o in orgs: chk(o,o['code']+' '+o['name'])
    return out
