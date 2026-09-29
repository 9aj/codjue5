import sys,unittest,random,math,json
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prepare_descent_chunks import partition,area,read_obj,ROOT

def vertex(x,y,z):return (x,y,z,2*x-y,y+z,0.,0.,1.)

class ChunkTests(unittest.TestCase):
    def test_plane_boundary_not_duplicated(self):
        tri=[vertex(10,0,0),vertex(10,10,0),vertex(10,0,10)]
        pieces=partition(tri,10)
        self.assertEqual(len(pieces),1)
        self.assertAlmostEqual(sum(map(area,pieces)),50)

    def test_negative_cells_uvs_and_winding(self):
        tri=[vertex(-25,-15,0),vertex(25,-15,0),vertex(-25,25,0)]
        pieces=partition(tri,10)
        self.assertAlmostEqual(sum(map(area,pieces)),1000)
        for a,b,c in pieces:
            self.assertGreater((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]),0)
            for v in (a,b,c):
                self.assertAlmostEqual(v[3],2*v[0]-v[1]);self.assertAlmostEqual(v[4],v[1]+v[2])

    def test_random_oblique_triangles(self):
        rng=random.Random(534)
        for _ in range(120):
            tri=[vertex(*(rng.uniform(-40,40) for _ in range(3))) for _ in range(3)]
            pieces=partition(tri,15)
            self.assertAlmostEqual(sum(map(area,pieces)),area(tri),places=7)
            for t in pieces:
                for axis in range(3):self.assertLessEqual(max(v[axis] for v in t)-min(v[axis] for v in t),15+1e-8)

    @unittest.skipUnless((ROOT/'artifacts/descent-chunks-100m/manifest.json').exists(), 'Optional private Descent fixture is not distributed')
    def test_serialized_descent_material_coverage(self):
        folder=ROOT/'artifacts/descent-chunks-100m'
        report=json.loads((folder/'manifest.json').read_text())
        original=defaultdict(float);result=defaultdict(float);count=0
        for mat,tri in read_obj(Path(report['source'])):original[mat]+=area(tri)
        for chunk in report['chunks']:
            faces=read_obj(folder/chunk['file'])
            self.assertEqual(len(faces),chunk['triangles']);count+=len(faces)
            self.assertEqual(set(m for m,t in faces),set(chunk['materials']))
            for mat,tri in faces:
                result[mat]+=area(tri)
                for vertex_ in tri:
                    self.assertTrue(all(math.isfinite(v) for v in vertex_))
                    self.assertTrue(all(abs(v)<=5000.00001 for v in vertex_[:3]))
            if chunk['kind']=='glass':self.assertTrue(set(chunk['materials'])<= {'surface_0019','surface_0022'})
            else:self.assertFalse(set(chunk['materials'])&{'surface_0019','surface_0022'})
        self.assertEqual(count,report['output_triangles'])
        self.assertEqual(set(original),set(result))
        for mat in original:self.assertLess(abs(original[mat]-result[mat]),max(1e-4,original[mat]*1e-9),mat)

if __name__=='__main__':unittest.main()
