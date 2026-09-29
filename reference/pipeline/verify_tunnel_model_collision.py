# Reference implementation: configure paths, source hashes and project dependencies first.
"""Read-only PIE trace checks against every substantial model collision face."""
import json,pathlib,unreal as u
root=pathlib.Path(__file__).resolve().parents[1];source=root/'artifacts/tunnel-models'
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();assert world
actors=list(u.GameplayStatics.get_all_actors_of_class(world,u.Actor))
data=json.loads((source/'decoded.json').read_text());records=[]
for instance in data['instances']:
    target=next(a for a in actors if a.get_actor_label()=='Tunnel source model collision %03d'%instance['index'])
    ignore=[a for a in actors if a!=target];vertices=[];hits=tested=skipped=0;misses=[]
    for line in (source/('TunnelModelCollision_%04d.obj'%instance['model_id'])).read_text().splitlines():
        p=line.split()
        if not p:continue
        if p[0]=='v':
            v=[float(x)*instance['scale'] for x in p[1:]];axis=instance['axis'];origin=instance['origin_cod']
            w=[sum(v[j]*axis[j*3+k] for j in range(3))+origin[k]*2.54 for k in range(3)]
            vertices.append(u.Vector(w[0],-w[1],w[2]))
        elif p[0]=='f':
            a,b,c=[vertices[int(i)-1] for i in p[1:]];normal=(b-a).cross(c-a);area=normal.length()
            longest=max((b-a).length(),(c-b).length(),(a-c).length())
            if area<1 or area/max(longest,1e-12)<.01:skipped+=1;continue
            normal=normal/area;center=(a+b+c)/3
            hit=u.SystemLibrary.line_trace_single(world,center+normal*2,center-normal*2,u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,False)
            tested+=1
            if hit is not None:hits+=1
            else:misses.append({'triangle':tested,'center':str(center)})
    records.append({'index':instance['index'],'tested':tested,'hits':hits,'precision_slivers_skipped':skipped,'misses':misses})
report={'passed':all(r['tested']>0 and not r['misses'] for r in records),'instances':records}
(source/'runtime-collision.json').write_text(json.dumps(report,indent=2))
assert report['passed'],'Model collision trace failures; see report'
