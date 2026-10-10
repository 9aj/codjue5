"""Live-editor re-export. Call stage(), then apply() through VibeUE Python.

Never launches/quits the editor. Requires the intended project and map already open.
Fresh revision assets isolate the old map backup from subsequent imports.
"""
import json
import re
from pathlib import Path
import unreal as u
from .__main__ import validate
from .project_jump import layout
from .unreal_import import create_materials, import_mesh, save_json
from .movement import inspect_mesh


def preflight(manifest_path, expected_project, revision):
    data = validate(manifest_path)
    assert data['config'].get('profile') == 'project_jump'
    assert not data['issues'], 'Partial geometry is not accepted for live replacement'
    assert re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', revision), 'Invalid revision'
    assert Path(u.Paths.get_project_file_path()).resolve() == Path(expected_project).resolve(), 'Wrong project'
    import vibeue
    assert not vibeue.exec_tool('EditorToolset.EditorAppToolset', 'IsPIERunning'), 'Stop PIE before importing'
    _, level, dest = layout(data)
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    assert world.get_path_name().split('.')[0] == level, 'Wrong loaded map'
    return data, level, dest+'/'+revision


def stage(manifest_path, expected_project, revision):
    data, level, dest = preflight(manifest_path, expected_project, revision)
    work = Path(manifest_path).resolve().parent
    marker = work/'mcp-stage.json'
    if marker.exists():
        previous = json.loads(marker.read_text())
        assert previous['fingerprint'] == data['fingerprint'] and previous['destination'] == dest
    else:
        assert not u.EditorAssetLibrary.does_directory_exist(dest), 'Revision already exists; choose a fresh revision'
        save_json(marker, {'fingerprint': data['fingerprint'], 'destination': dest, 'status': 'staging'})
    u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.OBJ False')
    create_materials(data['materials'], dest, data['config'])
    for row in data['objects']:
        import_mesh(row, work, dest, data['materials'], data['config'])
    save_json(marker, {'fingerprint': data['fingerprint'], 'destination': dest, 'status': 'staged'})
    print('STAGED:', dest, len(data['objects']), 'independent meshes; live map unchanged')


def apply(manifest_path, expected_project, revision):
    data, level, dest = preflight(manifest_path, expected_project, revision)
    work = Path(manifest_path).resolve().parent
    staged = json.loads((work/'mcp-stage.json').read_text())
    assert staged == {'fingerprint': data['fingerprint'], 'destination': dest, 'status': 'staged'}
    # Gameplay rebuilding is a separate workflow; never silently orphan attached teleports.
    assert not data['gameplay']['teleports'], 'Live geometry refresh currently requires no source teleports'
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    owned = []
    for actor in actors.get_all_level_actors():
        if re.fullmatch(r'COD (Brush|Patch)_\d+', actor.get_actor_label()):
            identity = actor.get_actor_label()[4:]
            assert 'Source_'+identity in [str(t) for t in actor.tags], 'Missing source ownership tag'
            owned.append(actor)
    assert owned, 'No owned source geometry in current map'
    assert any(isinstance(a, u.PlayerStart) for a in actors.get_all_level_actors()), 'Place a PlayerStart first'
    # Verify all assets before the first live-world mutation.
    for row in data['objects']:
        mesh = u.load_asset(dest+'/Objects/SM_'+row['id'])
        assert isinstance(mesh, u.StaticMesh)
        if row['collision'] != 'none':inspect_mesh(mesh, u)
    # PackageMod scans every .umap inside the mod, including folders called Backups.
    # Unreferenced editor recovery maps must live outside that content mount.
    backup = '/Game/Developers/Codjue5Backups/'+level.split('/')[1]+'/'+level.rsplit('/', 1)[1]+'_Before_'+revision
    assert not u.EditorAssetLibrary.does_asset_exist(backup), 'Backup exists; use a fresh revision'
    assert levels.save_current_level()
    snapshot = u.EditorAssetLibrary.duplicate_asset(level, backup)
    assert snapshot and u.EditorAssetLibrary.save_loaded_asset(snapshot)
    backup_package = snapshot.get_outer()
    del snapshot
    unloaded, error = u.EditorLoadingAndSavingUtils.unload_packages([backup_package])
    assert unloaded, str(error)
    del backup_package
    print('BACKUP:', backup)
    preserved = len(actors.get_all_level_actors())-len(owned)
    existing = {a.get_actor_label()[4:]: a for a in owned}
    transforms = {}
    skipped = []
    with u.ScopedEditorTransaction('Refresh source mesh assets '+data['map_id']):
        for row in data['objects']:
            actor = existing.get(row['id'])
            if actor is None:
                # An absent actor may be an intentional user deletion.
                skipped.append(row['id'])
                continue
            p=actor.get_actor_location();r=actor.get_actor_rotation();s=actor.get_actor_scale3d()
            transforms[row['id']] = dict(position=[p.x,p.y,p.z], rotation=[r.pitch,r.yaw,r.roll], scale=[s.x,s.y,s.z])
            component = actor.static_mesh_component
            actor.modify();component.modify()
            assert component.set_static_mesh(u.load_asset(dest+'/Objects/SM_'+row['id']))
            assert actor.get_actor_location()==p and actor.get_actor_rotation()==r and actor.get_actor_scale3d()==s
    assert levels.save_current_level()
    report = dict(status='built', fingerprint=data['fingerprint'], project=str(Path(expected_project).resolve()).lower(),
                  level=level, destination=dest, backup=backup, completed=len(transforms),
                  source_transforms=transforms, skipped_absent_source_actors=skipped,
                  preserved_user_actors=preserved, source_summary=data['summary'],
                  saved_reload_verified=False, runtime_movement_verified=False,
                  issues=data['issues'], unresolved_gameplay=data['gameplay']['unresolved'], limitations=data['limitations'])
    save_json(work/'unreal-result.json', report)
    print('MODIFIED:', level, 'source objects:', len(transforms), 'preserved user actors:', preserved)
