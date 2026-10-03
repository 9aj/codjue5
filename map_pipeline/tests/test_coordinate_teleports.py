import unittest
from map_pipeline.gameplay import resolve_gameplay
from map_pipeline.config import validate_config
from map_pipeline.parser import MapError

class CoordinateTeleportTests(unittest.TestCase):
    def test_source_coordinate_conversion(self):
        config={'profile':'project_jump','teleports':[{'trigger':'tele1','destination':[38208,3072,61200],'angles':[0,270,0],'set_view':True}]}
        validate_config(config)
        objects=[{'id':'Brush_1','entity_id':'Entity_1','semantic':'trigger','entity':{'targetname':'tele1'}}]
        result=resolve_gameplay([],objects,config,2.54)
        self.assertEqual(result['teleports'][0]['destination_cm'],[97048.32,-7802.88,155448.0])
        self.assertEqual(result['teleports'][0]['destination_angles'],[0,-270,0])
        self.assertEqual(len(result['unresolved']),1) # Forced view rotation remains explicit.
    def test_reject_ambiguous_or_nonfinite_coordinates(self):
        for extra in ({'destination':[1,2,3],'target':'exit'},{'destination':[1,2]},{'destination':[1,float('inf'),3]}):
            with self.assertRaises(MapError):validate_config({'teleports':[{'trigger':'enter',**extra}]})
