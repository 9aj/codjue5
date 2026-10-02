"""Editor entrypoint. Run via pipeline/import-map.ps1 (full editor, not commandlet)."""
import json
import os
from pathlib import Path
import sys
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from map_pipeline.__main__ import validate
import unreal as u


def save_json(path,data):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,indent=2),encoding='utf-8');temp.replace(path)


def import_mesh(row,work,dest,materials,config):
    path=dest+'/Objects/SM_'+row['id']
    mesh=u.load_asset(path)
    if not mesh:
        t=u.AssetImportTask();t.filename=str(work/row['obj']);t.destination_path=dest+'/Objects';t.destination_name='SM_'+row['id'];t.automated=True;t.save=False
        options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_as_skeletal=False;options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        d=options.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.convert_scene=False;d.convert_scene_unit=False;d.generate_lightmap_u_vs=False
        t.options=options;t.factory=u.FbxFactory();u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
        mesh=u.load_asset(path);assert mesh,path
        ids={spec['id']:name for name,spec in materials.items()}
        for i,slot in enumerate(mesh.get_editor_property('static_materials')):
            key=str(slot.get_editor_property('imported_material_slot_name'))
            if key not in ids:key=str(slot.get_editor_property('material_slot_name'))
            assert key in ids and ids[key] in row['materials'],(row['id'],key)
            mesh.set_material(i,u.load_asset(dest+'/Materials/M_'+key))
        editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
        policy=row['collision']
        # Trigger meshes need overlap shapes even though the source actor is hidden/nonblocking.
        if row['semantic']=='trigger':policy='box' if row['shape']=='box' else 'convex'
        editor.remove_collisions(mesh)
        if policy in ('box','dop26'):
            shape=u.ScriptingCollisionShapeType.BOX if policy=='box' else u.ScriptingCollisionShapeType.NDOP26
            assert editor.add_simple_collisions(mesh,shape)>=0
        elif policy=='convex':
            assert editor.set_convex_decomposition_collisions(mesh,1,64,1000000)
            assert editor.get_convex_collision_count(mesh)==1
        body=mesh.get_editor_property('body_setup')
        if body:
            body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE if policy=='triangles' else u.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
            body.set_editor_property('double_sided_geometry',policy=='triangles')
        if config.get('nanite',False):
            settings=editor.get_nanite_settings(mesh);settings.enabled=True;editor.set_nanite_settings(mesh,settings,True)
        assert u.EditorAssetLibrary.save_loaded_asset(mesh)
    return mesh


