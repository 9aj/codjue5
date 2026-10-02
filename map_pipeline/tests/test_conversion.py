import json
import pathlib
import tempfile
import unittest

from map_pipeline.geometry import reconstruct
from map_pipeline.parser import MapError, parse
from map_pipeline.prepare import prepare, tessellate, brush_uv, safe_name
from map_pipeline.__main__ import validate
from map_pipeline.gameplay import audit_scripts

BOX=[[(0,0,0),(128,128,0),(0,128,0)],[(128,0,128),(0,128,128),(128,128,128)],[(0,0,128),(128,0,128),(128,0,0)],[(128,0,128),(128,128,128),(128,128,0)],[(0,128,0),(128,128,0),(128,128,128)],[(0,0,0),(0,128,0),(0,128,128)]]


def brush(material='stone',offset=0):
    return '\n'.join(['{']+[' '.join('( %s %s %s )'%(p[0]+offset,p[1],p[2]) for p in side)+' '+material+' 128 128 0 0 0 0 lightmap_gray 16384 16384 0 0 0 0' for side in BOX]+['}'])


def mesh(noncolliding=False):
    return '''{
mesh
{
toolFlags splitGeo;
%s
stone
lightmap_gray
2 2 16 8
(
v 0 0 256 t 0 0 0
v 0 128 256 t 0 0 1
)
(
v 128 0 256 t 0 1 0
v 128 128 256 t 0 1 1
)
}
}'''%('contents nonColliding;' if noncolliding else '')


def fixture():
    return 'iwmap 4\n{\n"classname" "worldspawn"\n'+brush()+ '\n'+mesh()+'\n'+mesh(True)+'''\n}
{
"classname" "trigger_multiple"
"targetname" "portal"
'''+brush('trigger',256)+'''
}
{
"classname" "script_origin"
"targetname" "destination"
"origin" "1024 0 128"
"angles" "0 90 0"
}
{
"classname" "mp_dm_spawn"
"origin" "64 64 128"
}
'''


