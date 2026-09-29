# Reference implementation: configure paths, source hashes and project dependencies first.
"""Cut only the marked Z864 landing; keep original source assets untouched."""
import pathlib,json
root=pathlib.Path(__file__).resolve().parents[1];out=root/'artifacts/tunnel-landing-stairs';out.mkdir(exist_ok=True)
lo=[352*2.54,8224*2.54,2080.0];hi=[576*2.54,8320*2.54,864*2.54+.01]
def clip(poly,axis,value,greater):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[axis]-value)*(1 if greater else -1);db=(b[axis]-value)*(1 if greater else -1)
        if da>=0:result.append(a)
        if (da<0 and db>0) or (da>0 and db<0):
            t=da/(da-db);result.append([x+(y-x)*t for x,y in zip(a,b)])
    return result
def subtract(poly):
    inside=poly;outside=[]
    for axis in range(3):
        for val,g in ((lo[axis],True),(hi[axis],False)):
            part=clip(inside,axis,val,not g)
            if len(part)>=3 and any((q[axis]-val)*(1 if g else -1)<-1e-6 for q in inside):outside.append(part)
            inside=clip(inside,axis,val,g)
            if len(inside)<3:return outside
    return outside
reports=[]
for slot in (7,10):
    file=root/f'artifacts/tunnel-unreal-build/surfaces/surface_{slot:04d}.obj';v=[];uv=[];n=[];faces=[];changed=0
    for line in file.read_text().splitlines():
        p=line.split()
        if not p:continue
        if p[0]=='v':v.append([float(p[1]),-float(p[2]),float(p[3])])
        elif p[0]=='vt':uv.append(list(map(float,p[1:3])))
        elif p[0]=='vn':n.append(list(map(float,p[1:4])))
        elif p[0]=='f':
            poly=[v[int(q[0])-1]+uv[int(q[1])-1]+n[int(q[2])-1] for q in (s.split('/') for s in p[1:])]
            overlap=all(max(a[i] for a in poly)>lo[i]+(-.001 if i==1 else .001) and min(a[i] for a in poly)<hi[i]-(-.001 if i==1 else .001) for i in range(3))
            # Planar boundary faces are retained unless actually within the cut volume.
            if overlap:faces.extend(subtract(poly));changed+=1
            else:faces.append(poly)
    lines=['# Local landing stair cut; source coordinates and UVs retained','s off'];idx=1;tri=0
    for poly in faces:
        for j in range(1,len(poly)-1):
            a,b,c=poly[0],poly[j],poly[j+1]
            ab=[b[i]-a[i] for i in range(3)];ac=[c[i]-a[i] for i in range(3)];area=sum((ab[(i+1)%3]*ac[(i+2)%3]-ab[(i+2)%3]*ac[(i+1)%3])**2 for i in range(3))
            if area<1e-10:continue
            for q in (a,b,c):lines.extend(['v %.8f %.8f %.8f'%(q[0],-q[1],q[2]),'vt %.8f %.8f'%tuple(q[3:5]),'vn %.8f %.8f %.8f'%tuple(q[5:8])])
            lines.append('f '+' '.join(f'{k}/{k}/{k}' for k in range(idx,idx+3)));idx+=3;tri+=1
    assert changed>0
    path=out/f'surface_{slot:04d}_stairs.obj';path.write_text('\n'.join(lines));reports.append({'slot':slot,'file':str(path),'clipped_source_triangles':changed,'result_triangles':tri})
(out/'build.json').write_text(json.dumps({'cut_min':lo,'cut_max':hi,'surfaces':reports,'tread_z_cod':[852,840,828],'tread_depth_cod':32,'drop_cod':36},indent=2));print(reports)
