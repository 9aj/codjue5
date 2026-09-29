# Reference implementation: configure paths, source hashes and project dependencies first.
"""Import verified local meshes, retain source placements and authored materials."""
import json, math, pathlib, traceback
import unreal as u
ROOT=pathlib.Path(__file__).resolve().parents[1]
SOURCE=ROOT/'artifacts/tunnel-models'
REPORT=SOURCE/'unreal-import.json'
LEVEL='/Tunnel/Maps/Tunnel_Greybox'
lib=u.MaterialEditingLibrary

def material(name,color,kind):
    path='/Tunnel/Materials/Models/'+name
    mat=u.load_asset(path)
    if mat is None: mat=u.AssetToolsHelpers.get_asset_tools().create_asset(name,'/Tunnel/Materials/Models',u.Material,u.MaterialFactoryNew())
    assert mat is not None,path
    lib.delete_all_material_expressions(mat)
    mat.set_editor_property('two_sided',True)
    pos=lib.create_material_expression(mat,u.MaterialExpressionWorldPosition,-600,0)
    normal=lib.create_material_expression(mat,u.MaterialExpressionVertexNormalWS,-600,180)
    tint=lib.create_material_expression(mat,u.MaterialExpressionVectorParameter,-600,360)
    tint.set_editor_property('parameter_name','Tint');tint.set_editor_property('default_value',u.LinearColor(*color,1))
    custom=lib.create_material_expression(mat,u.MaterialExpressionCustom,-250,0)
    code='''float3 a=abs(N); float2 q=a.z>max(a.x,a.y)?P.xy:(a.x>a.y?P.yz:P.xz);
float grain=.5+.5*sin(q.x*.35+sin(q.y*.017)*3+sin(q.x*.071+q.y*.009));
float variation=.5+.5*sin(dot(P,float3(.041,.027,.033)))*sin(dot(P,float3(.19,.077,.051)));
'''
    if kind=='wood': code+='float seam=step(.975,frac(q.x/42)); return Tint.rgb*(.58+.3*grain+.2*variation)*(1-.45*seam);'
    elif kind=='bark': code+='float ring=.5+.5*sin(P.z*.22+sin(P.x*.06)*2); return Tint.rgb*(.55+.22*grain+.35*ring);'
    elif kind=='leaf': code+='return Tint.rgb*(.65+.35*variation+.15*grain);'
    else: code+='return Tint.rgb*(.65+.45*variation);'
    custom.set_editor_property('code',code)
    custom.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    inputs=[]
    for name,expression in [('P',pos),('N',normal),('Tint',tint)]:
        item=u.CustomInput();item.set_editor_property('input_name',name);inputs.append(item)
    custom.set_editor_property('inputs',inputs)
    for name,expression in [('P',pos),('N',normal),('Tint',tint)]: assert lib.connect_material_expressions(expression,'',custom,name)
    assert lib.connect_material_property(custom,'',u.MaterialProperty.MP_BASE_COLOR)
    rough=lib.create_material_expression(mat,u.MaterialExpressionConstant,0,200);rough.set_editor_property('r',.82)
    assert lib.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    lib.recompile_material(mat);u.EditorAssetLibrary.save_loaded_asset(mat)
    return mat

