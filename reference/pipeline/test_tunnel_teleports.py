# Reference implementation: configure paths, source hashes and project dependencies first.
"""Exercise actual PIE overlap events at all six recovered teleport volumes."""
import json,pathlib,time,unreal as u
root=pathlib.Path(__file__).resolve().parents[1]
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();assert world
pawn=u.GameplayStatics.get_player_pawn(world,0);assert pawn
records=json.loads((root/'artifacts/tunnel-teleports.json').read_text())['triggers']
start=pawn.get_actor_location();rotation=pawn.get_actor_rotation();rows=[]
phase=0;index=0;next_time=time.monotonic();immediate=None
def check(dt):
    global phase,index,next_time,immediate
    if time.monotonic()<next_time:return
    try:
        if phase==0:
            pawn.set_actor_location(u.Vector(0,0,80000),False,True)
            phase=1;next_time=time.monotonic()+.1
        elif phase==1:
            pawn.set_actor_location(u.Vector(*records[index]['center_cm']),False,True)
            immediate=pawn.get_actor_location()
            phase=2;next_time=time.monotonic()+.03
        else:
            actual=immediate;expected=u.Vector(*records[index]['destination_cm'])
            error=(actual-expected).length()
            rows.append({'label':records[index]['label'],'immediate_cm':[actual.x,actual.y,actual.z],'after_gravity':str(pawn.get_actor_location()),'expected_cm':records[index]['destination_cm'],'error_cm':error,'passed':error<.1})
            index+=1;phase=0;next_time=time.monotonic()+.05
            if index==len(records):
                pawn.set_actor_location(start,False,True);pawn.set_actor_rotation(rotation,False)
                (root/'artifacts/tunnel-runtime-teleports.json').write_text(json.dumps({'passed':all(r['passed'] for r in rows),'tolerance_cm':.1,'triggers':rows},indent=2))
                u.unregister_slate_post_tick_callback(handle)
    except Exception:
        u.unregister_slate_post_tick_callback(handle)
        raise
handle=u.register_slate_post_tick_callback(check)
