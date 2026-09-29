# Reference implementation: configure paths, source hashes and project dependencies first.
"""Original procedural replacement materials; preserve world geometry and slots."""
import json,pathlib,unreal as u
ROOT=pathlib.Path(__file__).resolve().parents[1]
WORK=ROOT/'artifacts/tunnel-unreal-build'
SOURCE=ROOT/'artifacts/mp_tunnel/20260927T163238586Z-a01d31d1/ue5'
lib=u.MaterialEditingLibrary
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
assert ed.get_editor_world().get_name()=='Tunnel_Greybox'
assert ed.get_game_world() is None
entries=json.loads((SOURCE/'material-replacements.json').read_text())['materials']
# Material categories preserve readability, not original texture artwork.
styles=[('water',(.025,.16,.19)),('concrete',(.12,.115,.10)),('metal',(.16,.22,.23)),
        ('corrugated',(.28,.34,.30)),('corrugated',(.14,.22,.25)),('grass',(.14,.23,.065)),
        ('snow',(.72,.78,.81)),('stone',(.32,.35,.32)),('tile',(.42,.43,.36)),('tile',(.21,.27,.29)),
        ('concrete',(.23,.26,.22)),('wood',(.30,.17,.075)),('wood',(.36,.23,.12)),
        ('concrete',(.025,.035,.04)),('metal',(.20,.28,.27)),('concrete',(.48,.45,.36)),
        ('concrete',(.42,.43,.37)),('metal',(.045,.055,.05)),('wood',(.24,.13,.055)),
        ('metal',(.38,.43,.42)),('glass',(.06,.18,.20)),('sky',(.3,.4,.5))]
assert len(entries)==len(styles)

def expression(mat,typ):return lib.create_material_expression(mat,typ)
def scalar(mat,name,value):
    node=expression(mat,u.MaterialExpressionScalarParameter);node.set_editor_property('parameter_name',name);node.set_editor_property('default_value',value);return node
def custom(mat,code,inputs):
    node=expression(mat,u.MaterialExpressionCustom);node.set_editor_property('code',code);node.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    items=[]
    for name in inputs:
        v=u.CustomInput();v.set_editor_property('input_name',name);items.append(v)
    node.set_editor_property('inputs',items)
    for name,value in inputs.items():assert lib.connect_material_expressions(value,'',node,name)
    return node

materials={};records=[]
for entry,(kind,tint) in zip(entries,styles):
    if kind=='sky':continue
    name='M_Tunnel_'+entry['slot'];path='/Tunnel/Materials/World/'+name
    mat=u.load_asset(path)
    if mat is None:mat=u.AssetToolsHelpers.get_asset_tools().create_asset(name,'/Tunnel/Materials/World',u.Material,u.MaterialFactoryNew())
    assert mat
    lib.delete_all_material_expressions(mat)
    mat.set_editor_property('two_sided',True)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT if kind=='glass' else u.BlendMode.BLEND_OPAQUE)
    if kind=='glass':mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    p=expression(mat,u.MaterialExpressionWorldPosition);n=expression(mat,u.MaterialExpressionVertexNormalWS)
    color=expression(mat,u.MaterialExpressionVectorParameter);color.set_editor_property('parameter_name','Tint');color.set_editor_property('default_value',u.LinearColor(*tint,1))
    code='''struct Pattern { float h(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);} float n(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(h(i),h(i+float2(1,0)),f.x),lerp(h(i+float2(0,1)),h(i+1),f.x),f.y);} }; Pattern pat;
float3 a=abs(N);float2 q=a.z>max(a.x,a.y)?P.xy:(a.x>a.y?P.yz:P.xz);
float broad=pat.n(q*.018),fine=pat.n(q*.3);float3 col=Tint.rgb*(.72+.3*broad+.10*fine);
'''
    if kind=='wood':code+='float grain=.5+.5*sin(q.x*.3+sin(q.y*.012)*3+pat.n(q*.02)*6);float seam=1-smoothstep(.4,1.1,min(frac(q.x/38),1-frac(q.x/38))*38);col*=.63+.45*grain;col*=1-.5*seam;'
    elif kind=='corrugated':code+='float wave=.5+.5*cos(q.x*.26);col*=.68+.45*wave;float rust=smoothstep(.67,.84,pat.n(q*.034))*smoothstep(.4,.65,broad);col=lerp(col,float3(.22,.075,.025),rust*.6);'
    elif kind in ('tile','stone'):
        code+=('float2 size=float2(90,90);' if kind=='tile' else 'float2 size=float2(110,48);q.x+=fmod(floor(q.y/size.y),2)*size.x*.5;')
        code+='float2 f=frac(q/size);float joint=1-smoothstep(.6,1.5,min(min(f.x,1-f.x)*size.x,min(f.y,1-f.y)*size.y));col*=.85+.25*pat.h(floor(q/size));col=lerp(col,float3(.075,.085,.075),joint);'
    elif kind=='metal':code+='float2 f=frac(q/160);float edge=min(min(f.x,1-f.x),min(f.y,1-f.y))*160;col*=1-.45*(1-smoothstep(.3,1.2,edge));'
    elif kind=='grass':code+='col*=.7+.4*pat.n(q*float2(.18,.6));'
    elif kind=='snow':code+='col=Tint.rgb*(.88+.12*broad+.03*fine);'
    elif kind=='water':code+='col=Tint.rgb*(.7+.15*sin(q.x*.023+q.y*.017)+.1*sin(q.x*.04-q.y*.035));'
    code+='return col;'
    base=custom(mat,code,{'P':p,'N':n,'Tint':color});assert lib.connect_material_property(base,'',u.MaterialProperty.MP_BASE_COLOR)
    rough=.15 if kind in ('water','glass') else .43 if kind in ('metal','tile') else .78
    assert lib.connect_material_property(scalar(mat,'Roughness',rough),'',u.MaterialProperty.MP_ROUGHNESS)
    assert lib.connect_material_property(scalar(mat,'Metallic',.55 if kind in ('metal','corrugated') else 0),'',u.MaterialProperty.MP_METALLIC)
    if kind=='glass':assert lib.connect_material_property(scalar(mat,'Opacity',.2),'',u.MaterialProperty.MP_OPACITY)
    lib.recompile_material(mat);u.EditorAssetLibrary.save_loaded_asset(mat);materials[entry['slot']]=mat
    records.append({**entry,'replacement_asset':path,'description':kind,'license':'Original procedural shader','provenance':'pipeline/style_tunnel_world.py; no original pixels','status':'assigned'})

