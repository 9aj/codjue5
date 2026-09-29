# Reference implementation: configure paths, source hashes and project dependencies first.
"""SHA-pinned collision terrain and static-model placement audit for Tunnel."""
import hashlib,json,math,pathlib,struct,zlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
SOURCE=pathlib.Path('C:/Program Files (x86)/Steam/steamapps/common/Call of Duty 4/usermaps/mp_tunnel/mp_tunnel.ff')
raw=SOURCE.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='5e6b87d5f96320669af9968d9cc14aec805e41e4159e0077251dc92e97172ee9'
d=zlib.decompress(raw[12:])
assert struct.unpack_from('<4I',d,12160983)==(14,0xffffffff,455,0xffffffff)
verts=list(struct.iter_unpack('<3f',d[12332761:12370801]))
triangles=list(struct.iter_unpack('<3H',d[12370801:12408025]))
assert len(verts)==3170 and len(triangles)==6204
assert all(all(math.isfinite(v) and abs(v)<100000 for v in p) for p in verts)
assert max(max(t) for t in triangles)<len(verts)
materials=[]
for i in range(40):
    o=12161935+i*72
    materials.append({'name':d[o:o+64].split(b'\0')[0].decode('ascii'),'contents':struct.unpack_from('<I',d,o+68)[0]})
parts=[struct.unpack_from('<BB2xII',d,12412145+i*12) for i in range(946)]
coverage=[0]*len(triangles);part_materials={};max_bounds_error=0
for i in range(1668):
    v=struct.unpack_from('<6fHHI',d,12423497+i*32)
    assert all(math.isfinite(x) for x in v[:6]) and all(x>=0 for x in v[3:6])
    material,children,index=v[6:]
    if children:
        assert index+children<=1668
        continue
    assert index<len(parts) and material<len(materials)
    part_materials.setdefault(index,set()).add(material)
    count,_,first,_=parts[index]
    assert first+count<=len(triangles)
    for t in triangles[first:first+count]:
        for vertex in t:
            for k in range(3):max_bounds_error=max(max_bounds_error,abs(verts[vertex][k]-v[k])-v[k+3])
assert len(part_materials)==len(parts)
assert max_bounds_error<.02, max_bounds_error
kept=[];excluded=[]
for i,(count,_,first,_) in enumerate(parts):
    flags={materials[m]['contents'] & 0x10001 for m in part_materials[i]}
    assert len(flags)==1, ('Conflicting partition contents',i)
    for j in range(first,first+count):
        coverage[j]+=1
        (kept if next(iter(flags)) else excluded).append(j)
assert set(coverage)=={1}
obj=['# Source player-blocking collision terrain; centimetres, source axes']
obj+=['v '+' '.join(format(v*2.54,'.9g') for v in p) for p in verts]
degenerate=0
for i in kept:
    tri=triangles[i]
    if len(set(tri))<3:degenerate+=1;continue
    obj.append('f '+' '.join(str(v+1) for v in tri))
(ROOT/'artifacts/tunnel-unreal-build/TunnelTerrainCollision.obj').write_text('\n'.join(obj)+'\n')
# Collision placements are an independent source for the visual model transforms.
models=json.loads((ROOT/'artifacts/tunnel-models/decoded.json').read_text())
placements=[]
for i in range(10):
    o=12161135+i*80; p=struct.unpack_from('<3f',d,o+8); inv=struct.unpack_from('<9f',d,o+20)
    matches=[m for m in models['instances'] if max(abs(a-b) for a,b in zip(m['origin_cod'],p))<.002]
    assert len(matches)==1
    m=matches[0];axis=m['axis'];scale=m['scale']
    error=max(abs(inv[r*3+c]-axis[c*3+r]/scale) for r in range(3) for c in range(3))
    assert error<1e-5,(i,error)
    bounds=struct.unpack_from('<6f',d,o+56)
    placements.append({'collision_index':i,'visual_index':m['index'],'transform_error':error,'collision_bounds_cod':bounds})
report={'source_sha256':hashlib.sha256(raw).hexdigest(),'vertices':len(verts),'source_triangles':len(triangles),
        'player_blocking_triangles':len(kept)-degenerate,'excluded_triangles':len(excluded),'degenerate_triangles':degenerate,
        'partitions':len(parts),'max_aabb_error_cod':max_bounds_error,'static_model_transform_checks':placements,
        'materials':materials,'limitations':['Contents filter includes SOLID and PLAYERCLIP','Model collision bounds are evidence only, not box replacements']}
(ROOT/'artifacts/tunnel-terrain.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('materials','static_model_transform_checks')}))
