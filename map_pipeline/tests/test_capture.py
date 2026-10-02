import tempfile
import unittest
from pathlib import Path
from map_pipeline.capture import export_config, validate_export
from map_pipeline.parser import MapError
from map_pipeline.tests.test_conversion import fixture


class CaptureTests(unittest.TestCase):
    def test_collision_initializes_before_export(self):
        commands=export_config(2,3).splitlines()
        self.assertEqual(commands[:6],['wait','wait','r_drawCollision 3','wait','wait','wait'])
        self.assertEqual(commands[-1],'mapexport')
        self.assertIn('mapexport_useFilters 0',commands)
        for option in ('Triangles','Quads','Entities','Models','DynModels'):
            self.assertIn('mapexport_write'+option+' 1',commands)

    def test_validate_snapshot_and_reject_truncation(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'source.map';path.write_text(fixture())
            result=validate_export(path)
            self.assertEqual(result['source_objects'],4)
            self.assertEqual(result['status'],'validated_capture')
            path.write_text(fixture()[:-3])
            with self.assertRaises(MapError):validate_export(path)

    def test_bad_wait_count(self):
        with self.assertRaises(ValueError):export_config(0,10)
