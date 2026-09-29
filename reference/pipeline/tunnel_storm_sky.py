# Reference implementation: configure paths, source hashes and project dependencies first.
"""Original storm-night sky: layered clouds, veiled moon, dark horizon."""
import unreal as u,json,pathlib
root=pathlib.Path(__file__).resolve().parents[1];lib=u.MaterialEditingLibrary
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
assert ed.get_editor_world().get_name()=='Tunnel_Greybox' and ed.get_game_world() is None
path='/Tunnel/Materials/Sky/M_Tunnel_StormNight';mat=u.load_asset(path)
if mat is None:mat=u.AssetToolsHelpers.get_asset_tools().create_asset('M_Tunnel_StormNight','/Tunnel/Materials/Sky',u.Material,u.MaterialFactoryNew())
lib.delete_all_material_expressions(mat);mat.set_editor_property('two_sided',True);mat.set_editor_property('is_sky',True);mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
p=lib.create_material_expression(mat,u.MaterialExpressionWorldPosition)
c=lib.create_material_expression(mat,u.MaterialExpressionCustom);c.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
i=u.CustomInput();i.set_editor_property('input_name','P');c.set_editor_property('inputs',[i]);lib.connect_material_expressions(p,'',c,'P')
c.set_editor_property('code','''struct Cloud {
float h(float2 p){float3 q=frac(float3(p.xyx)*.1031);q+=dot(q,q.yzx+33.33);return frac((q.x+q.y)*q.z);}
float n(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(h(i),h(i+float2(1,0)),f.x),lerp(h(i+float2(0,1)),h(i+1),f.x),f.y);}
float fb(float2 p){float a=0,w=.52;for(int i=0;i<6;i++){a+=n(p)*w;p=p*2.07+float2(17,31);w*=.49;}return a;}
};Cloud cloud;
float3 d=normalize(P-float3(10000,10000,12000));
float elevation=saturate(d.z);float3 zenith=float3(.006,.012,.028),horizon=float3(.034,.048,.072);
float3 col=lerp(horizon,zenith,pow(elevation,.55));
float2 q=d.xy/(max(d.z,.015)+.32)*2.1;
float field=cloud.fb(q+float2(4,9)),detail=cloud.fb(q*3.7+23);
float cover=smoothstep(.28,.66,field+.10*detail);
float3 moonDir=normalize(float3(-.36,.65,.46));float md=length(d-moonDir);
float halo=exp(-md*14);float silver=pow(saturate(dot(d,moonDir)),18);
float3 cloudColor=lerp(float3(.008,.013,.023),float3(.052,.066,.088),smoothstep(.42,.70,field)*silver);
col=lerp(col,cloudColor,cover*.94);
float disk=1-smoothstep(.012,.014,md);float crater=.7+.3*cloud.fb(d.xy*380);
col+=float3(.25,.31,.39)*disk*crater*(1-cover*.90)+float3(.012,.019,.031)*halo;
float stars=pow(cloud.h(floor(d.xy*1400)),1400)*smoothstep(.25,.8,d.z)*(1-cover);
col+=stars*.07;
col=lerp(float3(.007,.011,.017),col,smoothstep(-.005,.08,d.z));return col;
''')
lib.connect_material_property(c,'',u.MaterialProperty.MP_EMISSIVE_COLOR);lib.recompile_material(mat);u.EditorAssetLibrary.save_loaded_asset(mat)
allactors=actors.get_all_level_actors();dome=next((a for a in allactors if a.get_actor_label()=='Tunnel Storm Night sky'),None)
if dome is None:dome=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(10000,10000,12000));dome.set_actor_label('Tunnel Storm Night sky')
dome.set_actor_scale3d(u.Vector(16000,16000,16000));dome.set_folder_path('Tunnel/Atmosphere')
comp=dome.static_mesh_component;comp.set_static_mesh(u.load_asset('/Engine/BasicShapes/Sphere'));comp.set_material(0,mat);comp.set_collision_profile_name('NoCollision');comp.set_editor_property('cast_shadow',False);dome.set_actor_enable_collision(False)
for a in allactors:
    if isinstance(a,u.SkyAtmosphere):a.get_component_by_class(u.SkyAtmosphereComponent).set_visibility(False)
    if isinstance(a,u.DirectionalLight):
        a.set_actor_rotation(u.Rotator(pitch=-27,yaw=120,roll=0),False);a.light_component.set_light_color(u.LinearColor(.42,.57,.78,1));a.light_component.set_intensity(.30)
    if isinstance(a,u.SkyLight):
        a.light_component.set_editor_property('real_time_capture',False);a.light_component.set_intensity(.7);a.light_component.set_editor_property('lower_hemisphere_is_black',False);a.light_component.recapture_sky()
assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
(root/'artifacts/tunnel-storm-sky.json').write_text(json.dumps({'saved':True,'material':path,'original_shader':True,'collision':False}))
