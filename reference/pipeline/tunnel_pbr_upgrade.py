# Reference implementation: configure paths, source hashes and project dependencies first.
"""4K scanned rock/timber with triplanar mapping; all source geometry retained."""
import unreal as u,json,pathlib
root=pathlib.Path(__file__).resolve().parents[1];lib=u.MaterialEditingLibrary
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
assert ed.get_editor_world().get_name()=='Tunnel_Greybox' and ed.get_game_world() is None
records=json.loads((root/'artifacts/tunnel-pbr/manifest.json').read_text(encoding='utf-8-sig'));textures={};tasks=[]
for r in records:
    name='T_'+pathlib.Path(r['file']).stem;r['unreal_asset']='/Tunnel/Textures/PBR/'+name
    if u.load_asset(r['unreal_asset']) is None:
        t=u.AssetImportTask();t.filename=r['file'];t.destination_path='/Tunnel/Textures/PBR';t.destination_name=name;t.automated=True;t.save=True;tasks.append(t)
if tasks:u.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
for r in records:
    tex=u.load_asset(r['unreal_asset']);assert isinstance(tex,u.Texture2D)
    normal=r['map']=='nor_dx';mask=r['map']=='arm'
    tex.set_editor_property('srgb',not(normal or mask));tex.set_editor_property('max_texture_size',4096)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_MASKS if mask else u.TextureCompressionSettings.TC_DEFAULT)
    tex.set_editor_property('lod_bias',0)
    if normal:tex.set_editor_property('flip_green_channel',False)
    r['dimensions']=[tex.blueprint_get_size_x(),tex.blueprint_get_size_y()] # Runtime dimensions may reflect streaming during import
    u.EditorAssetLibrary.save_loaded_asset(tex);textures[(r['asset'],r['map'])]=tex
