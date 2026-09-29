import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prepare_descent_surfaces import islands

def tri(points,material='floor'):
    return material,[tuple(p)+(0,0,0,0,1) for p in points]
class SurfaceTests(unittest.TestCase):
    def test_flat_shared_edge_merges_but_wall_and_disconnected_faces_do_not(self):
        faces=[tri([(0,0,0),(1,0,0),(1,1,0)]),tri([(0,0,0),(1,1,0),(0,1,0)]),tri([(0,0,0),(1,0,0),(1,0,1)]),tri([(5,0,0),(6,0,0),(6,1,0)])]
        groups,_=islands(faces)
        self.assertEqual(sorted(sorted(g) for g in groups),[[0,1],[2],[3]])
    def test_material_boundary_stays_separate(self):
        groups,_=islands([tri([(0,0,0),(1,0,0),(1,1,0)]),tri([(0,0,0),(1,1,0),(0,1,0)],'trim')])
        self.assertEqual(len(groups),2)
if __name__=='__main__':unittest.main()
