"""Build a portable, hashed per-object manifest and local OBJ geometry."""
import collections
import hashlib
import json
import math
from pathlib import Path
import re

from .geometry import cross, dot, reconstruct, sub
from .hull import cloud_hull
from .parser import MapError, mesh_grid, numbers, parse

TOOL = {'caulk','clip','playerclip','clip_player','trigger','ladder','nodraw','portal','hint','skip','weaponclip','clip_missile'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_name(value):
    readable = re.sub(r'[^A-Za-z0-9_]', '_', value).strip('_')[:48] or 'unnamed'
    return readable+'_'+hashlib.sha256(value.encode()).hexdigest()[:8]


def point_cm(point, scale):
    return [point[0]*scale, -point[1]*scale, point[2]*scale]


def tool_material(name):
    base = name.lower().rsplit('/',1)[-1]
    return base in TOOL or base.startswith('sky')


def semantic(obj, mats):
    names = {m.lower().rsplit('/',1)[-1] for m in mats}
    lines = ' '.join(s for _,s in obj['lines']).lower()
    classname = obj['entity'].get('classname','')
    if classname.startswith('trigger_') or 'trigger' in names:
        return 'trigger'
    if 'noncolliding' in lines or names <= {'weaponclip','clip_missile','portal','hint','skip','nodraw'}:
        return 'noncolliding'
    if names & {'clip','playerclip','clip_player'}:
        return 'playerclip'
    if names and all(n.startswith('sky') or n in {'caulk','nodraw'} for n in names) and any(n.startswith('sky') for n in names):
        return 'sky'
    if 'ladder' in names:
        return 'ladder'
    return 'solid'


def brush_uv(point, normal, texdef, default_repeat):
    # IWMap texdef: repeat size U/V, shift U/V, rotation, tool integer.
    # Exported files often have only reconstructed repeat size, not original UVs.
    axis=max(range(3), key=lambda k:abs(normal[k]))
    axes=[k for k in range(3) if k!=axis]
    words=texdef.split()
    try:
        values=numbers(' '.join(words[:6]),6)
    except MapError:
        raise MapError('Unsupported brush texture definition: '+texdef)
    su,sv,shift_u,shift_v,angle,_=values
    if abs(su)<1e-8 or abs(sv)<1e-8:
        raise MapError('Zero brush texture repeat size')
    radians=math.radians(angle)
    x,y=point[axes[0]],point[axes[1]]
    return [(x*math.cos(radians)-y*math.sin(radians)+shift_u)/su,
            (x*math.sin(radians)+y*math.cos(radians)+shift_v)/sv]


def tessellate(width,height,points,uvs,steps,linear=False):
    if linear or width==height==2:
        faces=[[x*height+y,(x+1)*height+y,(x+1)*height+y+1,x*height+y+1]
               for x in range(width-1) for y in range(height-1)]
        return points,faces,uvs
    if width%2==0 or height%2==0:
        raise MapError('Curved mesh needs odd control-grid dimensions; use splitGeo for linear grids')
    vertices,out_uvs,faces=[],[],[]
    for bx in range(0,width-2,2):
        for by in range(0,height-2,2):
            offset=len(vertices)
            for ix in range(steps+1):
                t=ix/steps; wx=((1-t)**2,2*t*(1-t),t*t)
                for iy in range(steps+1):
                    s=iy/steps; wy=((1-s)**2,2*s*(1-s),s*s)
                    ids=[(bx+a)*height+by+b for a in range(3) for b in range(3)]
                    weights=[wx[a]*wy[b] for a in range(3) for b in range(3)]
                    vertices.append([sum(points[i][k]*w for i,w in zip(ids,weights)) for k in range(3)])
                    out_uvs.append([sum(uvs[i][k]*w for i,w in zip(ids,weights)) for k in range(2)])
            for ix in range(steps):
                for iy in range(steps):
                    a=offset+ix*(steps+1)+iy;b=a+steps+1
                    faces.append([a,b,b+1,a+1])
    return vertices,faces,out_uvs


def emit_obj(path,obj_id,verts,faces,mats,uv_faces,scale,material_ids):
    lo=[min(v[k] for v in verts) for k in range(3)]
    hi=[max(v[k] for v in verts) for k in range(3)]
    center=[(a+b)/2 for a,b in zip(lo,hi)]
    lines=['mtllib materials.mtl','o '+obj_id]
    offset=triangles=0
    for face,mat,uvs in zip(faces,mats,uv_faces):
        poly=[verts[i] for i in face]
        lines+=['v '+' '.join(f'{(p[k]-center[k])*scale:.10g}' for k in range(3)) for p in poly]
        lines+=['vt '+' '.join(f'{v:.10g}' for v in uv) for uv in uvs]
        lines.append('usemtl '+material_ids[mat])
        for j in range(1,len(poly)-1):
            n=cross(sub(poly[j],poly[0]),sub(poly[j+1],poly[0]))
            if dot(n,n)<1e-12:
                continue
            # UE legacy OBJ import reflects Y. Reverse winding at the boundary.
            ids=(offset+1,offset+j+2,offset+j+1)
            lines.append('f '+' '.join(f'{i}/{i}' for i in ids));triangles+=1
        offset+=len(poly)
    if not triangles:
        raise MapError('Object contains no nondegenerate triangles')
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return point_cm(center,scale),[(b-a)*scale for a,b in zip(lo,hi)],triangles


def prepare(source,output,config=None):
    source,output=Path(source).resolve(),Path(output).resolve()
    config=config or {}
    from .config import validate_config
    validate_config(config)
    if not source.is_file():raise MapError('Source map not found: '+str(source))
    scale=float(config.get('units_to_cm',2.54));steps=int(config.get('patch_subdivisions',8))
    if not math.isfinite(scale) or scale<=0 or not 1<=steps<=64:raise MapError('Invalid scale or patch subdivisions')
    entities,objects,unsupported=parse(source.read_text(encoding='utf-8-sig'))
    if not objects:raise MapError('No supported source geometry found')
    output.mkdir(parents=True,exist_ok=True)
    dependencies={}
    for spec in config.get('materials',{}).values():
        if spec.get('texture'):dependencies[str(Path(spec['texture']).resolve())]=digest(spec['texture'])
    for filename in config.get('sky',{}).get('faces',{}).values():dependencies[str(Path(filename).resolve())]=digest(filename)
    if config.get('scripts'):
        if not Path(config['scripts']).is_dir():raise MapError('Script directory not found')
        dependencies.update({str(p.resolve()):digest(p) for p in Path(config['scripts']).rglob('*.gsc')})
    for directory in config.get('texture_roots',[]):
        dependencies.update({str(p.resolve()):digest(p) for p in Path(directory).rglob('*') if p.is_file() and p.suffix.lower() in ('.tga','.png','.jpg','.jpeg','.dds')})
    config_hash=hashlib.sha256(json.dumps({'config':config,'dependencies':dependencies},sort_keys=True).encode()).hexdigest()
    fingerprint=hashlib.sha256((digest(source)+config_hash+'schema1').encode()).hexdigest()
    if (output/'manifest.json').exists():
        previous=json.loads((output/'manifest.json').read_text())
        if previous['fingerprint']!=fingerprint:
            raise MapError('Output belongs to different inputs; select a new output directory')
    (output/'source.map').write_bytes(source.read_bytes())
    known_materials={s['material'] for o in objects for s in o['sides']}
    for o in objects:
        if o['kind']=='patch':
            try:known_materials.add(mesh_grid(o)[4])
            except MapError:pass
    material_ids={m:safe_name(m) for m in sorted(known_materials)}
    # Exact basenames only; ambiguity is an error, never an arbitrary choice.
    texture_index={}
    for directory in config.get('texture_roots',[]):
        if not Path(directory).is_dir():raise MapError('Texture root not found: '+str(directory))
        for file in Path(directory).rglob('*'):
            if file.suffix.lower() in ('.tga','.png','.jpg','.jpeg','.dds'):
                key=file.stem.lower().removesuffix('.iwi_out')
                texture_index.setdefault(key,[]).append(file.resolve())
    records,issues=[],list(unsupported)
    fallbacks=[]
    for obj in objects:
        try:
            fallback=False
            if obj['kind']=='brush':
                sides=[(s['points'],s['material']) for s in obj['sides']]
                try:verts,faces,planes=reconstruct(sides)
                except ValueError:
                    if not config.get('allow_fallback_hulls',False):raise
                    verts,faces=cloud_hull([p for pts,_ in sides for p in pts]);planes=[];fallback=True
                source_planes=[]
                for side in obj['sides']:
                    n=cross(sub(side['points'][1],side['points'][0]),sub(side['points'][2],side['points'][0]));length=math.sqrt(dot(n,n))
                    if length>1e-8:
                        n=tuple(x/length for x in n);source_planes.append((n,dot(n,side['points'][0]),side))
                matched=[min(source_planes,key=lambda s:max(abs(dot(s[0],verts[i])-s[1]) for i in f)) for f in faces]
                mats=[s[2]['material'] for s in matched]
                uvs=[[brush_uv(verts[i],s[0],s[2]['texdef'],128) for i in f] for f,s in zip(faces,matched)]
                box=(not fallback and len(verts)==8 and all(sum(abs(v)>1e-5 for v in n)==1 for n,_ in planes))
                shape='box' if box else 'convex'
                uv_mode='iw_repeat_projection'
            else:
                width,height,verts,uvs,mat=mesh_grid(obj)
                verts,faces,uvs=tessellate(width,height,verts,uvs,steps,any('splitGeo' in s for _,s in obj['lines']))
                mats=[mat]*len(faces);uvs=[[uvs[i] for i in f] for f in faces]
                shape='surface';uv_mode='source_mesh_uv'
            sem=semantic(obj,mats)
            collision='none' if sem in ('noncolliding','sky','trigger','ladder') else 'box' if shape=='box' else 'convex' if shape=='convex' else config.get('surface_collision','dop26' if config.get('profile')=='project_jump' else 'triangles')
            if collision not in ('none','box','convex','triangles','dop26'):raise MapError('Invalid surface collision policy')
            override=config.get('object_overrides',{}).get(obj['id'],{})
            collision=override.get('collision',collision)
            if collision not in ('none','box','convex','triangles','dop26'):raise MapError('Invalid object collision override')
            filename=obj['id']+'.obj'
            center,size,triangles=emit_obj(output/filename,obj['id'],verts,faces,mats,uvs,scale,material_ids)
            if fallback:fallbacks.append(obj['id'])
            records.append({'id':obj['id'],'kind':obj['kind'],'index':obj['index'],'source_line':obj['line'],'entity_id':obj['entity_id'],'entity':obj['entity'],'obj':filename,'obj_sha256':digest(output/filename),'center_cm':center,'size_cm':size,'materials':list(dict.fromkeys(mats)),'collision':collision,'semantic':sem,'shape':shape,'tool_surface':all(tool_material(m) for m in mats),'fallback_hull':fallback,'triangles':triangles,'uv_mode':uv_mode,'layer':next((s[6:].strip('"') for _,s in obj['lines'] if s.startswith('layer ')),'')})
        except (ValueError,StopIteration,OverflowError) as exc:
            issues.append({'id':obj['id'],'source_line':obj['line'],'reason':str(exc) or type(exc).__name__})
    materials={}
    for row in records:row['slick']=bool(config.get('object_overrides',{}).get(row['id'],{}).get('slick',False))
    for name,asset_id in material_ids.items():
        spec=dict(config.get('materials',{}).get(name,{}))
        if not spec and not tool_material(name):
            candidates=texture_index.get(name.rsplit('/',1)[-1].lower(),[])
            if len(candidates)>1:raise MapError('Ambiguous diffuse texture for '+name+'; provide an explicit material mapping')
            if candidates:spec['texture']=str(candidates[0])
        texture=spec.get('texture')
        if texture:
            texture=Path(texture).resolve()
            if not texture.is_file():raise MapError('Material texture not found: '+str(texture))
            spec.update(texture=str(texture),texture_sha256=digest(texture))
        materials[name]={'id':asset_id,'tool':tool_material(name),**spec}
    missing_textures=[name for name,spec in materials.items() if not spec['tool'] and not any(k in spec for k in ('texture','unreal_asset','color'))]
    (output/'materials.mtl').write_text('\n'.join('newmtl '+v+'\nKd 0.6 0.6 0.6' for v in material_ids.values()))
    from .gameplay import resolve_gameplay
    gameplay=resolve_gameplay(entities,records,config,scale)
    map_id=config.get('map_id',safe_name(source.stem))
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}',map_id):raise MapError('map_id must be a valid asset identifier')
    manifest={'schema_version':1,'map_id':map_id,'source':str(source),'source_sha256':digest(source),'fingerprint':fingerprint,'config':config,'dependencies':dependencies,'entities':entities,'objects':records,'materials':materials,'gameplay':gameplay,'issues':issues,'fallback_hulls':fallbacks,'summary':{'source_objects':len(objects),'prepared_objects':len(records),'brushes':sum(o['kind']=='brush' for o in records),'patches':sum(o['kind']=='patch' for o in records),'triangles':sum(o['triangles'] for o in records),'collisions':dict(collections.Counter(o['collision'] for o in records))},'limitations':['IW3XO reconstructed exports do not retain original brush UV offsets/rotation or original patch diffuse materials.','Bezier mesh tessellation and auto convex/DOP collision are approximations requiring playtesting.','Arbitrary GSC is not executed; unresolved behaviours and entities are reported.']}
    manifest['status']='prepared_with_issues' if issues else 'prepared'
    manifest['missing_materials']=missing_textures
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest
