"""Run the real live apply function against editor doubles without importing UE."""
import ast
import json
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, MagicMock


class LiveRefreshTests(unittest.TestCase):
    def test_authored_transform_identity_attachments_and_deletion_survive(self):
        source=Path(__file__).parents[1]/'unreal_mcp_import.py'
        fn=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='apply')
        actor=Mock()
        actor.get_actor_label.return_value='COD Brush_00001'
        actor.tags=['Source_Brush_00001','CustomUserTag']
        actor.get_actor_location.return_value=SimpleNamespace(x=100,y=461,z=32)
        actor.get_actor_rotation.return_value=SimpleNamespace(pitch=15,yaw=37,roll=10)
        actor.get_actor_scale3d.return_value=SimpleNamespace(x=2,y=3,z=4)
        actor.get_attached_actors.return_value=[Mock()]
        actor.static_mesh_component.set_static_mesh.return_value=True
        class PlayerStart:
            def get_actor_label(self):return 'PlayerStart'
        actors=Mock();actors.get_all_level_actors.return_value=[actor,PlayerStart()]
        levels=Mock();levels.save_current_level.return_value=True
        u=Mock();u.PlayerStart=PlayerStart;u.StaticMesh=object
        u.EditorActorSubsystem='actors';u.LevelEditorSubsystem='levels'
        u.get_editor_subsystem.side_effect=lambda key: actors if key=='actors' else levels
        u.EditorAssetLibrary.does_asset_exist.return_value=False
        u.EditorLoadingAndSavingUtils.unload_packages.return_value=(True,'')
        u.ScopedEditorTransaction=MagicMock()
        data=dict(fingerprint='test',map_id='Echo',summary={},issues=[],limitations=[],gameplay={'teleports':[],'unresolved':[]},objects=[dict(id='Brush_00001',collision='box',center_cm=[0,0,0]),dict(id='Brush_00002',collision='box',center_cm=[5,5,5])])
        save=Mock()
        namespace=dict(u=u,Path=Path,json=json,re=re,preflight=Mock(return_value=(data,'/Echo/Maps/Echo','/Echo/Generated/Test')),inspect_mesh=Mock(),save_json=save)
        exec(compile(ast.Module(body=[fn],type_ignores=[]),str(source),'exec'),namespace)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'manifest.json'
            (Path(tmp)/'mcp-stage.json').write_text(json.dumps(dict(fingerprint='test',destination='/Echo/Generated/Test',status='staged')))
            namespace['apply'](path,'project.uproject','Test')
        actors.destroy_actor.assert_not_called()
        actors.spawn_actor_from_class.assert_not_called()
        actor.set_actor_location.assert_not_called()
        actor.set_actor_rotation.assert_not_called()
        actor.set_actor_scale3d.assert_not_called()
        actor.set_actor_label.assert_not_called()
        self.assertEqual(actor.tags,['Source_Brush_00001','CustomUserTag'])
        actor.static_mesh_component.set_collision_profile_name.assert_not_called()
        actor.static_mesh_component.set_static_mesh.assert_called_once()
        report=save.call_args.args[1]
        self.assertEqual(report['completed'],1)
        self.assertEqual(report['skipped_absent_source_actors'],['Brush_00002'])
        self.assertEqual(report['source_transforms']['Brush_00001']['position'],[100,461,32])
        self.assertEqual(report['source_transforms']['Brush_00001']['rotation'],[15,37,10])
        self.assertEqual(report['source_transforms']['Brush_00001']['scale'],[2,3,4])