def node(m,t):return lib.create_material_expression(m,t)
def custom(m,code,inputs,output=u.CustomMaterialOutputType.CMOT_FLOAT3):
    n=node(m,u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('output_type',output)
    items=[]
    for k in inputs:
        x=u.CustomInput();x.set_editor_property('input_name',k);items.append(x)
    n.set_editor_property('inputs',items)
    for k,v in inputs.items():assert lib.connect_material_expressions(v,'',n,k)
    return n
def prop(n,p):assert lib.connect_material_property(n,'',p)
def scalar(m,name,value):
    n=node(m,u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
def make(name,source,tint,scale,strength,local=False):
    path='/Tunnel/Materials/PBR/'+name;m=u.load_asset(path)
    if m is None:m=u.AssetToolsHelpers.get_asset_tools().create_asset(name,'/Tunnel/Materials/PBR',u.Material,u.MaterialFactoryNew())
    lib.delete_all_material_expressions(m);m.set_editor_property('two_sided',True);m.set_editor_property('tangent_space_normal',local)
    p=node(m,u.MaterialExpressionWorldPosition);n=node(m,u.MaterialExpressionVertexNormalWS)
    size=scalar(m,'Tile centimetres',scale);ns=scalar(m,'Normal strength',strength)
    color=node(m,u.MaterialExpressionVectorParameter);color.set_editor_property('parameter_name','Tint');color.set_editor_property('default_value',u.LinearColor(*tint,1))
    samples={}
    if local:
        coords={'Z':node(m,u.MaterialExpressionTextureCoordinate)}
    else:
        coords={axis:custom(m,code,{'P':p,'N':n,'S':size},u.CustomMaterialOutputType.CMOT_FLOAT2) for axis,code in {
            'X':'return float2(P.y,P.z*sign(N.x))/S;',
            'Y':'return float2(P.x,-P.z*sign(N.y))/S;',
            'Z':'return float2(P.x,P.y*sign(N.z))/S;'}.items()}
    for axis,uv in coords.items():
        for typ in ('Diffuse','nor_dx','arm'):
            sample=node(m,u.MaterialExpressionTextureSample);sample.set_editor_property('texture',textures[(source,typ)])
            sample.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if typ=='nor_dx' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if typ=='arm' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            assert lib.connect_material_expressions(uv,'',sample,'UVs');samples[(axis,typ)]=sample
    weight='float3 w=pow(abs(N),8);w/=max(w.x+w.y+w.z,.001);'
    if local:
        albedo=samples[('Z','Diffuse')];arm=samples[('Z','arm')]
        normal=custom(m,'return normalize(float3(B.xy*S,max(B.z,.25)));',{'B':samples[('Z','nor_dx')],'S':ns})
    else:
        albedo=custom(m,weight+'return X*w.x+Y*w.y+Z*w.z;',{'X':samples[('X','Diffuse')],'Y':samples[('Y','Diffuse')],'Z':samples[('Z','Diffuse')],'N':n})
        arm=custom(m,weight+'return X*w.x+Y*w.y+Z*w.z;',{'X':samples[('X','arm')],'Y':samples[('Y','arm')],'Z':samples[('Z','arm')],'N':n})
        normal=custom(m,weight+'''float3 g=float3(0,X.x,X.y*sign(N.x))*w.x+float3(Y.x,0,-Y.y*sign(N.y))*w.y+float3(Z.x,Z.y*sign(N.z),0)*w.z;
g-=N*dot(g,N);float wall=1-smoothstep(.45,.9,abs(N.z));return normalize(N+g*S*lerp(.5,1,wall));''',{'X':samples[('X','nor_dx')],'Y':samples[('Y','nor_dx')],'Z':samples[('Z','nor_dx')],'N':n,'S':ns})
    wood='wood' in source
    code='float gray=dot(A,float3(.2126,.7152,.0722));float3 c=lerp(gray.xxx,A,'+('.75' if wood else '.28')+')*Tint.rgb;'
    code+='float variation=.88+.12*sin(P.x*.0017+sin(P.y*.0021)+P.z*.0009);return c*variation;'
    base=custom(m,code,{'A':albedo,'Tint':color,'P':p});prop(base,u.MaterialProperty.MP_BASE_COLOR);prop(normal,u.MaterialProperty.MP_NORMAL)
    rough=custom(m,'return clamp(A.g*.65+.24,.35,.94);',{'A':arm},u.CustomMaterialOutputType.CMOT_FLOAT1);prop(rough,u.MaterialProperty.MP_ROUGHNESS)
    ao=custom(m,'return lerp(1,A.r,.65);',{'A':arm},u.CustomMaterialOutputType.CMOT_FLOAT1);prop(ao,u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    fill=custom(m,'return A*.012;',{'A':base});prop(fill,u.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(m);assert u.EditorAssetLibrary.save_loaded_asset(m)
    return m
rock=make('M_Tunnel_Cliff_4K','rock_boulder_cracked',(.72,.80,.86),220,1.15)
ground=make('M_Tunnel_RockFloor_4K','rock_boulder_dry',(.65,.70,.73),180,.85)
dark=make('M_Tunnel_DampRock_4K','rock_boulder_cracked',(.42,.53,.59),190,1.0)
wood=make('M_Tunnel_TimberWorld_4K','wooden_rough_planks',(.68,.58,.43),180,.85)
beam=make('M_Tunnel_TimberBeam_4K','wooden_rough_planks',(.68,.57,.42),180,.85,True)
rockslots={1,3,4,5,6,7,8,9,10,15,16};woodslots={11,12,18};assignments=[]
for a in actors.get_all_level_actors():
    label=a.get_actor_label()
    if label.startswith('Tunnel surface surface_'):
        slot=int(label.rsplit('_',1)[1])
        m=wood if slot in woodslots else ground if slot in (5,6,8,9) else dark if slot in (1,4,10) else rock if slot in rockslots else None
        if m:a.static_mesh_component.set_material(0,m);assignments.append({'actor':label,'material':m.get_path_name()})
    elif label.startswith('Tunnel source model ') and not label.startswith('Tunnel source model collision'):
        if int(label.rsplit(' ',1)[1])<5:a.static_mesh_component.set_material(0,wood)
        elif label.endswith('009'):a.static_mesh_component.set_material(0,rock)
assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
(root/'artifacts/tunnel-pbr-upgrade.json').write_text(json.dumps({'saved':True,'textures':records,'assignments':assignments,'texture_density':'4K repeats across 1.8–2.2 metres','geometry_changes':False},indent=2))
