# Reference implementation: configure paths, source hashes and project dependencies first.
"""Sample actual upward-facing source surfaces for local cave lighting."""
import json,math,pathlib
root=pathlib.Path(__file__).resolve().parents[1];cells={}
for file in sorted((root/'artifacts/tunnel-unreal-build/surfaces').glob('*.obj')):
    if file.stem in ('surface_0000','surface_0001','surface_0013','surface_0020'):continue
    verts=[];normals=[]
    for line in file.read_text().splitlines():
        p=line.split()
        if not p:continue
        if p[0]=='v':verts.append(tuple(map(float,p[1:])))
        elif p[0]=='vn':normals.append(tuple(map(float,p[1:])))
        elif p[0]=='f':
            indices=[tuple(map(int,x.split('/'))) for x in p[1:]]
            if sum(normals[i[2]-1][2] for i in indices)/3<.65:continue
            a,b,c=[verts[i[0]-1] for i in indices]
            edge=max(math.dist(a,b),math.dist(b,c),math.dist(a,c));count=max(1,math.ceil(edge/700))
            for i in range(count):
                for j in range(count-i):
                    s=(i+1/3)/count;t=(j+1/3)/count
                    v=[a[k]+s*(b[k]-a[k])+t*(c[k]-a[k]) for k in range(3)];v[1]=-v[1]
                    key=(round(v[0]/1350),round(v[1]/1350),round(v[2]/700))
                    score=(v[0]-key[0]*1350)**2+(v[1]-key[1]*1350)**2
                    if key not in cells or score<cells[key][0]:cells[key]=(score,v)
points=[]
for _,p in sorted(cells.values(),key=lambda r:(r[1][2],r[1][0],r[1][1])):
    if all(math.dist(p,q)>1000 for q in points):points.append(p)
(root/'artifacts/tunnel-cave-light-candidates.json').write_text(json.dumps(points,indent=2))
print(len(points),'floor samples')
