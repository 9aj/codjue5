# Reference implementation: configure paths, source hashes and project dependencies first.
"""Apply verified axis-aligned solid brushes to live Tunnel; safe to rerun."""
import unreal as u,json,pathlib
root=pathlib.Path(__file__).resolve().parents[1]
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
assert ed.get_editor_world().get_name()=='Tunnel_Greybox'
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
existing={a.get_actor_label():a for a in actors.get_all_level_actors()}
data=json.loads((root/'artifacts/tunnel-collision.json').read_text())
mesh_path='/Tunnel/Generated/SM_CollisionUnitBox'
mesh=u.load_asset(mesh_path) if u.EditorAssetLibrary.does_asset_exist(mesh_path) else u.EditorAssetLibrary.duplicate_asset('/Engine/BasicShapes/Cube',mesh_path)
assert len(mesh.get_editor_property('body_setup').get_editor_property('agg_geom').get_editor_property('box_elems'))==1, 'Unit cube must have one simple box'
mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
u.EditorAssetLibrary.save_loaded_asset(mesh)
bounds=mesh.get_bounding_box()
size=[bounds.max.x-bounds.min.x,bounds.max.y-bounds.min.y,bounds.max.z-bounds.min.z]
assert all(abs(x-100)<0.01 for x in size),'Unexpected unit cube size'
applied=[]
for b in data['world_brushes']:
    # COD4 CONTENTS_SOLID=1, CONTENTS_PLAYERCLIP=0x10000; verified against
    # audit/cod4x-surfaceflags.h. Water/sky/monster-only volumes are excluded.
    # Sloped brushes require their actual planes, never their bounding boxes.
    if not (b['contents'] & 0x10001) or b['non_axial_side_count']!=0: continue
    label=('COD4 solid box ' if b['contents'] & 1 else 'COD4 playerclip box ')+str(b['index'])
    a=existing.get(label)
    if a is None: a=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*b['center_cm']))
    a.set_actor_label(label)
    a.set_actor_location(u.Vector(*b['center_cm']),False,False)
    a.set_actor_scale3d(u.Vector(*[x/50 for x in b['half_extent_cm']]))
    a.set_folder_path('Tunnel/Collision')
    a.set_actor_hidden_in_game(True)
    comp=a.static_mesh_component
    comp.set_static_mesh(mesh)
    comp.set_visibility(False)
    comp.set_collision_profile_name('BlockAll')
    comp.set_editor_property('cast_shadow',False)
    a.set_editor_property('tags',['TunnelSourceSolid',str(b['index'])])
    applied.append(b['index'])
assert len(applied)==303
report={'player_blocking_boxes':len(applied),'indices':applied,'zone_properties':dir(u.TimerZone),
    'zone_enum':dir(u.TimerZoneType),'saved':u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()}
(root/'artifacts/tunnel-collision-applied.json').write_text(json.dumps(report,indent=2))
