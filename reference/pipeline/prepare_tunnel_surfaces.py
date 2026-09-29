# Reference implementation: configure paths, source hashes and project dependencies first.
"""Split the verified world by material, preserving every retained triangle."""
import collections,json,pathlib
root=pathlib.Path(__file__).resolve().parents[1]
work=root/'artifacts/tunnel-unreal-build'
dest=work/'surfaces';dest.mkdir(exist_ok=True)
attributes={'v':[],'vt':[],'vn':[]};groups=collections.defaultdict(list);slot=None
for line in (work/'TunnelWorld.obj').read_text().splitlines():
    p=line.split()
    if not p:continue
    if p[0] in attributes:attributes[p[0]].append(tuple(map(float,p[1:])))
    elif p[0]=='usemtl':slot=p[1]
    elif p[0]=='f':groups[slot].append([tuple(map(int,s.split('/'))) for s in p[1:]])
records=[]
for slot,faces in sorted(groups.items()):
    out=[];remaps=[]
    for j,key in enumerate(('v','vt','vn')):
        ids=sorted({v[j] for f in faces for v in f});remaps.append({old:i+1 for i,old in enumerate(ids)})
        for i in ids:out.append(key+' '+' '.join(format(x,'.9g') for x in attributes[key][i-1]))
    for f in faces:out.append('f '+' '.join('/'.join(str(remaps[j][v[j]]) for j in range(3)) for v in f))
    (dest/(slot+'.obj')).write_text('\n'.join(out)+'\n')
    records.append({'slot':slot,'triangles':len(faces),'vertices':len(remaps[0]),'file':str(dest/(slot+'.obj'))})
assert sum(r['triangles'] for r in records)==10595-48
(dest/'manifest.json').write_text(json.dumps(records,indent=2)+'\n')
print(len(records),'surfaces;',sum(r['triangles'] for r in records),'triangles preserved')
