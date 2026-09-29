# Reference implementation: configure paths, source hashes and project dependencies first.
"""Local three-tread replacement, with source mesh and collision rollback."""
import unreal as u,pathlib,json,zipfile,hashlib
root=pathlib.Path(__file__).resolve().parents[1];ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
assert ed.get_editor_world().get_name()=='Tunnel_Greybox' and ed.get_game_world() is None
existing={a.get_actor_label():a for a in actors.get_all_level_actors()}
assert 'Tunnel Landing Stair 1' not in existing,'Already applied; use saved report to inspect or restore'
assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
backup=root/'artifacts/backups/Tunnel-before-landing-stairs-20260927.zip';assert not backup.exists()
plugin=pathlib.Path('C:/Path/To/YourUnrealProject/Plugins/Tunnel')
with zipfile.ZipFile(backup,'w',zipfile.ZIP_DEFLATED) as z:
    for f in plugin.rglob('*'):
        if f.is_file():z.write(f,'Tunnel/'+f.relative_to(plugin).as_posix())
with zipfile.ZipFile(backup) as z:assert z.testzip() is None
backup.with_suffix('.zip.sha256').write_text(hashlib.sha256(backup.read_bytes()).hexdigest())
data=json.loads((root/'artifacts/tunnel-landing-stairs/build.json').read_text());lo=data['cut_min'];hi=data['cut_max'];originals=[]
for row in data['surfaces']:
    slot=row['slot'];name=f'SM_Tunnel_surface_{slot:04d}_LandingStairs';path='/Tunnel/Edits/'+name
    task=u.AssetImportTask();task.filename=row['file'];task.destination_path='/Tunnel/Edits';task.destination_name=name;task.automated=True;task.save=True
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False;opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.convert_scene=False;d.convert_scene_unit=False;d.import_uniform_scale=1.;d.generate_lightmap_u_vs=False
    task.options=opt;task.factory=u.FbxFactory();u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(path);assert mesh
    a=existing[f'Tunnel surface surface_{slot:04d}'];c=a.static_mesh_component;old=c.static_mesh;mat=c.get_material(0);originals.append({'actor':a.get_actor_label(),'mesh':old.get_path_name()})
    mesh.set_material(0,mat);u.EditorAssetLibrary.save_loaded_asset(mesh);c.set_static_mesh(mesh);c.set_material(0,mat);c.set_collision_profile_name('NoCollision')
unit=u.load_asset('/Tunnel/Generated/SM_CollisionUnitBox');mat=u.load_asset('/Tunnel/Materials/PBR/M_Tunnel_DampRock_4K')
def box(label,mn,mx,visible):
    a=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*[(x+y)/2 for x,y in zip(mn,mx)]));a.set_actor_label(label);a.set_folder_path('Tunnel/Landing stairs')
    a.set_actor_scale3d(u.Vector(*[(y-x)/100 for x,y in zip(mn,mx)]));c=a.static_mesh_component;c.set_static_mesh(unit);c.set_material(0,mat);c.set_collision_profile_name('BlockAll');c.set_visibility(visible);a.set_actor_hidden_in_game(not visible);c.set_editor_property('cast_shadow',visible);return a
brushes=json.loads((root/'artifacts/tunnel-collision.json').read_text())['world_brushes'];parts=[]
for index in (303,328):
    a=existing[f'COD4 solid box {index}'];a.static_mesh_component.set_collision_profile_name('NoCollision');a.tags=list(a.tags)+['TunnelStairReplaced']
    b=next(b for b in brushes if b['index']==index);mn=[c-h for c,h in zip(b['center_cm'],b['half_extent_cm'])];mx=[c+h for c,h in zip(b['center_cm'],b['half_extent_cm'])]
    # Disjoint six-slab box difference; preserve every part outside the local cut.
    count=0
    for axis in range(3):
        if mn[axis]<lo[axis]:
            end=mx.copy();end[axis]=min(lo[axis],mx[axis])
            if all(end[i]-mn[i]>.001 for i in range(3)):box(f'Tunnel Landing preserved {index}-{count}',mn,end,False);count+=1
            mn[axis]=max(mn[axis],lo[axis])
        if mx[axis]>hi[axis]:
            start=mn.copy();start[axis]=max(hi[axis],mn[axis])
            if all(mx[i]-start[i]>.001 for i in range(3)):box(f'Tunnel Landing preserved {index}-{count}',start,mx,False);count+=1
            mx[axis]=min(mx[axis],hi[axis])
    parts.append({'source_brush':index,'remainder_boxes':count})
stairs=[]
for i,z in enumerate(data['tread_z_cod']):
    mn=[lo[0],lo[1]+i*32*2.54,lo[2]];mx=[hi[0],lo[1]+(i+1)*32*2.54,z*2.54]
    box(f'Tunnel Landing Stair {i+1}',mn,mx,True);stairs.append({'min_cm':mn,'max_cm':mx,'z_cod':z})
# Trace centres in the editor after rebuilding collision, then save.
tests=[]
for s in stairs:
    p=u.Vector((s['min_cm'][0]+s['max_cm'][0])/2,(s['min_cm'][1]+s['max_cm'][1])/2,2200)
    hit=u.SystemLibrary.line_trace_single(ed.get_editor_world(),p,p-u.Vector(0,0,200),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,[],u.DrawDebugTrace.NONE,False)
    assert hit;h=hit.to_dict();z=p.z-h['distance'];assert abs(z-s['max_cm'][2])<.05,(z,s)
    tests.append({'expected':s['max_cm'][2],'hit':z})
assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
ed.set_level_viewport_camera_info(u.Vector(1130,21400,2480),u.Rotator(pitch=-38,yaw=-90,roll=0))
(root/'artifacts/tunnel-landing-stairs/applied.json').write_text(json.dumps({'saved':True,'backup':str(backup),'originals':originals,'collision_replacements':parts,'stairs':stairs,'traces':tests,'drop_cod':36,'drop_cm':91.44},indent=2))
