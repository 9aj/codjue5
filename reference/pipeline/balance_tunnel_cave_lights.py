# Reference implementation: configure paths, source hashes and project dependencies first.
"""Pull lights away from walls to avoid blown-out rock at narrow ledges."""
import unreal as u,json,pathlib
root=pathlib.Path(__file__).resolve().parents[1];ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=ed.get_editor_world();assert world.get_name()=='Tunnel_Greybox' and ed.get_game_world() is None
actors=u.get_editor_subsystem(u.EditorActorSubsystem);allactors=actors.get_all_level_actors();existing={a.get_actor_label():a for a in allactors}
facts=json.loads((root/'artifacts/tunnel-cave-style.json').read_text());rows=[]
ignore=[a for a in allactors if a.get_actor_label().startswith('Tunnel Cave')]
for row in facts['lights']:
    light=existing[row['label']];old=light.get_actor_location();p=u.Vector(*row['position_cm'])
    for step in range(2):
        for d in (u.Vector(1,0,0),u.Vector(-1,0,0),u.Vector(0,1,0),u.Vector(0,-1,0)):
            hit=u.SystemLibrary.line_trace_single(world,p,p+d*130,u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,False)
            if hit:
                data={str(k).lower():v for k,v in hit.to_dict().items()};distance=data['distance']
                if distance>1:p=p-d*(130-distance)
    delta=p-old;light.set_actor_location(p,False,False)
    light.light_component.set_intensity(1000 if row['warm'] else 700)
    light.light_component.set_editor_property('source_radius',30)
    for suffix in (' glass',' cap',' foot',' hanger'):
        lamp=existing.get(row['label'].replace('pool','lamp')+suffix)
        if lamp:lamp.set_actor_location(lamp.get_actor_location()+delta,False,False)
    rows.append({'light':row['label'],'position_cm':[p.x,p.y,p.z],'moved_cm':delta.length()})
assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
(root/'artifacts/tunnel-cave-light-balance.json').write_text(json.dumps({'saved':True,'lights':rows},indent=2))
