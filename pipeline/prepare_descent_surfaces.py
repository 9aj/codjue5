"""Surface islands: shared edges, same material and coplanar normals; no geometry edits."""
import json, math, hashlib
from pathlib import Path
from collections import defaultdict,Counter
from prepare_descent_chunks import read_obj,area
ROOT=Path(__file__).resolve().parents[1]
def islands(faces):
    parents=list(range(len(faces)));edges=defaultdict(list);normals=[]
    def find(i):
        while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
        return i
    for i,(mat,t) in enumerate(faces):
        a,b,c=[v[:3] for v in t];x=[b[k]-a[k] for k in range(3)];y=[c[k]-a[k] for k in range(3)]
        n=[x[1]*y[2]-x[2]*y[1],x[2]*y[0]-x[0]*y[2],x[0]*y[1]-x[1]*y[0]];length=math.sqrt(sum(q*q for q in n))
        n=[q/length for q in n] if length else [0,0,0]
        if sum(n[k]*t[0][5+k] for k in range(3))<0:n=[-q for q in n]
        normals.append(n)
        vertices=[tuple(round(v[k],4) for k in range(3)) for v in t]
        for p,q in zip(vertices,vertices[1:]+vertices[:1]):edges[tuple(sorted((p,q)))].append(i)
    for ids in edges.values():
        for i in ids:
            for j in ids:
                if j<=i or faces[i][0]!=faces[j][0]:continue
                if sum(normals[i][k]*normals[j][k] for k in range(3))<.999999:continue
                if max(abs(sum(normals[i][k]*(v[k]-faces[i][1][0][k]) for k in range(3))) for v in faces[j][1])>.01:continue
                parents[find(j)]=find(i)
    groups=defaultdict(list)
    for i in range(len(faces)):groups[find(i)].append(i)
    return list(groups.values()),normals

def prepare():
    folder=ROOT/'artifacts/descent-surface-test';folder.mkdir(exist_ok=True)
    source=ROOT/'artifacts/descent-chunks-100m/opaque_0_0_0.obj'
    faces=read_obj(source);groups,normals=islands(faces);parts=[]
    for number,ids in enumerate(groups):
        n=normals[ids[0]];kind='Landing' if n[2]>.999 else 'Underside' if n[2]<-.999 else 'Wall' if abs(n[2])<.001 else 'Slope'
        name=f'{kind}_{number:03d}';verts=[v for i in ids for v in faces[i][1]]
        lo=[min(v[k] for v in verts) for k in range(3)];hi=[max(v[k] for v in verts) for k in range(3)];center=[(lo[k]+hi[k])/2 for k in range(3)]
        material=faces[ids[0]][0];lines=['mtllib materials.mtl','usemtl '+material]
        for v in verts:
            lines+=['v '+' '.join(format(v[k]-center[k],'.12g') for k in range(3)),'vt '+' '.join(format(x,'.12g') for x in v[3:5]),'vn '+' '.join(format(x,'.12g') for x in v[5:8])]
        for i in range(0,len(verts),3):lines.append('f '+' '.join(f'{j}/{j}/{j}' for j in range(i+1,i+4)))
        path=folder/(name+'.obj');path.write_text('\n'.join(lines)+'\n')
        actual=read_obj(path);assert len(actual)==len(ids)
        for (_,original),(_,serialized) in zip([faces[i] for i in ids],actual):
            for a,b in zip(original,serialized):
                assert max(abs(a[k]-(b[k]+center[k])) for k in range(3))<1e-6
                assert max(abs(a[k]-b[k]) for k in range(3,8))<1e-8
        parts.append(dict(name=name,kind=kind,file=path.name,material=material,triangles=len(ids),faces=ids,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),origin_ue_cm=[5000+center[0],-5000-center[1],5000+center[2]],bounds_local=[ [lo[k]-center[k] for k in range(3)],[hi[k]-center[k] for k in range(3)]]))
    assert sorted(i for p in parts for i in p['faces'])==list(range(len(faces)))
    (folder/'materials.mtl').write_text('\n'.join('newmtl '+m+'\nKd 0.5 0.5 0.5\n' for m in sorted({f[0] for f in faces})))
    report=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),triangles=len(faces),parts=parts,counts=dict(Counter(p['kind'] for p in parts)),validated_exact_face_coverage_and_attributes=True)
    (folder/'manifest.json').write_text(json.dumps(report,indent=2));print(len(parts),report['counts'])
if __name__=='__main__':prepare()
