# Reference implementation: configure paths, source hashes and project dependencies first.
"""Sparse wall-anchored construction frames; all new details have no collision."""
import unreal as u,json,pathlib,math
root=pathlib.Path(__file__).resolve().parents[1];ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=ed.get_editor_world();assert world.get_name()=='Tunnel_Greybox' and ed.get_game_world() is None
actors=u.get_editor_subsystem(u.EditorActorSubsystem);meshpath='/Tunnel/Details/SM_TunnelTimberBeam'
mesh=u.load_asset(meshpath)
if mesh is None:
    task=u.AssetImportTask();task.filename=str(root/'artifacts/tunnel-pbr/SM_TunnelTimberBeam.obj');task.destination_path='/Tunnel/Details';task.destination_name='SM_TunnelTimberBeam';task.automated=True;task.save=True
    options=u.FbxImportUI();options.import_materials=False;options.import_textures=False;options.static_mesh_import_data.set_editor_property('auto_generate_collision',False);task.options=options
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(meshpath)
assert mesh
wood=u.load_asset('/Tunnel/Materials/PBR/M_Tunnel_TimberBeam_4K');iron=u.load_asset('/Tunnel/Materials/Cave/M_MineLamp_Iron');assert wood and iron
for a in actors.get_all_level_actors():
    if a.get_actor_label().startswith('Tunnel Timber '):actors.destroy_actor(a)
ignore=[a for a in actors.get_all_level_actors() if a.get_actor_label().startswith(('Tunnel Cave','Tunnel Storm'))]
def trace(p,q):
    hit=u.SystemLibrary.line_trace_single(world,p,q,u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,False)
    if not hit:return None
    d={str(k).lower():v for k,v in hit.to_dict().items()}
    return d if d.get('blocking_hit',False) else None
def beam(name,p,q,width,depth=None,material=None):
    a=actors.spawn_actor_from_class(u.StaticMeshActor,(p+q)*.5);a.set_actor_label('Tunnel Timber '+name);a.set_folder_path('Tunnel/Construction')
    a.set_actor_rotation(u.MathLibrary.make_rot_from_z(q-p),False);a.set_actor_scale3d(u.Vector(width/100,(depth or width)/100,(q-p).length()/100))
    c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_material(0,material or wood);c.set_collision_profile_name('NoCollision');a.set_actor_enable_collision(False);return a
points=[[-4300,4500,-1219.2]]+json.loads((root/'artifacts/tunnel-cave-light-candidates.json').read_text());frames=[]
for coords in points:
    p=u.Vector(*coords)
    if any((p-u.Vector(*r['floor'])).length()<1800 for r in frames):continue
    ceiling=trace(p+u.Vector(0,0,120),p+u.Vector(0,0,1500))
    if not ceiling:continue
    top=p.z+120+ceiling['distance']
    if top-p.z<340:continue
    choices=[]
    for axis in (u.Vector(1,0,0),u.Vector(0,1,0)):
        start=p+u.Vector(0,0,180);l=trace(start,start-axis*1500);r=trace(start,start+axis*1500)
        if l and r and l['distance']>30 and r['distance']>30 and 400<l['distance']+r['distance']<2300:choices.append((l['distance']+r['distance'],axis,l,r))
    if not choices:continue
    _,axis,l,r=min(choices,key=lambda x:x[0]);ends=[p-axis*(l['distance']+4),p+axis*(r['distance']+4)]
    footing=[]
    for end,direction in zip(ends,(axis,axis*-1)):
        foot=trace(end+direction*25+u.Vector(0,0,150),end+direction*25-u.Vector(0,0,250))
        if not foot:break
        footing.append(end.z+150-foot['distance'])
    if len(footing)!=2:continue
    num=len(frames);tops=[u.Vector(e.x,e.y,top-6) for e in ends]
    beam('%02d header'%num,tops[0]-axis*22,tops[1]+axis*22,26,30)
    for side,(end,z,t,inward) in enumerate(zip(ends,footing,tops,(axis,axis*-1))):
        beam('%02d post %d'%(num,side),u.Vector(end.x,end.y,z),t,24,28)
        beam('%02d brace %d'%(num,side),t-u.Vector(0,0,95),t+inward*95,16,18)
        beam('%02d iron collar %d'%(num,side),t-u.Vector(0,0,55),t-u.Vector(0,0,45),26,30,iron)
    frames.append({'floor':coords,'height':top-p.z,'width':l['distance']+r['distance'],'top':[top],'axis':[axis.x,axis.y,axis.z]})
    if len(frames)>=28:break
assert frames,'No safe enclosed support placements found'
details=[a for a in actors.get_all_level_actors() if a.get_actor_label().startswith('Tunnel Timber ')]
assert all(a.static_mesh_component.get_collision_enabled()==u.CollisionEnabled.NO_COLLISION for a in details)
assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
(root/'artifacts/tunnel-timber-supports.json').write_text(json.dumps({'saved':True,'frames':frames,'detail_actors':len(details),'all_noncolliding':True},indent=2))
