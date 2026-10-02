"""Content-only, engine-Actor Blueprint teleports for Project Jump maps."""
import unreal as u
from .project_jump import layout

def blueprint(path,row,config):
    if u.EditorAssetLibrary.does_asset_exist(path):return u.load_asset(path)
    lib=u.BlueprintEditorLibrary;pins=u.BlueprintGraphPinLibrary
    bp=lib.create_blueprint_asset_with_parent(path,u.TriggerBox);assert bp
    assert lib.add_member_variable(bp,'PendingActor',lib.get_object_reference_type(u.Actor))
    event=lib.add_event_override(bp,'ReceiveActorBeginOverlap',u.IntPoint(0,0))
    editor=u.BlueprintGraphEditor.get_graph_editor(lib.find_event_graph(bp))
    def call(name):
        node=editor.add_call_function_node('/Script/Engine.'+name);assert node,name;return node
    def ip(node,name):return lib.find_input_pin(node,name)
    def op(node,name):return lib.find_output_pin(node,name)
    def link(a,b):assert pins.try_create_connection(a,b)
    def value(node,name,text):assert pins.set_pin_value(ip(node,name),str(text))
    once=editor.add_macro_node('/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:DoOnce')
    pending_set=editor.add_set_member_variable_node('PendingActor','')
    pending_get=editor.add_get_member_variable_node('PendingActor','')
    pending=op(pending_get,'PendingActor')
    other_root=call('Actor.K2_GetRootComponent');link(op(event,'OtherActor'),ip(other_root,'self'))
    locked=call('ActorComponent.ComponentHasTag');value(locked,'Tag','CODJumpTeleportLock')
    check=editor.add_branch_node()
    link(lib.find_result_pin(other_root),ip(locked,'self'))
    link(lib.find_then_pin(event),ip(once,'execute'))
    link(op(once,'Completed'),lib.find_execute_pin(check))
    link(lib.find_result_pin(locked),lib.find_condition_pin(check))
    link(lib.find_then_pin(check),ip(once,'Reset'))
    link(lib.find_else_pin(check),lib.find_execute_pin(pending_set))
    link(op(event,'OtherActor'),ip(pending_set,'PendingActor'))
    root=call('Actor.K2_GetRootComponent');link(pending,ip(root,'self'))
    tags=editor.add_get_member_variable_node('ComponentTags','/Script/Engine.ActorComponent');link(lib.find_result_pin(root),ip(tags,'self'))
    add=call('KismetArrayLibrary.Array_AddUnique');link(op(tags,'ComponentTags'),ip(add,'TargetArray'));value(add,'NewItem','CODJumpTeleportLock')
    link(lib.find_then_pin(pending_set),lib.find_execute_pin(add))
    delay=call('KismetSystemLibrary.Delay');value(delay,'Duration',row['delay'])
    link(lib.find_then_pin(add),lib.find_execute_pin(delay))
    overlap=call('Actor.IsOverlappingActor');link(pending,ip(overlap,'Other'))
    inside=editor.add_branch_node();link(lib.find_then_pin(delay),lib.find_execute_pin(inside));link(lib.find_result_pin(overlap),lib.find_condition_pin(inside))
    move=call('Actor.K2_TeleportTo');link(pending,ip(move,'self'));link(lib.find_then_pin(inside),lib.find_execute_pin(move))
    xyz=list(row['destination_cm'])
    if config.get('source_origin_at_feet',True):
        bounds=call('Actor.GetActorBounds');link(pending,ip(bounds,'self'));value(bounds,'bOnlyCollidingComponents','true')
        split=call('KismetMathLibrary.BreakVector');link(op(bounds,'BoxExtent'),ip(split,'InVec'))
        add_z=call('KismetMathLibrary.Add_DoubleDouble');link(op(split,'Z'),ip(add_z,'B'));value(add_z,'A',xyz[2])
        vector=call('KismetMathLibrary.MakeVector');value(vector,'X',xyz[0]);value(vector,'Y',xyz[1]);link(lib.find_result_pin(add_z),ip(vector,'Z'));link(lib.find_result_pin(vector),ip(move,'DestLocation'))
    else:value(move,'DestLocation',','.join(map(str,xyz)))
    # Actor rotation is allowed. The game owns controller/view rotation.
    if row['set_view']:value(move,'DestRotation',','.join(map(str,row['destination_angles'])))
    else:
        rotation=call('Actor.K2_GetActorRotation');link(pending,ip(rotation,'self'));link(lib.find_result_pin(rotation),ip(move,'DestRotation'))
    cooldown=call('KismetSystemLibrary.Delay');value(cooldown,'Duration',max(.05,row['cooldown']))
    link(lib.find_then_pin(move),lib.find_execute_pin(cooldown));link(lib.find_else_pin(inside),lib.find_execute_pin(cooldown))
    remove=call('KismetArrayLibrary.Array_RemoveItem');link(op(tags,'ComponentTags'),ip(remove,'TargetArray'));value(remove,'Item','CODJumpTeleportLock')
    link(lib.find_then_pin(cooldown),lib.find_execute_pin(remove));link(lib.find_then_pin(remove),ip(once,'Reset'))
    for i,node in enumerate(editor.list_all_nodes()):lib.set_node_pos(node,u.IntPoint((i%6)*320,(i//6)*220))
    assert lib.compile_blueprint(bp),'Teleport Blueprint compile failed'
    assert u.EditorAssetLibrary.save_loaded_asset(bp)
    return bp

def place_teleports(manifest,actors,source_actors,config):
    _,_,dest=layout(manifest);placed=[]
    existing={a.get_actor_label():a for a in actors.get_all_level_actors()}
    for row in manifest['gameplay']['teleports']:
        path=dest+'/Gameplay/BP_Teleport_'+row['object_id'];blueprint(path,row,config)
        label='COD Teleport '+row['object_id'];parent=source_actors[row['object_id']]
        cls=u.EditorAssetLibrary.load_blueprint_class(path);assert cls
        actor=existing.get(label) or actors.spawn_actor_from_class(cls,parent.get_actor_location())
        actor.set_actor_label(label);actor.set_folder_path('COD/Gameplay')
        box=actor.get_component_by_class(u.BoxComponent);assert box
        source=next(o for o in manifest['objects'] if o['id']==row['object_id'])
        box.set_box_extent(u.Vector(*(max(.5,v/2) for v in source['size_cm'])),True)
        box.set_collision_response_to_all_channels(u.CollisionResponseType.ECR_IGNORE)
        box.set_collision_response_to_channel(u.CollisionChannel.ECC_PAWN,u.CollisionResponseType.ECR_OVERLAP)
        box.set_collision_enabled(u.CollisionEnabled.QUERY_ONLY);box.set_editor_property('generate_overlap_events',True)
        rule=u.AttachmentRule.KEEP_WORLD;assert actor.attach_to_actor(parent,u.Name('None'),rule,rule,rule,False)
        placed.append(row['object_id'])
    return placed
