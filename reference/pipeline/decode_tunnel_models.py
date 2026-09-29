# Reference implementation: configure paths, source hashes and project dependencies first.
"""Decode captured IW3 LOD0 static models without original texture pixels.

Vertices are already in model space: applying base bone transforms again would
double-transform the palm. Check combined bounds against the XModel header.
"""
import hashlib, json, math, pathlib, struct

ROOT=pathlib.Path(__file__).resolve().parents[1]
SOURCE=ROOT/'artifacts/mp_tunnel/models-20260927T165429174Z'
DEST=ROOT/'artifacts/tunnel-models'

def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b): return sum(x*y for x,y in zip(a,b))

def main():
    assert json.loads((SOURCE/'status.json').read_text())['status']=='captured'
    metadata=json.loads((SOURCE/'models.json').read_text())
    DEST.mkdir(parents=True,exist_ok=True)
    reports=[]
    for model in metadata['models']:
        src=SOURCE/f"model_{model['id']:04d}"
        header=(src/'header.bin').read_bytes()
        declared=struct.unpack_from('<6f',header,172)
        lines=['# Captured map model: cm, source axes; no original texture references.']
        vertices=[]; offset=0; slots=[]; triangles=0; degenerate=0; flipped=0
        for surface in model['surfaces']:
            assert not surface['deformed'], 'Skinned surfaces need a separate decoder'
            prefix=f"surface_{surface['index']}"
            raw=(src/(prefix+'_vertices.bin')).read_bytes()
            indices=(src/(prefix+'_triangles.bin')).read_bytes()
            assert len(raw)==surface['vertices']*32 and len(indices)==surface['triangles']*6
            slot='model_%04d_surface_%02d'%(model['id'],surface['index'])
            slots.append({'slot':slot,'source_material':surface['material']})
            points=[]; normals=[]
            for i in range(surface['vertices']):
                o=i*32; point=struct.unpack_from('<3f',raw,o)
                uv=struct.unpack_from('<2e',raw,o+20)
                packed=struct.unpack_from('<4B',raw,o+24)
                n=tuple((packed[k]-127)*(packed[3]+192)/32385 for k in range(3))
                length=math.sqrt(dot(n,n)); assert length>.1
                n=tuple(v/length for v in n)
                assert all(math.isfinite(v) for v in (*point,*uv,*n))
                points.append(point); vertices.append(point); normals.append(n)
                lines.append('v '+' '.join(format(v*2.54,'.9g') for v in point))
                lines.append('vt %.9g %.9g'%(uv[0],1-uv[1]))
                lines.append('vn '+' '.join(format(v,'.9g') for v in n))
            lines.append('usemtl '+slot)
            for tri in struct.iter_unpack('<3H',indices):
                assert max(tri)<len(points)
                a,b,c=(points[j] for j in tri)
                normal=cross(tuple(b[k]-a[k] for k in range(3)),tuple(c[k]-a[k] for k in range(3)))
                if len(set(tri))<3 or dot(normal,normal)<1e-16:
                    degenerate+=1; continue
                average=tuple(sum(normals[j][k] for j in tri) for k in range(3))
                if dot(normal,average)<0: tri=(tri[0],tri[2],tri[1]); flipped+=1
                lines.append('f '+' '.join('/'.join([str(offset+j+1)]*3) for j in tri)); triangles+=1
            offset+=len(points)
        actual=tuple(min(p[k] for p in vertices) for k in range(3))+tuple(max(p[k] for p in vertices) for k in range(3))
        error=max(abs(a-b) for a,b in zip(actual,declared))
        assert error<.001, (model['name'],actual,declared)
        filename='TunnelModel_%04d.obj'%model['id']
        mtl=pathlib.Path(filename).with_suffix('.mtl').name
        (DEST/filename).write_text('mtllib '+mtl+'\n'+'\n'.join(lines)+'\n')
        (DEST/mtl).write_text('\n'.join('newmtl '+s['slot']+'\nKd 0.5 0.5 0.5\n' for s in slots))
        reports.append({'id':model['id'],'source_name':model['name'],'obj':filename,'slots':slots,
                        'vertices':len(vertices),'triangles':triangles,'degenerate_triangles_removed':degenerate,
                        'winding_flips':flipped,'bounds_cod':actual,'header_bounds_error_cod':error})
    hashes={str(p.relative_to(SOURCE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.rglob('*') if p.is_file()}
    report={'source':str(SOURCE),'source_hashes':hashes,'models':reports,'instances':metadata['instances'],
            'coordinates':{'local_mesh':'source axes in cm; legacy UE OBJ import reflects Y',
                           'instance_origin':'COD4 units; multiply by 2.54 and reflect Y',
                           'instance_axis':'basis vectors in rows; UE yaw is negative source yaw',
                           'scale':'preserve source uniform scale'},
            'limitations':['Static instances only','Model collision currently uses visible triangles','Foliage transparency needs visual verification']}
    (DEST/'decoded.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'models':len(reports),'instances':len(metadata['instances']),'triangles_per_unique_models':sum(m['triangles'] for m in reports),'bounds_verified':True}))

if __name__=='__main__': main()
