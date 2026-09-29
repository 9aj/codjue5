# Reference implementation: configure paths, source hashes and project dependencies first.
"""Runtime tread, riser and clearance checks at the changed landing."""
import unreal as u,pathlib,json
root=pathlib.Path(__file__).resolve().parents[1];world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();assert world
pawn=u.GameplayStatics.get_player_pawn(world,0);data=json.loads((root/'artifacts/tunnel-landing-stairs/applied.json').read_text());checks=[]
def trace(a,b):
    h=u.SystemLibrary.line_trace_single(world,u.Vector(*a),u.Vector(*b),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,[pawn],u.DrawDebugTrace.NONE,False)
    return h.to_dict() if h else None
for s in data['stairs']:
    for fraction in (.1,.5,.9):
        x=s['min_cm'][0]+fraction*(s['max_cm'][0]-s['min_cm'][0]);y=(s['min_cm'][1]+s['max_cm'][1])/2;z=s['max_cm'][2]
        h=trace([x,y,2200],[x,y,2050]);assert h and h['blocking_hit'];actual=2200-h['distance'];assert abs(actual-z)<.05
        # Standing-height clearance above each tread; no previous floor remains.
        overhead=trace([x,y,z+2],[x,y,z+182.88]);assert not overhead or not overhead['blocking_hit']
        checks.append({'x':x,'y':y,'expected_z':z,'actual_z':actual,'standing_clearance':True})
for i in (0,1):
    high=data['stairs'][i];low=data['stairs'][i+1];x=1178.56;y=high['max_cm'][1];z=high['max_cm'][2]
    h=trace([x,y+15,z+1],[x,y-15,z+1]);assert not h or not h['blocking_hit']
    h=trace([x,y+15,z-15],[x,y-15,z-15]);assert h and h['blocking_hit']
(root/'artifacts/tunnel-landing-stairs/runtime.json').write_text(json.dumps({'passed':True,'tread_probes':checks,'risers_verified':2,'total_drop_cod':36,'full_route_test':False},indent=2))
