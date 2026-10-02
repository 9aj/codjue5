import json,tempfile,unittest
from pathlib import Path
from map_pipeline.project_jump import install_content_plugin,layout,plugin_name
from map_pipeline.prepare import prepare
from map_pipeline.config import validate_config
from map_pipeline.parser import MapError
from map_pipeline.tests.test_conversion import fixture

class ProjectJumpTests(unittest.TestCase):
    def test_plugin_layout_and_unchanged_kit(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'mp_example.map';source.write_text(fixture())
            project=root/'project_jump.uproject';project.write_text('{"FileVersion":3}')
            before=project.read_bytes();data=prepare(source,root/'output',{'profile':'project_jump','map_id':'mp_example'})
            result=install_content_plugin(project,data)
            self.assertEqual(result['level'],'/mpexample/Maps/mpexample')
            descriptor=json.loads((Path(result['folder'])/'mpexample.uplugin').read_text())
            self.assertTrue(descriptor['CanContainContent']);self.assertNotIn('Modules',descriptor)
            self.assertEqual(project.read_bytes(),before)
            self.assertFalse((root/'Content').exists())
            self.assertNotIn('triangles',data['summary']['collisions'])
            self.assertEqual(install_content_plugin(project,data),result)
            data['fingerprint']='other'
            with self.assertRaises(MapError):install_content_plugin(project,data)

    def test_reject_noncompliant_settings(self):
        for config in ({'surface_collision':'triangles'},{'units_to_cm':1},{'unreal_root':'/Game/Maps'}):
            with self.subTest(config=config),self.assertRaises(MapError):validate_config(dict(config,profile='project_jump'))
        for name in ('MainMenu','Aquatic','Tutorial','JumpLevel2'):
            with self.assertRaises(MapError):plugin_name(name)

    def test_explicit_plugin_identity(self):
        self.assertEqual(layout({'map_id':'mp_example','config':{'plugin_name':'Example'}}),('Example','/Example/Maps/Example','/Example/Generated'))
