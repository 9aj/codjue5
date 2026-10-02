"""Validate imported geometry, slots, collisions and links in a fresh editor."""
import json,os,pathlib,sys,traceback
import unreal as u
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from map_pipeline.__main__ import validate
from map_pipeline.unreal_import import save_json


def main():
    path=pathlib.Path(os.environ['CODJUE_MANIFEST']).resolve();work=path.parent
    data=validate(path);report_path=work/'unreal-result.json';report=json.loads(report_path.read_text())
    assert report['status'] in ('built','complete')
    assert report['fingerprint']==data['fingerprint']
    assert report['project']==str(pathlib.Path(u.Paths.get_project_file_path()).resolve()).lower(),'Checkpoint belongs to another project'
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(report['level'])
    actors=u.get_editor_subsystem(u.EditorActorSubsystem);editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    labels={a.get_actor_label():a for a in actors.get_all_level_actors()};paths=[];worst=0
    for row in data['objects']:
        a=labels['COD '+row['id']];mesh=a.static_mesh_component.static_mesh;assert mesh
        assert (a.get_actor_location()-u.Vector(*row['center_cm'])).length()<.1,row['id']
        assert a.get_actor_scale3d()==u.Vector(1,1,1)
        bounds=mesh.get_bounding_box();size=[bounds.max.x-bounds.min.x,bounds.max.y-bounds.min.y,bounds.max.z-bounds.min.z]
        error=max(abs(x-y) for x,y in zip(size,row['size_cm']));worst=max(worst,error);assert error<.1,(row['id'],error)
        paths.append(mesh.get_path_name())
        actual={a.static_mesh_component.get_material(i).get_name() for i in range(a.static_mesh_component.get_num_materials())}
        expected={'M_'+data['materials'][m]['id'] for m in row['materials']};assert actual==expected,(row['id'],actual,expected)
        assert a.static_mesh_component.get_collision_profile_name()==('NoCollision' if row['collision']=='none' else 'BlockAll')
        body=mesh.get_editor_property('body_setup')
        policy=row['collision']
        if row['semantic']=='trigger':policy='box' if row['shape']=='box' else 'convex'
        if policy=='box':assert editor.get_simple_collision_count(mesh)>0,(row['id'],policy)
        if policy=='dop26':assert editor.get_convex_collision_count(mesh)>0,(row['id'],policy)
        if policy=='convex':assert editor.get_convex_collision_count(mesh)==1
        if policy=='triangles':assert body.get_editor_property('collision_trace_flag')==u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
    assert len(set(paths))==len(data['objects']),'Source objects share mesh assets'
    assert len([n for n in labels if n.startswith('COD Brush_') or n.startswith('COD Patch_')])==len(data['objects'])
    for row in data['gameplay']['teleports']:
        a=labels['COD Teleport '+row['object_id']];assert a.get_attach_parent_actor()==labels['COD '+row['object_id']]
        assert (a.get_editor_property('destination')-u.Vector(*row['destination_cm'])).length()<.1
        assert a.get_editor_property('delay_seconds')==row['delay'] or abs(a.get_editor_property('delay_seconds')-row['delay'])<.00001
        assert a.get_editor_property('set_view')==row['set_view']
    move_verified=False
    if len(data['objects'])>1:
        a=labels['COD '+data['objects'][0]['id']];b=labels['COD '+data['objects'][1]['id']];p=a.get_actor_location();q=b.get_actor_location();children=a.get_attached_actors();before=[c.get_actor_location() for c in children];delta=u.Vector(100,0,0)
        try:
            a.set_actor_location(p+delta,False,False);assert (b.get_actor_location()-q).length()<.01
            for child,old in zip(children,before):assert (child.get_actor_location()-old-delta).length()<.01
            move_verified=True
        finally:a.set_actor_location(p,False,False)
    report.update(status='complete',saved_reload_verified=True,independent_move_verified=move_verified,verified_source_actors=len(paths),unique_render_meshes=len(set(paths)),worst_bounds_error_cm=worst)
    save_json(report_path,report)


if __name__=='__main__':
    try:main()
    except Exception:
        path=pathlib.Path(os.environ['CODJUE_MANIFEST']).parent/'unreal-result.json';report=json.loads(path.read_text());report.update(status='verification_failed',error=traceback.format_exc());save_json(path,report);raise
    finally:
        if os.environ.get('CODJUE_QUIT','1')=='1':u.SystemLibrary.quit_editor()
