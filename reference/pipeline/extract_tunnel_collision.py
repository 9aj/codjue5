# Reference implementation: configure paths, source hashes and project dependencies first.
"""Extract collision facts from the inspected Tunnel fastfile.

Offsets are a SHA-256-pinned profile, not a general fastfile parser. No executable
assets are loaded. Layout cross-checked against OpenAssetTools IW3_Assets.h.
"""
import hashlib,json,math,pathlib,struct,sys,zlib
root=pathlib.Path(__file__).resolve().parents[1]
raw=pathlib.Path(sys.argv[1]).read_bytes()
expected='5e6b87d5f96320669af9968d9cc14aec805e41e4159e0077251dc92e97172ee9'
assert hashlib.sha256(raw).hexdigest()==expected,'Unrecognized fastfile; offsets are not portable'
d=zlib.decompress(raw[12:])
intake=root/'artifacts/mp_tunnel/intake'
intake.mkdir(parents=True,exist_ok=True)
(intake/'decompressed.bin').write_bytes(d)
model_offset=12476873
brush_offset=model_offset+14*72
assert struct.unpack_from('<4I',d,12160983)==(14,0xffffffff,455,0xffffffff)
entities=json.loads((root/'artifacts/mp_tunnel/20260927T163238586Z-a01d31d1/ue5/gameplay-entities.json').read_text(encoding='utf-8-sig'))['entities']
by_model={int(e['properties']['model'][1:]):e for e in entities if e['category']=='trigger'}
def bounds_to_ue(lo,hi,origin=(0,0,0)):
    center=[((lo[k]+hi[k])*0.5+origin[k])*2.54 for k in range(3)]
    center[1]*=-1
    return {'center_cm':center,'half_extent_cm':[(hi[k]-lo[k])*1.27 for k in range(3)]}
brushes=[]
for i in range(455):
    v=struct.unpack_from('<3fi3fII',d,brush_offset+80*i)
    lo,hi=v[:3],v[4:7]
    assert all(math.isfinite(x) and abs(x)<200000 for x in (*lo,*hi))
    assert all(lo[k]<hi[k] for k in range(3))
    brushes.append({'index':i,'mins_cod':lo,'maxs_cod':hi,'contents':v[3],'non_axial_side_count':v[7],
                    'side_pointer':v[8],**bounds_to_ue(lo,hi)})
triggers=[]
for i in range(1,14):
    offset=model_offset+i*72
    v=struct.unpack_from('<7f',d,offset)
    radius=math.sqrt(sum(max(abs(v[k]),abs(v[k+3]))**2 for k in range(3)))
    assert abs(radius-v[6])<0.01
    leaf=struct.unpack_from('<HHii6fih',d,offset+28)
    brush=brushes[441+i]
    assert leaf[2]==brush['contents']==0x8000001
    assert brush['non_axial_side_count']==0
    assert leaf[-2]==1655+i
    for k in range(3):
        assert abs(leaf[4+k]-(brush['mins_cod'][k]-0.125))<0.001
        assert abs(leaf[7+k]-(brush['maxs_cod'][k]+0.125))<0.001
        assert abs(v[k]-(brush['mins_cod'][k]-1))<0.001
        assert abs(v[k+3]-(brush['maxs_cod'][k]+1))<0.001
    entity=by_model[i]
    origin=list(map(float,entity['properties']['origin'].split()))
    triggers.append({'entity_index':entity['index'],'properties':entity['properties'],
        'model_index':i,'brush_index':441+i,
        **bounds_to_ue(brush['mins_cod'],brush['maxs_cod'],origin)})
result={'source_sha256':expected,'layout_reference':'https://github.com/Laupetin/OpenAssetTools/blob/main/src/Common/Game/IW3/IW3_Assets.h',
    'profile':{'model_offset':model_offset,'model_stride':72,'brush_offset':brush_offset,'brush_stride':80},
    'world_brushes':brushes[:442],'triggers':triggers,
    'limitations':['Non-axial brushes require their side planes; do not substitute bounding boxes.','Contents masks must be classified before building player collision.']}
out=root/'artifacts/tunnel-collision.json'
out.write_text(json.dumps(result,indent=2)+'\n')
print(f'Validated {len(brushes)} brushes and {len(triggers)} exact box triggers: {out}')
