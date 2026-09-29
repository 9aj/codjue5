# Reference implementation: configure paths, source hashes and project dependencies first.
"""Use recovered source model collision, independently of replacement art."""
import json, math, pathlib, unreal as u
root=pathlib.Path(__file__).resolve().parents[1]
source=root/'artifacts/tunnel-models'
facts=json.loads((source/'collision.json').read_text())
data=json.loads((source/'decoded.json').read_text())
levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
assert u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world().get_name()=='Tunnel_Greybox'
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.OBJ False')
meshes={}
for record in facts['models']:
    name='SM_TunnelModelCollision_%04d'%record['model_id']
    task=u.AssetImportTask();task.filename=str(source/record['obj']);task.destination_path='/Tunnel/Generated';task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=True
    opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
    opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    d=opts.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.convert_scene=False;d.convert_scene_unit=False;d.generate_lightmap_u_vs=False
    task.options=opts;task.factory=u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh=u.load_asset('/Tunnel/Generated/'+name);assert mesh
    body=mesh.get_editor_property('body_setup');body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    body.set_editor_property('double_sided_geometry',True)
    assert u.EditorAssetLibrary.save_loaded_asset(mesh)
    meshes[record['model_id']]=mesh
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
existing={a.get_actor_label():a for a in actors.get_all_level_actors()}
placed=[]
for instance in data['instances']:
    index=instance['index'];visual=existing['Tunnel source model %03d'%index]
    label='Tunnel source model collision %03d'%index
    a=existing.get(label) or actors.spawn_actor_from_class(u.StaticMeshActor,visual.get_actor_location())
    a.set_actor_label(label);a.set_folder_path('Tunnel/Collision/Models')
    a.set_actor_transform(visual.get_actor_transform(),False,False)
    a.set_actor_hidden_in_game(True);a.tags=[u.Name('TunnelSourceModelCollision')]
    c=a.static_mesh_component;c.set_static_mesh(meshes[instance['model_id']]);c.set_visibility(False)
    c.set_collision_profile_name('BlockAll');c.set_editor_property('cast_shadow',False)
    visual.static_mesh_component.set_collision_profile_name('NoCollision')
    placed.append({'index':index,'model_id':instance['model_id'],'transform':str(a.get_actor_transform())})
assert levels.save_current_level()
(source/'collision-applied.json').write_text(json.dumps({'saved':True,'instances':placed,'source':facts},indent=2))
