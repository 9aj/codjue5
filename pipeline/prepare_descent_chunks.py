"""Offline, attribute-preserving grid clipping. Never touches Unreal assets."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def area(tri):
    a,b,c=[v[:3] for v in tri]
    x=[b[i]-a[i] for i in range(3)];y=[c[i]-a[i] for i in range(3)]
    cross=(x[1]*y[2]-x[2]*y[1],x[2]*y[0]-x[0]*y[2],x[0]*y[1]-x[1]*y[0])
    return math.sqrt(sum(v*v for v in cross))*.5

def split(poly,axis,plane):
    low=[];high=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=a[axis]-plane;db=b[axis]-plane
        if da<=0:low.append(a)
        if da>=0:high.append(a)
        if (da<0<db) or (db<0<da):
            t=da/(da-db)
            p=tuple(plane if i==axis else a[i]+(b[i]-a[i])*t for i in range(len(a)))
            low.append(p);high.append(p)
    return low,high

def partition(triangle,size):
    polygons=[triangle]
    for axis in range(3):
        result=[]
        for poly in polygons:
            lo=min(v[axis] for v in poly);hi=max(v[axis] for v in poly)
            for grid in range(math.floor(lo/size)+1,math.ceil(hi/size)):
                left,poly=split(poly,axis,grid*size)
                if len(left)>=3:result.append(left)
            if len(poly)>=3:result.append(poly)
        polygons=result
    result=[]
    for poly in polygons:
        for i in range(1,len(poly)-1):
            tri=[poly[0],poly[i],poly[i+1]]
            if area(tri)>1e-12:result.append(tri)
    return result

def read_obj(path):
    positions=[];uvs=[];normals=[];faces=[];material=None
    for line in path.read_text().splitlines():
        p=line.split()
        if not p:continue
        if p[0]=='v':positions.append(tuple(map(float,p[1:4])))
        elif p[0]=='vt':uvs.append(tuple(map(float,p[1:3])))
        elif p[0]=='vn':normals.append(tuple(map(float,p[1:4])))
        elif p[0]=='usemtl':material=p[1]
        elif p[0]=='f':
            assert len(p)==4 and material, 'Expected triangulated OBJ with materials'
            vertices=[]
            for corner in p[1:]:
                vi,ti,ni=map(int,corner.split('/'))
                assert min(vi,ti,ni)>0
                vertices.append(positions[vi-1]+uvs[ti-1]+normals[ni-1])
            faces.append((material,vertices))
    return faces

def prepare(source,out,size):
    assert size>0
    faces=read_obj(source);buckets=defaultdict(list);checks=[]
    for index,(mat,tri) in enumerate(faces):
        pieces=partition(tri,size)
        expected=area(tri);actual=sum(area(t) for t in pieces)
        assert abs(expected-actual)<=max(1e-7,expected*1e-9),(index,expected,actual)
        # First moments detect translations and incorrect cuts, in addition to area loss.
        for axis in range(3):
            m0=expected*sum(v[axis] for v in tri)/3
            m1=sum(area(t)*sum(v[axis] for v in t)/3 for t in pieces)
            assert abs(m0-m1)<=max(1e-4,abs(m0)*1e-8,expected*1e-6)
        for t in pieces:
            cell=tuple(math.floor(sum(v[k] for v in t)/3/size) for k in range(3))
            kind='glass' if mat in ('surface_0019','surface_0022') else 'opaque'
            buckets[(kind,*cell)].append((mat,t,index))
        checks.append(abs(expected-actual))
    out.mkdir(parents=True,exist_ok=False)
    chunks=[]
    for key,triangles in sorted(buckets.items()):
        kind,*cell=key
        origin=[(x+.5)*size for x in cell]
        name=kind+'_'+ '_'.join(('m'+str(-x)) if x<0 else str(x) for x in cell)
        materials=sorted({t[0] for t in triangles})
        # Per-corner serialization preserves hard edges and UV seams.
        lines=['mtllib materials.mtl'];face_lines=[]
        last=None;counter=0
        for material,tri,index in triangles:
            if material!=last:face_lines.append('usemtl '+material);last=material
            ids=[]
            for vertex in tri:
                counter+=1;ids.append(f'{counter}/{counter}/{counter}')
                lines.append('v '+' '.join(format(vertex[k]-origin[k],'.12g') for k in range(3)))
                lines.append('vt '+' '.join(format(v,'.12g') for v in vertex[3:5]))
                lines.append('vn '+' '.join(format(v,'.12g') for v in vertex[5:8]))
            face_lines.append('f '+' '.join(ids))
        lines+=face_lines
        target=out/(name+'.obj');target.write_text('\n'.join(lines)+'\n')
        mins=[min(v[k] for _,t,_ in triangles for v in t) for k in range(3)]
        maxs=[max(v[k] for _,t,_ in triangles for v in t) for k in range(3)]
        assert all(maxs[k]-mins[k]<=size+1e-7 for k in range(3))
        chunks.append({'name':name,'file':target.name,'kind':kind,'origin_ue_cm':[origin[0],-origin[1],origin[2]],
                       'bounds_obj_cm':[mins,maxs],'triangles':len(triangles),'materials':materials,
                       'source_faces':sorted({t[2] for t in triangles}),
                       'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
    (out/'materials.mtl').write_text('\n'.join('newmtl '+m+'\nKd 0.5 0.5 0.5\nillum 1\n' for m in sorted({m for m,t in faces})))
    report={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'cell_size_cm':size,'input_triangles':len(faces),'output_triangles':sum(c['triangles'] for c in chunks),
            'max_source_face_area_error_cm2':max(checks),'verified_area_and_first_moment_per_face':True,
            'coordinate_note':'OBJ input uses legacy importer Y sign. Local origins are converted to UE (x,-y,z).',
            'chunks':chunks}
    (out/'manifest.json').write_text(json.dumps(report,indent=2))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--cell-cm',type=float,default=10000)
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/descent-chunks-100m')
    args=parser.parse_args()
    report=prepare(ROOT/'artifacts/unreal-build/DescentStyledWorld.obj',args.output,args.cell_cm)
    print(json.dumps({k:v for k,v in report.items() if k!='chunks'},indent=2))
    print('Chunks:',len(report['chunks']))
