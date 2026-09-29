# Reference implementation: configure paths, source hashes and project dependencies first.
import unreal as u,pathlib,json
root=pathlib.Path(__file__).resolve().parents[1];data=json.loads((root/'artifacts/tunnel-landing-stairs/build.json').read_text());actors=u.get_editor_subsystem(u.EditorActorSubsystem)
assert u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() is None
for row in data['surfaces']:
    name=f"SM_Tunnel_surface_{row['slot']:04d}_LandingStairs";task=u.AssetImportTask();task.filename=row['file'];task.destination_path='/Tunnel/Edits';task.destination_name=name;task.automated=True;task.save=True;task.replace_existing=True
    opt=u.FbxImportUI();opt.import_materials=False;opt.import_textures=False;opt.import_mesh=True;opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.convert_scene=False;d.convert_scene_unit=False;d.import_uniform_scale=1.;d.generate_lightmap_u_vs=False
    task.options=opt;task.factory=u.FbxFactory();u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
