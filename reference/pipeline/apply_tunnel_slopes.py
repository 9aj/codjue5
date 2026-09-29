# Reference implementation: configure paths, source hashes and project dependencies first.
"""Import verified closed source brush collision; retain render mesh separately."""
import unreal as u,json,pathlib
root=pathlib.Path(__file__).resolve().parents[1]
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
assert ed.get_editor_world().get_name()=='Tunnel_Greybox'
facts=json.loads((root/'artifacts/tunnel-convex-reconstruction.json').read_text())
assert len(facts['brushes'])==107
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.OBJ False')
task=u.AssetImportTask();task.filename=str(root/'artifacts/tunnel-unreal-build/TunnelSlopedCollision.obj')
task.destination_path='/Tunnel/Generated';task.destination_name='SM_TunnelSlopedCollision';task.automated=True;task.replace_existing=True;task.save=True
opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
d=opts.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.convert_scene=False;d.convert_scene_unit=False;d.generate_lightmap_u_vs=False
opts.static_mesh_import_data=d;task.options=opts;task.factory=u.FbxFactory()
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mesh=u.load_asset('/Tunnel/Generated/SM_TunnelSlopedCollision');assert mesh
body=mesh.get_editor_property('body_setup');body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
body.set_editor_property('double_sided_geometry',True)
u.EditorAssetLibrary.save_loaded_asset(mesh)
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
a=next((a for a in actors.get_all_level_actors() if a.get_actor_label()=='Tunnel source sloped collision'),None)
if a is None:a=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,0))
a.set_actor_label('Tunnel source sloped collision');a.set_folder_path('Tunnel/Collision');a.set_actor_hidden_in_game(True)
c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_visibility(False);c.set_collision_profile_name('BlockAll');c.set_editor_property('cast_shadow',False)
world=next(a for a in actors.get_all_level_actors() if isinstance(a,u.StaticMeshActor) and a.static_mesh_component.static_mesh and a.static_mesh_component.static_mesh.get_name() in ('SM_TunnelWorld','SM_TunnelStyledWorld'))
world.static_mesh_component.set_collision_profile_name('BlockAll')
world.set_actor_label('Tunnel world - provisional render collision plus source brushes')
report={'sloped_brushes':107,'triangles':sum(b['triangles'] for b in facts['brushes']),'mesh_bounds':str(mesh.get_bounding_box()),'render_collision':str(world.static_mesh_component.get_collision_enabled()),'saved':u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()}
(root/'artifacts/tunnel-slopes-applied.json').write_text(json.dumps(report,indent=2))
