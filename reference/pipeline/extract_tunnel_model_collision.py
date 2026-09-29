# Reference implementation: configure paths, source hashes and project dependencies first.
"""Recover source XModel collision triangles from their plane/barycentric forms."""
import hashlib,json,math,pathlib,struct,zlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
raw=pathlib.Path('C:/Program Files (x86)/Steam/steamapps/common/Call of Duty 4/usermaps/mp_tunnel/mp_tunnel.ff').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='5e6b87d5f96320669af9968d9cc14aec805e41e4159e0077251dc92e97172ee9'
d=zlib.decompress(raw[12:]);out=ROOT/'artifacts/tunnel-models';report=[]
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def solve(a,b,c):
    bc=cross(b,c);ca=cross(c,a);ab=cross(a,b);det=dot(a[:3],bc)
    assert abs(det)>1e-12
    return tuple((a[3]*bc[k]+b[3]*ca[k]+c[3]*ab[k])/det for k in range(3))
for model,header,start,count in [(0,8081,39713,1),(1,259424,460788,3),(2,478696,491794,1)]:
    assert struct.unpack_from('<II',d,header+152)==(0xffffffff,count)
    cursor=start+count*44;vertices=[];faces=[];surface_reports=[]
    for s in range(count):
        v=struct.unpack_from('<Ii6fiii',d,start+s*44)
        assert v[0]==0xffffffff and v[1]>0
        lo,hi=v[2:5],v[5:8];contents=v[9];points=[]
        for t in range(v[1]):
            values=struct.unpack_from('<12f',d,cursor+t*48)
            a,b,c=values[:4],values[4:8],values[8:]
            assert all(math.isfinite(x) for x in values)
            assert abs(dot(a[:3],a[:3])-1)<.001
            tri=[solve(a,(*b[:3],b[3]+u),(*c[:3],c[3]+w)) for u,w in ((0,0),(1,0),(0,1))]
            assert all(lo[k]-.01<=p[k]<=hi[k]+.01 for p in tri for k in range(3)),(model,s,t)
            points.extend(tri)
            if contents & 0x10001:
                i=len(vertices);vertices.extend(tri)
                normal=cross(tuple(tri[1][k]-tri[0][k] for k in range(3)),tuple(tri[2][k]-tri[0][k] for k in range(3)))
                faces.append((i,i+1,i+2) if dot(normal,a[:3])>0 else (i,i+2,i+1))
        cursor+=v[1]*48
        actual=tuple(min(p[k] for p in points) for k in range(3))+tuple(max(p[k] for p in points) for k in range(3))
        error=max(abs(x-y) for x,y in zip(actual,(*lo,*hi)));assert error<.02,(model,s,error)
        surface_reports.append({'index':s,'source_triangles':v[1],'contents':contents,'included':bool(contents&0x10001),'bounds_error_cod':error})
    lines=['# Source model collision; centimetres, source axes']
    lines+=['v '+' '.join(format(x*2.54,'.9g') for x in p) for p in vertices]
    lines+=['f '+' '.join(str(i+1) for i in f) for f in faces]
    name='TunnelModelCollision_%04d.obj'%model;(out/name).write_text('\n'.join(lines)+'\n')
    report.append({'model_id':model,'obj':name,'triangles':len(faces),'surfaces':surface_reports})
(out/'collision.json').write_text(json.dumps({'models':report,'source_sha256':hashlib.sha256(raw).hexdigest()},indent=2))
print(json.dumps(report))