# One mesh per surface avoids importer-dependent OBJ material-slot remapping.
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.OBJ False')
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
existing={a.get_actor_label():a for a in actors.get_all_level_actors()}
surfaces=json.loads((WORK/'surfaces/manifest.json').read_text());slots=[]
combined_min=[float('inf')]*3;combined_max=[-float('inf')]*3
for surface in surfaces:
    key=surface['slot'];assert key in materials
    name='SM_Tunnel_'+key;path='/Tunnel/Surfaces/'+name
    mesh=u.load_asset(path)
    if mesh is None:
        task=u.AssetImportTask();task.filename=surface['file'];task.destination_path='/Tunnel/Surfaces';task.destination_name=name;task.automated=True;task.replace_existing=False;task.save=True
        options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_as_skeletal=False
        options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        d=options.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.convert_scene=False;d.convert_scene_unit=False;d.import_uniform_scale=1.;d.generate_lightmap_u_vs=False
        task.options=options;task.factory=u.FbxFactory();u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(path)
    assert mesh
    assert len(mesh.get_editor_property('static_materials'))==1
    mesh.set_material(0,materials[key]);u.EditorAssetLibrary.save_loaded_asset(mesh)
    bounds=mesh.get_bounding_box()
    for k in range(3):
        combined_min[k]=min(combined_min[k],(bounds.min.x,bounds.min.y,bounds.min.z)[k])
        combined_max[k]=max(combined_max[k],(bounds.max.x,bounds.max.y,bounds.max.z)[k])
    label='Tunnel surface '+key
    actor=existing.get(label) or actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector())
    actor.set_actor_label(label);actor.set_folder_path('Tunnel/World')
    actor.static_mesh_component.set_static_mesh(mesh);actor.static_mesh_component.set_collision_profile_name('NoCollision')
    actor.tags=[u.Name('TunnelSourceSurface')];slots.append(key)
assert set(slots)==set(materials)
world=next(a for a in actors.get_all_level_actors() if isinstance(a,u.StaticMeshActor) and a.get_actor_label().startswith('Tunnel world -'))
old=world.static_mesh_component.static_mesh.get_bounding_box()
expected_min=(old.min.x,old.min.y,old.min.z);expected_max=(old.max.x,old.max.y,old.max.z)
assert max(abs(a-b) for a,b in zip(combined_min+combined_max,list(expected_min)+list(expected_max)))<.03
world.static_mesh_component.set_visibility(False);world.set_actor_hidden_in_game(True)
world.static_mesh_component.set_collision_profile_name('NoCollision')
assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
(ROOT/'artifacts/tunnel-materials.json').write_text(json.dumps({'materials':records,'world_slots':slots,'triangles':sum(s['triangles'] for s in surfaces),'geometry_bounds_verified':True,'saved':True},indent=2))
