# Reference implementation: configure paths, source hashes and project dependencies first.
"""Cave materials and local shadowed lighting; zero displacement/collision edits."""
import json,pathlib,math,hashlib,unreal as u
root=pathlib.Path(__file__).resolve().parents[1]
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);world=ed.get_editor_world()
assert world.get_name()=='Tunnel_Greybox' and ed.get_game_world() is None
lib=u.MaterialEditingLibrary;actors=u.get_editor_subsystem(u.EditorActorSubsystem)
existing={a.get_actor_label():a for a in actors.get_all_level_actors()}
def snapshot():
    records=[]
    for a in actors.get_all_level_actors():
        if a.get_actor_label().startswith('Tunnel Cave'):continue
        c=a.get_component_by_class(u.StaticMeshComponent)
        if c:
            p=a.get_actor_location();r=a.get_actor_rotation();s=a.get_actor_scale3d()
            records.append((a.get_actor_label(),[p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z],str(c.get_collision_enabled()),str(c.static_mesh.get_path_name()) if c.static_mesh else None))
    return sorted(records)
before=snapshot()
def get(label,cls,pos):
    a=existing.get(label)
    if a is None:a=actors.spawn_actor_from_class(cls,u.Vector(*pos));a.set_actor_label(label);existing[label]=a
    a.set_actor_location(u.Vector(*pos),False,False);a.set_folder_path('Tunnel/Cave atmosphere');return a
