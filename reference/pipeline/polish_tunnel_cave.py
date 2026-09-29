# Reference implementation: configure paths, source hashes and project dependencies first.
"""Ceiling-hung mine lamps and finer rock grain, with no added collision."""
import json,pathlib,unreal as u
root=pathlib.Path(__file__).resolve().parents[1];ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
assert ed.get_editor_world().get_name()=='Tunnel_Greybox' and ed.get_game_world() is None
actors=u.get_editor_subsystem(u.EditorActorSubsystem);lib=u.MaterialEditingLibrary
existing={a.get_actor_label():a for a in actors.get_all_level_actors()};facts=json.loads((root/'artifacts/tunnel-cave-style.json').read_text())
# Keep the coarse geology but add mineral grain instead of a smooth plaster finish.
for path in facts['materials']:
    mat=u.load_asset(path)
    for obj in u.ObjectIterator(u.MaterialExpressionCustom):
        if not obj.get_path_name().startswith(mat.get_path_name()):continue
        code=obj.get_editor_property('code')
        if 'float3 grad=broad.yzw' in code and 'micro=r.ng' not in code:
            code=code.replace('float3 grad=broad.yzw*.34+mid.yzw*.29+fine.yzw*.17;', 'float4 micro=r.ng(P*.65+113); float3 grad=broad.yzw*.24+mid.yzw*.29+fine.yzw*.26+micro.yzw*.12;')
            obj.set_editor_property('code',code)
    lib.recompile_material(mat);u.EditorAssetLibrary.save_loaded_asset(mat)
def material(name,color,emissive=False):
    path='/Tunnel/Materials/Cave/'+name;mat=u.load_asset(path)
    if mat is None:mat=u.AssetToolsHelpers.get_asset_tools().create_asset(name,'/Tunnel/Materials/Cave',u.Material,u.MaterialFactoryNew())
    lib.delete_all_material_expressions(mat)
    c=lib.create_material_expression(mat,u.MaterialExpressionConstant3Vector);c.set_editor_property('constant',u.LinearColor(*color,1))
    lib.connect_material_property(c,'',u.MaterialProperty.MP_EMISSIVE_COLOR if emissive else u.MaterialProperty.MP_BASE_COLOR)
    if emissive:mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    lib.recompile_material(mat);u.EditorAssetLibrary.save_loaded_asset(mat);return mat
warm=material('M_MineLamp_Amber',(3,1.6,.55),True);cool=material('M_MineLamp_Cold',(.45,1.3,2),True);metal=material('M_MineLamp_Iron',(.025,.03,.035))
cylinder=u.load_asset('/Engine/BasicShapes/Cylinder');world=ed.get_editor_world();placed=[]
def part(label,pos,scale,mat):
    a=existing.get(label)
    if a is None:a=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*pos));a.set_actor_label(label);existing[label]=a
    a.set_actor_location(u.Vector(*pos),False,False);a.set_actor_scale3d(u.Vector(*scale));a.set_folder_path('Tunnel/Cave atmosphere/Lamps')
    c=a.static_mesh_component;c.set_static_mesh(cylinder);c.set_material(0,mat);c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',False);a.set_actor_enable_collision(False)
for row in facts['lights']:
    light=existing[row['label']];p=light.get_actor_location()
    light.light_component.set_light_color(u.LinearColor(1,.69,.40,1) if row['warm'] else u.LinearColor(.30,.52,.67,1))
    light.light_component.set_editor_property('max_draw_distance',10000)
    hit=u.SystemLibrary.line_trace_single(world,p,p+u.Vector(0,0,750),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,[],u.DrawDebugTrace.NONE,False)
    if not hit:continue
    d={str(k).lower():v for k,v in hit.to_dict().items()}['distance']
    if d<25 or d>700:continue
    name=row['label'].replace('pool','lamp')
    part(name+' glass',(p.x,p.y,p.z),(.12,.12,.23),warm if row['warm'] else cool)
    part(name+' cap',(p.x,p.y,p.z+14),(.21,.21,.04),metal)
    part(name+' foot',(p.x,p.y,p.z-14),(.17,.17,.025),metal)
    part(name+' hanger',(p.x,p.y,p.z+(d+15)/2),(.012,.012,(d-15)/100),metal)
    placed.append(name)
assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
(root/'artifacts/tunnel-cave-polish.json').write_text(json.dumps({'saved':True,'noncolliding_lamps':placed,'lamp_count':len(placed),'max_light_draw_distance_cm':10000},indent=2))
