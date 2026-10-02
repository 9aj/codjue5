"""Optional six-face skybox, independent of map/project names."""
from pathlib import Path
import unreal as u


def add_sky(config,manifest,work,dest,actors):
    tools=u.AssetToolsHelpers.get_asset_tools();lib=u.MaterialEditingLibrary
    sky_dest=dest+'/Sky'
    faces=config.get('faces')
    if not faces:
        raise ValueError('Sky requires faces ft,bk,lf,rt,up,dn; cubemap-only input is not supported')
    if set(faces)!={'ft','bk','lf','rt','up','dn'}:raise ValueError('Sky needs exactly six named faces')
    orientation=config.get('orientation',{'ft':4,'bk':4,'lf':4,'rt':4,'up':5,'dn':7})
    corners={
        'ft':[(1,1,-1),(1,-1,-1),(1,-1,1),(1,1,1)],
        'bk':[(-1,-1,-1),(-1,1,-1),(-1,1,1),(-1,-1,1)],
        'rt':[(1,-1,-1),(-1,-1,-1),(-1,-1,1),(1,-1,1)],
        'lf':[(-1,1,-1),(1,1,-1),(1,1,1),(-1,1,1)],
        'up':[(1,1,1),(1,-1,1),(-1,-1,1),(-1,1,1)],
        'dn':[(-1,1,-1),(-1,-1,-1),(1,-1,-1),(1,1,-1)]}
    materials={};lines=['mtllib sky.mtl']
    for n,(face,poly) in enumerate(corners.items()):
        path=sky_dest+'/M_Sky_'+face;mat=u.load_asset(path)
        if not mat:
            task=u.AssetImportTask();task.filename=faces[face];task.destination_path=sky_dest;task.destination_name='T_Sky_'+face;task.automated=True;task.save=True;tools.import_asset_tasks([task])
            texture=u.load_asset(sky_dest+'/T_Sky_'+face);assert texture
            texture.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);texture.set_editor_property('address_y',u.TextureAddress.TA_CLAMP);texture.set_editor_property('never_stream',True);assert u.EditorAssetLibrary.save_loaded_asset(texture)
            mat=tools.create_asset('M_Sky_'+face,sky_dest,u.Material,u.MaterialFactoryNew());mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT);mat.set_editor_property('two_sided',True);mat.set_editor_property('is_sky',True)
            node=lib.create_material_expression(mat,u.MaterialExpressionTextureSample);node.set_editor_property('texture',texture);lib.connect_material_property(node,'RGB',u.MaterialProperty.MP_EMISSIVE_COLOR);lib.recompile_material(mat);assert u.EditorAssetLibrary.save_loaded_asset(mat)
        materials[face]=mat
        lines+=['v %s %s %s'%p for p in poly]
        variant=int(orientation.get(face,0));assert 0<=variant<8
        for uv in ((0,0),(1,0),(1,1),(0,1)):
            x,y=uv[0],1-uv[1]
            for _ in range(variant%4):x,y=1-y,x
            if variant>=4:x=1-x
            lines.append('vt %s %s'%(x,1-y))
        lines.append('usemtl '+face);a,b,c,d=[n*4+i for i in (1,2,3,4)]
        lines+=['f '+' '.join('%d/%d'%(i,i) for i in f) for f in ((a,b,c),(a,c,d))]
    path=sky_dest+'/SM_Sky';mesh=u.load_asset(path)
    if not mesh:
        (work/'sky.obj').write_text('\n'.join(lines));(work/'sky.mtl').write_text('\n'.join('newmtl '+f+'\nKd 1 1 1' for f in corners))
        task=u.AssetImportTask();task.filename=str(work/'sky.obj');task.destination_path=sky_dest;task.destination_name='SM_Sky';task.automated=True
        options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.convert_scene=False;data.convert_scene_unit=False;data.generate_lightmap_u_vs=False;task.options=options;task.factory=u.FbxFactory();tools.import_asset_tasks([task])
        mesh=u.load_asset(path);assert mesh
        for i,slot in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,materials[str(slot.get_editor_property('material_slot_name'))])
        assert u.EditorAssetLibrary.save_loaded_asset(mesh)
    lower=[min(r['center_cm'][k]-r['size_cm'][k]/2 for r in manifest['objects']) for k in range(3)]
    upper=[max(r['center_cm'][k]+r['size_cm'][k]/2 for r in manifest['objects']) for k in range(3)]
    center=u.Vector(*[(a+b)/2 for a,b in zip(lower,upper)]);radius=max(upper[k]-lower[k] for k in range(3))*2+10000
    existing=next((a for a in actors.get_all_level_actors() if a.get_actor_label()=='COD Skybox'),None)
    actor=existing or actors.spawn_actor_from_class(u.StaticMeshActor,center);actor.set_actor_label('COD Skybox');actor.set_folder_path('COD/Environment');actor.set_actor_scale3d(u.Vector(radius,radius,radius));actor.static_mesh_component.set_static_mesh(mesh);actor.static_mesh_component.set_collision_profile_name('NoCollision');actor.static_mesh_component.set_editor_property('cast_shadow',False)