def main():
    u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/Tunnel'],True)
    levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
    assert levels.load_level(LEVEL)
    data=json.loads((SOURCE/'decoded.json').read_text())
    materials={
        'wood':material('M_Tunnel_CrateWood',(.30,.14,.055),'wood'),
        'bark':material('M_Tunnel_PalmBark',(.24,.17,.095),'bark'),
        'leaf':material('M_Tunnel_PalmLeaves',(.07,.20,.035),'leaf'),
        'stone':material('M_Tunnel_ModelRock',(.30,.32,.28),'stone')}
    meshes={}; mesh_report=[]
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.OBJ False')
    for model in data['models']:
        name='SM_TunnelModel_LOD0_%04d'%model['id']; path='/Tunnel/Models/'+name
        if True:
            task=u.AssetImportTask();task.filename=str(SOURCE/model['obj']);task.destination_path='/Tunnel/Models';task.destination_name=name
            task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=True
            # The companion MTL contains numeric neutral colors only. Let the
            # FBX OBJ reader create slots, then assign our authored materials.
            options=u.FbxImportUI();options.import_mesh=True;options.import_materials=True;options.import_textures=False;options.import_as_skeletal=False
            options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
            d=options.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.convert_scene=False;d.convert_scene_unit=False;d.import_uniform_scale=1.;d.generate_lightmap_u_vs=False
            task.options=options;task.factory=u.FbxFactory()
            u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(path)
        assert isinstance(mesh,u.StaticMesh),path
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        mesh.get_editor_property('body_setup').set_editor_property('double_sided_geometry',True)
        source_slots={s['slot']:s['source_material'] for s in model['slots']}
        assignments=[]
        for i,slot in enumerate(mesh.get_editor_property('static_materials')):
            slotname=str(slot.get_editor_property('imported_material_slot_name'))
            assert slotname in source_slots,(path,slotname)
            original=source_slots[slotname]
            kind='wood' if 'crates' in original else 'leaf' if 'fronds' in original else 'bark' if 'bark' in original else 'stone'
            mesh.set_material(i,materials[kind]);assignments.append({'slot':slotname,'material':materials[kind].get_path_name()})
        bounds=mesh.get_bounding_box(); v=model['bounds_cod']
        expected=[v[0]*2.54,-v[4]*2.54,v[2]*2.54,v[3]*2.54,-v[1]*2.54,v[5]*2.54]
        actual=[bounds.min.x,bounds.min.y,bounds.min.z,bounds.max.x,bounds.max.y,bounds.max.z]
        error=max(abs(a-b) for a,b in zip(actual,expected));assert error<.02,(path,error)
        u.EditorAssetLibrary.save_loaded_asset(mesh);meshes[model['id']]=mesh
        mesh_report.append({'asset':path,'source':model['source_name'],'bounds_error_cm':error,'assignments':assignments})
    actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    existing={a.get_actor_label():a for a in actors.get_all_level_actors()}
    placed=[]
    for instance in data['instances']:
        axis=instance['axis'];assert max(abs(axis[i]) for i in (2,5,6,7))<1e-5 and abs(axis[8]-1)<1e-5,'Non-yaw instance requires full rotation conversion'
        origin=instance['origin_cod'];position=u.Vector(origin[0]*2.54,-origin[1]*2.54,origin[2]*2.54)
        yaw=-math.degrees(math.atan2(axis[1],axis[0]))
        label='Tunnel source model %03d'%instance['index']
        actor=existing.get(label) or actors.spawn_actor_from_class(u.StaticMeshActor,position)
        actor.set_actor_label(label);actor.set_folder_path('Tunnel/Models')
        actor.set_actor_location(position,False,False);actor.set_actor_rotation(u.Rotator(pitch=0,yaw=yaw,roll=0),False)
        actor.set_actor_scale3d(u.Vector(instance['scale'],instance['scale'],instance['scale']))
        actor.static_mesh_component.set_static_mesh(meshes[instance['model_id']])
        actor.static_mesh_component.set_collision_profile_name('BlockAll')
        actor.tags=[u.Name('TunnelSourceModel'),u.Name(str(instance['index']))]
        placed.append({'index':instance['index'],'model':instance['model_id'],'position_cm':[position.x,position.y,position.z],'yaw_ue':yaw,'scale':instance['scale']})
    assert levels.save_current_level()
    assert levels.load_level(LEVEL)
    restored=[a for a in actors.get_all_level_actors() if a.actor_has_tag(u.Name('TunnelSourceModel'))]
    assert len(restored)==len(placed)
    for record in placed:
        a=next(a for a in restored if a.get_actor_label()=='Tunnel source model %03d'%record['index'])
        p=a.get_actor_location();s=a.get_actor_scale3d()
        assert max(abs(v-w) for v,w in zip((p.x,p.y,p.z),record['position_cm']))<.02
        assert max(abs(v-record['scale']) for v in (s.x,s.y,s.z))<1e-5
    REPORT.write_text(json.dumps({'status':'saved_and_reloaded','meshes':mesh_report,'instances':placed,'limitations':['Visible triangle model collision is provisional','Foliage alpha masks not yet authored','No runtime playtest yet']},indent=2)+'\n')

try: main()
except Exception:
    REPORT.write_text(json.dumps({'status':'failed','error':traceback.format_exc()},indent=2));raise
