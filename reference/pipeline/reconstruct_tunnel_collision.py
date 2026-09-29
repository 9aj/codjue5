# Reference implementation: configure paths, source hashes and project dependencies first.
"""Reconstruct SHA-pinned Tunnel convex brushes from stock COD4 plane records."""
import pathlib,json,struct,itertools,math
root=pathlib.Path(__file__).resolve().parents[1]
d=(root/'artifacts/mp_tunnel/intake/decompressed.bin').read_bytes()
data=json.loads((root/'artifacts/tunnel-collision.json').read_text())
plane_offset,plane_ptr,plane_count=3527342,1074537333,646
side_offset,side_ptr,side_count=12164815,1076616753,261
P=[struct.unpack_from('<4f',d,plane_offset+20*i) for i in range(plane_count)]
assert all(abs(sum(x*x for x in p[:3])-1)<.0001 for p in P)
S=[]
for i in range(side_count):
 ptr,mat=struct.unpack_from('<II',d,side_offset+12*i)
 assert 0<=ptr-plane_ptr<20*plane_count and (ptr-plane_ptr)%20==0 and mat<40
 S.append((ptr-plane_ptr)//20)
assert sum(b['non_axial_side_count'] for b in data['world_brushes'])==261

def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def solve(a,b,c):
 bc=cross(b,c);ca=cross(c,a);ab=cross(a,b);det=dot(a[:3],bc)
 if abs(det)<1e-8:return None
 return tuple((a[3]*bc[i]+b[3]*ca[i]+c[3]*ab[i])/det for i in range(3))
records=[];obj=['# Original map collision geometry; no source materials or models'];offset=0
for b in data['world_brushes']:
 n=b['non_axial_side_count']
 if not n or not(b['contents']&0x10001):continue
 first=(b['side_pointer']-side_ptr)//12
 assert b['side_pointer']==side_ptr+first*12 and 0<=first and first+n<=261
 planes=[]
 for k in range(3):
  normal=[0.,0.,0.];normal[k]=1.;planes.append((*normal,b['maxs_cod'][k]))
  normal[k]=-1.;planes.append((*normal,-b['mins_cod'][k]))
 planes += [P[S[i]] for i in range(first,first+n)]
 # Clip a box by each side plane, retaining a closed polygon boundary.
 lo,hi=b['mins_cod'],b['maxs_cod']
 corners=[tuple((hi[k] if mask&(1<<k) else lo[k]) for k in range(3)) for mask in range(8)]
 polys=[[corners[i] for i in f] for f in ((0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6))]
 for p in planes[6:]:
  clipped=[];cap=[]
  for poly in polys:
   new=[]
   for va,vb in zip(poly,poly[1:]+poly[:1]):
    da,db=dot(p[:3],va)-p[3],dot(p[:3],vb)-p[3]
    if da<=0:new.append(va)
    if abs(da)<1e-8 and not any(sum((va[k]-q[k])**2 for k in range(3))<1e-12 for q in cap):cap.append(va)
    if (da<0<db) or (db<0<da):
     t=da/(da-db);v=tuple(va[k]+t*(vb[k]-va[k]) for k in range(3));new.append(v)
     if not any(sum((v[k]-q[k])**2 for k in range(3))<1e-12 for q in cap):cap.append(v)
   if len(new)>=3:clipped.append(new)
  if len(cap)>=3:
   center=tuple(sum(v[k] for v in cap)/len(cap) for k in range(3))
   axis=cross(p[:3],(1,0,0) if abs(p[0])<.9 else (0,1,0));other=cross(p[:3],axis)
   def angle(v):
    delta=tuple(v[k]-center[k] for k in range(3));return math.atan2(dot(delta,other),dot(delta,axis))
   cap.sort(key=angle);clipped.append(cap)
  polys=clipped
 verts=[];faces=[]
 for poly in polys:
  ids=[]
  for v in poly:
   j=next((i for i,w in enumerate(verts) if sum((v[k]-w[k])**2 for k in range(3))<1e-10),None)
   if j is None:j=len(verts);verts.append(v)
   if not ids or ids[-1]!=j:ids.append(j)
  if len(ids)>1 and ids[0]==ids[-1]:ids.pop()
  for j in range(1,len(ids)-1):faces.append((ids[0],ids[j+1],ids[j]))
 assert len(verts)>=4,(b['index'],len(verts))
 errors=[abs(min(v[k] for v in verts)-b['mins_cod'][k]) for k in range(3)]+[abs(max(v[k] for v in verts)-b['maxs_cod'][k]) for k in range(3)]
 assert max(errors)<.15,(b['index'],errors)
 faces=list({tuple(sorted(f)):f for f in faces if len(set(f))==3}.values())
 edges={}
 for f in faces:
  for a,c in zip(f,(f[1],f[2],f[0])):key=tuple(sorted((a,c)));edges[key]=edges.get(key,0)+1
 assert all(v==2 for v in edges.values()),(b['index'],'not closed')
 obj.append('o COD4_brush_'+str(b['index']))
 # UE OBJ importer mirrors Y, so input uses source Y; face winding above is
 # reversed again below to account for importer coordinate conversion.
 for v in verts:obj.append('v '+' '.join(format(x*2.54,'.9f') for x in v))
 for f in faces:obj.append('f '+' '.join(str(offset+i+1) for i in (f[0],f[2],f[1])))
 offset+=len(verts)
 records.append({'index':b['index'],'contents':b['contents'],'vertices':len(verts),'triangles':len(faces),'max_bounds_error_cod':max(errors)})
(root/'artifacts/tunnel-unreal-build/TunnelSlopedCollision.obj').write_text('\n'.join(obj)+'\n')
(root/'artifacts/tunnel-convex-reconstruction.json').write_text(json.dumps({'plane_offset':plane_offset,'side_offset':side_offset,'brushes':records},indent=2))
print(len(records),'brushes',offset,'vertices',sum(r['triangles'] for r in records),'triangles')
