import itertools
import math
import unittest
from map_pipeline.box_collision import exact_box


class ExactBoxTests(unittest.TestCase):
    def corners(self):
        return list(itertools.product((-2, 2), (-4, 4), (-1, 1)))

    def test_rotated_translated_box_and_reflection(self):
        angle=math.radians(37)
        points=[(100+x*math.cos(angle)-y*math.sin(angle),
                 -(200+x*math.sin(angle)+y*math.cos(angle)),30+z)
                for x,y,z in self.corners()]
        result=exact_box(points)
        self.assertIsNotNone(result)
        for actual,expected in zip(result['center'],(100,-200,30)):
            self.assertAlmostEqual(actual,expected)
        for actual,expected in zip(sorted(result['size']),(2,4,8)):
            self.assertAlmostEqual(actual,expected)

    def test_sheared_prism_is_not_box(self):
        self.assertIsNone(exact_box([(x+z*.2,y,z) for x,y,z in self.corners()]))

    def test_wedge_missing_or_displaced_corner_is_not_box(self):
        points=self.corners()
        self.assertIsNone(exact_box(points[:-1]))
        points[-1]=(2,4,.9)
        self.assertIsNone(exact_box(points))

    def test_duplicate_face_vertices_and_small_roundoff(self):
        points=self.corners()*3
        points[-1]=(2+1e-6,4,1)
        self.assertIsNotNone(exact_box(points))
