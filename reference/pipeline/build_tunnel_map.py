# Reference implementation: configure paths, source hashes and project dependencies first.
"""Run with UnrealEditor-Cmd -run=pythonscript -script=<this file>."""
import json, pathlib, traceback
import unreal as u

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'artifacts/mp_tunnel/20260927T163238586Z-a01d31d1/ue5'
WORK = ROOT / 'artifacts/tunnel-unreal-build'
WORK.mkdir(parents=True, exist_ok=True)
DEST = '/Tunnel/Generated'
LEVEL = '/Tunnel/Maps/Tunnel_Greybox'
REPORT = WORK / 'result.json'

def main():
    if u.EditorAssetLibrary.does_asset_exist(LEVEL):
        raise RuntimeError('Refusing to overwrite existing level '+LEVEL)
    replacements = json.loads((SOURCE/'material-replacements.json').read_text(encoding='utf-8-sig'))['materials']
    sky_slots = {m['slot'] for m in replacements if m['source_material'].startswith('sky_')}
    # Preserve centimetres and Z-up. The legacy OBJ reader mirrors Y into UE.
    vertices=[]; normals=[]; out=[]; current=''; removed=0
    for line in (SOURCE/'mp_tunnel_greybox.obj').read_text().splitlines():
        p=line.split()
        if not p: continue
        if p[0] in ('mtllib','g'): continue
        if p[0] in ('v','vn'):
            x,y,z=map(float,p[1:4]); value=(x,y,z)
            (vertices if p[0]=='v' else normals).append(value)
            out.append(p[0]+' '+' '.join(str(v) for v in value)); continue
        if p[0]=='usemtl': current=p[1]
        if p[0]=='f':
            if current in sky_slots: removed+=1; continue
            indices=[list(map(int,t.split('/'))) for t in p[1:]]
            a,b,c=[vertices[t[0]-1] for t in indices]
            ab=[b[i]-a[i] for i in range(3)]; ac=[c[i]-a[i] for i in range(3)]
            cross=(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0])
            normal=normals[indices[0][2]-1]
            if sum(cross[i]*normal[i] for i in range(3))<0: p[2],p[3]=p[3],p[2]
            line=' '.join(p)
        out.append(line)
    obj=WORK/'TunnelWorld.obj'; obj.write_text('\n'.join(out)+'\n')
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.OBJ False')
    task=u.AssetImportTask(); task.filename=str(obj); task.destination_path=DEST; task.destination_name='SM_TunnelWorld'
    task.automated=True; task.replace_existing=False; task.save=True
    opts=u.FbxImportUI(); opts.import_mesh=True; opts.import_materials=False; opts.import_textures=False; opts.import_as_skeletal=False
    opts.automated_import_should_detect_type=False; opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=opts.static_mesh_import_data
    data.combine_meshes=True; data.auto_generate_collision=False; data.import_uniform_scale=1.0
    data.convert_scene=False; data.convert_scene_unit=False; data.generate_lightmap_u_vs=False
    task.options=opts; task.factory=u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    meshes=[u.load_asset(p) for p in task.imported_object_paths if isinstance(u.load_asset(p),u.StaticMesh)]
    if len(meshes)!=1: raise RuntimeError('Expected one mesh: '+str(task.imported_object_paths))
    mesh=meshes[0]
    body=mesh.get_editor_property('body_setup')
    body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    # New materials contain only numeric colours, no original images.
    tools=u.AssetToolsHelpers.get_asset_tools()
    colours=[(0.34,0.39,0.44),(0.48,0.43,0.34),(0.23,0.31,0.36),(0.48,0.50,0.51)]
    materials=[]
    for i,colour in enumerate(colours):
        mat=tools.create_asset('M_Greybox_'+str(i),DEST,u.Material,u.MaterialFactoryNew())
        colour_node=u.MaterialEditingLibrary.create_material_expression(mat,u.MaterialExpressionConstant3Vector,0,0)
        colour_node.set_editor_property('constant',u.LinearColor(*colour,1))
        u.MaterialEditingLibrary.connect_material_property(colour_node,'',u.MaterialProperty.MP_BASE_COLOR)
        u.MaterialEditingLibrary.recompile_material(mat); u.EditorAssetLibrary.save_loaded_asset(mat)
        materials.append(mat)
    for i in range(len(mesh.get_editor_property('static_materials'))): mesh.set_material(i,materials[i%len(materials)])
    u.EditorAssetLibrary.save_loaded_asset(mesh)
    levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
    actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    if not levels.new_level(LEVEL): raise RuntimeError('Could not create level')
    world_actor=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,0))
    world_actor.set_actor_label('Tunnel world - provisional triangle collision')
    world_actor.static_mesh_component.set_static_mesh(mesh)
    world_actor.static_mesh_component.set_collision_profile_name('BlockAll')
    light=actors.spawn_actor_from_class(u.DirectionalLight,u.Vector(0,0,10000),u.Rotator(pitch=-45,yaw=30,roll=0))
    light.light_component.set_mobility(u.ComponentMobility.MOVABLE)
    light.light_component.set_intensity(5.0)
    sky=actors.spawn_actor_from_class(u.SkyLight,u.Vector(0,0,10000))
    sky.light_component.set_mobility(u.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property('real_time_capture',True)
    actors.spawn_actor_from_class(u.SkyAtmosphere,u.Vector(0,0,0))
    entities=json.loads((SOURCE/'gameplay-entities.json').read_text(encoding='utf-8-sig'))['entities']
    starts=[]; markers=0
    for entity in entities:
        p=entity['properties']; cls=p.get('classname','')
        if 'origin' not in p: continue
        x,y,z=[float(n)*2.54 for n in p['origin'].split()]
        if cls=='mp_dm_spawn':
            if starts: continue  # one deterministic starting point
            yaw=float(p.get('angles','0 0 0').split()[1])
            start=actors.spawn_actor_from_class(u.PlayerStart,u.Vector(x,-y,z+100),u.Rotator(pitch=0,yaw=-yaw,roll=0))
            start.set_actor_label('Tunnel Start'); starts.append([x,-y,z+100])
        elif entity['category']=='trigger':
            marker=actors.spawn_actor_from_class(u.TargetPoint,u.Vector(x,-y,z))
            marker.set_actor_label('UNIMPLEMENTED '+p.get('targetname',cls)+' '+str(entity['index']))
            marker.tags=[u.Name('SourceEntity_'+str(entity['index']))]; markers+=1
    if not starts: raise RuntimeError('No player start found')
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property('kill_z',-150000.0)
    location=u.Vector(starts[0][0]+600,starts[0][1]+1000,starts[0][2]+600)
    u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(location,u.Rotator(pitch=-20,yaw=-120,roll=0))
    if not levels.save_current_level(): raise RuntimeError('Level save failed')
    if not levels.load_level(LEVEL): raise RuntimeError('Saved level failed to reload')
    bounds=mesh.get_bounding_box()
    REPORT.write_text(json.dumps(dict(status='saved_and_reloaded',level=LEVEL,mesh=mesh.get_path_name(),bounds=str(bounds),sky_triangles_removed=removed,player_starts=starts,trigger_markers=markers,limitations=['No teleport/trigger logic','No original collision brushes','Orientation and movement need visual playtest']),indent=2))

try:
    main()
except Exception:
    REPORT.write_text(json.dumps({'status':'failed','error':traceback.format_exc()},indent=2))
    raise