def custom(mat,code,inputs,output=u.CustomMaterialOutputType.CMOT_FLOAT3):
    n=lib.create_material_expression(mat,u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('output_type',output)
    items=[]
    for key in inputs:
        i=u.CustomInput();i.set_editor_property('input_name',key);items.append(i)
    n.set_editor_property('inputs',items)
    for key,val in inputs.items():assert lib.connect_material_expressions(val,'',n,key)
    return n
noise='''struct Rock {
 float hash(float3 p){p=frac(p*.1031);p+=dot(p,p.yzx+33.33);return frac((p.x+p.y)*p.z);}
 float4 ng(float3 p){float3 i=floor(p),f=frac(p),v=f*f*(3-2*f),dv=6*f*(1-f);
 float a=hash(i),b=hash(i+float3(1,0,0)),c=hash(i+float3(0,1,0)),d=hash(i+float3(1,1,0));
 float e=hash(i+float3(0,0,1)),f1=hash(i+float3(1,0,1)),g=hash(i+float3(0,1,1)),h=hash(i+1);
 float k1=b-a,k2=c-a,k3=e-a,k4=a-b-c+d,k5=a-c-e+g,k6=a-b-e+f1,k7=-a+b+c-d+e-f1-g+h;
 return float4(a+k1*v.x+k2*v.y+k3*v.z+k4*v.x*v.y+k5*v.y*v.z+k6*v.x*v.z+k7*v.x*v.y*v.z,
 dv*float3(k1+k4*v.y+k6*v.z+k7*v.y*v.z,k2+k4*v.x+k5*v.z+k7*v.x*v.z,k3+k5*v.y+k6*v.x+k7*v.x*v.y));}
};Rock r;
float4 broad=r.ng(P*.008),mid=r.ng(P*.035+19),fine=r.ng(P*.16+71);
'''
palette={1:(.11,.105,.088),3:(.16,.145,.115),4:(.105,.13,.14),5:(.12,.135,.09),6:(.22,.23,.21),7:(.19,.18,.155),8:(.17,.165,.145),9:(.115,.135,.14),10:(.105,.115,.105),15:(.23,.205,.17),16:(.20,.19,.16)}
materials=[]
for slot,tint in palette.items():
    path='/Tunnel/Materials/World/M_Tunnel_surface_%04d'%slot;mat=u.load_asset(path);assert mat
    lib.delete_all_material_expressions(mat);mat.set_editor_property('tangent_space_normal',False);mat.set_editor_property('two_sided',True)
    p=lib.create_material_expression(mat,u.MaterialExpressionWorldPosition);n=lib.create_material_expression(mat,u.MaterialExpressionVertexNormalWS)
    color=lib.create_material_expression(mat,u.MaterialExpressionVectorParameter);color.set_editor_property('parameter_name','RockTint');color.set_editor_property('default_value',u.LinearColor(*tint,1))
    base=custom(mat,noise+'''float wall=1-smoothstep(.45,.85,abs(N.z));
float band=.5+.5*sin(P.z*.09+broad.x*8+mid.x*2);
float mineral=smoothstep(.70,.86,mid.x)*.18;
float variation=.48+.65*broad.x+.27*mid.x+.12*fine.x;
float3 col=Tint.rgb*variation*(1-wall*.18*(1-band));
return lerp(col,col*float3(.7,.85,.9),mineral);''',{'P':p,'N':n,'Tint':color})
    normal=custom(mat,noise+'''float wall=1-smoothstep(.45,.85,abs(N.z));
float3 grad=broad.yzw*.34+mid.yzw*.29+fine.yzw*.17;
float layer=cos(P.z*.09+broad.x*8+mid.x*2)*.15*wall;
grad+=float3(0,0,layer);grad-=N*dot(grad,N);
return normalize(N-grad*lerp(.28,1.1,wall));''',{'P':p,'N':n})
    rough=custom(mat,noise+'return .70+.23*mid.x;',{'P':p},u.CustomMaterialOutputType.CMOT_FLOAT1)
    for expr,prop in [(base,u.MaterialProperty.MP_BASE_COLOR),(normal,u.MaterialProperty.MP_NORMAL),(rough,u.MaterialProperty.MP_ROUGHNESS)]:assert lib.connect_material_property(expr,'',prop)
    lib.recompile_material(mat);assert u.EditorAssetLibrary.save_loaded_asset(mat);materials.append(path)
# Global light establishes a low visibility floor; local lights define each space.
for a in actors.get_all_level_actors():
    if isinstance(a,u.DirectionalLight):a.light_component.set_intensity(.35)
    if isinstance(a,u.SkyLight):a.light_component.set_intensity(.10)
pp=get('Tunnel Cave Exposure',u.PostProcessVolume,(0,0,0));pp.set_editor_property('unbound',True)
s=pp.get_editor_property('settings')
for key,value in [('auto_exposure_min_brightness',.5),('auto_exposure_max_brightness',.5),('auto_exposure_bias',0.0),('bloom_intensity',.18),('vignette_intensity',.22)]:
    s.set_editor_property('override_'+key,True);s.set_editor_property(key,value)
pp.set_editor_property('settings',s)
points=json.loads((root/'artifacts/tunnel-cave-light-candidates.json').read_text())
ignore=[a for a in actors.get_all_level_actors() if a.get_actor_label().startswith('Tunnel Cave')]
lights=[]
for i,p in enumerate(points):
    # Trace overhead before raising the light, so low tunnels retain valid placement.
    start=u.Vector(p[0],p[1],p[2]+70)
    hit=u.SystemLibrary.line_trace_single(world,start,start+u.Vector(0,0,600),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,False)
    height=340
    if hit:
        distance={str(k).lower():v for k,v in hit.to_dict().items()}['distance']
        if distance<75:continue
        height=min(height,70+distance-50)
    pos=(p[0],p[1],p[2]+height)
    warm=i%4!=2;color=(1,.59,.29) if warm else (.24,.49,.62)
    a=get('Tunnel Cave pool %03d'%i,u.PointLight,pos);c=a.light_component;c.set_mobility(u.ComponentMobility.MOVABLE)
    c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(3600 if warm else 2200)
    c.set_light_color(u.LinearColor(*color,1));c.set_editor_property('attenuation_radius',1650)
    c.set_editor_property('source_radius',18);c.set_editor_property('soft_source_radius',35);c.set_editor_property('cast_shadows',True)
    lights.append({'label':a.get_actor_label(),'position_cm':pos,'warm':warm})
assert snapshot()==before,'Existing geometry or collision changed'
assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
ed.set_level_viewport_camera_info(u.Vector(-4998.72,4673.6,-1060),u.Rotator(pitch=-5,yaw=-40,roll=0))
(root/'artifacts/tunnel-cave-style.json').write_text(json.dumps({'saved':True,'materials':materials,'lights':lights,'geometry_and_collision_unchanged':True,'wall_detail':'World-space rock normal shading; no displacement','baseline_snapshot':before},indent=2))
