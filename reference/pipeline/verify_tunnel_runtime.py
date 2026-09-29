# Reference implementation: configure paths, source hashes and project dependencies first.
"""Read-only PIE checks for spawn grounding and recovered collision surfaces."""
import json,pathlib,unreal as u
root=pathlib.Path(__file__).resolve().parents[1]
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
assert world is not None,'Run in Play in Editor'
actors=list(u.GameplayStatics.get_all_actors_of_class(world,u.Actor))
pawn=u.GameplayStatics.get_player_pawn(world,0);assert pawn
position=pawn.get_actor_location()
floor=u.SystemLibrary.line_trace_single(world,position+u.Vector(0,0,20),position-u.Vector(0,0,400),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,[pawn],u.DrawDebugTrace.NONE,False)
report={'pawn':str(pawn.get_class().get_name()),'pawn_position':str(position),'floor_trace':str(floor),'floor_hit':floor is not None,'collision':[]}
for label,filename in [('Tunnel source sloped collision','TunnelSlopedCollision.obj'),('Tunnel source terrain collision','TunnelTerrainCollision.obj')]:
    target=next(a for a in actors if a.get_actor_label()==label)
    ignore=[a for a in actors if a!=target]
    vertices=[];tested=hits=skipped=0;misses=[];brush=None;brushes={}
    for line in (root/'artifacts/tunnel-unreal-build'/filename).read_text().splitlines():
        p=line.split()
        if not p:continue
        if p[0]=='o':brush=p[1];brushes[brush]={'tested':0,'hits':0}
        elif p[0]=='v':vertices.append(u.Vector(float(p[1]),-float(p[2]),float(p[3])))
        elif p[0]=='f':
            a,b,c=[vertices[int(i)-1] for i in p[1:]]
            normal=(b-a).cross(c-a);area=normal.length();longest=max((b-a).length(),(c-b).length(),(a-c).length())
            if area<1 or area/max(longest,1e-12)<.01:skipped+=1;continue
            normal=normal/area;center=(a+b+c)/3
            hit=u.SystemLibrary.line_trace_single(world,center+normal*2,center-normal*2,u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,False)
            tested+=1
            if brush:brushes[brush]['tested']+=1
            if hit is not None:
                hits+=1
                if brush:brushes[brush]['hits']+=1
            else:misses.append({'triangle':tested,'brush':brush,'center':str(center)})
    report['collision'].append({'label':label,'tested':tested,'hits':hits,'precision_slivers_skipped':skipped,'misses':misses,'brushes':brushes})
report['passed']=report['floor_hit'] and all(not c['misses'] for c in report['collision'])
(root/'artifacts/tunnel-runtime-collision.json').write_text(json.dumps(report,indent=2))
assert report['passed'], 'Collision trace failures; see report'
