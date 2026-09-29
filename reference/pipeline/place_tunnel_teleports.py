# Reference implementation: configure paths, source hashes and project dependencies first.
"""Restore the six source destinations using Tunnel-owned Blueprint copies.

This first pass teleports immediately and retains incoming view direction.
Source 0.1-second delays and forced destination view remain follow-up work.
"""
import json,pathlib,unreal as u
root=pathlib.Path(__file__).resolve().parents[1]
assert u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world().get_name()=='Tunnel_Greybox'
entities=json.loads((root/'artifacts/mp_tunnel/20260927T163238586Z-a01d31d1/ue5/gameplay-entities.json').read_text())['entities']
triggers=json.loads((root/'artifacts/tunnel-collision.json').read_text())['triggers']
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
lib=u.BlueprintEditorLibrary;pins=u.BlueprintGraphPinLibrary;rows=[]
for t in triggers:
    if t['properties'].get('targetname')!='enter':continue
    targets=[e['properties'] for e in entities if e['properties'].get('targetname')==t['properties']['target']]
    assert len(targets)==1
    target=targets[0];p=[float(x) for x in target['origin'].split()]
    destination=[p[0]*2.54,-p[1]*2.54,p[2]*2.54+88.9]
    path='/Tunnel/Generated/BP_TunnelTeleport_%02d'%t['model_index']
    bp=u.load_asset(path)
    if bp is None:bp=u.EditorAssetLibrary.duplicate_asset('/Descent/Generated/BP_DescentReturnTeleport',path)
    assert bp
    graph=lib.find_event_graph(bp)
    nodes=[n for n in u.ObjectIterator(u.EdGraphNode) if n.get_outer()==graph and lib.get_node_title(n)=='Teleport']
    assert len(nodes)==1
    pin=lib.find_input_pin(nodes[0],'DestLocation')
    assert not pins.list_connected_pins(pin)
    assert pins.set_pin_value(pin,','.join('%.6f'%x for x in destination))
    assert lib.compile_blueprint(bp)
    assert u.EditorAssetLibrary.save_loaded_asset(bp)
    cls=u.EditorAssetLibrary.load_blueprint_class(path);assert cls
    label='Tunnel teleport %02d'%t['model_index']
    a=next((a for a in actors.get_all_level_actors() if a.get_actor_label()==label),None)
    if a is None:a=actors.spawn_actor_from_class(cls,u.Vector(*t['center_cm']))
    a.set_actor_label(label);a.set_actor_location(u.Vector(*t['center_cm']),False,False)
    a.set_folder_path('Tunnel/Gameplay');a.tags=[u.Name('TunnelTeleport')]
    box=a.get_component_by_class(u.BoxComponent);assert box
    box.set_box_extent(u.Vector(*t['half_extent_cm']),True);box.set_collision_profile_name('Trigger')
    box.set_editor_property('generate_overlap_events',True)
    rows.append({'label':label,'blueprint':path,'entity_index':t['entity_index'],'center_cm':t['center_cm'],'half_extent_cm':t['half_extent_cm'],'destination_cm':destination,'source_target':target})
assert len(rows)==6
assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
(root/'artifacts/tunnel-teleports.json').write_text(json.dumps({'saved':True,'triggers':rows,'limitations':['Immediate teleport instead of source 0.1-second delays','Incoming view retained instead of source target angles']},indent=2))