def create_materials(materials,dest,config):
    tools=u.AssetToolsHelpers.get_asset_tools();lib=u.MaterialEditingLibrary
    for name,spec in materials.items():
        path=dest+'/Materials/M_'+spec['id']
        if u.EditorAssetLibrary.does_asset_exist(path):continue
        if spec.get('unreal_asset'):
            original=u.load_asset(spec['unreal_asset']);assert original,'Missing material asset '+spec['unreal_asset']
            assert u.EditorAssetLibrary.duplicate_asset(spec['unreal_asset'],path);continue
        mat=tools.create_asset('M_'+spec['id'],dest+'/Materials',u.Material,u.MaterialFactoryNew());assert mat
        mat.set_editor_property('two_sided',True);mat.set_editor_property('used_with_nanite',True)
        if spec['tool']:
            mat.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
            node=lib.create_material_expression(mat,u.MaterialExpressionConstant);node.set_editor_property('r',0)
            lib.connect_material_property(node,'',u.MaterialProperty.MP_OPACITY_MASK)
        else:
            if spec.get('texture'):
                task=u.AssetImportTask();task.filename=spec['texture'];task.destination_path=dest+'/Textures';task.destination_name='T_'+spec['id'];task.automated=True;task.save=True
                tools.import_asset_tasks([task]);texture=u.load_asset(dest+'/Textures/T_'+spec['id']);assert texture
                node=lib.create_material_expression(mat,u.MaterialExpressionTextureSample);node.set_editor_property('texture',texture);pin='RGB'
            else:
                node=lib.create_material_expression(mat,u.MaterialExpressionConstant3Vector);node.set_editor_property('constant',u.LinearColor(*spec.get('color',[.5,.5,.5]),1));pin=''
            lib.connect_material_property(node,pin,u.MaterialProperty.MP_BASE_COLOR)
            ambient=float(config.get('ambient_emission',.15))
            if ambient:
                multiply=lib.create_material_expression(mat,u.MaterialExpressionMultiply);multiply.set_editor_property('const_b',ambient);lib.connect_material_expressions(node,pin,multiply,'A');lib.connect_material_property(multiply,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
            rough=lib.create_material_expression(mat,u.MaterialExpressionConstant);rough.set_editor_property('r',float(spec.get('roughness',.8)));lib.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
        lib.recompile_material(mat);assert u.EditorAssetLibrary.save_loaded_asset(mat)


def decorate(manifest,actors,config):
    existing={a.get_actor_label():a for a in actors.get_all_level_actors()}
    def spawn(cls,label,pos=u.Vector(0,0,0),rot=u.Rotator(0,0,0)):
        if label in existing:return existing[label]
        a=actors.spawn_actor_from_class(cls,pos,rot);a.set_actor_label(label);a.set_folder_path('COD/Environment');return a
    spawn(u.SkyAtmosphere,'COD Sky Atmosphere')
    light=spawn(u.DirectionalLight,'COD Sun',u.Vector(0,0,1000),u.Rotator(pitch=-55,yaw=30,roll=0))
    light.light_component.set_mobility(u.ComponentMobility.MOVABLE);light.light_component.set_intensity(float(config.get('sun_intensity',5)))
    sky=spawn(u.SkyLight,'COD Skylight');sky.light_component.set_mobility(u.ComponentMobility.MOVABLE);sky.light_component.set_intensity(float(config.get('skylight_intensity',1)));sky.light_component.set_editor_property('real_time_capture',True);sky.light_component.set_editor_property('lower_hemisphere_is_black',False)
    pp=spawn(u.PostProcessVolume,'COD Exposure');pp.set_editor_property('unbound',True)
    settings=pp.get_editor_property('settings');settings.set_editor_property('override_auto_exposure_min_brightness',True);settings.set_editor_property('override_auto_exposure_max_brightness',True);settings.set_editor_property('auto_exposure_min_brightness',0);settings.set_editor_property('auto_exposure_max_brightness',0);pp.set_editor_property('settings',settings)
    for i,row in enumerate(manifest['gameplay']['spawns']):
        xyz=list(row['location_cm']);xyz[2]+=float(config.get('spawn_height_cm',100))
        a=spawn(u.PlayerStart,'COD '+row['entity_id']+' PlayerStart',u.Vector(*xyz),u.Rotator(pitch=row['angles'][0],yaw=row['angles'][1],roll=row['angles'][2]));a.set_folder_path('COD/Entities')
    if not manifest['gameplay']['spawns']:
        spawn(u.PlayerStart,'COD Fallback PlayerStart',u.Vector(0,0,500))
    for row in manifest['gameplay']['markers']:
        a=spawn(u.TargetPoint,'COD '+row['entity_id']+' '+row['classname'],u.Vector(*row['location_cm']));a.set_folder_path('COD/Entities');a.tags=[u.Name(row['entity_id']),u.Name('UnimplementedMetadata')]
    for row in manifest['gameplay']['models']:
        if not row['asset']:continue
        mesh=u.load_asset(row['asset']);assert isinstance(mesh,u.StaticMesh),'Model asset must be StaticMesh: '+row['asset']
        angle=row['angles'];a=spawn(u.StaticMeshActor,'COD '+row['entity_id']+' Model',u.Vector(*row['location_cm']),u.Rotator(pitch=-angle[0],yaw=-angle[1],roll=angle[2]));a.static_mesh_component.set_static_mesh(mesh);a.set_folder_path('COD/Models')


def gameplay(manifest,actors,source_actors,config):
    if not manifest['gameplay']['teleports']:return []
    cls=u.load_class(None,'/Script/CodMapRuntime.CodMapTeleport')
    if not cls:raise RuntimeError('Teleports require the included CodMapRuntime plugin. Install and build it before import.')
    placed=[];existing={a.get_actor_label():a for a in actors.get_all_level_actors()}
    for row in manifest['gameplay']['teleports']:
        label='COD Teleport '+row['object_id'];parent=source_actors[row['object_id']]
        a=existing.get(label) or actors.spawn_actor_from_class(cls,parent.get_actor_location())
        a.set_actor_label(label);a.set_folder_path('COD/Gameplay')
        c=a.get_editor_property('trigger_mesh');c.set_static_mesh(parent.static_mesh_component.static_mesh);c.set_collision_profile_name('Trigger');c.set_editor_property('generate_overlap_events',True)
        a.set_editor_property('destination',u.Vector(*row['destination_cm']))
        angle=row['destination_angles'];a.set_editor_property('destination_rotation',u.Rotator(pitch=angle[0],yaw=angle[1],roll=angle[2]))
        a.set_editor_property('set_view',row['set_view']);a.set_editor_property('source_origin_at_feet',config.get('source_origin_at_feet',True));a.set_editor_property('delay_seconds',row['delay']);a.set_editor_property('cooldown_seconds',row['cooldown'])
        rule=u.AttachmentRule.KEEP_WORLD;assert a.attach_to_actor(parent,u.Name('None'),rule,rule,rule,False)
        placed.append(row['object_id'])
    return placed


def main():
    manifest_path=Path(os.environ['CODJUE_MANIFEST']).resolve();work=manifest_path.parent
    report_path=work/'unreal-result.json';data=validate(manifest_path);config=data['config']
    if data['issues'] and os.environ.get('CODJUE_ALLOW_PARTIAL')!='1':raise RuntimeError('Source geometry has unresolved conversion errors')
    level=config.get('unreal_root','/Game/CodMaps')+'/'+data['map_id']+'/Map_'+data['map_id'];dest=level.rsplit('/',1)[0]+'/Generated'
    levels=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    prior=json.loads(report_path.read_text()) if report_path.exists() else {}
    project=os.path.normcase(os.path.abspath(u.Paths.get_project_file_path()))
    if prior and prior.get('project')!=project:raise RuntimeError('Checkpoint belongs to another Unreal project')
    if prior and prior.get('fingerprint')!=data['fingerprint']:raise RuntimeError('Checkpoint does not match source/config')
    if u.EditorAssetLibrary.does_asset_exist(level):
        if not prior:raise RuntimeError('Existing destination has no matching checkpoint; select a new map_id')
        assert levels.load_level(level)
    else:
        if u.EditorAssetLibrary.does_directory_exist(dest):raise RuntimeError('Unowned destination assets exist')
        save_json(report_path,{'status':'building','fingerprint':data['fingerprint'],'project':project,'level':level,'completed':0})
        assert levels.new_level(level)
        assert levels.save_current_level()
    if prior.get('status')=='complete':return
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.OBJ False')
    create_materials(data['materials'],dest,config)
    existing={a.get_actor_label():a for a in actors.get_all_level_actors()};source_actors={}
    for index,row in enumerate(data['objects'],1):
        label='COD '+row['id'];mesh=import_mesh(row,work,dest,data['materials'],config)
        a=existing.get(label)
        if not a:
            a=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*row['center_cm']));a.set_actor_location(u.Vector(*row['center_cm']),False,False);a.set_actor_label(label);a.set_folder_path('COD/'+row['kind'].title()+'es')
            a.static_mesh_component.set_static_mesh(mesh);a.static_mesh_component.set_collision_profile_name('NoCollision' if row['collision']=='none' else 'BlockAll');a.set_actor_hidden_in_game(row['tool_surface']);a.static_mesh_component.set_editor_property('cast_shadow',not row['tool_surface'])
            a.tags=[u.Name('Source_'+row['id']),u.Name(row['entity_id']),u.Name('SourceLine_'+str(row['source_line']))]
            if row['fallback_hull']:a.tags=list(a.tags)+[u.Name('REVIEW_FallbackHull')]
        source_actors[row['id']]=a
        if index%int(config.get('checkpoint_interval',100))==0:
            assert levels.save_current_level();save_json(report_path,{'status':'building','fingerprint':data['fingerprint'],'project':project,'level':level,'completed':index,'total':len(data['objects'])})
    decorate(data,actors,config)
    teleports=gameplay(data,actors,source_actors,config)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property('kill_z',min(r['center_cm'][2]-r['size_cm'][2]/2 for r in data['objects'])-10000)
    if config.get('sky'):
        from map_pipeline.unreal_sky import add_sky
        add_sky(config['sky'],data,work,dest,actors)
    assert levels.save_current_level()
    save_json(report_path,{'status':'built','fingerprint':data['fingerprint'],'project':project,'level':level,'completed':len(source_actors),'teleports':teleports,'source_summary':data['summary'],'saved_reload_verified':False,'runtime_movement_verified':False,'issues':data['issues'],'unresolved_gameplay':data['gameplay']['unresolved'],'limitations':data['limitations']})


if __name__=='__main__':
    try:main()
    except Exception:
        path=Path(os.environ['CODJUE_MANIFEST']).parent/'unreal-result.json'
        prior=json.loads(path.read_text()) if path.exists() else {};prior.update(status='failed',error=traceback.format_exc());save_json(path,prior);raise
    finally:
        if os.environ.get('CODJUE_QUIT','1')=='1':u.SystemLibrary.quit_editor()