class ConversionTests(unittest.TestCase):
    def test_config_rejects_mistyped_runtime_settings(self):
        from map_pipeline.config import validate_config
        for config in ({'nanite':'false'}, {'teleports':[{'trigger':'x','set_view':'false'}]},
                       {'teleports':[{'trigger':'x','entitiy_id':'y'}]},
                       {'object_overrides':{'Brush_00000':{'colision':'box'}}}):
            with self.subTest(config=config), self.assertRaises(MapError):validate_config(config)
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name)
        self.source=self.root/'unrelated.map';self.source.write_text(fixture());self.out=self.root/'output'
    def tearDown(self):self.temp.cleanup()
    def test_separate_objects_and_uvs(self):
        data=prepare(self.source,self.out)
        self.assertEqual(data['summary']['prepared_objects'],4)
        self.assertEqual(data['summary']['brushes'],2)
        self.assertEqual(data['summary']['patches'],2)
        self.assertEqual(len({r['obj'] for r in data['objects']}),4)
        self.assertEqual([r['collision'] for r in data['objects']],['box','triangles','none','none'])
        self.assertEqual(data['objects'][0]['center_cm'],[162.56,-162.56,162.56])
        self.assertIn('vt 1 1',(self.out/'Patch_00000.obj').read_text())
        self.assertEqual(validate(self.out/'manifest.json')['status'],'prepared')
    def test_map_names_do_not_affect_geometry(self):
        a=prepare(self.source,self.out)
        renamed=self.root/'completely_different.map';renamed.write_text(fixture())
        b=prepare(renamed,self.root/'other')
        self.assertNotEqual(a['map_id'],b['map_id'])
        self.assertEqual([r['obj_sha256'] for r in a['objects']],[r['obj_sha256'] for r in b['objects']])
    def test_changed_source_refuses_checkpoint(self):
        prepare(self.source,self.out);self.source.write_text(fixture()+'\n// changed')
        with self.assertRaises(MapError):prepare(self.source,self.out)
    def test_changed_geometry_fails_validation(self):
        prepare(self.source,self.out);(self.out/'Brush_00000.obj').write_text('modified')
        with self.assertRaises(MapError):validate(self.out/'manifest.json')
    def test_teleport_resolution(self):
        data=prepare(self.source,self.out,{'teleports':[{'trigger':'portal','target':'destination','set_view':True,'delay':.1}]})
        row=data['gameplay']['teleports'][0]
        self.assertEqual(row['destination_cm'],[2600.96,0,325.12]);self.assertTrue(row['set_view'])
        self.assertEqual(row['object_id'],'Brush_00001');self.assertEqual(row['destination_angles'],[0,-90,0])
    def test_ambiguous_destination_is_not_promoted(self):
        self.source.write_text(fixture()+'{\n"classname" "script_origin"\n"targetname" "destination"\n"origin" "0 0 0"\n}\n')
        data=prepare(self.source,self.out,{'teleports':[{'trigger':'portal','target':'destination'}]})
        self.assertFalse(data['gameplay']['teleports']);self.assertTrue(any('ambiguous' in r['reason'] for r in data['gameplay']['unresolved']))
    def test_malformed_braces(self):
        with self.assertRaises(MapError):parse('{\n"classname" "worldspawn"')
        with self.assertRaises(MapError):parse('}')
    def test_comments_in_quoted_values(self):
        entities,_,_=parse('{\n"url" "https://example.test/a//b" // a comment\n"classname" "worldspawn"\n}')
        self.assertEqual(entities[0]['properties']['url'],'https://example.test/a//b')
    def test_missing_mesh_vertices_are_reported(self):
        self.source.write_text(fixture().replace('v 128 128 256 t 0 1 1',''))
        data=prepare(self.source,self.out);self.assertEqual(data['status'],'prepared_with_issues');self.assertEqual(len(data['issues']),2)
    def test_bezier_curved_grid(self):
        points=[[x,y,4 if x==y==1 else 0] for x in range(3) for y in range(3)]
        verts,faces,uvs=tessellate(3,3,points,[[x/2,y/2] for x in range(3) for y in range(3)],4)
        self.assertEqual(len(verts),25);self.assertEqual(len(faces),16);self.assertEqual(verts[12],[1,1,1]);self.assertEqual(uvs[12],[.5,.5])
    def test_patchdef2_control_grid(self):
        rows=['( '+' '.join('( %s %s 0 %s %s )'%(x,y,x/2,y/2) for y in range(3))+' )' for x in range(3)]
        self.source.write_text('{\n"classname" "worldspawn"\n{\npatchDef2\n{\nstone\n( 3 3 0 0 0 )\n(\n'+'\n'.join(rows)+'\n)\n}\n}\n}\n')
        data=prepare(self.source,self.out,{'patch_subdivisions':4});self.assertFalse(data['issues']);self.assertEqual(data['objects'][0]['triangles'],32)
    def test_source_rotation_and_repeat(self):
        uv=brush_uv((128,0,0),(0,0,1),'128 64 0 0 90 0 lightmap_gray',128)
        self.assertAlmostEqual(uv[0],0);self.assertAlmostEqual(uv[1],2)
    def test_unique_material_asset_names(self):self.assertNotEqual(safe_name('a/b'),safe_name('a_b'))
    def test_gsc_is_audited_and_not_executed(self):
        scripts=self.root/'scripts';scripts.mkdir();(scripts/'teleport.gsc').write_text('''portal()
{
t = getent("portal", "targetname");
d = getent("destination", "targetname");
t waittill("trigger", p);
p setorigin(d.origin);
}
''')
        files,candidates=audit_scripts(scripts);self.assertEqual(len(files),1);self.assertEqual(len(candidates),1)
        data=prepare(self.source,self.out,{'scripts':str(scripts)});self.assertFalse(data['gameplay']['teleports'])
    def test_degenerate_plane_and_reverse_winding(self):
        sides=[(p,'x') for p in BOX]+[([(0,0,0)]*3,'x')]
        v,f,_=reconstruct(sides);self.assertEqual(len(v),8);self.assertEqual(len(f),6)
        v,f,_=reconstruct([(list(reversed(p)),m) for p,m in sides]);self.assertEqual(len(v),8)


if __name__=='__main__':unittest.main()
