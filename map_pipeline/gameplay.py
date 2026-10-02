"""Entity linking and conservative GSC audit. Scripts remain data, never code."""
import re
from pathlib import Path
from .parser import numbers, MapError, strip_comment
from .prepare import point_cm, digest


def audit_scripts(directory):
    scripts=[]
    candidates=[]
    if not directory:return scripts,candidates
    for path in sorted(Path(directory).rglob('*.gsc')):
        text=path.read_text(encoding='utf-8-sig',errors='replace')
        scripts.append({'file':str(path.resolve()),'sha256':digest(path),'status':'audited_not_executed'})
        clean='\n'.join(strip_comment(line) for line in text.splitlines())
        clean=re.sub(r'/\*.*?\*/','',clean,flags=re.S)
        # Restrict matching to brace-balanced function bodies, not across handlers.
        for match in re.finditer(r'(?m)^\s*(\w+)\s*\([^\n{}]*\)\s*\{',clean):
            start=match.end();depth=1;end=start;quoted=False;escape=False
            while end<len(clean) and depth:
                ch=clean[end]
                if ch=='"' and not escape:quoted=not quoted
                if not quoted:depth+=(ch=='{')-(ch=='}')
                escape=ch=='\\' and not escape;end+=1
            body=clean[start:end]
            gets=dict((m[1],m[2]) for m in re.finditer(r'\b(\w+)\s*=\s*getent\s*\(\s*"([^"]+)"\s*,\s*"targetname"\s*\)',body,re.I))
            events=list(re.finditer(r'\b(\w+)\s+waittill\s*\(\s*"trigger"',body,re.I))
            moves=list(re.finditer(r'\b(\w+)\s+setorigin\s*\(\s*(\w+)\.origin\s*\)',body,re.I))
            for event in events:
                for move in moves:
                    if event[1] in gets and move[2] in gets and event.start()<move.start():
                        candidates.append({'script':str(path.resolve()),'function':match[1],'trigger':gets[event[1]],'target':gets[move[2]],'status':'candidate_requires_configuration','reason':'Trigger/getent/setorigin pattern; activation, conditions and player receiver need review'})
    return scripts,candidates


def resolve_gameplay(entities,objects,config,scale):
    by_target={}
    for entity in entities:
        name=entity['properties'].get('targetname')
        if name:by_target.setdefault(name,[]).append(entity)
    scripts,candidates=audit_scripts(config.get('scripts'))
    teleports=[];unresolved=[];spawns=[];models=[];markers=[]
    for entity in entities:
        props=entity['properties'];classname=props.get('classname','')
        if 'origin' in props:
            try:origin=point_cm(numbers(props['origin'],3),scale)
            except MapError as exc:unresolved.append({'entity':entity['id'],'reason':str(exc)});continue
            if classname in ('mp_dm_spawn','mp_tdm_spawn','mp_sd_spawn_attacker','mp_sd_spawn_defender','info_player_start','info_player_deathmatch'):
                angles=numbers(props.get('angles','0 '+props.get('angle','0')+' 0'),3)
                spawns.append({'entity_id':entity['id'],'location_cm':origin,'angles':[-angles[0],-angles[1],angles[2]]})
            elif classname in ('misc_model','script_model') and props.get('model'):
                spec=config.get('models',{}).get(props['model'])
                models.append({'entity_id':entity['id'],'source_model':props['model'],'location_cm':origin,'angles':numbers(props.get('angles','0 0 0'),3),'asset':spec})
                if not spec:unresolved.append({'entity':entity['id'],'reason':'Model has no Unreal asset mapping','model':props['model']})
            elif classname!='worldspawn':markers.append({'entity_id':entity['id'],'location_cm':origin,'classname':classname,'properties':props})
    bindings=list(config.get('teleports',[]))
    for entity in entities:
        props=entity['properties']
        if props.get('classname')=='trigger_teleport' and props.get('target'):
            bindings.append({'entity_id':entity['id'],'target':props['target']})
    used=set()
    for binding in bindings:
        triggers=[o for o in objects if o['semantic']=='trigger' and (o['entity_id']==binding['entity_id'] if 'entity_id' in binding else o['entity'].get('targetname')==binding.get('trigger'))]
        if not triggers:
            unresolved.append({'binding':binding,'reason':'No matching trigger brush'});continue
        for obj in triggers:
            target=binding.get('target') or obj['entity'].get('target')
            destinations=[e for e in by_target.get(target,[]) if 'origin' in e['properties']]
            if len(destinations)!=1:
                unresolved.append({'object':obj['id'],'target':target,'reason':'Destination missing or ambiguous'});continue
            if obj['id'] in used:
                raise MapError('Multiple teleport mappings for '+obj['id'])
            used.add(obj['id'])
            props=destinations[0]['properties'];angles=numbers(props.get('angles','0 0 0'),3)
            delay=float(binding.get('delay',0));cooldown=float(binding.get('cooldown',0.5))
            if not 0<=delay<=60 or not 0<=cooldown<=60:raise MapError('Invalid teleport timing')
            teleports.append({'object_id':obj['id'],'target':target,'destination_cm':point_cm(numbers(props['origin'],3),scale),'destination_angles':[-angles[0],-angles[1],angles[2]],'set_view':bool(binding.get('set_view',False)),'delay':delay,'cooldown':cooldown})
            if config.get('profile')=='project_jump' and binding.get('set_view'):
                unresolved.append({'object':obj['id'],'reason':'Actor destination rotation is imported; forced controller/view rotation belongs to the game and is not called by map Blueprints'})
    for obj in objects:
        if obj['semantic']=='trigger' and obj['id'] not in used:unresolved.append({'object':obj['id'],'entity':obj['entity'],'reason':'Trigger has no supported gameplay binding'})
        if obj['semantic']=='ladder':unresolved.append({'object':obj['id'],'reason':'Ladder movement requires a project adapter'})
    return {'spawns':spawns,'teleports':teleports,'models':models,'markers':markers,'scripts':scripts,'script_candidates':candidates,'unresolved':unresolved}
